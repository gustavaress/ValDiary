"""Lista de linhas editáveis (ex.: bebidas, medicamentos) com botões + e ✕."""

import customtkinter as ctk

from app.ui import tema
from app.ui.componentes.formulario import nova_entrada
from app.ui.componentes.seletor_hora import SeletorHora

TEXTO = "texto"
HORA = "hora"


class ListaEditavel(ctk.CTkFrame):
    def __init__(self, master, colunas: list[tuple[str, str, int, str]], texto_adicionar: str):
        """colunas: lista de (chave, placeholder, largura, tipo), tipo = TEXTO ou HORA."""
        super().__init__(master, fg_color="transparent")
        self._colunas = colunas
        self._linhas: list[tuple[ctk.CTkFrame, dict]] = []

        self._area = ctk.CTkFrame(self, fg_color="transparent")
        self._area.pack(fill="x")
        ctk.CTkButton(
            self, text=texto_adicionar, width=120, height=30, font=tema.fonte_pequena(),
            fg_color="transparent", border_width=1, border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO_SECUNDARIO, hover_color=tema.COR_CARTAO_HOVER,
            command=self.adicionar_linha,
        ).pack(anchor="w", pady=(4, 0))

    def adicionar_linha(self, valores: dict | None = None) -> None:
        linha = ctk.CTkFrame(self._area, fg_color="transparent")
        linha.pack(fill="x", pady=2)
        campos = {}
        for chave, placeholder, largura, tipo in self._colunas:
            valor = (valores or {}).get(chave)
            if tipo == HORA:
                campo = SeletorHora(linha)
                campo.set(valor)
            else:
                campo = nova_entrada(linha, largura, placeholder)
                if valor:
                    campo.insert(0, valor)
            campo.pack(side="left", padx=(0, 6))
            campos[chave] = campo
        ctk.CTkButton(
            linha, text="✕", width=34, height=34, fg_color="transparent",
            hover_color=tema.COR_BORDA, text_color=tema.COR_TEXTO_SECUNDARIO,
            command=lambda: self._remover(linha),
        ).pack(side="left")
        self._linhas.append((linha, campos))

    def _remover(self, linha: ctk.CTkFrame) -> None:
        self._linhas = [(l, c) for l, c in self._linhas if l is not linha]
        linha.destroy()

    def get(self) -> list[dict]:
        """Linhas preenchidas (linhas totalmente vazias são ignoradas)."""
        itens = []
        for _, campos in self._linhas:
            item = {chave: campo.get().strip() for chave, campo in campos.items()}
            if any(item.values()):
                itens.append(item)
        return itens

    def set(self, itens: list[dict] | None) -> None:
        for linha, _ in self._linhas:
            linha.destroy()
        self._linhas = []
        for item in itens or []:
            self.adicionar_linha(item)
