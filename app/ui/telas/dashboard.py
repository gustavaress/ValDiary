"""Dashboard: evolução de uma métrica no tempo e sua relação com a classificação do dia."""

import customtkinter as ctk
import matplotlib.dates as mdates
import pandas as pd

from app.analysis.dataframe import CLASSIFICACAO_NOTA, filtrar_periodo, registros_para_dataframe
from app.analysis.metricas import METRICAS
from app.ui import tema
from app.ui.componentes import CartaoInfo
from app.ui.componentes.grafico import SERIE_1, Grafico
from app.ui.formatacao import valor_metrica
from app.ui.telas.base import TelaBase

PERIODOS = {"Últimos 30 dias": 30, "Últimos 90 dias": 90, "Todo o período": None}
METRICA_PADRAO = "K/D"
JANELA_MEDIA_MOVEL = "7D"

# Do melhor para o pior, para os gráficos lerem da esquerda para a direita.
ORDEM_CLASSIFICACAO = sorted(CLASSIFICACAO_NOTA, key=CLASSIFICACAO_NOTA.get, reverse=True)


class TelaDashboard(TelaBase):
    titulo = "Dashboard"
    subtitulo = "Evolução do seu desempenho e da sua rotina ao longo do tempo"

    def montar(self) -> None:
        self._metricas = {m.rotulo: m for m in METRICAS}
        self._df = registros_para_dataframe([])

        filtros = ctk.CTkFrame(self.corpo, fg_color="transparent")
        filtros.pack(fill="x", pady=(0, 10))
        estilo_menu = dict(height=32, fg_color=tema.COR_CARTAO, button_color=tema.COR_CARTAO_HOVER,
                           button_hover_color=tema.COR_BORDA, dropdown_fg_color=tema.COR_CARTAO,
                           command=lambda _: self._atualizar())
        self._menu_metrica = ctk.CTkOptionMenu(filtros, values=list(self._metricas), width=260, **estilo_menu)
        self._menu_metrica.set(METRICA_PADRAO)
        self._menu_metrica.pack(side="left")
        self._menu_periodo = ctk.CTkOptionMenu(filtros, values=list(PERIODOS), width=160, **estilo_menu)
        self._menu_periodo.pack(side="left", padx=(10, 0))

        area = ctk.CTkScrollableFrame(self.corpo, fg_color="transparent")
        area.pack(fill="both", expand=True)
        area.grid_columnconfigure((0, 1, 2), weight=1, uniform="col")

        self._cartao_media = CartaoInfo(area, "Média no período")
        self._cartao_recente = CartaoInfo(area, "Média dos últimos 7 dias")
        self._cartao_dias = CartaoInfo(area, "Dias com este dado")
        for coluna, cartao in enumerate((self._cartao_media, self._cartao_recente, self._cartao_dias)):
            cartao.grid(row=0, column=coluna, sticky="nsew", padx=6, pady=6)

        self._grafico_tempo = Grafico(area, "Evolução no tempo", altura=280)
        self._grafico_tempo.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=6, pady=6)

        inferior = ctk.CTkFrame(area, fg_color="transparent")
        inferior.grid(row=2, column=0, columnspan=3, sticky="nsew")
        inferior.grid_columnconfigure((0, 1), weight=1, uniform="metade")
        self._grafico_classificacao = Grafico(inferior, "Média por classificação do dia", altura=240)
        self._grafico_classificacao.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self._grafico_distribuicao = Grafico(inferior, "Dias por classificação", altura=240)
        self._grafico_distribuicao.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)

    def ao_exibir(self) -> None:
        registros, _ = self.repositorio.carregar_todos()
        self._df = registros_para_dataframe(registros, self.janela.rr_por_dia(registros))
        self._atualizar()

    def _atualizar(self) -> None:
        metrica = self._metricas[self._menu_metrica.get()]
        df = filtrar_periodo(self._df, PERIODOS[self._menu_periodo.get()])
        serie = df[["data", metrica.chave]].dropna()

        self._atualizar_cartoes(metrica, serie)
        self._desenhar_evolucao(metrica, serie)
        self._desenhar_por_classificacao(metrica, df)
        self._desenhar_distribuicao(df)

    # --- Partes -----------------------------------------------------------

    def _atualizar_cartoes(self, metrica, serie) -> None:
        valores = serie[metrica.chave]
        self._cartao_media.atualizar(valor_metrica(metrica, valores.mean()), metrica.rotulo)
        recentes = serie[serie["data"] >= serie["data"].max() - pd.Timedelta(days=6)] if not serie.empty else serie
        self._cartao_recente.atualizar(valor_metrica(metrica, recentes[metrica.chave].mean()),
                                       "a partir do último registro")
        self._cartao_dias.atualizar(str(len(serie)), "dias com este campo preenchido")

    def _desenhar_evolucao(self, metrica, serie) -> None:
        grafico = self._grafico_tempo
        grafico.limpar(metrica.rotulo)
        if serie.empty:
            grafico.mostrar_vazio("Nenhum dado desta métrica no período.")
            return

        eixo = grafico.eixo
        datas, valores = serie["data"], serie[metrica.chave]
        media_movel = serie.set_index("data")[metrica.chave].rolling(JANELA_MEDIA_MOVEL, min_periods=1).mean()

        eixo.plot(datas, valores, linestyle="none", marker="o", markersize=6, color=SERIE_1, alpha=0.45,
                  markeredgecolor=tema.COR_CARTAO, markeredgewidth=1.5, label="Valor do dia")
        if len(serie) >= 3:
            eixo.plot(media_movel.index, media_movel.values, color=SERIE_1, linewidth=2,
                      label="Média móvel (7 dias)")
        grafico.legenda()

        eixo.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=8))
        eixo.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
        if metrica.nota:
            eixo.set_ylim(0.5, 10.5)
        if metrica.hora:
            grafico.eixo_y_em_horas()

        pontos = []
        for data, valor in zip(datas, valores):
            texto = f"{data:%d/%m/%Y}\n{metrica.rotulo}: {valor_metrica(metrica, valor)}"
            if len(serie) >= 3:
                texto += f"\nMédia 7 dias: {valor_metrica(metrica, media_movel.loc[data])}"
            pontos.append((mdates.date2num(data), valor, texto))
        grafico.definir_dicas(pontos, so_eixo_x=True)
        grafico.desenhar()

    def _desenhar_por_classificacao(self, metrica, df) -> None:
        grafico = self._grafico_classificacao
        grupos = df.dropna(subset=[metrica.chave]).groupby("classificacao")[metrica.chave].agg(["mean", "count"])
        grupos = grupos.reindex([c for c in ORDEM_CLASSIFICACAO if c in grupos.index])
        grafico.limpar(f"{metrica.rotulo} médio(a) em cada tipo de dia  ·  n = nº de dias")
        if grupos.empty:
            grafico.mostrar_vazio("Classifique seus dias para ver esta comparação.")
            return

        eixo = grafico.eixo
        rotulos = [f"{tema.ROTULOS_CLASSIFICACAO[c]}\nn={int(n)}" for c, n in zip(grupos.index, grupos["count"])]
        posicoes = range(len(grupos))
        eixo.bar(posicoes, grupos["mean"], width=0.6, color=SERIE_1)
        eixo.set_xticks(list(posicoes), rotulos)
        if metrica.nota:
            eixo.set_ylim(0, 10.5)
        if metrica.hora:
            grafico.eixo_y_em_horas()
            eixo.set_ylim(grupos["mean"].min() - 1, grupos["mean"].max() + 1)
        grafico.definir_dicas([
            (i, media, f"{tema.ROTULOS_CLASSIFICACAO[c]}: {valor_metrica(metrica, media)}\n{int(n)} dia(s)")
            for i, (c, media, n) in enumerate(zip(grupos.index, grupos["mean"], grupos["count"]))
        ])
        grafico.desenhar()

    def _desenhar_distribuicao(self, df) -> None:
        grafico = self._grafico_distribuicao
        contagem = df["classificacao"].value_counts().reindex(ORDEM_CLASSIFICACAO, fill_value=0)
        sem_classificacao = int(df["classificacao"].isna().sum())
        grafico.limpar(f"{sem_classificacao} dia(s) sem classificação no período" if sem_classificacao else "")
        if contagem.sum() == 0:
            grafico.mostrar_vazio("Nenhum dia classificado no período.")
            return

        eixo = grafico.eixo
        posicoes = range(len(contagem))
        eixo.bar(posicoes, contagem.values, width=0.6, color=SERIE_1)
        eixo.set_xticks(list(posicoes), [tema.ROTULOS_CLASSIFICACAO[c] for c in contagem.index])
        eixo.yaxis.get_major_locator().set_params(integer=True)
        total = int(contagem.sum())
        grafico.definir_dicas([
            (i, n, f"{tema.ROTULOS_CLASSIFICACAO[c]}: {int(n)} dia(s) ({n / total:.0%})")
            for i, (c, n) in enumerate(contagem.items())
        ])
        grafico.desenhar()
