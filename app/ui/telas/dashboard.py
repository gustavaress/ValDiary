"""Dashboard: evolução de uma métrica no tempo e sua relação com a classificação do dia."""

from datetime import date

import customtkinter as ctk
import matplotlib.dates as mdates
import pandas as pd
from matplotlib.ticker import FuncFormatter

from app.analysis.dataframe import CLASSIFICACAO_NOTA, filtrar_periodo, registros_para_dataframe
from app.analysis.desempenho import aim_routines_por_semana, desempenho_por, fez_aim_routine
from app.analysis.filtros import filtrar
from app.analysis.metricas import METRICAS
from app.analysis.ranking import evolucao_ranking, rr_por_dia
from app.models.datas import semana_da_data
from app.models.ranking import ELOS, RR_POR_DIVISAO, pontos_totais
from app.ui import tema
from app.ui.componentes import CartaoInfo, Secao, Tabela
from app.ui.componentes.grafico import SERIE_1, Grafico
from app.ui.formatacao import numero, valor_metrica
from app.ui.telas.base import TelaBase

PERIODOS = {"Últimos 30 dias": 30, "Últimos 90 dias": 90, "Todo o período": None}
METRICA_PADRAO = "K/D"
JANELA_MEDIA_MOVEL = "7D"

# Do melhor para o pior, para os gráficos lerem da esquerda para a direita.
ORDEM_CLASSIFICACAO = sorted(CLASSIFICACAO_NOTA, key=CLASSIFICACAO_NOTA.get, reverse=True)


class TelaDashboard(TelaBase):
    titulo = "Dashboard"
    subtitulo = "Evolução do desempenho, ranking, aim routine, mapas e agentes"

    def montar(self) -> None:
        self._metricas = {m.rotulo: m for m in METRICAS}
        self._df = registros_para_dataframe([])
        self._registros, self._definicoes = [], []

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

        self.area = area = ctk.CTkScrollableFrame(self.corpo, fg_color="transparent")
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

        self._grafico_ranking = Grafico(area, "Ranking ao longo do tempo", altura=260)
        self._grafico_ranking.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=6, pady=6)

        aim = ctk.CTkFrame(area, fg_color="transparent")
        aim.grid(row=4, column=0, columnspan=3, sticky="nsew")
        aim.grid_columnconfigure(1, weight=1)
        cartoes_aim = ctk.CTkFrame(aim, fg_color="transparent")
        cartoes_aim.grid(row=0, column=0, sticky="nsew")
        self._cartao_aim_semana = CartaoInfo(cartoes_aim, "Aim routines nesta semana")
        self._cartao_aim_semana.pack(fill="x", padx=6, pady=6)
        self._cartao_aim_periodo = CartaoInfo(cartoes_aim, "Aim routines no período")
        self._cartao_aim_periodo.pack(fill="x", padx=6, pady=6)
        self._grafico_aim = Grafico(aim, "Aim routine por semana", altura=230)
        self._grafico_aim.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)

        tabelas = ctk.CTkFrame(area, fg_color="transparent")
        tabelas.grid(row=5, column=0, columnspan=3, sticky="nsew")
        tabelas.grid_columnconfigure((0, 1), weight=1, uniform="metade")
        colunas = [("nome", "", 110, "w"), ("partidas", "Jogos", 62, "center"), ("winrate", "Winrate", 62, "center"),
                   ("kd", "K/D", 50, "center"), ("acs", "ACS", 50, "center"), ("hs", "HS%", 50, "center"),
                   ("rr", "RR/jogo", 72, "center")]
        self._tabelas_desempenho = {}
        # (atributo da Partida, título, cabeçalho da 1ª coluna)
        grupos = [("mapa", "Desempenho por mapa", "Mapa"), ("agente", "Desempenho por agente", "Agente"),
                  ("conta", "Main x Smurf", "Conta"), ("tier_inimigos", "Por elo dos inimigos", "Elo inimigo")]
        for posicao, (atributo, titulo, cabecalho) in enumerate(grupos):
            secao = Secao(tabelas, titulo, "Só partidas com esse dado registrado. Ordenado pelo mais jogado.")
            secao.grid(row=posicao // 2, column=posicao % 2, sticky="nsew", padx=6, pady=6)
            tabela = Tabela(secao.conteudo, [(c, cabecalho if c == "nome" else t, l, a)
                                             for c, t, l, a in colunas], altura_automatica=True)
            tabela.pack(fill="x")
            self._tabelas_desempenho[atributo] = tabela

    def ao_exibir(self) -> None:
        registros, _ = self.repositorio.carregar_todos()
        self._registros = registros
        self._definicoes = self.janela.definicoes_ranking()
        self._df = registros_para_dataframe(registros, rr_por_dia(registros, self._definicoes))
        self._atualizar()

    def _atualizar(self) -> None:
        metrica = self._metricas[self._menu_metrica.get()]
        df = filtrar_periodo(self._df, PERIODOS[self._menu_periodo.get()])
        serie = df[["data", metrica.chave]].dropna()

        self._atualizar_cartoes(metrica, serie)
        self._desenhar_evolucao(metrica, serie)
        self._desenhar_por_classificacao(metrica, df)
        self._desenhar_distribuicao(df)

        registros = filtrar(self._registros, ultimos_dias=PERIODOS[self._menu_periodo.get()])
        self._desenhar_ranking(registros)
        self._desenhar_aim(registros)
        for atributo, tabela in self._tabelas_desempenho.items():
            tabela.preencher([
                (l.nome, l.partidas, numero(l.winrate_pct, 0, "%"), numero(l.kd), numero(l.acs, 0),
                 numero(l.hs_pct, 1, "%"), f"{l.rr_medio:+.1f}".replace(".", ",") if l.rr_medio is not None else "—")
                for l in desempenho_por(registros, atributo)
            ])

    def _desenhar_ranking(self, registros) -> None:
        grafico = self._grafico_ranking
        grafico.limpar("Ranking ao fim de cada dia (aba Ranking + RR das partidas)")
        datas_periodo = {r.data for r in registros}
        evolucao = [e for e in evolucao_ranking(self._registros, self._definicoes) if e.data in datas_periodo]
        if not evolucao:
            grafico.mostrar_vazio("Defina seu ranking na aba Ranking e registre o RR das partidas.")
            return

        eixo = grafico.eixo
        datas = [pd.Timestamp(e.data) for e in evolucao]
        pontos = [pontos_totais(e.final) for e in evolucao]
        eixo.plot(datas, pontos, color=SERIE_1, linewidth=2, marker="o", markersize=6,
                  markeredgecolor=tema.COR_CARTAO, markeredgewidth=1.5)
        # Uma linha de grade por elo, com o nome do elo no eixo.
        menor, maior = min(pontos) // RR_POR_DIVISAO, max(pontos) // RR_POR_DIVISAO + 1
        eixo.set_yticks([i * RR_POR_DIVISAO for i in range(menor, maior + 1) if i < len(ELOS)])
        eixo.yaxis.set_major_formatter(FuncFormatter(
            lambda valor, _: ELOS[int(valor) // RR_POR_DIVISAO] if 0 <= int(valor) // RR_POR_DIVISAO < len(ELOS) else ""))
        eixo.set_ylim(menor * RR_POR_DIVISAO - 10, maior * RR_POR_DIVISAO + 10)
        eixo.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=8))
        eixo.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
        grafico.definir_dicas([
            (mdates.date2num(d), p, f"{e.data:%d/%m/%Y}\n{e.final.texto}"
                                    + (f"\n{e.variacao:+d} RR no dia" if e.variacao is not None else ""))
            for d, p, e in zip(datas, pontos, evolucao)
        ], so_eixo_x=True)
        grafico.desenhar()

    def _desenhar_aim(self, registros) -> None:
        hoje = date.today()
        semana_atual = semana_da_data(hoje)
        na_semana = sum(1 for r in self._registros if r.semana == semana_atual and fez_aim_routine(r))
        self._cartao_aim_semana.atualizar(f"{na_semana}/7", "dias com aim routine nesta semana")
        no_periodo = sum(1 for r in registros if fez_aim_routine(r))
        self._cartao_aim_periodo.atualizar(str(no_periodo), f"em {len(registros)} dia(s) registrados")

        grafico = self._grafico_aim
        grafico.limpar("Dias com aim routine em cada semana (as últimas 8; a última é a atual)")
        semanas = aim_routines_por_semana(self._registros, hoje)
        if not any(n for _, n in semanas):
            grafico.mostrar_vazio("Nenhuma aim routine registrada nas últimas 8 semanas.")
            return
        eixo = grafico.eixo
        posicoes = range(len(semanas))
        cores = [tema.COR_BORDA_FORTE] * (len(semanas) - 1) + [SERIE_1]  # destaca a semana atual
        eixo.bar(posicoes, [n for _, n in semanas], width=0.6, color=cores)
        eixo.set_xticks(list(posicoes), [rotulo for rotulo, _ in semanas])
        eixo.set_ylim(0, 7.5)
        eixo.yaxis.get_major_locator().set_params(integer=True)
        grafico.definir_dicas([(i, n, f"Semana {rotulo[1:]}: {n} dia(s) com aim routine")
                               for i, (rotulo, n) in enumerate(semanas)])
        grafico.desenhar()

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
