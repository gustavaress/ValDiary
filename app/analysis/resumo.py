"""Resumos numéricos de um conjunto de dias (usados na tela inicial)."""

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.models import RegistroDia, ResumoJogo
from app.models.ranking import Ranking


@dataclass
class ResumoPeriodo:
    dias: int = 0
    partidas: int = 0
    winrate_pct: float | None = None
    kd: float | None = None
    kda: float | None = None
    acs_medio: float | None = None
    hs_medio: float | None = None
    sono_medio: float | None = None
    concentracao_media: float | None = None
    rr: int | None = None
    classificacoes: Counter = field(default_factory=Counter)


def _media(valores) -> float | None:
    presentes = [v for v in valores if v is not None]
    return round(sum(presentes) / len(presentes), 2) if presentes else None


def _media_por_partida(resumos: list[ResumoJogo], atributo: str) -> float | None:
    """Média de uma estatística diária (ACS, HS%) ponderada pelas partidas.

    Um dia com 6 partidas pesa mais que um dia com 1. Se o número de partidas
    não foi registrado, o dia conta com peso 1.
    """
    soma = peso_total = 0
    for resumo in resumos:
        valor = getattr(resumo, atributo)
        if valor is None:
            continue
        peso = resumo.partidas or 1
        soma += valor * peso
        peso_total += peso
    return round(soma / peso_total, 1) if peso_total else None


def resumir(registros: list[RegistroDia]) -> ResumoPeriodo:
    resumos = [r.valorant.resumo for r in registros]

    # Winrate, K/D e KDA usam a soma do período (e não a média das médias
    # diárias), para que dias com mais partidas tenham o peso correto.
    com_resultado = [r for r in resumos if r.vitorias is not None and r.partidas_com_resultado]
    periodo = ResumoJogo(
        vitorias=_soma(r.vitorias for r in com_resultado),
        partidas_com_resultado=_soma(r.partidas_com_resultado for r in com_resultado),
        **_totais_kda(resumos),
    )
    return ResumoPeriodo(
        dias=len(registros),
        partidas=sum(r.partidas or 0 for r in resumos),
        winrate_pct=periodo.winrate_pct,
        kd=periodo.kd,
        kda=periodo.kda,
        acs_medio=_media_por_partida(resumos, "acs"),
        hs_medio=_media_por_partida(resumos, "hs_pct"),
        sono_medio=_media(r.rotina.sono.horas_efetivas for r in registros),
        concentracao_media=_media(r.valorant.avaliacao.concentracao for r in registros),
        rr=_soma(r.rr for r in resumos),
        classificacoes=Counter(r.classificacao.value for r in registros if r.classificacao),
    )


def _soma(valores) -> int | None:
    presentes = [v for v in valores if v is not None]
    return sum(presentes) if presentes else None


def _totais_kda(resumos: list[ResumoJogo]) -> dict:
    """Soma K, D e A só dos dias que têm abates E mortes, para o K/D não ficar distorcido."""
    com_kd = [r for r in resumos if r.abates is not None and r.mortes is not None]
    if not com_kd:
        return {}
    return {"abates": sum(r.abates for r in com_kd), "mortes": sum(r.mortes for r in com_kd),
            "assistencias": sum(r.assistencias or 0 for r in com_kd)}


def sequencia_atual(registros: list[RegistroDia], hoje: date) -> int:
    """Quantos dias seguidos foram registrados até hoje.

    Se hoje ainda não foi registrado, a sequência conta até ontem (o dia
    ainda não acabou, então ela não está "quebrada").
    """
    datas = {r.data for r in registros}
    dia = hoje if hoje in datas else hoje - timedelta(days=1)
    contagem = 0
    while dia in datas:
        contagem += 1
        dia -= timedelta(days=1)
    return contagem


def ranking_mais_recente(registros: list[RegistroDia], antes_de: date | None = None) -> tuple[Ranking, date] | None:
    """Ranking ao fim do dia mais recente que tem ranking (opcionalmente, antes de uma data).

    Retorna (ranking, data do dia) ou None se nenhum dia tem ranking.
    """
    candidatos = [r for r in registros
                  if r.valorant.ranking_final and (antes_de is None or r.data < antes_de)]
    if not candidatos:
        return None
    ultimo = max(candidatos, key=lambda r: r.data)
    return ultimo.valorant.ranking_final, ultimo.data
