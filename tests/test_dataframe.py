from datetime import date

import pandas as pd

from app.analysis.dataframe import filtrar_periodo, hora_decimal, registros_para_dataframe
from app.analysis.metricas import METRICAS
from app.models import Bebida, Classificacao, RegistroDia


def test_hora_decimal():
    assert hora_decimal("19:30") == 19.5
    assert hora_decimal("01:30") == 1.5
    assert hora_decimal("01:30", noturno=True) == 25.5
    assert hora_decimal("23:30", noturno=True) == 23.5
    assert hora_decimal(None) is None


def test_media_de_horario_noturno_faz_sentido():
    # 23:30 e 00:30 -> média meia-noite (24.0), e não meio-dia.
    media = (hora_decimal("23:30", True) + hora_decimal("00:30", True)) / 2
    assert media == 24.0


def test_dataframe_tem_todas_as_metricas_e_nan_para_vazios():
    r1 = RegistroDia(data=date(2026, 11, 3), classificacao=Classificacao.BOM)
    r1.valorant.abates, r1.valorant.mortes = 30, 20
    r1.rotina.bebidas = [Bebida("café"), Bebida("energético")]
    r2 = RegistroDia(data=date(2026, 11, 2))

    df = registros_para_dataframe([r1, r2])
    assert list(df["data"].dt.day) == [2, 3]  # ordenado por data
    for metrica in METRICAS:
        assert metrica.chave in df.columns
        assert df[metrica.chave].dtype == "float64"
    assert df.loc[1, "kd"] == 1.5
    assert df.loc[1, "bebidas_qtd"] == 2
    assert df.loc[1, "classificacao_nota"] == 4
    assert pd.isna(df.loc[0, "kd"])
    assert df["kd"].mean() == 1.5  # NaN é ignorado na média


def test_dataframe_vazio():
    df = registros_para_dataframe([])
    assert df.empty
    assert "kd" in df.columns


def test_filtrar_periodo():
    registros = [RegistroDia(data=date(2026, 11, d)) for d in (1, 5, 10)]
    df = registros_para_dataframe(registros)
    assert len(filtrar_periodo(df, 7, hoje=date(2026, 11, 10))) == 2  # 04/11 a 10/11
    assert len(filtrar_periodo(df, None)) == 3
