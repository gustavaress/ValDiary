"""Funcionalidades da V4: mapa por partida, aim routine, aquecimento e insights."""

from datetime import date, timedelta

from app.analysis.comparacao import frequencias_habitos
from app.analysis.desempenho import aim_routines_por_semana, desempenho_por
from app.analysis.insights import gerar_insights
from app.models import AimRoutine, Classificacao, ExercicioAim, Partida, RegistroDia
from app.storage.repositorio_aim import ROTINA_INICIAL, RepositorioAim
from app.ui.mapeamento_registro import formulario_para_registro, registro_para_formulario

HOJE = date(2026, 11, 2)


def _dia(i: int, classificacao=None, partidas=(), sono=None, aim=None) -> RegistroDia:
    r = RegistroDia(data=HOJE - timedelta(days=i), classificacao=classificacao)
    r.valorant.partidas = list(partidas)
    r.rotina.sono.horas = sono
    r.valorant.aim_routine.feita = aim
    return r


def test_desempenho_por_mapa_e_agente():
    registros = [_dia(0, partidas=[Partida("Jett", "vitoria", 20, 10, rr=20, mapa="Ascent"),
                                   Partida("Jett", "derrota", 10, 20, rr=-15, mapa="Bind")]),
                 _dia(1, partidas=[Partida("Omen", "vitoria", 15, 15, rr=18, mapa="Ascent")])]
    por_mapa = {l.nome: l for l in desempenho_por(registros, "mapa")}
    assert por_mapa["Ascent"].partidas == 2 and por_mapa["Ascent"].winrate_pct == 100
    assert por_mapa["Ascent"].kd == round(35 / 25, 2) and por_mapa["Bind"].rr_medio == -15
    assert [l.nome for l in desempenho_por(registros, "agente")] == ["Jett", "Omen"]  # mais jogado primeiro


def test_aim_routines_por_semana():
    registros = [_dia(0, aim=True), _dia(1, aim=True), _dia(8, aim=True), _dia(2, aim=False)]
    semanas = aim_routines_por_semana(registros, HOJE, semanas=3)
    assert [n for _, n in semanas] == [0, 1, 2]  # semana atual (domingo 01/11) por último


def test_aim_routine_pelo_formulario():
    formulario = registro_para_formulario(RegistroDia(data=HOJE))
    formulario["aim_exercicios"] = [{"nome": "Tracking", "meta": "5 minutos", "feito": True},
                                    {"nome": "Hard Bots", "meta": "10", "feito": False}]
    formulario["aim_duracao"] = "40"
    registro, erros = formulario_para_registro(formulario)
    aim = registro.valorant.aim_routine
    assert erros == [] and aim.feita is True and aim.duracao_min == 40  # marcou exercício: fez
    assert [e.nome for e in aim.exercicios_feitos] == ["Tracking"]

    # Lista da rotina padrão sem nada marcado e "não fez": não guarda os exercícios.
    formulario["aim_exercicios"][0]["feito"] = False
    formulario["aim_feita"] = "nao"
    registro, _ = formulario_para_registro(formulario)
    assert registro.valorant.aim_routine.exercicios == []


def test_aquecimento_descricao_so_vale_se_fez():
    formulario = registro_para_formulario(RegistroDia(data=HOJE))
    formulario["aquecimento"], formulario["aquecimento_descricao"] = "nao", "texto que sobrou"
    registro, _ = formulario_para_registro(formulario)
    assert registro.valorant.aquecimento is False and registro.valorant.aquecimento_descricao is None
    formulario["aquecimento"] = "sim"
    registro, _ = formulario_para_registro(formulario)
    assert registro.valorant.aquecimento_descricao == "texto que sobrou"


def test_mapa_e_treino_atravessam_o_json():
    r = RegistroDia(data=HOJE)
    r.valorant.partidas = [Partida("Jett", "vitoria", mapa="Lotus")]
    r.valorant.aquecimento = True
    r.valorant.aim_routine = AimRoutine(True, 30, [ExercicioAim("Tracking", "5 min", True)])
    assert RegistroDia.from_dict(r.to_dict()).to_dict() == r.to_dict()


def test_rotina_padrao(tmp_path):
    repo = RepositorioAim(tmp_path)
    assert [e.nome for e in repo.carregar_padrao()] == [e.nome for e in ROTINA_INICIAL]
    repo.salvar_padrao([ExercicioAim("Gridshot", "3x")])
    assert [(e.nome, e.meta) for e in repo.carregar_padrao()] == [("Gridshot", "3x")]


def test_habitos_incluem_treino():
    registros = [_dia(i, Classificacao.BOM, aim=True) for i in range(2)] + [_dia(5, Classificacao.RUIM)]
    itens = {h.item for h in frequencias_habitos(registros)}
    assert "Treino: aim routine" in itens


def test_insights_pedem_mais_dados_quando_faltam_dias():
    insights = gerar_insights([_dia(i, Classificacao.BOM) for i in range(3)])
    assert insights.frases == [] and "Faltam 2 dia(s) bom(ns) e 5 dia(s) ruim(ns)" in insights.aviso


def test_insights_encontram_diferencas_relevantes():
    bons = [_dia(i, Classificacao.BOM, sono=8 + (i % 2) * 0.5, aim=True) for i in range(6)]
    ruins = [_dia(10 + i, Classificacao.RUIM, sono=6 + (i % 2) * 0.5, aim=False) for i in range(6)]
    frases = gerar_insights(bons + ruins).frases
    assert any(f.startswith("Horas de sono: em média 8,2h nos dias bons") for f in frases)
    assert any("aim routine em 100% dos dias bons e em 0% dos dias ruins" in f for f in frases)
    assert len(frases) <= 4


def test_nao_jogou_descarta_os_dados_de_jogo_mas_mantem_a_aim_routine():
    formulario = registro_para_formulario(RegistroDia(data=HOJE))
    formulario.update(jogou="nao", jogo_inicio="20:00", mira=8, notas_jogo="sobrou", aquecimento="sim",
                      partidas=[{"agente": "Jett", "resultado": "vitoria", "abates": "20", "rr": "+18"}],
                      aim_exercicios=[{"nome": "Tracking", "meta": "5 min", "feito": True}])
    registro, erros = formulario_para_registro(formulario)
    jogo = registro.valorant
    assert erros == [] and jogo.jogou is False
    assert (jogo.horario_inicio, jogo.partidas, jogo.avaliacao.mira, jogo.notas, jogo.aquecimento) == (None, [], None, None, None)
    assert jogo.aim_routine.feita is True
