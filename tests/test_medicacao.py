from datetime import date, timedelta

from app.analysis.medicacao import (
    SEM_MEDICAMENTO,
    comparar_medicamentos,
    horas_desde_ultimo_medicamento,
    medicamentos_antes_do_jogo,
)
from app.models import Medicamento, Partida, RegistroDia


def _dia(i: int, inicio="19:00", remedios=(), abates=20, mortes=10) -> RegistroDia:
    r = RegistroDia(data=date(2026, 10, 1) + timedelta(days=i))
    r.valorant.horario_inicio = inicio
    r.valorant.partidas = [Partida(abates=abates, mortes=mortes)]
    r.rotina.medicamentos = [Medicamento(nome, "10mg", horario) for nome, horario in remedios]
    return r


def test_tempo_antes_do_jogo():
    dia = _dia(0, remedios=[("Remédio A", "17:30"), ("Remédio B", "20:00"), ("Remédio C", None)])
    antes = medicamentos_antes_do_jogo(dia)
    assert [(m.nome, m.minutos_antes) for m in antes] == [("Remédio A", 90)]  # B foi depois; C sem horário
    assert antes[0].texto == "Remédio A: tomado 1h30 antes do início"
    assert horas_desde_ultimo_medicamento(dia) == 1.5


def test_sem_horario_de_inicio_nao_cruza():
    assert medicamentos_antes_do_jogo(_dia(0, inicio=None, remedios=[("A", "10:00")])) == []


def test_comparacao_agrupa_por_janela_e_junta_grafias():
    registros = [
        _dia(0, remedios=[("Ritalina", "18:00")], abates=30),   # 1h antes
        _dia(1, remedios=[("ritalina", "18:30")], abates=30),   # 30 min antes (mesmo remédio)
        _dia(2, remedios=[("Ritalina", "14:00")], abates=10),   # 5h antes
        _dia(3, abates=10),                                     # não tomou
    ]
    comparacao = comparar_medicamentos(registros)
    assert [c.nome for c in comparacao] == ["Ritalina"]
    grupos = {g.faixa: g for g in comparacao[0].grupos}
    assert grupos["Até 2h antes"].dias == 2 and grupos["Até 2h antes"].medias["kd"] == 3.0
    assert grupos["Mais de 4h antes"].dias == 1 and grupos["Mais de 4h antes"].medias["kd"] == 1.0
    assert grupos[SEM_MEDICAMENTO].dias == 1
    assert not grupos["Até 2h antes"].suficiente  # menos de 5 dias: sinalizado como poucos dados
