"""Cartão com um gráfico Matplotlib embutido e dica (tooltip) ao passar o mouse."""

import math

import customtkinter as ctk
import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from app.ui import tema  # noqa: E402
from app.ui.formatacao import hora_texto  # noqa: E402

from matplotlib import font_manager  # noqa: E402

# Cores das séries, validadas para daltonismo e contraste sobre o fundo dos
# cartões (#171A20). Série única: o vermelho da marca. Comparação entre grupos:
# azul (dias bons) x vermelho (dias ruins).
SERIE_1 = tema.COR_DESTAQUE
SERIE_BONS = "#3987e5"
SERIE_RUINS = tema.COR_DESTAQUE
_SUPERFICIE = tema.COR_CARTAO
_GRADE = "#23272F"
_EIXO = tema.COR_BORDA_FORTE

# Mesmas fontes do resto do app nos gráficos (as embutidas em assets/fontes).
for _arquivo in tema.PASTA_FONTES.glob("Barlow-*.ttf"):
    font_manager.fontManager.addfont(str(_arquivo))
matplotlib.rcParams["font.family"] = [tema.FONTE_TEXTO, "Segoe UI", "DejaVu Sans"]


class Grafico(ctk.CTkFrame):
    def __init__(self, master, titulo: str, altura: int = 260):
        super().__init__(master, fg_color=_SUPERFICIE, corner_radius=tema.RAIO,
                         border_width=1, border_color=tema.COR_BORDA)
        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.pack(fill="x", padx=18, pady=(14, 0))
        ctk.CTkFrame(cabecalho, width=3, height=20, corner_radius=0,
                     fg_color=tema.COR_DESTAQUE).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(cabecalho, text=titulo.upper(), font=tema.fonte_secao(), height=26,
                     text_color=tema.COR_TEXTO).pack(side="left")
        self._subtitulo = ctk.CTkLabel(self, text="", font=tema.fonte_pequena(),
                                       text_color=tema.COR_TEXTO_SECUNDARIO)
        self._subtitulo.pack(anchor="w", padx=18)

        self.figura = Figure(figsize=(6, altura / 100), dpi=100, facecolor=_SUPERFICIE, layout="constrained")
        self.eixo = self.figura.add_subplot()
        self._area_mpl = FigureCanvasTkAgg(self.figura, master=self)
        widget = self._area_mpl.get_tk_widget()
        widget.configure(bg=_SUPERFICIE, highlightthickness=0, height=altura)
        widget.pack(fill="both", expand=True, padx=10, pady=(4, 12))

        self._pontos: list[tuple[float, float, str]] = []
        self._so_eixo_x = False
        self._area_mpl.mpl_connect("motion_notify_event", self._ao_mover)
        self._area_mpl.mpl_connect("figure_leave_event", lambda _: self._esconder_dica())
        self.limpar()

    # --- Desenho ----------------------------------------------------------

    def limpar(self, subtitulo: str = "") -> None:
        """Apaga o gráfico e reaplica o estilo base (grade discreta, sem bordas)."""
        self._subtitulo.configure(text=subtitulo)
        eixo = self.eixo
        eixo.clear()
        eixo.set_facecolor(_SUPERFICIE)
        for lado in ("top", "right", "left"):
            eixo.spines[lado].set_visible(False)
        eixo.spines["bottom"].set_color(_EIXO)
        eixo.tick_params(colors=tema.COR_TEXTO_SECUNDARIO, labelsize=9, length=0, pad=6)
        eixo.grid(axis="y", color=_GRADE, linewidth=0.8)
        eixo.set_axisbelow(True)

        self._pontos = []
        # A linha-guia só é criada no primeiro movimento do mouse: se nascesse em
        # x=0, o Matplotlib esticaria o eixo de datas até 01/01/1970.
        self._guia = None
        self._dica = eixo.annotate(
            "", xy=(0, 0), xytext=(12, 12), textcoords="offset points", visible=False,
            fontsize=9, color=tema.COR_TEXTO, zorder=10,
            bbox={"boxstyle": "square,pad=0.6", "fc": tema.COR_MENU, "ec": tema.COR_DESTAQUE, "lw": 1},
        )

    def mostrar_vazio(self, mensagem: str) -> None:
        self.eixo.set_xticks([])
        self.eixo.set_yticks([])
        self.eixo.spines["bottom"].set_visible(False)
        self.eixo.text(0.5, 0.5, mensagem, transform=self.eixo.transAxes, ha="center", va="center",
                       color=tema.COR_TEXTO_SECUNDARIO, fontsize=10)
        self.desenhar()

    def eixo_y_em_horas(self) -> None:
        self.eixo.yaxis.set_major_formatter(FuncFormatter(lambda valor, _: hora_texto(valor)))

    def legenda(self) -> None:
        # Acima da área do gráfico, para nunca cobrir os dados.
        self.eixo.legend(loc="lower left", bbox_to_anchor=(0, 1.0), frameon=False, fontsize=9,
                         labelcolor=tema.COR_TEXTO_SECUNDARIO, ncols=4, borderaxespad=0.2)

    def definir_dicas(self, pontos: list[tuple[float, float, str]], so_eixo_x: bool = False) -> None:
        """pontos: (x, y, texto) em coordenadas do gráfico.

        so_eixo_x=True (gráficos de linha): a dica segue o mouse na horizontal,
        com uma linha-guia vertical, sem precisar mirar no ponto.
        """
        self._pontos = pontos
        self._so_eixo_x = so_eixo_x

    def definir_altura(self, altura: int) -> None:
        self._area_mpl.get_tk_widget().configure(height=altura)

    def desenhar(self) -> None:
        self._area_mpl.draw_idle()

    # --- Dica ao passar o mouse ------------------------------------------

    def _ao_mover(self, evento) -> None:
        if evento.inaxes is not self.eixo or not self._pontos:
            self._esconder_dica()
            return
        transformar = self.eixo.transData.transform
        melhor, menor_distancia = None, math.inf
        for ponto in self._pontos:
            px, py = transformar(ponto[:2])
            distancia = abs(px - evento.x) if self._so_eixo_x else math.hypot(px - evento.x, py - evento.y)
            if distancia < menor_distancia:
                melhor, menor_distancia = ponto, distancia
        if melhor is None or menor_distancia > 40:
            self._esconder_dica()
            return

        x, y, texto = melhor
        # Perto da borda direita, a dica abre para a esquerda para não ser cortada.
        a_direita = transformar((x, y))[0] > self.eixo.bbox.x0 + self.eixo.bbox.width * 0.6
        self._dica.set_position((-12, 12) if a_direita else (12, 12))
        self._dica.set_horizontalalignment("right" if a_direita else "left")
        self._dica.xy = (x, y)
        self._dica.set_text(texto)
        self._dica.set_visible(True)
        if self._so_eixo_x:
            if self._guia is None:
                self._guia = self.eixo.axvline(x, color=_EIXO, linewidth=1, zorder=1)
            self._guia.set_xdata([x, x])
            self._guia.set_visible(True)
        self.desenhar()

    def _esconder_dica(self) -> None:
        if self._dica.get_visible():
            self._dica.set_visible(False)
            if self._guia is not None:
                self._guia.set_visible(False)
            self.desenhar()
