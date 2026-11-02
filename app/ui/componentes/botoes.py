"""Botões padronizados do app. Use estes em vez de configurar CTkButton à mão.

- primário: ação principal da tela (vermelho, texto display em maiúsculas);
- secundário: ações de apoio (contorno discreto);
- ícone: botões pequenos de um símbolo (◀ ▶ ✕ − +).
"""

import customtkinter as ctk

from app.ui import tema


def botao_primario(master, texto: str, comando, largura: int = 140, altura: int = 40) -> ctk.CTkButton:
    return ctk.CTkButton(
        master, text=texto.upper(), command=comando, width=largura, height=altura,
        font=tema.fonte_display(20), corner_radius=tema.RAIO_BOTAO,
        fg_color=tema.COR_DESTAQUE, hover_color=tema.COR_DESTAQUE_HOVER, text_color=tema.COR_TEXTO,
    )


def botao_secundario(master, texto: str, comando, largura: int = 140, altura: int = 36) -> ctk.CTkButton:
    return ctk.CTkButton(
        master, text=texto, command=comando, width=largura, height=altura,
        font=tema.fonte_forte(), corner_radius=tema.RAIO_BOTAO,
        fg_color="transparent", hover_color=tema.COR_CARTAO_HOVER, border_width=1,
        border_color=tema.COR_BORDA_FORTE, text_color=tema.COR_TEXTO,
    )


def botao_icone(master, simbolo: str, comando, largura: int = 34, altura: int = 34,
                destaque: bool = False) -> ctk.CTkButton:
    return ctk.CTkButton(
        master, text=simbolo, command=comando, width=largura, height=altura,
        font=tema.fonte_forte(), corner_radius=tema.RAIO_BOTAO,
        fg_color=tema.COR_CAMPO if destaque else "transparent", hover_color=tema.COR_BORDA,
        border_width=1 if destaque else 0, border_color=tema.COR_BORDA,
        text_color=tema.COR_TEXTO if destaque else tema.COR_TEXTO_SECUNDARIO,
    )
