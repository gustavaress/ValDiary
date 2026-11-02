import pytest

from app.models.ranking import ELOS, Ranking, aplicar_rr, erros_ranking


@pytest.mark.parametrize("inicio, variacao, esperado", [
    (("Ouro 2", 45), +20, ("Ouro 2", 65)),          # sem mudar de divisão
    (("Ouro 2", 85), +38, ("Ouro 3", 23)),          # promoção
    (("Ouro 3", 90), +15, ("Platina 1", 5)),        # muda de tier
    (("Ouro 2", 10), -25, ("Ouro 1", 85)),          # rebaixamento
    (("Platina 1", 5), -20, ("Ouro 3", 85)),        # cai de tier
    (("Ferro 1", 10), -30, ("Ferro 1", 0)),         # Ferro 1 é o piso
    (("Ascendente 3", 95), +20, ("Imortal 1", 15)), # entra no Imortal
    (("Imortal 1", 80), +60, ("Imortal 1", 140)),   # no topo o RR acumula
    (("Imortal 1", 10), -30, ("Ascendente 3", 80)), # sai do Imortal
    (("Ouro 2", 50), 0, ("Ouro 2", 50)),
])
def test_aplicar_rr(inicio, variacao, esperado):
    resultado = aplicar_rr(Ranking(*inicio), variacao)
    assert (resultado.elo, resultado.rr) == esperado


def test_varias_divisoes_de_uma_vez():
    assert aplicar_rr(Ranking("Prata 1", 50), +260) == Ranking("Ouro 1", 10)


def test_elos_em_ordem():
    assert ELOS[0] == "Ferro 1" and ELOS[-1] == "Radiante" and len(ELOS) == 25


def test_validacao_do_ranking():
    assert erros_ranking(Ranking("Ouro 2", 50), "x") == []
    assert erros_ranking(Ranking("Imortal 2", 350), "x") == []   # topo não tem teto
    assert erros_ranking(Ranking("Ouro 2", 150), "x")
    assert erros_ranking(Ranking("Ouro 2", -1), "x")
    assert erros_ranking(Ranking("Mestre", 10), "x")
