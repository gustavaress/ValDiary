import pytest

from app.models.ranking import ELOS, Ranking, aplicar_partida, aplicar_partidas, erros_definicao


def test_exemplo_do_jogador():
    # Ascendente 3 com 1 RR: perde 20 (protegido, zera) e ganha 17.
    assert aplicar_partidas(Ranking("Ascendente 3", 1), [-20, +17]) == Ranking("Ascendente 3", 17)


@pytest.mark.parametrize("inicio, variacao, esperado", [
    (("Ouro 2", 45), +20, ("Ouro 2", 65)),           # sem mudar de divisão
    (("Ouro 2", 85), +38, ("Ouro 3", 23)),           # promoção
    (("Ouro 3", 90), +15, ("Platina 1", 5)),         # muda de tier
    (("Ouro 2", 30), -18, ("Ouro 2", 12)),           # perda normal
    (("Ouro 2", 10), -25, ("Ouro 2", 0)),            # proteção: zera, não rebaixa
    (("Ouro 2", 0), -20, ("Ouro 1", 80)),            # com 0 RR, rebaixa
    (("Platina 1", 0), -15, ("Ouro 3", 85)),         # rebaixa de tier
    (("Ferro 1", 0), -30, ("Ferro 1", 0)),           # Ferro 1 é o piso
    (("Ascendente 3", 95), +20, ("Imortal 1", 15)),  # entra no Imortal
    (("Imortal 1", 80), +60, ("Imortal 1", 140)),    # no topo o RR acumula
    (("Imortal 1", 10), -30, ("Imortal 1", 0)),      # proteção também no topo
    (("Imortal 1", 0), -20, ("Ascendente 3", 80)),   # sai do Imortal
])
def test_aplicar_partida(inicio, variacao, esperado):
    assert aplicar_partida(Ranking(*inicio), variacao) == Ranking(*esperado)


def test_ordem_das_partidas_importa():
    # Mesma soma (-3), resultados diferentes por causa da proteção.
    assert aplicar_partidas(Ranking("Ouro 2", 5), [-20, +17]) == Ranking("Ouro 2", 17)
    assert aplicar_partidas(Ranking("Ouro 2", 5), [+17, -20]) == Ranking("Ouro 2", 2)


def test_elos_em_ordem():
    assert ELOS[0] == "Ferro 1" and ELOS[-1] == "Radiante" and len(ELOS) == 25


def test_validacao_da_definicao():
    assert erros_definicao("Ouro 2", 50) == []
    assert erros_definicao("Imortal 2", 350) == []   # topo não tem teto
    assert erros_definicao("Ouro 2", 100)             # 100 já seria promoção
    assert erros_definicao("Ouro 2", -1)
    assert erros_definicao(None, 10)
    assert erros_definicao("Ouro 2", None)
