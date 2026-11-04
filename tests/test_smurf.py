"""Partidas na smurf (sem RR) e elo médio dos inimigos."""

from datetime import date

from app.analysis.desempenho import desempenho_por
from app.analysis.ranking import evolucao_ranking
from app.models import Partida, RegistroDia, validar_registro
from app.models.ranking import DefinicaoRanking, Ranking
from app.ui.mapeamento_registro import formulario_para_registro, registro_para_formulario

DIA = date(2026, 11, 4)


def _formulario(*partidas):
    formulario = registro_para_formulario(RegistroDia(data=DIA))
    formulario["partidas"] = list(partidas)
    return formulario


def test_smurf_descarta_o_rr_e_guarda_as_estatisticas():
    registro, erros = formulario_para_registro(_formulario(
        {"agente": "Jett", "resultado": "vitoria", "abates": "25", "mortes": "10", "rr": "+20", "smurf": True,
         "elo_inimigos": "Ouro 2"},
        {"agente": "Omen", "resultado": "derrota", "rr": "-15", "smurf": False}))
    smurf, main = registro.valorant.partidas
    assert erros == []
    assert (smurf.smurf, smurf.rr, smurf.abates, smurf.elo_inimigos) == (True, None, 25, "Ouro 2")
    assert (main.smurf, main.rr) == (False, -15)
    assert registro.valorant.resumo.rr == -15 and registro.valorant.resumo.partidas == 2


def test_smurf_nao_mexe_no_ranking():
    registro = RegistroDia(data=DIA)
    registro.valorant.partidas = [Partida("Jett", "vitoria", rr=30, smurf=True), Partida("Jett", "vitoria", rr=18)]
    evolucao = evolucao_ranking([registro], [DefinicaoRanking(DIA, "Ascendente 3", 1)])
    assert evolucao[0].final == Ranking("Ascendente 3", 19)


def test_validacao():
    registro = RegistroDia(data=DIA)
    registro.valorant.partidas = [Partida("Jett", rr=10, smurf=True), Partida("Jett", elo_inimigos="Mestre 1")]
    erros = validar_registro(registro)
    assert any("smurf não vale RR" in e for e in erros) and any("elo dos inimigos" in e for e in erros)


def test_json_e_partidas_antigas():
    registro = RegistroDia(data=DIA)
    registro.valorant.partidas = [Partida("Jett", smurf=True, elo_inimigos="Imortal 1")]
    assert RegistroDia.from_dict(registro.to_dict()).to_dict() == registro.to_dict()
    antiga = Partida(**{"agente": "Jett", "rr": 10})  # salva antes da v6: main, sem elo
    assert (antiga.smurf, antiga.elo_inimigos, antiga.conta) == (False, None, "Main")


def test_desempenho_por_conta_e_tier_inimigo():
    registro = RegistroDia(data=DIA)
    registro.valorant.partidas = [Partida("Jett", "vitoria", smurf=True, elo_inimigos="Ouro 2"),
                                  Partida("Jett", "derrota", elo_inimigos="Ascendente 3"),
                                  Partida("Jett", "vitoria", elo_inimigos="Ascendente 1")]
    por_conta = {l.nome: l.partidas for l in desempenho_por([registro], "conta")}
    assert por_conta == {"Main": 2, "Smurf": 1}
    por_tier = {l.nome: l.winrate_pct for l in desempenho_por([registro], "tier_inimigos")}
    assert por_tier == {"Ascendente": 50, "Ouro": 100}
