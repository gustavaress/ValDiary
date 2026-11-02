"""Janela principal: menu lateral + área onde as telas são exibidas."""

import os
from tkinter import messagebox

import customtkinter as ctk

from app import config
from app.storage import RepositorioDiario
from app.ui import tema
from app.ui.telas import (
    TelaComparacao,
    TelaDashboard,
    TelaHistorico,
    TelaImportExport,
    TelaInicio,
    TelaRegistro,
)
from app.ui.telas.base import TelaBase

# (chave, rótulo no menu, classe da tela). A ordem aqui é a ordem do menu.
TELAS = [
    ("inicio", "Início", TelaInicio),
    ("registro", "Novo registro", TelaRegistro),
    ("historico", "Histórico", TelaHistorico),
    ("dashboard", "Dashboard", TelaDashboard),
    ("comparacao", "Comparação", TelaComparacao),
    ("import_export", "Importar / Exportar", TelaImportExport),
]


class JanelaPrincipal(ctk.CTk):
    def __init__(self, repositorio: RepositorioDiario):
        super().__init__(fg_color=tema.COR_FUNDO)
        self.repositorio = repositorio

        self.title(config.NOME_APP)
        self.geometry("1200x760")
        self.minsize(1000, 650)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._telas: dict[str, TelaBase] = {}
        self._botoes: dict[str, ctk.CTkButton] = {}
        self._tela_atual: str | None = None

        self._criar_menu()
        self._area = ctk.CTkFrame(self, fg_color="transparent")
        self._area.grid(row=0, column=1, sticky="nsew", padx=32, pady=28)
        self._area.grid_columnconfigure(0, weight=1)
        self._area.grid_rowconfigure(0, weight=1)

        self.mostrar_tela("inicio")
        # Espera a janela aparecer antes de mostrar avisos.
        self.after(300, self._avisar_arquivos_com_problema)

    # --- Menu lateral -----------------------------------------------------

    def _criar_menu(self) -> None:
        menu = ctk.CTkFrame(self, fg_color=tema.COR_MENU, corner_radius=0, width=230)
        menu.grid(row=0, column=0, sticky="nsw")
        menu.grid_propagate(False)
        menu.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(menu, text="DIÁRIO DE\nPERFORMANCE", justify="left",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=tema.COR_TEXTO).grid(row=0, column=0, sticky="w", padx=24, pady=(28, 0))
        ctk.CTkFrame(menu, height=3, width=40, fg_color=tema.COR_DESTAQUE,
                     corner_radius=0).grid(row=1, column=0, sticky="w", padx=24, pady=(10, 28))

        for linha, (chave, rotulo, _) in enumerate(TELAS, start=2):
            botao = ctk.CTkButton(
                menu, text=rotulo, anchor="w", height=42, corner_radius=8,
                font=tema.fonte_normal(), fg_color="transparent",
                text_color=tema.COR_TEXTO_SECUNDARIO, hover_color=tema.COR_CARTAO,
                command=lambda c=chave: self.mostrar_tela(c),
            )
            botao.grid(row=linha, column=0, sticky="ew", padx=12, pady=2)
            self._botoes[chave] = botao

        # Empurra o rodapé para baixo.
        menu.grid_rowconfigure(len(TELAS) + 2, weight=1)

        ctk.CTkButton(
            menu, text="Abrir pasta de dados", height=34, font=tema.fonte_pequena(),
            fg_color="transparent", border_width=1, border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO_SECUNDARIO, hover_color=tema.COR_CARTAO,
            command=lambda: os.startfile(self.repositorio.pasta_dados),
        ).grid(row=len(TELAS) + 3, column=0, sticky="ew", padx=16, pady=(0, 20))

    # --- Navegação --------------------------------------------------------

    def mostrar_tela(self, chave: str) -> None:
        # As telas são criadas só na primeira vez que são abertas (mais rápido para iniciar).
        if chave not in self._telas:
            classe = next(c for k, _, c in TELAS if k == chave)
            tela = classe(self._area, self)
            tela.grid(row=0, column=0, sticky="nsew")
            self._telas[chave] = tela

        tela = self._telas[chave]
        tela.tkraise()
        tela.ao_exibir()
        self._tela_atual = chave

        for k, botao in self._botoes.items():
            ativo = k == chave
            botao.configure(
                fg_color=tema.COR_CARTAO if ativo else "transparent",
                text_color=tema.COR_DESTAQUE if ativo else tema.COR_TEXTO_SECUNDARIO,
            )

    # --- Avisos -----------------------------------------------------------

    def _avisar_arquivos_com_problema(self) -> None:
        _, problemas = self.repositorio.carregar_todos()
        if not problemas:
            return
        lista = "\n".join(f"• {p.caminho.parent.name}/{p.caminho.name}: {p.motivo}" for p in problemas)
        messagebox.showwarning(
            "Arquivos com problema",
            "Alguns arquivos de dados não puderam ser lidos e foram ignorados:\n\n"
            f"{lista}\n\n"
            "Eles NÃO foram alterados. Você pode corrigi-los manualmente ou "
            "restaurar uma versão da pasta _backups.",
            parent=self,
        )
