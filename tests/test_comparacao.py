from datetime import date, timedelta

from app.analysis.comparacao import (
    MIN_DIAS_CORRELACAO,
    comparar_grupos,
    correlacoes,
    frequencias_habitos,
)
from app.analysis.dataframe import registros_para_dataframe
from app.models import Bebida, Classificacao, RegistroDia

INICIO = date(2026, 10, 1)


def _dia(i: int, classificacao, sono=None, mira=None, bebida=None) -> RegistroDia:
    r = RegistroDia(data=INICIO + timedelta(days=i), classificacao=classificacao)
    r.rotina.sono.horas = sono
    r.valorant.avaliacao.mira = mira
    if bebida:
        r.rotina.bebidas = [Bebida(tipo=bebida)]
    return r


def _linha(linhas, chave):
    return next(l for l in linhas if l.metrica.chave == chave)


def test_medias_por_grupo_e_n():
    registros = [
        _dia(0, Classificacao.EXCELENTE, sono=8), _dia(1, Classificacao.BOM, sono=7),
        _dia(2, Classificacao.RUIM, sono=5), _dia(3, Classificacao.PESSIMO, sono=4),
        _dia(4, Classificacao.NORMAL, sono=10),  # dias normais não entram em nenhum grupo
        _dia(5, Classificacao.BOM),              # sem sono registrado: não conta no n
    ]
    linha = _linha(comparar_grupos(registros_para_dataframe(registros)), "sono_horas")
    assert linha.media_bons == 7.5 and linha.n_bons == 2
    assert linha.media_ruins == 4.5 and linha.n_ruins == 2
    assert linha.diferenca == 3.0
    assert linha.suficiente is False  # menos de 5 dias por grupo


def test_grupo_vazio_nao_quebra():
    registros = [_dia(0, Classificacao.BOM, sono=8)]
    linha = _linha(comparar_grupos(registros_para_dataframe(registros)), "sono_horas")
    assert linha.media_ruins is None and linha.diferenca is None


def test_correlacao_positiva_com_dados_suficientes():
    ordem = [Classificacao.PESSIMO, Classificacao.RUIM, Classificacao.NORMAL, Classificacao.BOM,
             Classificacao.EXCELENTE]
    # Mira acompanha a classificação: dias melhores, mira mais alta.
    registros = [_dia(i, ordem[i % 5], mira=2 + (i % 5) * 2) for i in range(MIN_DIAS_CORRELACAO)]
    resultado = {c.metrica.chave: c for c in correlacoes(registros_para_dataframe(registros))}
    mira = resultado["mira"]
    assert mira.suficiente and mira.rho == 1.0
    assert mira.forca == "forte"
    assert "melhores" in mira.leitura
    assert correlacoes(registros_para_dataframe(registros))[0].metrica.chave == "mira"  # mais forte primeiro


def test_correlacao_com_poucos_dados_e_sinalizada():
    registros = [_dia(i, c, mira=m) for i, (c, m) in enumerate(
        [(Classificacao.BOM, 8), (Classificacao.RUIM, 3), (Classificacao.EXCELENTE, 9)])]
    mira = next(c for c in correlacoes(registros_para_dataframe(registros)) if c.metrica.chave == "mira")
    assert mira.rho is not None
    assert not mira.suficiente
    assert "Poucos dados" in mira.leitura


def test_correlacao_sem_variacao():
    registros = [_dia(i, Classificacao.BOM, mira=7) for i in range(12)]
    mira = next(c for c in correlacoes(registros_para_dataframe(registros)) if c.metrica.chave == "mira")
    assert mira.rho is None and not mira.suficiente


def test_habitos_agrupam_grafias_e_calculam_percentuais():
    registros = [
        _dia(0, Classificacao.BOM, bebida="Café"), _dia(1, Classificacao.BOM, bebida="cafe"),
        _dia(2, Classificacao.BOM), _dia(3, Classificacao.RUIM, bebida="Energético"),
        _dia(4, Classificacao.PESSIMO, bebida="energetico"),
    ]
    habitos = {h.item: h for h in frequencias_habitos(registros)}
    cafe = habitos["Bebida: Café"]
    assert (cafe.dias_bons, cafe.total_bons, cafe.dias_ruins) == (2, 3, 0)
    assert round(cafe.pct_bons) == 67
    energetico = habitos["Bebida: Energético"]
    assert energetico.pct_ruins == 100 and energetico.pct_bons == 0
