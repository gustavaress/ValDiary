"""Cartão de informação: título pequeno, valor grande e um detalhe opcional."""

import customtkinter as ctk

from app.ui import tema


class CartaoInfo(ctk.CTkFrame):
    def __init__(self, master, titulo: str, valor: str = "—", detalhe: str = ""):
        super().__init__(master, fg_color=tema.COR_CARTAO, corner_radius=12,
                         border_width=1, border_color=tema.COR_BORDA)

        ctk.CTkLabel(self, text=titulo.upper(), font=tema.fonte_pequena(),
                     text_color=tema.COR_TEXTO_SECUNDARIO).pack(anchor="w", padx=18, pady=(16, 0))
        self._valor = ctk.CTkLabel(self, text=valor, font=tema.fonte_valor(),
                                   text_color=tema.COR_TEXTO)
        self._valor.pack(anchor="w", padx=18)
        self._detalhe = ctk.CTkLabel(self, text=detalhe, font=tema.fonte_pequena(),
                                     text_color=tema.COR_TEXTO_SECUNDARIO)
        self._detalhe.pack(anchor="w", padx=18, pady=(0, 16))

    def atualizar(self, valor: str, detalhe: str = "", cor_valor: str = tema.COR_TEXTO) -> None:
        self._valor.configure(text=valor, text_color=cor_valor)
        self._detalhe.configure(text=detalhe)
