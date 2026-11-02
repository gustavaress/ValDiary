"""Classe base de todas as telas."""

import customtkinter as ctk

from app.ui import tema


class TelaBase(ctk.CTkFrame):
    titulo = ""
    subtitulo = ""

    def __init__(self, master, janela):
        super().__init__(master, fg_color="transparent")
        # A janela dá acesso ao repositório e à navegação entre telas.
        self.janela = janela
        self.repositorio = janela.repositorio

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        ctk.CTkLabel(cabecalho, text=self.titulo, font=tema.fonte_titulo(),
                     text_color=tema.COR_TEXTO).pack(anchor="w")
        if self.subtitulo:
            ctk.CTkLabel(cabecalho, text=self.subtitulo, font=tema.fonte_subtitulo(),
                         text_color=tema.COR_TEXTO_SECUNDARIO).pack(anchor="w")

        self.corpo = ctk.CTkFrame(self, fg_color="transparent")
        self.corpo.grid(row=1, column=0, sticky="nsew")

        self.montar()

    def montar(self) -> None:
        """Subclasses criam seus widgets dentro de self.corpo."""

    def ao_exibir(self) -> None:
        """Chamado toda vez que a tela é mostrada. Use para recarregar dados."""


class TelaEmConstrucao(TelaBase):
    """Tela provisória para funcionalidades de etapas futuras."""
    etapa = 0

    def montar(self) -> None:
        caixa = ctk.CTkFrame(self.corpo, fg_color=tema.COR_CARTAO, corner_radius=12,
                             border_width=1, border_color=tema.COR_BORDA)
        caixa.pack(fill="x")
        ctk.CTkLabel(caixa, text="Em construção", font=tema.fonte_secao(),
                     text_color=tema.COR_AVISO).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(caixa, text=f"Esta tela será implementada na Etapa {self.etapa}.",
                     font=tema.fonte_normal(),
                     text_color=tema.COR_TEXTO_SECUNDARIO).pack(anchor="w", padx=20, pady=(0, 18))
