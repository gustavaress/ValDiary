"""Cores e fontes do aplicativo. Para mudar o visual, mude aqui."""

import customtkinter as ctk

# Paleta
COR_FUNDO = "#0F1923"
COR_MENU = "#0B131B"
COR_CARTAO = "#1A2632"
COR_CARTAO_HOVER = "#223140"
COR_BORDA = "#2A3A49"
COR_DESTAQUE = "#FF4655"
COR_DESTAQUE_HOVER = "#E03C4B"
COR_TEXTO = "#ECE8E1"
COR_TEXTO_SECUNDARIO = "#8B97A2"
COR_SUCESSO = "#3FC48A"
COR_AVISO = "#F5B841"

CORES_CLASSIFICACAO = {
    "excelente": "#3FC48A",
    "bom": "#8BD46E",
    "normal": "#8B97A2",
    "ruim": "#F5934A",
    "pessimo": "#FF4655",
}

ROTULOS_CLASSIFICACAO = {
    "excelente": "Excelente",
    "bom": "Bom",
    "normal": "Normal",
    "ruim": "Ruim",
    "pessimo": "Péssimo",
}


# Fontes são funções porque o CTkFont só pode ser criado depois da janela existir.
def fonte_titulo() -> ctk.CTkFont:
    return ctk.CTkFont(size=26, weight="bold")


def fonte_subtitulo() -> ctk.CTkFont:
    return ctk.CTkFont(size=14)


def fonte_secao() -> ctk.CTkFont:
    return ctk.CTkFont(size=16, weight="bold")


def fonte_valor() -> ctk.CTkFont:
    return ctk.CTkFont(size=30, weight="bold")


def fonte_normal() -> ctk.CTkFont:
    return ctk.CTkFont(size=14)


def fonte_pequena() -> ctk.CTkFont:
    return ctk.CTkFont(size=12)
