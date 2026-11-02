"""Emblemas dos ranks: todo elo do app tem uma imagem em assets/ranks."""

from app.models.ranking import ELOS
from app.ui.componentes.emblema_rank import arquivo_rank


def test_todo_elo_tem_emblema():
    faltando = [elo for elo in ELOS if not arquivo_rank(elo).exists()]
    assert faltando == []


def test_nome_do_arquivo():
    assert arquivo_rank("Ascendente 3").name == "Ascendant_3_Rank.png"
    assert arquivo_rank("Radiante").name == "Radiant_Rank.png"
    assert arquivo_rank("Desconhecido 1") is None
