"""Resumos numéricos de um conjunto de dias (usados na tela inicial)."""

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.models import RegistroDia


@dataclass
class ResumoPeriodo:
    dias: int = 0
    partidas: int = 0
    winrate_pct: float | None = None
    kd: float | None = None
    acs_medio: float | None = None
    adr_medio: float | None = None
    hs_medio: float | None = None
    sono_medio: float | None = None
    concentracao_media: float | None = None
    classificacoes: Counter = field(default_factory=Counter)


def _media(valores) -> float | None:
    presentes = [v for v in valores if v is not None]
    return round(sum(presentes) / len(presentes), 2) if presentes else None


def _media_por_partida(registros: list[RegistroDia], atributo: str) -> float | None:
    """Média de uma estatística diária (ACS, ADR, HS%) ponderada pelas partidas.

    Um dia com 6 partidas pesa mais que um dia com 1. Se o número de partidas
    não foi registrado, o dia conta com peso 1.
    """
    soma = peso_total = 0
    for registro in registros:
        valor = getattr(registro.valorant, atributo)
        if valor is None:
            continue
        peso = registro.valorant.partidas or 1
        soma += valor * peso
        peso_total += peso
    return round(soma / peso_total, 1) if peso_total else None


def resumir(registros: list[RegistroDia]) -> ResumoPeriodo:
    jogos = [r.valorant for r in registros]

    # Winrate e K/D usam a soma do período (e não a média das médias diárias),
    # para que dias com mais partidas tenham o peso correto.
    com_resultado = [j for j in jogos if j.partidas and j.vitorias is not None]
    partidas_com_resultado = sum(j.partidas for j in com_resultado)
    winrate = (round(sum(j.vitorias for j in com_resultado) / partidas_com_resultado * 100, 1)
               if partidas_com_resultado else None)

    com_kd = [j for j in jogos if j.abates is not None and j.mortes is not None]
    kd = (round(sum(j.abates for j in com_kd) / max(sum(j.mortes for j in com_kd), 1), 2)
          if com_kd else None)

    return ResumoPeriodo(
        dias=len(registros),
        partidas=sum(j.partidas or 0 for j in jogos),
        winrate_pct=winrate,
        kd=kd,
        acs_medio=_media_por_partida(registros, "acs"),
        adr_medio=_media_por_partida(registros, "adr"),
        hs_medio=_media_por_partida(registros, "hs_pct"),
        sono_medio=_media(r.rotina.sono.horas_efetivas for r in registros),
        concentracao_media=_media(j.avaliacao.concentracao for j in jogos),
        classificacoes=Counter(r.classificacao.value for r in registros if r.classificacao),
    )


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
