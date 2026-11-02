from datetime import date

from app.analysis.filtros import filtrar
from app.models import Classificacao, RegistroDia

HOJE = date(2026, 11, 10)


def _dia(dia: int, classificacao=None, notas=None) -> RegistroDia:
    r = RegistroDia(data=date(2026, 11, dia), classificacao=classificacao)
    r.valorant.notas = notas
    return r


REGISTROS = [
    _dia(1, Classificacao.BOM, "Mira muito consistente"),
    _dia(5, Classificacao.RUIM, "Estava muito ansioso nos confrontos"),
    _dia(9, Classificacao.BOM),
    _dia(10),
]


def test_sem_filtros_retorna_tudo_do_mais_recente_para_o_mais_antigo():
    assert [r.data.day for r in filtrar(REGISTROS, hoje=HOJE)] == [10, 9, 5, 1]


def test_filtro_por_classificacao():
    assert [r.data.day for r in filtrar(REGISTROS, classificacao="bom", hoje=HOJE)] == [9, 1]


def test_filtro_por_periodo():
    # Últimos 7 dias contando hoje: 04/11 a 10/11.
    assert [r.data.day for r in filtrar(REGISTROS, ultimos_dias=7, hoje=HOJE)] == [10, 9, 5]


def test_busca_ignora_maiusculas_e_acentos():
    assert [r.data.day for r in filtrar(REGISTROS, busca="ANSIÓSO", hoje=HOJE)] == [5]


def test_filtros_combinados():
    assert filtrar(REGISTROS, classificacao="bom", busca="ansioso", hoje=HOJE) == []
