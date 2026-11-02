from datetime import date

from app.models.datas import data_livre_mais_recente, erro_data_nova, proxima_data_livre

HOJE = date(2026, 11, 10)
REGISTRADAS = {date(2026, 11, 10), date(2026, 11, 9), date(2026, 11, 7)}


def test_data_livre_e_aceita():
    assert erro_data_nova(date(2026, 11, 8), REGISTRADAS, HOJE) is None


def test_data_ja_registrada_e_recusada():
    erro = erro_data_nova(date(2026, 11, 9), REGISTRADAS, HOJE)
    assert "09/11/2026 já tem um registro" in erro


def test_data_futura_e_recusada():
    assert "ainda não aconteceu" in erro_data_nova(date(2026, 11, 11), REGISTRADAS, HOJE)


def test_setas_pulam_dias_registrados():
    # Voltando a partir de 10/11: 10 e 9 estão registrados -> 08/11.
    assert proxima_data_livre(date(2026, 11, 10), -1, REGISTRADAS, HOJE) == date(2026, 11, 8)
    # Voltando a partir de 07/11 (registrado) -> 06/11.
    assert proxima_data_livre(date(2026, 11, 7), -1, REGISTRADAS, HOJE) == date(2026, 11, 6)


def test_setas_nao_vao_para_o_futuro():
    assert proxima_data_livre(date(2026, 11, 9), +1, REGISTRADAS, HOJE) is None
    assert proxima_data_livre(date(2026, 11, 7), +1, REGISTRADAS, HOJE) == date(2026, 11, 8)


def test_data_livre_mais_recente():
    assert data_livre_mais_recente(REGISTRADAS, HOJE) == date(2026, 11, 8)
    assert data_livre_mais_recente(set(), HOJE) == HOJE
