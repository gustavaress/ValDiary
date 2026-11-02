from datetime import date

import pytest

from app.analysis.ranking import evolucao_ranking, ranking_atual, ranking_no_inicio_do_dia
from app.models import Partida, RegistroDia
from app.models.ranking import DefinicaoRanking, Ranking
from app.storage.repositorio import ArquivoCorrompidoError
from app.storage.repositorio_ranking import RepositorioRanking


def _dia(dia: int, *rrs) -> RegistroDia:
    r = RegistroDia(data=date(2026, 11, dia))
    r.valorant.partidas = [Partida(rr=rr) for rr in rrs]
    return r


DEFINICAO = DefinicaoRanking(date(2026, 11, 2), "Ascendente 3", 1)


def test_exemplo_do_jogador_ao_longo_do_dia():
    evolucao = evolucao_ranking([_dia(2, -20, +17)], [DEFINICAO])
    assert evolucao[0].inicio == Ranking("Ascendente 3", 1)
    assert evolucao[0].final == Ranking("Ascendente 3", 17)
    assert evolucao[0].rr == -3 and evolucao[0].redefinido


def test_ranking_continua_de_um_dia_para_o_outro():
    registros = [_dia(2, -20, +17), _dia(3, +20), _dia(5, +70)]
    evolucao = evolucao_ranking(registros, [DEFINICAO])
    assert [e.final for e in evolucao] == [Ranking("Ascendente 3", 17), Ranking("Ascendente 3", 37),
                                          Ranking("Imortal 1", 7)]
    assert ranking_atual(registros, [DEFINICAO]) == Ranking("Imortal 1", 7)


def test_dias_antes_da_primeira_definicao_sao_ignorados():
    assert [e.data.day for e in evolucao_ranking([_dia(1, +20), _dia(2, +5)], [DEFINICAO])] == [2]


def test_nova_definicao_substitui_o_calculo():
    redefinicao = DefinicaoRanking(date(2026, 11, 4), "Diamante 1", 50)
    registros = [_dia(2, +10), _dia(4, +10)]
    evolucao = evolucao_ranking(registros, [DEFINICAO, redefinicao])
    assert evolucao[1].inicio == Ranking("Diamante 1", 50) and evolucao[1].redefinido
    assert ranking_atual(registros, [DEFINICAO, redefinicao]) == Ranking("Diamante 1", 60)


def test_definicao_mais_nova_que_os_dias_vale_como_atual():
    redefinicao = DefinicaoRanking(date(2026, 11, 10), "Ouro 1", 20)
    assert ranking_atual([_dia(2, +10)], [DEFINICAO, redefinicao]) == Ranking("Ouro 1", 20)


def test_sem_definicao_nao_ha_ranking():
    assert ranking_atual([_dia(2, +10)], []) is None
    assert evolucao_ranking([_dia(2, +10)], []) == []


def test_ranking_no_inicio_de_um_dia_ignora_o_proprio_dia_e_os_seguintes():
    registros = [_dia(2, +10), _dia(3, +5), _dia(4, +50)]
    assert ranking_no_inicio_do_dia(date(2026, 11, 4), registros, [DEFINICAO]) == Ranking("Ascendente 3", 16)
    assert ranking_no_inicio_do_dia(date(2026, 11, 2), registros, [DEFINICAO]) == Ranking("Ascendente 3", 1)
    assert ranking_no_inicio_do_dia(date(2026, 11, 1), registros, [DEFINICAO]) is None


def test_repositorio_de_definicoes(tmp_path):
    repo = RepositorioRanking(tmp_path / "dados", tmp_path / "dados" / "_backups")
    assert repo.carregar() == []
    repo.definir(date(2026, 11, 2), "Ascendente 3", 1)
    repo.definir(date(2026, 11, 9), "Imortal 1", 30)
    repo.definir(date(2026, 11, 2), "Ascendente 2", 50)  # mesma data: substitui
    assert [(d.data.day, d.elo, d.rr) for d in repo.carregar()] == [(2, "Ascendente 2", 50), (9, "Imortal 1", 30)]
    repo.remover(date(2026, 11, 9))
    assert [d.data.day for d in repo.carregar()] == [2]


def test_arquivo_de_ranking_corrompido(tmp_path):
    repo = RepositorioRanking(tmp_path, tmp_path / "_backups")
    repo.arquivo.write_text("{ quebrado", encoding="utf-8")
    with pytest.raises(ArquivoCorrompidoError):
        repo.carregar()


def test_ranking_atual_com_data_do_ultimo_dia():
    from app.analysis.ranking import ranking_atual_com_data
    registros = [_dia(1, -20, +17)]
    definicao = DefinicaoRanking(date(2026, 11, 1), "Ascendente 3", 1)
    assert ranking_atual_com_data(registros, [definicao]) == (Ranking("Ascendente 3", 17), date(2026, 11, 1))
    ajuste_futuro = DefinicaoRanking(date(2026, 11, 5), "Imortal 1", 10)
    assert ranking_atual_com_data(registros, [definicao, ajuste_futuro]) == (Ranking("Imortal 1", 10), None)


def test_ranking_salvo_e_preservado_ao_mexer_nas_definicoes(tmp_path):
    from app.storage.repositorio_ranking import RankingSalvo
    repo = RepositorioRanking(tmp_path / "dados", tmp_path / "dados" / "_backups")
    repo.definir(date(2026, 11, 1), "Ascendente 3", 1)
    assert repo.carregar_atual() is None

    salvo = RankingSalvo(Ranking("Ascendente 3", 17), date(2026, 11, 1))
    assert repo.salvar_atual(salvo) is True
    assert repo.salvar_atual(salvo) is False        # sem mudança: não regrava
    assert repo.carregar_atual() == salvo

    repo.definir(date(2026, 11, 9), "Imortal 1", 30)  # ajuste não apaga o ranking salvo
    assert repo.carregar_atual() == salvo
    assert [d.data.day for d in repo.carregar()] == [1, 9]
