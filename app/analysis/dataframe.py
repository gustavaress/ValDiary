"""Conversão dos registros para um DataFrame do pandas (uma linha por dia).

É a base de todas as análises: cada métrica de metricas.py vira uma coluna
numérica, e campos não registrados viram NaN (ignorados nas médias).
"""

from datetime import date, timedelta

import pandas as pd

from app.analysis.medicacao import horas_desde_ultimo_medicamento
from app.analysis.metricas import METRICAS
from app.models import RegistroDia

# Classificação como número, para ordenar e correlacionar (5 = excelente).
CLASSIFICACAO_NOTA = {"pessimo": 1, "ruim": 2, "normal": 3, "bom": 4, "excelente": 5}


def hora_decimal(hhmm: str | None, noturno: bool = False) -> float | None:
    """ "19:30" -> 19.5.

    noturno=True trata a madrugada como continuação da noite: "01:30" -> 25.5.
    Assim a média de 23:30 e 00:30 dá 24.0 (meia-noite), e não 12.0 (meio-dia).
    """
    if not hhmm:
        return None
    horas, minutos = hhmm.split(":")
    valor = int(horas) + int(minutos) / 60
    if noturno and valor < 12:
        valor += 24
    return valor


def registros_para_dataframe(registros: list[RegistroDia], rr_por_dia: dict | None = None) -> pd.DataFrame:
    """rr_por_dia: RR de cada dia já considerando a proteção contra rebaixamento
    (ver analysis/ranking.rr_por_dia). Sem ele, usa a soma do RR das partidas."""
    linhas = []
    for registro in registros:
        rotina, jogo = registro.rotina, registro.valorant
        avaliacao = jogo.avaliacao
        resumo = jogo.resumo
        classificacao = registro.classificacao.value if registro.classificacao else None
        linhas.append({
            "data": registro.data,
            "classificacao": classificacao,
            "classificacao_nota": CLASSIFICACAO_NOTA.get(classificacao),
            "sono_horas": rotina.sono.horas_efetivas,
            "sono_qualidade": rotina.sono.qualidade,
            "horario_dormir": hora_decimal(rotina.sono.dormiu_as, noturno=True),
            "agua_litros": rotina.agua_litros,
            "bebidas_qtd": len(rotina.bebidas),
            "disposicao_fisica": rotina.disposicao_fisica,
            "disposicao_mental": rotina.disposicao_mental,
            "estresse": rotina.estresse,
            "inicio_jogo": hora_decimal(jogo.horario_inicio),
            "medicacao_antes_jogo_h": horas_desde_ultimo_medicamento(registro),
            "partidas": resumo.partidas,
            "winrate_pct": resumo.winrate_pct,
            "kd": resumo.kd,
            "kda": resumo.kda,
            "acs": resumo.acs,
            "hs_pct": resumo.hs_pct,
            "rr": rr_por_dia.get(registro.data) if rr_por_dia is not None else resumo.rr,
            "mira": avaliacao.mira,
            "movimentacao": avaliacao.movimentacao,
            "tomada_decisao": avaliacao.tomada_decisao,
            "concentracao": avaliacao.concentracao,
            "consistencia": avaliacao.consistencia,
        })

    colunas_metricas = [m.chave for m in METRICAS]
    df = pd.DataFrame(linhas, columns=["data", "classificacao", "classificacao_nota", *colunas_metricas])
    df["data"] = pd.to_datetime(df["data"])
    df[["classificacao_nota", *colunas_metricas]] = df[["classificacao_nota", *colunas_metricas]].astype("float64")
    return df.sort_values("data").reset_index(drop=True)


def filtrar_periodo(df: pd.DataFrame, ultimos_dias: int | None, hoje: date | None = None) -> pd.DataFrame:
    """Mantém só os últimos N dias (contando hoje). None = todo o período."""
    if ultimos_dias is None:
        return df
    hoje = hoje or date.today()
    inicio = pd.Timestamp(hoje - timedelta(days=ultimos_dias - 1))
    return df[df["data"] >= inicio]
