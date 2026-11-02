"""Identidade visual do aplicativo: cores, fontes e tema global. Para mudar o visual, mude aqui.

Linguagem inspirada no Valorant: grafite quase preto, cinzas escalonados,
off-white "papel" no texto e o vermelho #FF4655 usado só como acento.
Tipografia: Bebas Neue (display, condensada) + Barlow (texto), embutidas em
assets/fontes (licença OFL), então funcionam sem instalar nada.
"""

import customtkinter as ctk

from app import config

# --- Paleta -----------------------------------------------------------------
COR_FUNDO = "#0E1014"          # fundo da janela
COR_MENU = "#0A0B0E"           # menu lateral
COR_CARTAO = "#171A20"         # cartões, seções
COR_CARTAO_HOVER = "#1F232A"   # hover / linhas alternadas
COR_CAMPO = "#101317"          # campos de entrada (mais fundos que o cartão)
COR_BORDA = "#2A2F37"
COR_BORDA_FORTE = "#3A404A"
COR_DESTAQUE = "#FF4655"       # vermelho Valorant
COR_DESTAQUE_HOVER = "#E23B4A"
COR_DESTAQUE_SUAVE = "#2A1519" # fundo avermelhado discreto (item ativo do menu)
COR_TEXTO = "#ECE8E1"          # off-white "papel"
COR_TEXTO_SECUNDARIO = "#8B929C"
COR_TEXTO_FRACO = "#5D636C"
COR_SUCESSO = "#3FC48A"
COR_AVISO = "#F5B841"

CORES_CLASSIFICACAO = {
    "excelente": "#3FC48A",
    "bom": "#8BD46E",
    "normal": "#8B929C",
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

# Cantos quase retos: o Valorant usa formas angulares.
RAIO = 4
RAIO_BOTAO = 3

# --- Fontes -----------------------------------------------------------------
FONTE_DISPLAY = "Bebas Neue"
FONTE_TEXTO = "Barlow"
FONTE_TEXTO_FORTE = "Barlow SemiBold"
PASTA_FONTES = config.PASTA_RECURSOS / "fontes"


def carregar_fontes() -> None:
    """Registra as fontes embutidas no Windows (só para este processo).

    Deve rodar antes de criar a janela. Se falhar, o Tk usa a fonte padrão.
    """
    for arquivo in sorted(PASTA_FONTES.glob("*.ttf")):
        ctk.FontManager.load_font(str(arquivo))


# Fontes são funções porque o CTkFont só pode ser criado depois da janela existir.
def fonte_display(tamanho: int) -> ctk.CTkFont:
    return ctk.CTkFont(family=FONTE_DISPLAY, size=tamanho)


def fonte_titulo() -> ctk.CTkFont:
    return fonte_display(40)


def fonte_subtitulo() -> ctk.CTkFont:
    return ctk.CTkFont(family=FONTE_TEXTO, size=14)


def fonte_secao() -> ctk.CTkFont:
    return fonte_display(22)


def fonte_valor() -> ctk.CTkFont:
    return fonte_display(40)


def fonte_normal() -> ctk.CTkFont:
    return ctk.CTkFont(family=FONTE_TEXTO, size=14)


def fonte_forte() -> ctk.CTkFont:
    return ctk.CTkFont(family=FONTE_TEXTO_FORTE, size=14)


def fonte_pequena() -> ctk.CTkFont:
    return ctk.CTkFont(family=FONTE_TEXTO, size=12)


def fonte_rotulo() -> ctk.CTkFont:
    """Rótulos curtos em maiúsculas (ex.: títulos de cartões)."""
    return ctk.CTkFont(family=FONTE_TEXTO_FORTE, size=11)


# --- Tema global do CustomTkinter -------------------------------------------

def _cor(valor: str) -> list[str]:
    return [valor, valor]  # [modo claro, modo escuro]: o app é só escuro


def aplicar_tema() -> None:
    """Ajusta os padrões de todos os widgets de uma vez (antes de criar a janela)."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    estilos = {
        "CTk": {"fg_color": _cor(COR_FUNDO)},
        "CTkToplevel": {"fg_color": _cor(COR_FUNDO)},
        "CTkFrame": {"corner_radius": RAIO, "fg_color": _cor(COR_CARTAO), "top_fg_color": _cor(COR_CARTAO_HOVER),
                     "border_color": _cor(COR_BORDA)},
        "CTkButton": {"corner_radius": RAIO_BOTAO, "fg_color": _cor(COR_DESTAQUE),
                      "hover_color": _cor(COR_DESTAQUE_HOVER), "border_color": _cor(COR_BORDA_FORTE),
                      "text_color": _cor(COR_TEXTO), "text_color_disabled": _cor(COR_TEXTO_FRACO)},
        "CTkLabel": {"text_color": _cor(COR_TEXTO)},
        "CTkEntry": {"corner_radius": RAIO_BOTAO, "border_width": 1, "fg_color": _cor(COR_CAMPO),
                     "border_color": _cor(COR_BORDA), "text_color": _cor(COR_TEXTO),
                     "placeholder_text_color": _cor(COR_TEXTO_FRACO)},
        "CTkCheckBox": {"corner_radius": 2, "border_width": 2, "fg_color": _cor(COR_DESTAQUE),
                        "border_color": _cor(COR_BORDA_FORTE), "hover_color": _cor(COR_DESTAQUE_HOVER),
                        "checkmark_color": _cor(COR_TEXTO), "text_color": _cor(COR_TEXTO),
                        "text_color_disabled": _cor(COR_TEXTO_FRACO)},
        "CTkOptionMenu": {"corner_radius": RAIO_BOTAO, "fg_color": _cor(COR_CAMPO),
                          "button_color": _cor(COR_CAMPO), "button_hover_color": _cor(COR_BORDA),
                          "text_color": _cor(COR_TEXTO), "text_color_disabled": _cor(COR_TEXTO_FRACO)},
        "CTkScrollbar": {"corner_radius": 2, "fg_color": "transparent", "button_color": _cor(COR_BORDA),
                         "button_hover_color": _cor(COR_DESTAQUE)},
        "CTkSegmentedButton": {"corner_radius": RAIO_BOTAO, "border_width": 0, "fg_color": _cor(COR_CARTAO),
                               "selected_color": _cor(COR_DESTAQUE), "selected_hover_color": _cor(COR_DESTAQUE_HOVER),
                               "unselected_color": _cor(COR_CARTAO), "unselected_hover_color": _cor(COR_CARTAO_HOVER),
                               "text_color": _cor(COR_TEXTO), "text_color_disabled": _cor(COR_TEXTO_FRACO)},
        "CTkTextbox": {"corner_radius": RAIO_BOTAO, "border_width": 1, "fg_color": _cor(COR_CAMPO),
                       "border_color": _cor(COR_BORDA), "text_color": _cor(COR_TEXTO),
                       "scrollbar_button_color": _cor(COR_BORDA), "scrollbar_button_hover_color": _cor(COR_DESTAQUE)},
        "CTkScrollableFrame": {"label_fg_color": _cor(COR_CARTAO)},
        "DropdownMenu": {"fg_color": _cor(COR_CARTAO), "hover_color": _cor(COR_DESTAQUE_SUAVE),
                         "text_color": _cor(COR_TEXTO)},
        "CTkFont": {"family": FONTE_TEXTO, "size": 14, "weight": "normal"},
    }
    tema = ctk.ThemeManager.theme
    for widget, valores in estilos.items():
        if widget in tema:
            tema[widget].update({chave: valor for chave, valor in valores.items() if chave in tema[widget]})
