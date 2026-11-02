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

# Cores das séries: azul e laranja, validadas para daltonismo e contraste
# sobre o fundo dos cartões (#1A2632).
SERIE_1 = "#3987e5"
SERIE_2 = "#d95926"
_SUPERFICIE = tema.COR_CARTAO
_GRADE = "#253444"
_EIXO = "#3A4B5C"

matplotlib.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]


class Grafico(ctk.CTkFrame):
    def __init__(self, master, titulo: str, altura: int = 260):
        super().__init__(master, fg_color=_SUPERFICIE, corner_radius=12,
                         border_width=1, border_color=tema.COR_BORDA)
        ctk.CTkLabel(self, text=titulo, font=tema.fonte_secao(),
                     text_color=tema.COR_TEXTO).pack(anchor="w", padx=18, pady=(14, 0))
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
            bbox={"boxstyle": "round,pad=0.6", "fc": tema.COR_MENU, "ec": tema.COR_BORDA},
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
