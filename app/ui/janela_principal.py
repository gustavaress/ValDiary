"""Janela principal: menu lateral + área onde as telas são exibidas."""

import os
from datetime import date
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from app import config
from app.storage import RepositorioDiario
from app.storage.rascunho import apagar_rascunho, carregar_rascunho
from app.storage.reorganizacao import reorganizar_se_preciso
from app.ui import tema
from app.ui.formatacao import data_curta
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
    ("registro", "Registro diário", TelaRegistro),
    ("historico", "Histórico", TelaHistorico),
    ("dashboard", "Dashboard", TelaDashboard),
    ("comparacao", "Comparação", TelaComparacao),
    ("import_export", "Importar / Exportar", TelaImportExport),
]


class JanelaPrincipal(ctk.CTk):
    def __init__(self, repositorio: RepositorioDiario,
                 arquivo_rascunho: Path = config.ARQUIVO_RASCUNHO):
        super().__init__(fg_color=tema.COR_FUNDO)
        self.repositorio = repositorio
        self.arquivo_rascunho = arquivo_rascunho
        # Antes de qualquer tela ler os dados: ajusta arquivos do formato antigo
        # de semanas (segunda a domingo) para o atual (domingo a sábado).
        self._reorganizacao = reorganizar_se_preciso(repositorio)

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
        self.protocol("WM_DELETE_WINDOW", self._ao_fechar)
        # Espera a janela aparecer antes de mostrar avisos.
        self.after(300, self._verificacoes_iniciais)

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

    def abrir_registro(self, data: date) -> None:
        """Abre a tela de registro já na data indicada."""
        self.mostrar_tela("registro")
        self._telas["registro"].abrir_registro(data)

    def _ao_fechar(self) -> None:
        # Garante que o que foi digitado e ainda não salvo vire rascunho.
        if "registro" in self._telas:
            self._telas["registro"].salvar_rascunho_agora()
        self.destroy()

    # --- Avisos -----------------------------------------------------------

    def _verificacoes_iniciais(self) -> None:
        self._avisar_reorganizacao()
        self._avisar_arquivos_com_problema()
        self._oferecer_rascunho()

    def _avisar_reorganizacao(self) -> None:
        resultado = self._reorganizacao
        if resultado is None or (resultado.dias == 0 and not resultado.ignorados):
            return
        texto = (f"A semana agora começa no domingo. Seus {resultado.dias} dias registrados foram "
                 f"redistribuídos nos arquivos semanais novos.\n\n"
                 f"Uma cópia dos arquivos antigos foi guardada em:\n{resultado.backup}")
        if resultado.ignorados:
            lista = "\n".join(f"• {a.parent.name}/{a.name}" for a in resultado.ignorados)
            texto += f"\n\nNão foi possível ler (ficaram só no backup):\n{lista}"
        messagebox.showinfo("Dados reorganizados", texto, parent=self)

    def _oferecer_rascunho(self) -> None:
        rascunho = carregar_rascunho(self.arquivo_rascunho)
        if rascunho is None:
            return
        formulario = rascunho["formulario"]
        try:
            data = date.fromisoformat(formulario["data"])
        except (KeyError, TypeError, ValueError):
            apagar_rascunho(self.arquivo_rascunho)
            return
        if messagebox.askyesno(
            "Registro não salvo",
            f"Existe um registro de {data_curta(data)} que não foi salvo "
            "(o app foi fechado antes).\n\nDeseja recuperá-lo?",
            parent=self,
        ):
            self.mostrar_tela("registro")
            self._telas["registro"].recuperar_rascunho(formulario)
        else:
            apagar_rascunho(self.arquivo_rascunho)

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
