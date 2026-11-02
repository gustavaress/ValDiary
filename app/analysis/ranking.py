"""Evolução do ranking ao longo dos dias.

O ranking nunca é digitado no dia: ele é CALCULADO a partir da definição mais
recente (feita na aba Ranking) e do RR de cada partida registrada depois dela,
na ordem em que foram jogadas. Por isso, registrar um dia antigo ou corrigir o
RR de uma partida ajusta tudo automaticamente.
"""

from dataclasses import dataclass
from datetime import date

from app.models import RegistroDia
from app.models.ranking import DefinicaoRanking, Ranking, aplicar_partidas


@dataclass(frozen=True)
class RankingDoDia:
    data: date
    inicio: Ranking
    final: Ranking
    rr: int | None        # soma do RR das partidas do dia
    redefinido: bool      # uma definição passou a valer neste dia


def variacoes_do_dia(registro: RegistroDia) -> list[int]:
    return [p.rr for p in registro.valorant.partidas if p.rr is not None]


def evolucao_ranking(registros: list[RegistroDia], definicoes: list[DefinicaoRanking]) -> list[RankingDoDia]:
    """Ranking no início e no fim de cada dia registrado a partir da primeira definição."""
    definicoes = sorted(definicoes, key=lambda d: d.data)
    if not definicoes:
        return []
    dias = sorted((r for r in registros if r.data >= definicoes[0].data), key=lambda r: r.data)

    resultado = []
    atual: Ranking | None = None
    proxima = 0
    for registro in dias:
        # Definições que passam a valer até este dia substituem o valor calculado.
        redefinido = False
        while proxima < len(definicoes) and definicoes[proxima].data <= registro.data:
            atual = definicoes[proxima].ranking
            proxima += 1
            redefinido = True
        final = aplicar_partidas(atual, variacoes_do_dia(registro))
        resultado.append(RankingDoDia(registro.data, atual, final, registro.valorant.resumo.rr, redefinido))
        atual = final
    return resultado


def ranking_atual_com_data(registros: list[RegistroDia],
                           definicoes: list[DefinicaoRanking]) -> tuple[Ranking, date | None] | None:
    """(ranking depois de todos os dias registrados, último dia aplicado).

    O dia é None quando a definição mais recente é mais nova que qualquer dia
    registrado (o ranking é a própria definição). Retorna None se nunca foi definido.
    """
    if not definicoes:
        return None
    ultima = max(definicoes, key=lambda d: d.data)
    evolucao = evolucao_ranking(registros, definicoes)
    if evolucao and evolucao[-1].data >= ultima.data:
        return evolucao[-1].final, evolucao[-1].data
    return ultima.ranking, None


def ranking_atual(registros: list[RegistroDia], definicoes: list[DefinicaoRanking]) -> Ranking | None:
    """Ranking depois de todos os dias registrados (None se nunca foi definido)."""
    resultado = ranking_atual_com_data(registros, definicoes)
    return resultado[0] if resultado else None


def ranking_no_inicio_do_dia(data: date, registros: list[RegistroDia],
                             definicoes: list[DefinicaoRanking]) -> Ranking | None:
    """Ranking ao começar `data`, considerando só os dias anteriores a ela."""
    anteriores = [r for r in registros if r.data < data]
    return ranking_atual(anteriores, [d for d in definicoes if d.data <= data])
