from datetime import date

from app.analysis.resumo import resumir, sequencia_atual
from app.models import Classificacao, RegistroDia


def _dia(dia, partidas=None, vitorias=None, abates=None, mortes=None, acs=None, classificacao=None):
    r = RegistroDia(data=date(2026, 11, dia), classificacao=classificacao)
    # Totais do dia (formato legado): mantém os testes simples e cobre esse caminho.
    r.valorant.legado = {"partidas": partidas, "vitorias": vitorias, "abates": abates,
                         "mortes": mortes, "acs": acs}
    return r


def test_resumo_vazio():
    resumo = resumir([])
    assert resumo.dias == 0
    assert resumo.kd is None and resumo.winrate_pct is None and resumo.acs_medio is None


def test_winrate_e_kd_usam_soma_do_periodo():
    registros = [
        _dia(2, partidas=1, vitorias=1, abates=20, mortes=10),
        _dia(3, partidas=3, vitorias=0, abates=30, mortes=50),
    ]
    resumo = resumir(registros)
    assert resumo.partidas == 4
    assert resumo.winrate_pct == 25.0          # 1 vitória em 4 partidas
    assert resumo.kd == round(50 / 60, 2)      # e não a média de 2,0 e 0,6


def test_acs_ponderado_por_partidas():
    registros = [_dia(2, partidas=1, acs=300), _dia(3, partidas=3, acs=200)]
    assert resumir(registros).acs_medio == 225.0


def test_campos_vazios_sao_ignorados():
    registros = [_dia(2, acs=250), _dia(3)]
    resumo = resumir(registros)
    assert resumo.acs_medio == 250.0
    assert resumo.dias == 2


def test_contagem_de_classificacoes():
    registros = [_dia(2, classificacao=Classificacao.BOM), _dia(3, classificacao=Classificacao.BOM),
                 _dia(4, classificacao=Classificacao.RUIM), _dia(5)]
    assert resumir(registros).classificacoes == {"bom": 2, "ruim": 1}


def test_sequencia_inclui_hoje():
    registros = [_dia(8), _dia(9), _dia(10)]
    assert sequencia_atual(registros, date(2026, 11, 10)) == 3


def test_sequencia_conta_ate_ontem_se_hoje_ainda_nao_foi_registrado():
    registros = [_dia(8), _dia(9)]
    assert sequencia_atual(registros, date(2026, 11, 10)) == 2


def test_sequencia_quebrada():
    registros = [_dia(5), _dia(7), _dia(8)]
    assert sequencia_atual(registros, date(2026, 11, 10)) == 0
