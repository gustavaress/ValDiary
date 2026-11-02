"""Bandeja de agentes: janela com as fotos, para escolher o agente de uma partida."""

import time
from functools import cache

import customtkinter as ctk
from PIL import Image

from app.storage.catalogo_agentes import agrupar_por_funcao, carregar_agentes
from app.ui import tema

TAMANHO_FOTO = 56
TEMPO_MINIMO_ABERTA_S = 0.3
AGENTES_POR_LINHA = 8

_PLURAL_FUNCAO = {"Duelista": "Duelistas", "Iniciador": "Iniciadores",
                  "Controlador": "Controladores", "Sentinela": "Sentinelas"}


@cache
def imagem_agente(nome: str, tamanho: int) -> ctk.CTkImage | None:
    """Foto do agente no tamanho pedido (carregada uma vez e reaproveitada)."""
    agente = next((a for a in carregar_agentes() if a.nome == nome), None)
    if agente is None or not agente.imagem.exists():
        return None
    return ctk.CTkImage(Image.open(agente.imagem).convert("RGBA"), size=(tamanho, tamanho))


class BandejaAgentes(ctk.CTkToplevel):
    """Janela modal. Use escolher_agente() em vez de instanciar direto."""

    def __init__(self, pai, atual: str | None):
        super().__init__(pai, fg_color=tema.COR_CARTAO)
        self._aberta_em = time.monotonic()
        self.title("Escolha o agente")
        self.resizable(False, False)
        self.escolhido: str | None = None

        catalogo = carregar_agentes()
        if not catalogo:
            ctk.CTkLabel(self, text="Imagens dos agentes não encontradas.\n"
                                    "Rode no terminal: python scripts/gerar_agentes.py",
                         text_color=tema.COR_AVISO, font=tema.fonte_normal()).pack(padx=30, pady=30)

        grade = ctk.CTkFrame(self, fg_color="transparent")
        grade.pack(padx=18, pady=(12, 6))
        linha = 0
        for funcao, agentes in agrupar_por_funcao(catalogo):
            ctk.CTkLabel(grade, text=_PLURAL_FUNCAO.get(funcao, funcao).upper(), font=tema.fonte_pequena(),
                         text_color=tema.COR_TEXTO_SECUNDARIO).grid(row=linha, column=0, columnspan=8,
                                                                    sticky="w", pady=(8, 2))
            linha += 1
            for i, agente in enumerate(agentes):
                selecionado = agente.nome == atual
                ctk.CTkButton(
                    grade, text=agente.nome, image=imagem_agente(agente.nome, TAMANHO_FOTO), compound="top",
                    width=78, height=88, corner_radius=10, border_width=2, font=tema.fonte_pequena(),
                    fg_color=tema.COR_CARTAO_HOVER if selecionado else "transparent",
                    border_color=tema.COR_DESTAQUE if selecionado else tema.COR_CARTAO,
                    hover_color=tema.COR_CARTAO_HOVER, text_color=tema.COR_TEXTO,
                    command=lambda n=agente.nome: self._escolher(n),
                ).grid(row=linha + i // AGENTES_POR_LINHA, column=i % AGENTES_POR_LINHA, padx=3, pady=3)
            linha += (len(agentes) - 1) // AGENTES_POR_LINHA + 1

        ctk.CTkButton(self, text="Cancelar", width=110, fg_color="transparent", border_width=1,
                      border_color=tema.COR_BORDA, text_color=tema.COR_TEXTO_SECUNDARIO,
                      hover_color=tema.COR_CARTAO_HOVER, command=self.destroy).pack(pady=(4, 16))
        self.bind("<Escape>", lambda _: self.destroy())

        # Centraliza sobre a janela principal e bloqueia o resto do app enquanto aberta.
        self.update_idletasks()
        janela = pai.winfo_toplevel()
        x = janela.winfo_rootx() + (janela.winfo_width() - self.winfo_width()) // 2
        y = janela.winfo_rooty() + (janela.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.transient(janela)
        self._agendamento_foco = self.after(50, self._capturar_foco)

    def _capturar_foco(self) -> None:
        # A bandeja pode ter sido fechada antes deste agendamento rodar.
        if self.winfo_exists():
            self.grab_set()
            self.focus_force()

    def _escolher(self, nome: str) -> None:
        self.escolhido = nome
        self.destroy()

    def destroy(self) -> None:
        # O CustomTkinter agenda ajustes internos logo após criar a janela (barra
        # de título do Windows). Destruí-la antes disso derrubava o app nos
        # testes, então uma bandeja recém-aberta espera esse instante para fechar.
        restante_ms = int((TEMPO_MINIMO_ABERTA_S - (time.monotonic() - self._aberta_em)) * 1000)
        if restante_ms > 0:
            self.after(restante_ms, self.destroy)
            return
        self.after_cancel(self._agendamento_foco)
        super().destroy()


def escolher_agente(pai, atual: str | None = None) -> str | None:
    """Abre a bandeja e espera a escolha. Retorna o nome, ou None se cancelou."""
    bandeja = BandejaAgentes(pai, atual)
    pai.wait_window(bandeja)
    return bandeja.escolhido
