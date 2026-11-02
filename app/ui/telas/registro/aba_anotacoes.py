"""Aba Anotações: situações nas partidas e observações gerais do dia."""

from app.ui.componentes import CampoTextoLongo, Secao


class AbaAnotacoes:
    def __init__(self, tela, area):
        secao = Secao(area, "Situações nas partidas",
                      'Ex.: "Consegui fazer microajustes com facilidade." / '
                      '"Estava muito ansioso durante os confrontos."')
        secao.pack(fill="x", pady=(0, 10))
        tela.campos["notas_jogo"] = CampoTextoLongo(secao.conteudo, "", altura=180)
        tela.campos["notas_jogo"].pack(fill="x")

        secao = Secao(area, "Observações gerais sobre o dia")
        secao.pack(fill="x", pady=10)
        tela.campos["observacoes"] = CampoTextoLongo(secao.conteudo, "", altura=180)
        tela.campos["observacoes"].pack(fill="x")

    def atualizar(self) -> None:
        """Nada calculado nesta aba."""
