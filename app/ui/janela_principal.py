"""Janela principal: menu lateral + área onde as telas são exibidas."""

import os
from datetime import date
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from app import config
from app.analysis.ranking import ranking_atual_com_data, rr_por_dia
from app.storage import ArquivoCorrompidoError, RepositorioDiario
from app.storage.rascunho import apagar_rascunho, carregar_rascunho
from app.storage.reorganizacao import reorganizar_se_preciso
from app.storage.repositorio_aim import RepositorioAim
from app.storage.repositorio_ranking import RankingSalvo, RepositorioRanking
from app.ui import tema
from app.ui.componentes.botoes import botao_secundario
from app.ui.logo import desenhar_logo
from app.ui.formatacao import data_curta
from app.ui.telas import (
    TelaComparacao,
    TelaDashboard,
    TelaHistorico,
    TelaImportExport,
    TelaInicio,
    TelaRanking,
    TelaRegistro,
)
from app.ui.telas.base import TelaBase

# (chave, rótulo no menu, classe da tela). A ordem aqui é a ordem do menu.
TELAS = [
    ("inicio", "Início", TelaInicio),
    ("registro", "Registro diário", TelaRegistro),
    ("ranking", "Ranking", TelaRanking),
    ("historico", "Histórico", TelaHistorico),
    ("dashboard", "Dashboard", TelaDashboard),
    ("comparacao", "Comparação", TelaComparacao),
    ("import_export", "Importar / Exportar", TelaImportExport),
]


class _ItemMenu(ctk.CTkFrame):
    """Item do menu lateral: barra de destaque + número + nome, tudo clicável."""

    def __init__(self, master, numero: int, rotulo: str, ao_clicar):
        super().__init__(master, fg_color="transparent", corner_radius=0, height=46, cursor="hand2")
        self.pack_propagate(False)
        self._ativo = False
        self._barra = ctk.CTkFrame(self, width=3, corner_radius=0, fg_color="transparent")
        self._barra.pack(side="left", fill="y")
        self._numero = ctk.CTkLabel(self, text=f"{numero:02d}", width=34, font=tema.fonte_display(17),
                                    text_color=tema.COR_TEXTO_FRACO)
        self._numero.pack(side="left", padx=(16, 4))
        self._rotulo = ctk.CTkLabel(self, text=rotulo.upper(), font=tema.fonte_display(21),
                                    text_color=tema.COR_TEXTO_SECUNDARIO)
        self._rotulo.pack(side="left")
        for widget in (self, self._numero, self._rotulo):
            widget.bind("<Button-1>", lambda _: ao_clicar())
            widget.bind("<Enter>", lambda _: self._pintar(passando=True))
            widget.bind("<Leave>", lambda _: self._pintar())

    def ativar(self, ativo: bool) -> None:
        self._ativo = ativo
        self._pintar()

    def _pintar(self, passando: bool = False) -> None:
        if self._ativo:
            self.configure(fg_color=tema.COR_DESTAQUE_SUAVE)
            self._barra.configure(fg_color=tema.COR_DESTAQUE)
            self._numero.configure(text_color=tema.COR_DESTAQUE)
            self._rotulo.configure(text_color=tema.COR_TEXTO)
        else:
            self.configure(fg_color=tema.COR_CARTAO if passando else "transparent")
            self._barra.configure(fg_color="transparent")
            self._numero.configure(text_color=tema.COR_TEXTO_FRACO)
            self._rotulo.configure(text_color=tema.COR_TEXTO if passando else tema.COR_TEXTO_SECUNDARIO)


class JanelaPrincipal(ctk.CTk):
    def __init__(self, repositorio: RepositorioDiario,
                 arquivo_rascunho: Path = config.ARQUIVO_RASCUNHO):
        # Fontes e tema precisam estar prontos antes de qualquer widget existir.
        tema.carregar_fontes()
        tema.aplicar_tema()
        super().__init__(fg_color=tema.COR_FUNDO)
        icone = config.PASTA_RECURSOS / "icone.ico"
        if icone.exists():
            self.iconbitmap(str(icone))
        self.repositorio = repositorio
        self.arquivo_rascunho = arquivo_rascunho
        self.repositorio_ranking = RepositorioRanking(repositorio.pasta_dados, repositorio.pasta_backups)
        self.repositorio_aim = RepositorioAim(repositorio.pasta_dados)
        # Antes de qualquer tela ler os dados: ajusta arquivos do formato antigo
        # de semanas (segunda a domingo) para o atual (domingo a sábado).
        self._reorganizacao = reorganizar_se_preciso(repositorio)
        self.atualizar_ranking_salvo()

        self.title(config.NOME_APP)
        self.geometry("1360x820")
        self.minsize(1100, 680)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._telas: dict[str, TelaBase] = {}
        self._botoes: dict[str, _ItemMenu] = {}
        self._tela_atual: str | None = None

        self._criar_menu()
        self._area = ctk.CTkFrame(self, fg_color="transparent")
        self._area.grid(row=0, column=1, sticky="nsew", padx=36, pady=(26, 22))
        self._area.grid_columnconfigure(0, weight=1)
        self._area.grid_rowconfigure(0, weight=1)

        self.mostrar_tela("inicio")
        self.protocol("WM_DELETE_WINDOW", self._ao_fechar)
        # Espera a janela aparecer antes de mostrar avisos.
        self.after(300, self._verificacoes_iniciais)

    # --- Menu lateral -----------------------------------------------------

    def _criar_menu(self) -> None:
        menu = ctk.CTkFrame(self, fg_color=tema.COR_MENU, corner_radius=0, width=240)
        menu.grid(row=0, column=0, sticky="nsw")
        menu.grid_propagate(False)
        menu.grid_columnconfigure(0, weight=1)
        # Linha fina separando o menu do conteúdo.
        ctk.CTkFrame(self, width=1, corner_radius=0, fg_color=tema.COR_BORDA).grid(row=0, column=0, sticky="nse")

        marca = ctk.CTkFrame(menu, fg_color="transparent")
        marca.grid(row=0, column=0, sticky="w", padx=22, pady=(26, 0))
        self._logo = ctk.CTkImage(desenhar_logo(96), size=(38, 38))
        ctk.CTkLabel(marca, text="", image=self._logo, width=38).pack(side="left", padx=(0, 10))
        textos = ctk.CTkFrame(marca, fg_color="transparent")
        textos.pack(side="left")
        ctk.CTkLabel(textos, text="VALDIARY", font=tema.fonte_display(34), height=32,
                     text_color=tema.COR_TEXTO).pack(anchor="w")
        ctk.CTkLabel(textos, text="DIÁRIO DE PERFORMANCE", font=tema.fonte_rotulo(), height=14,
                     text_color=tema.COR_TEXTO_FRACO).pack(anchor="w")

        ctk.CTkFrame(menu, height=1, corner_radius=0, fg_color=tema.COR_BORDA).grid(
            row=1, column=0, sticky="ew", padx=22, pady=(22, 16))

        for linha, (numero, (chave, rotulo, _)) in enumerate(enumerate(TELAS, start=1), start=2):
            item = _ItemMenu(menu, numero, rotulo, lambda c=chave: self.mostrar_tela(c))
            item.grid(row=linha, column=0, sticky="ew", pady=1)
            self._botoes[chave] = item

        # Empurra o rodapé para baixo.
        menu.grid_rowconfigure(len(TELAS) + 2, weight=1)

        rodape = ctk.CTkFrame(menu, fg_color="transparent")
        rodape.grid(row=len(TELAS) + 3, column=0, sticky="ew", padx=18, pady=(0, 18))
        botao_secundario(rodape, "Abrir pasta de dados", lambda: os.startfile(self.repositorio.pasta_dados),
                         altura=34).pack(fill="x")
        ctk.CTkLabel(rodape, text=f"VERSÃO {config.VERSAO_APP}", font=tema.fonte_rotulo(),
                     text_color=tema.COR_TEXTO_FRACO).pack(anchor="w", pady=(10, 0))

    def numero_da_tela(self, classe) -> int | None:
        """Posição da tela no menu (usada no cabeçalho: // 02 · REGISTRO)."""
        return next((i for i, (_, _, c) in enumerate(TELAS, start=1) if c is classe), None)

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

        for k, item in self._botoes.items():
            item.ativar(k == chave)

    def definicoes_ranking(self) -> list:
        """Ajustes manuais de ranking (lista vazia se o arquivo estiver com problema;
        o problema é avisado ao abrir a aba Ranking)."""
        try:
            return self.repositorio_ranking.carregar()
        except ArquivoCorrompidoError:
            return []

    def rr_por_dia(self, registros) -> dict:
        """RR do dia a mostrar nas telas: variação real no ranking (com proteção) ou a soma."""
        return rr_por_dia(registros, self.definicoes_ranking())

    def atualizar_ranking_salvo(self) -> RankingSalvo | None:
        """Recalcula o ranking ao fim do último dia registrado e grava em ranking.json.

        Chamado sempre que algo que afeta o ranking muda: dia salvo, editado,
        excluído ou importado, ou ajuste manual na aba Ranking.
        """
        try:
            registros, _ = self.repositorio.carregar_todos()
            resultado = ranking_atual_com_data(registros, self.repositorio_ranking.carregar())
            salvo = RankingSalvo(*resultado) if resultado else None
            self.repositorio_ranking.salvar_atual(salvo)
        except (ArquivoCorrompidoError, OSError):
            return None  # o arquivo com problema é avisado ao abrir a aba Ranking
        return salvo

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
