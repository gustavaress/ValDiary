"""Logo do ValDiary: um "V" angular vermelho (desenho próprio, não é o logo do Valorant).

Desenhado por código para ficar nítido em qualquer tamanho. Também gera o
ícone da janela (.ico) usado pelo app e pelo futuro .exe.
"""

from pathlib import Path

from PIL import Image, ImageDraw

VERMELHO = (255, 70, 85, 255)
GRAFITE = (14, 16, 20, 255)

# Pontos do "V" numa grade 16x16: dois braços que se encontram embaixo,
# com um corte reto no topo de cada braço (linguagem angular).
_FORMA_V = [(1.0, 2.5), (5.2, 2.5), (8.0, 10.2), (10.8, 2.5), (15.0, 2.5), (9.7, 14.5), (6.3, 14.5)]
# Traço curto "de anotação" que corta o braço direito.
_TRACO = [(11.6, 6.2), (15.0, 6.2), (14.2, 7.6), (11.1, 7.6)]


def desenhar_logo(tamanho: int = 256, fundo: bool = False) -> Image.Image:
    """Logo em RGBA. fundo=True desenha um quadrado grafite atrás (para o ícone da barra de tarefas)."""
    escala = 4  # desenha maior e reduz: bordas suaves (antialiasing)
    lado = tamanho * escala
    imagem = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    desenho = ImageDraw.Draw(imagem)
    unidade = lado / 16
    if fundo:
        desenho.rounded_rectangle((0, 0, lado - 1, lado - 1), radius=int(unidade * 2.4), fill=GRAFITE)
    desenho.polygon([(x * unidade, y * unidade) for x, y in _FORMA_V], fill=VERMELHO)
    traco = [(x * unidade, y * unidade) for x, y in _TRACO]
    if fundo:
        desenho.polygon(traco, fill=GRAFITE)  # o traço "corta" o V mostrando o fundo
    else:
        # Sem fundo, o traço é um recorte transparente no braço do V.
        recorte = Image.new("L", (lado, lado), 0)
        ImageDraw.Draw(recorte).polygon(traco, fill=255)
        imagem.putalpha(Image.composite(Image.new("L", (lado, lado), 0), imagem.getchannel("A"), recorte))
    return imagem.resize((tamanho, tamanho), Image.Resampling.LANCZOS)


def gerar_icone(destino: Path) -> Path:
    """Arquivo .ico com vários tamanhos (Windows escolhe o melhor para cada lugar)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    desenhar_logo(256, fundo=True).save(destino, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                                                        (128, 128), (256, 256)])
    return destino
