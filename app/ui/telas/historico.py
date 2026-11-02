"""Histórico: tabela de todos os dias com filtros, edição e exclusão."""

from tkinter import messagebox

import customtkinter as ctk

from app.analysis.filtros import filtrar
from app.ui import tema
from app.ui.componentes.botoes import botao_primario, botao_secundario
from app.ui.componentes import SeletorClassificacao, Tabela
from app.ui.formatacao import data_curta, data_extensa, data_tabela, numero
from app.ui.telas.base import TelaBase

# (chave, título, largura em pixels, alinhamento)
COLUNAS = [
    ("data", "Data", 120, "w"),
    ("classificacao", "Dia", 90, "w"),
    ("sono", "Sono", 60, "center"),
    ("partidas", "Partidas", 70, "center"),
    ("resultado", "V / D / E", 80, "center"),
    ("kda", "K / D / A", 100, "center"),
    ("kd", "K/D", 60, "center"),
    ("acs", "ACS", 60, "center"),
    ("hs", "HS%", 60, "center"),
    ("rr", "RR", 55, "center"),
    ("mira", "Mira", 50, "center"),
    ("concentracao", "Conc.", 50, "center"),
]

PERIODOS = {
    "Todo o período": None,
    "Últimos 7 dias": 7,
    "Últimos 30 dias": 30,
    "Últimos 90 dias": 90,
}


def _valores_linha(registro) -> tuple:
    rotina, jogo = registro.rotina, registro.valorant.resumo
    avaliacao = registro.valorant.avaliacao
    classificacao = registro.classificacao
    resultado = "—"
    if jogo.vitorias is not None or jogo.derrotas is not None:
        resultado = f"{jogo.vitorias or 0}V {jogo.derrotas or 0}D"
        if jogo.empates:
            resultado += f" {jogo.empates}E"
    return (
        data_tabela(registro.data),
        tema.ROTULOS_CLASSIFICACAO[classificacao] if classificacao else "—",
        numero(rotina.sono.horas_efetivas, 1, "h"),
        numero(jogo.partidas),
        resultado,
        jogo.kda_texto or "—",
        numero(jogo.kd),
        numero(jogo.acs, 0),
        numero(jogo.hs_pct, 1),
        f"{jogo.rr:+d}" if jogo.rr is not None else "—",
        numero(avaliacao.mira),
        numero(avaliacao.concentracao),
    )


class TelaHistorico(TelaBase):
    titulo = "Histórico"
    subtitulo = "Todos os dias registrados. Clique duas vezes num dia para editar."

    def montar(self) -> None:
        self._registros = []
        self._visiveis: dict[str, object] = {}  # iid da linha -> registro

        self.corpo.grid_columnconfigure(0, weight=1)
        self.corpo.grid_rowconfigure(1, weight=1)
        self._montar_filtros()
        self._montar_tabela()
        self._montar_detalhe()

    # --- Montagem ---------------------------------------------------------

    def _montar_filtros(self) -> None:
        barra = ctk.CTkFrame(self.corpo, fg_color="transparent")
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        linha1 = ctk.CTkFrame(barra, fg_color="transparent")
        linha1.pack(fill="x")
        linha2 = ctk.CTkFrame(barra, fg_color="transparent")
        linha2.pack(fill="x", pady=(8, 0))

        self._filtro_classificacao = SeletorClassificacao(linha1, ao_mudar=lambda _: self._atualizar_tabela())
        self._filtro_classificacao.pack(side="left")

        self._filtro_periodo = ctk.CTkOptionMenu(
            linha1, values=list(PERIODOS), width=160, height=32,
            fg_color=tema.COR_CARTAO, button_color=tema.COR_CARTAO_HOVER,
            button_hover_color=tema.COR_BORDA, dropdown_fg_color=tema.COR_CARTAO,
            command=lambda _: self._atualizar_tabela(),
        )
        self._filtro_periodo.pack(side="left", padx=(12, 0))

        self._busca = ctk.CTkEntry(linha2, width=360, height=32,
                                   placeholder_text="Buscar nas anotações, refeições e agentes...",
                                   fg_color=tema.COR_CARTAO, border_color=tema.COR_BORDA)
        self._busca.pack(side="left")
        self._busca.bind("<KeyRelease>", lambda _: self._atualizar_tabela())

        self._contador = ctk.CTkLabel(linha2, text="", font=tema.fonte_pequena(),
                                      text_color=tema.COR_TEXTO_SECUNDARIO)
        self._contador.pack(side="right")

    def _montar_tabela(self) -> None:
        moldura = ctk.CTkFrame(self.corpo, fg_color=tema.COR_CARTAO, corner_radius=tema.RAIO,
                               border_width=1, border_color=tema.COR_BORDA)
        moldura.grid(row=1, column=0, sticky="nsew")

        self._componente_tabela = Tabela(moldura, COLUNAS)
        self._componente_tabela.pack(fill="both", expand=True, padx=8, pady=8)
        self._tabela = self._componente_tabela.arvore

        self._tabela.bind("<<TreeviewSelect>>", lambda _: self._mostrar_detalhe())
        self._tabela.bind("<Double-1>", lambda _: self._editar())

        self._vazio = ctk.CTkLabel(moldura, text="", font=tema.fonte_normal(),
                                   text_color=tema.COR_TEXTO_SECUNDARIO)

    def _montar_detalhe(self) -> None:
        painel = ctk.CTkFrame(self.corpo, fg_color=tema.COR_CARTAO, corner_radius=tema.RAIO,
                              border_width=1, border_color=tema.COR_BORDA)
        painel.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        painel.grid_columnconfigure(0, weight=1)

        self._detalhe_titulo = ctk.CTkLabel(painel, text="Selecione um dia", font=tema.fonte_secao(),
                                            text_color=tema.COR_TEXTO)
        self._detalhe_titulo.grid(row=0, column=0, sticky="w", padx=18, pady=(14, 4))

        botoes = ctk.CTkFrame(painel, fg_color="transparent")
        botoes.grid(row=0, column=1, sticky="e", padx=18, pady=(14, 4))
        self._botao_editar = botao_primario(botoes, "Editar", self._editar, largura=100, altura=34)
        self._botao_editar.pack(side="left", padx=(0, 8))
        self._botao_excluir = botao_secundario(botoes, "Excluir", self._excluir, largura=100, altura=34)
        self._botao_excluir.pack(side="left")

        self._detalhe_texto = ctk.CTkTextbox(painel, height=90, fg_color=tema.COR_CAMPO,
                                             text_color=tema.COR_TEXTO, font=tema.fonte_normal(),
                                             wrap="word", state="disabled")
        self._detalhe_texto.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 16))

    # --- Dados ------------------------------------------------------------

    def ao_exibir(self) -> None:
        self._registros, _ = self.repositorio.carregar_todos()
        self._atualizar_tabela()

    def _atualizar_tabela(self) -> None:
        filtrados = filtrar(
            self._registros,
            classificacao=self._filtro_classificacao.get(),
            ultimos_dias=PERIODOS[self._filtro_periodo.get()],
            busca=self._busca.get(),
        )

        selecionado = self._tabela.selection()
        self._visiveis = {r.data.isoformat(): r for r in filtrados}
        self._componente_tabela.preencher([_valores_linha(r) for r in filtrados], ids=list(self._visiveis))
        if selecionado and selecionado[0] in self._visiveis:
            self._tabela.selection_set(selecionado[0])

        total = len(self._registros)
        self._contador.configure(text=f"{len(filtrados)} de {total} dias")
        if not filtrados:
            mensagem = ("Nenhum dia registrado ainda." if total == 0
                        else "Nenhum dia corresponde aos filtros.")
            self._vazio.configure(text=mensagem)
            self._vazio.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self._vazio.place_forget()
        self._mostrar_detalhe()

    def _selecionado(self):
        selecao = self._tabela.selection()
        return self._visiveis.get(selecao[0]) if selecao else None

    def _mostrar_detalhe(self) -> None:
        registro = self._selecionado()
        estado = "normal" if registro else "disabled"
        self._botao_editar.configure(state=estado)
        self._botao_excluir.configure(state=estado)

        self._detalhe_texto.configure(state="normal")
        self._detalhe_texto.delete("1.0", "end")
        if registro is None:
            self._detalhe_titulo.configure(text="Selecione um dia")
        else:
            self._detalhe_titulo.configure(text=data_extensa(registro.data))
            partes = []
            agentes = registro.valorant.resumo.agentes
            if agentes:
                texto = ", ".join(f"{nome} ({n})" if n else nome for nome, n in agentes.items())
                partes.append(f"Agentes: {texto}")
            if registro.valorant.notas:
                partes.append(f"Partidas: {registro.valorant.notas}")
            if registro.rotina.observacoes:
                partes.append(f"Dia: {registro.rotina.observacoes}")
            self._detalhe_texto.insert("1.0", "\n".join(partes) or "Sem anotações neste dia.")
        self._detalhe_texto.configure(state="disabled")

    def _editar(self) -> None:
        registro = self._selecionado()
        if registro:
            self.janela.abrir_registro(registro.data)

    def _excluir(self) -> None:
        registro = self._selecionado()
        if registro is None:
            return
        if not messagebox.askyesno(
            "Excluir registro",
            f"Excluir o registro de {data_curta(registro.data)}?\n\n"
            "Uma cópia da semana fica guardada em _backups.",
            icon="warning", parent=self,
        ):
            return
        self.repositorio.excluir_dia(registro.data)
        self.janela.atualizar_ranking_salvo()
        self.ao_exibir()
