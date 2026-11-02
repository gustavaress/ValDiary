"""Ranking competitivo: elos e cálculo (estimado) do ranking após as partidas.

Regra usada: cada divisão (Ferro 1 ... Ascendente 3) vai de 0 a 100 RR. Passar
de 100 promove (o excedente vai para a divisão seguinte); ficar abaixo de 0
rebaixa (100 + o valor negativo). No Imortal e no Radiante o RR acumula sem
teto, porque a divisão depende do ranking global do jogo.

É uma ESTIMATIVA: o jogo tem regras próprias (ex.: proteção contra
rebaixamento) que não dá para reproduzir. Se o valor real for diferente,
basta corrigir o ranking inicial do dia seguinte.
"""

from dataclasses import dataclass

_TIERS_COM_DIVISAO = ("Ferro", "Bronze", "Prata", "Ouro", "Platina", "Diamante", "Ascendente")
DIVISOES = [f"{tier} {numero}" for tier in _TIERS_COM_DIVISAO for numero in (1, 2, 3)]
TOPO = ["Imortal 1", "Imortal 2", "Imortal 3", "Radiante"]
ELOS = DIVISOES + TOPO

RR_POR_DIVISAO = 100


@dataclass
class Ranking:
    elo: str | None = None
    rr: int | None = None

    @property
    def completo(self) -> bool:
        return self.elo in ELOS and self.rr is not None

    @property
    def texto(self) -> str | None:
        if not self.completo:
            return None
        return f"{self.elo} · {self.rr} RR"


def aplicar_rr(inicio: Ranking, variacao: int) -> Ranking:
    """Ranking depois de ganhar/perder `variacao` RR a partir de `inicio` (que deve estar completo)."""
    indice = ELOS.index(inicio.elo)
    rr = inicio.rr + variacao
    ultima_divisao = len(DIVISOES) - 1
    while True:
        no_topo = indice > ultima_divisao
        if rr >= RR_POR_DIVISAO and not no_topo:
            indice += 1          # promoção (Ascendente 3 -> Imortal 1 inclusive)
            rr -= RR_POR_DIVISAO
        elif rr < 0 and indice > 0:
            # Rebaixamento. Do topo, sempre volta para Ascendente 3.
            indice = min(indice, ultima_divisao + 1) - 1
            rr += RR_POR_DIVISAO
        elif rr < 0:
            rr = 0               # Ferro 1 é o piso
        else:
            break
    return Ranking(ELOS[indice], rr)


def erros_ranking(ranking: Ranking, rotulo: str) -> list[str]:
    erros = []
    if ranking.elo is not None and ranking.elo not in ELOS:
        erros.append(f"{rotulo}: elo desconhecido ({ranking.elo}).")
    if ranking.rr is not None:
        no_topo = ranking.elo in TOPO
        if ranking.rr < 0 or (not no_topo and ranking.rr > RR_POR_DIVISAO):
            limite = "maior ou igual a 0" if no_topo else f"entre 0 e {RR_POR_DIVISAO}"
            erros.append(f"{rotulo}: o RR deve estar {limite}.")
    return erros
