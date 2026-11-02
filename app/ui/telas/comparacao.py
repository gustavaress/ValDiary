"""Comparação: o que diferencia os dias bons dos dias ruins."""

import customtkinter as ctk

from app.analysis.comparacao import (
    MIN_DIAS_CORRELACAO,
    MIN_DIAS_POR_GRUPO,
    comparar_grupos,
    correlacoes,
    frequencias_habitos,
    separar_grupos,
)
from app.analysis.dataframe import filtrar_periodo, registros_para_dataframe
from app.analysis.filtros import filtrar
from app.ui import tema
from app.ui.componentes import CartaoInfo, Secao, Tabela
from app.ui.componentes.grafico import SERIE_1, SERIE_2, Grafico
from app.ui.formatacao import numero, valor_metrica
from app.ui.telas.base import TelaBase

PERIODOS = {"Todo o período": None, "Últimos 90 dias": 90, "Últimos 30 dias": 30}


def _media_com_n(metrica, media, n) -> str:
    return f"{valor_metrica(metrica, media)}  (n={n})" if n else "—"


def _diferenca(linha) -> str:
    diferenca = linha.diferenca
    if diferenca is None:
        return "—"
    sinal = "+" if diferenca > 0 else "−" if diferenca < 0 else ""
    if linha.metrica.hora:
        minutos = round(abs(diferenca) * 60)
        return f"{sinal}{minutos // 60}h{minutos % 60:02d}"
    return sinal + numero(abs(diferenca), linha.metrica.casas, linha.metrica.sufixo)


def _percentual(dias: int, total: int) -> str:
    return f"{dias / total:.0%}  ({dias}/{total})" if total else "—"


class TelaComparacao(TelaBase):
    titulo = "Comparação"
    subtitulo = "Dias bons (Excelente + Bom) × dias ruins (Ruim + Péssimo): o que muda?"

    def montar(self) -> None:
        self._registros = []

        topo = ctk.CTkFrame(self.corpo, fg_color="transparent")
        topo.pack(fill="x", pady=(0, 10))
        self._menu_periodo = ctk.CTkOptionMenu(
            topo, values=list(PERIODOS), width=160, height=32, fg_color=tema.COR_CARTAO,
            button_color=tema.COR_CARTAO_HOVER, button_hover_color=tema.COR_BORDA,
            dropdown_fg_color=tema.COR_CARTAO, command=lambda _: self._atualizar(),
        )
        self._menu_periodo.pack(side="left")
        ctk.CTkLabel(topo, text="Associações observadas nos seus registros, não relações de causa e efeito.",
                     font=tema.fonte_pequena(), text_color=tema.COR_TEXTO_SECUNDARIO).pack(side="left", padx=14)

        area = ctk.CTkScrollableFrame(self.corpo, fg_color="transparent")
        area.pack(fill="both", expand=True)
        area.grid_columnconfigure((0, 1, 2), weight=1, uniform="col")

        self._cartao_bons = CartaoInfo(area, "Dias bons")
        self._cartao_ruins = CartaoInfo(area, "Dias ruins")
        self._cartao_outros = CartaoInfo(area, "Fora da comparação")
        for coluna, cartao in enumerate((self._cartao_bons, self._cartao_ruins, self._cartao_outros)):
            cartao.grid(row=0, column=coluna, sticky="nsew", padx=6, pady=6)

        self._aviso = ctk.CTkFrame(area, fg_color=tema.COR_CARTAO, corner_radius=12,
                                   border_width=1, border_color=tema.COR_AVISO)
        self._texto_aviso = ctk.CTkLabel(self._aviso, text="", justify="left", font=tema.fonte_normal(),
                                         text_color=tema.COR_AVISO, wraplength=820)
        self._texto_aviso.pack(anchor="w", padx=18, pady=12)

        self._grafico = Grafico(area, "Notas de 1 a 10: dias bons × dias ruins", altura=400)
        self._grafico.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=6, pady=6)

        secao = Secao(area, "Todas as métricas",
                      f"Média em cada grupo e n = nº de dias com o dado. "
                      f"Com menos de {MIN_DIAS_POR_GRUPO} dias em algum grupo, a diferença pode ser acaso.")
        secao.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=6, pady=6)
        self._tabela_metricas = Tabela(secao.conteudo, [
            ("metrica", "Métrica", 220, "w"), ("bons", "Dias bons", 130, "center"),
            ("ruins", "Dias ruins", 130, "center"), ("diferenca", "Diferença", 90, "center"),
            ("confianca", "Dados", 110, "center"),
        ], altura_automatica=True)
        self._tabela_metricas.pack(fill="x")

        secao = Secao(area, "Correlação com a classificação do dia",
                      "ρ (Spearman) vai de −1 a +1: perto de 0 = sem relação; positivo = acompanha dias "
                      f"melhores; negativo = acompanha dias piores. Exige {MIN_DIAS_CORRELACAO}+ dias classificados.")
        secao.grid(row=4, column=0, columnspan=3, sticky="nsew", padx=6, pady=6)
        self._tabela_correlacoes = Tabela(secao.conteudo, [
            ("metrica", "Métrica", 220, "w"), ("rho", "ρ", 60, "center"), ("n", "Dias", 60, "center"),
            ("forca", "Força", 100, "center"), ("leitura", "Leitura", 340, "w"),
        ], altura_automatica=True)
        self._tabela_correlacoes.pack(fill="x")

        secao = Secao(area, "Hábitos e escolhas frequentes",
                      "Em que porcentagem dos dias bons e dos dias ruins cada item apareceu.")
        secao.grid(row=5, column=0, columnspan=3, sticky="nsew", padx=6, pady=6)
        self._tabela_habitos = Tabela(secao.conteudo, [
            ("item", "Item", 280, "w"), ("bons", "Nos dias bons", 160, "center"),
            ("ruins", "Nos dias ruins", 160, "center"),
        ], altura_automatica=True)
        self._tabela_habitos.pack(fill="x")
        self._habitos_vazio = ctk.CTkLabel(secao.conteudo, text="", font=tema.fonte_pequena(),
                                           text_color=tema.COR_TEXTO_SECUNDARIO)
        self._habitos_vazio.pack(anchor="w", pady=(6, 0))

    def ao_exibir(self) -> None:
        self._registros, _ = self.repositorio.carregar_todos()
        self._atualizar()

    def _atualizar(self) -> None:
        dias = PERIODOS[self._menu_periodo.get()]
        registros = filtrar(self._registros, ultimos_dias=dias)
        df = filtrar_periodo(registros_para_dataframe(registros), dias)
        bons, ruins = separar_grupos(df)
        n_bons, n_ruins = len(bons), len(ruins)

        self._cartao_bons.atualizar(str(n_bons), "Excelente + Bom")
        self._cartao_ruins.atualizar(str(n_ruins), "Ruim + Péssimo")
        self._cartao_outros.atualizar(str(len(df) - n_bons - n_ruins), "dias normais ou sem classificação")
        self._atualizar_aviso(n_bons, n_ruins)

        linhas = comparar_grupos(df)
        self._desenhar_grafico([l for l in linhas if l.metrica.nota])
        self._tabela_metricas.preencher([
            (l.metrica.rotulo, _media_com_n(l.metrica, l.media_bons, l.n_bons),
             _media_com_n(l.metrica, l.media_ruins, l.n_ruins), _diferenca(l),
             "ok" if l.suficiente else "poucos dados")
            for l in linhas if l.n_bons or l.n_ruins
        ])
        self._tabela_correlacoes.preencher([
            (c.metrica.rotulo, numero(c.rho) if c.rho is not None else "—", c.n,
             c.forca if c.suficiente else "—", c.leitura)
            for c in correlacoes(df) if c.n
        ])
        habitos = frequencias_habitos(registros)
        self._tabela_habitos.preencher([
            (h.item, _percentual(h.dias_bons, h.total_bons), _percentual(h.dias_ruins, h.total_ruins))
            for h in habitos
        ])
        self._habitos_vazio.configure(
            text="" if habitos else "Nenhum item (bebida, medicamento, agente...) apareceu em 2 ou mais dias ainda.")

    def _atualizar_aviso(self, n_bons: int, n_ruins: int) -> None:
        if n_bons >= MIN_DIAS_POR_GRUPO and n_ruins >= MIN_DIAS_POR_GRUPO:
            self._aviso.grid_forget()
            return
        self._texto_aviso.configure(text=(
            f"⚠  Ainda há poucos dias para comparar ({n_bons} bons e {n_ruins} ruins). "
            f"Com menos de {MIN_DIAS_POR_GRUPO} dias em cada grupo, as diferenças abaixo podem ser apenas "
            "acaso. Continue registrando e classificando seus dias."
        ))
        self._aviso.grid(row=1, column=0, columnspan=3, sticky="ew", padx=6, pady=6)

    def _desenhar_grafico(self, linhas) -> None:
        grafico = self._grafico
        grafico.limpar("Média de cada nota nos dois grupos. Passe o mouse nas barras para ver o nº de dias.")
        linhas = [l for l in linhas if l.media_bons is not None or l.media_ruins is not None]
        if not linhas:
            grafico.mostrar_vazio("Classifique dias como bons e ruins e preencha as notas para comparar.")
            return

        # A altura acompanha a quantidade de notas, para as barras não ficarem gigantes.
        grafico.definir_altura(90 + 44 * len(linhas))
        eixo = grafico.eixo
        altura = 0.38
        posicoes = list(range(len(linhas)))
        pontos = []
        for deslocamento, cor, rotulo, atributo_media, atributo_n in (
            (-altura / 2, SERIE_1, "Dias bons", "media_bons", "n_bons"),
            (altura / 2, SERIE_2, "Dias ruins", "media_ruins", "n_ruins"),
        ):
            medias = [getattr(l, atributo_media) or 0 for l in linhas]
            y = [p + deslocamento for p in posicoes]
            eixo.barh(y, medias, height=altura, color=cor, label=rotulo)
            for l, yi, media in zip(linhas, y, medias):
                if getattr(l, atributo_media) is None:
                    continue
                # Rótulo direto no fim da barra (texto neutro, a cor fica na barra).
                eixo.text(media + 0.15, yi, numero(media, 1), va="center", fontsize=8,
                          color=tema.COR_TEXTO_SECUNDARIO)
                pontos.append((media, yi, f"{rotulo} · {l.metrica.rotulo}\n"
                                          f"Média {numero(media, 1)}  ·  {getattr(l, atributo_n)} dia(s)"))

        eixo.set_yticks(posicoes, [l.metrica.rotulo for l in linhas])
        eixo.invert_yaxis()
        eixo.set_xlim(0, 10.8)
        eixo.grid(axis="y", visible=False)
        eixo.grid(axis="x", color="#253444", linewidth=0.8)
        eixo.spines["bottom"].set_visible(False)
        grafico.legenda()
        grafico.definir_dicas(pontos)
        grafico.desenhar()
