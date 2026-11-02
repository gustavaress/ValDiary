"""Seletores de botões: escolha única que pode ficar vazia."""

import customtkinter as ctk

from app.config import ESCALA_MAX, ESCALA_MIN
from app.ui import tema


class SeletorBotoes(ctk.CTkFrame):
    """Fileira de botões em que no máximo um fica selecionado.

    Clicar no botão já selecionado desmarca (volta para "não informado").
    """

    def __init__(self, master, opcoes: list[tuple], cores: dict | None = None,
                 largura_botao: int = 36, ao_mudar=None):
        super().__init__(master, fg_color="transparent")
        self._valor = None
        self._cores = cores or {}
        self._ao_mudar = ao_mudar
        self._botoes: dict = {}

        for coluna, (valor, rotulo) in enumerate(opcoes):
            botao = ctk.CTkButton(
                self, text=rotulo, width=largura_botao, height=32, corner_radius=tema.RAIO_BOTAO,
                font=tema.fonte_forte(), border_width=1, border_color=tema.COR_BORDA,
                command=lambda v=valor: self._clicar(v),
            )
            botao.grid(row=0, column=coluna, padx=(0, 4))
            self._botoes[valor] = botao
        self._pintar()

    def _clicar(self, valor) -> None:
        self.set(None if valor == self._valor else valor)
        if self._ao_mudar:
            self._ao_mudar(self._valor)

    def _pintar(self) -> None:
        for valor, botao in self._botoes.items():
            if valor == self._valor:
                cor = self._cores.get(valor, tema.COR_DESTAQUE)
                texto = tema.COR_FUNDO if valor in self._cores else "#FFFFFF"
                botao.configure(fg_color=cor, hover_color=cor, text_color=texto)
            else:
                botao.configure(fg_color=tema.COR_CAMPO, hover_color=tema.COR_BORDA,
                                text_color=tema.COR_TEXTO_SECUNDARIO)

    def get(self):
        return self._valor

    def set(self, valor) -> None:
        self._valor = valor if valor in self._botoes else None
        self._pintar()

    def habilitar(self, ativo: bool) -> None:
        for botao in self._botoes.values():
            botao.configure(state="normal" if ativo else "disabled")


class SeletorNota(SeletorBotoes):
    """Notas de 1 a 10."""

    def __init__(self, master, ao_mudar=None):
        opcoes = [(n, str(n)) for n in range(ESCALA_MIN, ESCALA_MAX + 1)]
        super().__init__(master, opcoes, largura_botao=34, ao_mudar=ao_mudar)


class SeletorClassificacao(SeletorBotoes):
    def __init__(self, master, ao_mudar=None):
        opcoes = list(tema.ROTULOS_CLASSIFICACAO.items())
        super().__init__(master, opcoes, cores=tema.CORES_CLASSIFICACAO,
                         largura_botao=96, ao_mudar=ao_mudar)
