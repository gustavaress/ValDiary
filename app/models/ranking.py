"""Ranking competitivo: elos, definições do jogador e cálculo partida a partida.

Regras (aplicadas a cada partida, na ordem em que foram jogadas):
- Cada divisão (Ferro 1 ... Ascendente 3) vai de 0 a 100 RR. Chegar a 100
  promove; o excedente vai para a divisão seguinte.
- Proteção contra rebaixamento: perder com RR acima de 0 nunca rebaixa. Se a
  perda for maior que o RR atual, os pontos zeram e o elo continua o mesmo.
- Perder já estando com 0 RR rebaixa para o elo anterior, com 100 menos a perda.
- Ferro 1 é o piso (o RR não fica negativo).
- No Imortal e no Radiante não há promoção pelo app: a divisão depende do
  ranking global do jogo, então o RR só acumula.

É uma ESTIMATIVA. Se ficar diferente do jogo, redefina o ranking na aba Ranking.
"""

from dataclasses import dataclass
from datetime import date, datetime

_TIERS_COM_DIVISAO = ("Ferro", "Bronze", "Prata", "Ouro", "Platina", "Diamante", "Ascendente")
DIVISOES = [f"{tier} {numero}" for tier in _TIERS_COM_DIVISAO for numero in (1, 2, 3)]
TOPO = ["Imortal 1", "Imortal 2", "Imortal 3", "Radiante"]
ELOS = DIVISOES + TOPO

RR_POR_DIVISAO = 100


@dataclass(frozen=True)
class Ranking:
    elo: str
    rr: int

    @property
    def texto(self) -> str:
        return f"{self.elo} · {self.rr} RR"


@dataclass(frozen=True)
class DefinicaoRanking:
    """Ranking informado pelo jogador, valendo a partir do INÍCIO de `data`."""
    data: date
    elo: str
    rr: int
    definido_em: datetime | None = None

    @property
    def ranking(self) -> Ranking:
        return Ranking(self.elo, self.rr)

    def to_dict(self) -> dict:
        return {"data": self.data.isoformat(), "elo": self.elo, "rr": self.rr,
                "definido_em": self.definido_em.isoformat(timespec="seconds") if self.definido_em else None}

    @classmethod
    def from_dict(cls, dados: dict) -> "DefinicaoRanking":
        definido_em = dados.get("definido_em")
        return cls(date.fromisoformat(dados["data"]), dados["elo"], int(dados["rr"]),
                   datetime.fromisoformat(definido_em) if definido_em else None)


def aplicar_partida(atual: Ranking, variacao: int) -> Ranking:
    """Ranking depois de uma partida que rendeu `variacao` RR (positivo ou negativo)."""
    indice = ELOS.index(atual.elo)
    rr = atual.rr + variacao

    if rr < 0:
        if atual.rr > 0 or indice == 0:
            return Ranking(atual.elo, 0)          # proteção contra rebaixamento / piso do Ferro 1
        # Já estava com 0 RR: rebaixa. Do Imortal/Radiante, volta para Ascendente 3.
        anterior = min(indice, len(DIVISOES)) - 1
        return Ranking(ELOS[anterior], max(RR_POR_DIVISAO + variacao, 0))

    no_topo = indice >= len(DIVISOES)
    if rr >= RR_POR_DIVISAO and not no_topo:
        return Ranking(ELOS[indice + 1], rr - RR_POR_DIVISAO)  # promoção
    return Ranking(atual.elo, rr)


def aplicar_partidas(inicio: Ranking, variacoes: list[int]) -> Ranking:
    atual = inicio
    for variacao in variacoes:
        atual = aplicar_partida(atual, variacao)
    return atual


def erros_definicao(elo: str | None, rr: int | None) -> list[str]:
    erros = []
    if elo not in ELOS:
        erros.append("Escolha o elo.")
    if rr is None:
        erros.append("Informe o RR.")
    elif elo in TOPO and rr < 0:
        erros.append("O RR deve ser maior ou igual a 0.")
    elif elo not in TOPO and not (0 <= rr < RR_POR_DIVISAO):
        erros.append(f"O RR deve estar entre 0 e {RR_POR_DIVISAO - 1}.")
    return erros
