import json
from datetime import date

import pytest

from app.models import Classificacao, RegistroDia
from app.storage import (
    ArquivoCorrompidoError,
    RegistroDuplicadoError,
    RepositorioDiario,
    VersaoIncompativelError,
)
from app.storage.rascunho import apagar_rascunho, carregar_rascunho, salvar_rascunho


@pytest.fixture
def repo(tmp_path) -> RepositorioDiario:
    # Cada teste recebe uma pasta temporária nova; seus dados reais nunca são tocados.
    return RepositorioDiario(tmp_path / "dados", tmp_path / "dados" / "_backups", max_backups=3)


def _dia(ano, mes, dia, kd_abates=None) -> RegistroDia:
    r = RegistroDia(data=date(ano, mes, dia))
    r.valorant.abates = kd_abates
    return r


def test_cria_arquivo_da_semana_automaticamente(repo):
    repo.salvar_dia(_dia(2026, 11, 2))
    arquivo = repo.pasta_dados / "2026" / "semana_45.json"
    assert arquivo.exists()
    conteudo = json.loads(arquivo.read_text(encoding="utf-8"))
    assert conteudo["semana"] == 45
    assert conteudo["periodo"] == {"inicio": "2026-11-02", "fim": "2026-11-08"}
    assert conteudo["versao_schema"] == 1


def test_dias_da_mesma_semana_vao_para_o_mesmo_arquivo_ordenados(repo):
    repo.salvar_dia(_dia(2026, 11, 5))
    repo.salvar_dia(_dia(2026, 11, 2))
    repo.salvar_dia(_dia(2026, 11, 3))
    datas = [r.data.day for r in repo.carregar_semana(2026, 45)]
    assert datas == [2, 3, 5]
    assert repo.listar_semanas() == [(2026, 45)]


def test_nao_permite_duplicar_data(repo):
    repo.salvar_dia(_dia(2026, 11, 2))
    with pytest.raises(RegistroDuplicadoError):
        repo.salvar_dia(_dia(2026, 11, 2))
    assert len(repo.carregar_semana(2026, 45)) == 1


def test_editar_substitui_e_preserva_os_outros_dias(repo):
    repo.salvar_dia(_dia(2026, 11, 2, kd_abates=10))
    repo.salvar_dia(_dia(2026, 11, 3, kd_abates=20))
    criado_em = repo.obter_dia(date(2026, 11, 2)).criado_em

    editado = _dia(2026, 11, 2, kd_abates=99)
    editado.classificacao = Classificacao.EXCELENTE
    repo.salvar_dia(editado, sobrescrever=True)

    dia2 = repo.obter_dia(date(2026, 11, 2))
    assert dia2.valorant.abates == 99
    assert dia2.classificacao == Classificacao.EXCELENTE
    assert dia2.criado_em == criado_em
    assert dia2.editado_em is not None
    assert repo.obter_dia(date(2026, 11, 3)).valorant.abates == 20


def test_excluir_dia(repo):
    repo.salvar_dia(_dia(2026, 11, 2))
    repo.salvar_dia(_dia(2026, 11, 3))
    assert repo.excluir_dia(date(2026, 11, 2)) is True
    assert repo.excluir_dia(date(2026, 11, 2)) is False
    assert [r.data.day for r in repo.carregar_semana(2026, 45)] == [3]


def test_virada_de_ano_usa_ano_iso(repo):
    repo.salvar_dia(_dia(2027, 1, 1))
    assert (repo.pasta_dados / "2026" / "semana_53.json").exists()
    assert repo.obter_dia(date(2027, 1, 1)) is not None


def test_backup_criado_e_rotacionado(repo):
    for dia in range(2, 8):  # 6 gravações na mesma semana
        repo.salvar_dia(_dia(2026, 11, dia))
    backups = list((repo.pasta_backups / "2026").glob("semana_45_*.json"))
    assert len(backups) == 3  # max_backups=3 no fixture


def test_nao_deixa_arquivo_temporario(repo):
    repo.salvar_dia(_dia(2026, 11, 2))
    assert not list(repo.pasta_dados.rglob("*.tmp"))


def test_arquivo_corrompido_nunca_e_sobrescrito(repo):
    repo.salvar_dia(_dia(2026, 11, 2))
    arquivo = repo.pasta_dados / "2026" / "semana_45.json"
    arquivo.write_text("{ isso não é json", encoding="utf-8")

    with pytest.raises(ArquivoCorrompidoError):
        repo.salvar_dia(_dia(2026, 11, 3))
    assert arquivo.read_text(encoding="utf-8") == "{ isso não é json"


def test_arquivo_corrompido_nao_impede_ler_os_outros(repo):
    repo.salvar_dia(_dia(2026, 11, 2))
    repo.salvar_dia(_dia(2026, 11, 10))  # semana 46
    (repo.pasta_dados / "2026" / "semana_45.json").write_text("lixo", encoding="utf-8")

    registros, problemas = repo.carregar_todos()
    assert [r.data for r in registros] == [date(2026, 11, 10)]
    assert len(problemas) == 1


def test_recusa_arquivo_de_versao_mais_nova(repo):
    arquivo = repo.pasta_dados / "2026" / "semana_45.json"
    arquivo.parent.mkdir(parents=True)
    arquivo.write_text(json.dumps({"versao_schema": 999, "dias": []}), encoding="utf-8")
    with pytest.raises(VersaoIncompativelError):
        repo.salvar_dia(_dia(2026, 11, 2))


def test_pastas_internas_sao_ignoradas_na_listagem(repo):
    repo.salvar_dia(_dia(2026, 11, 2))
    repo.salvar_dia(_dia(2026, 11, 3))  # gera backup em _backups
    assert repo.listar_semanas() == [(2026, 45)]


def test_rascunho(tmp_path):
    caminho = tmp_path / "_rascunho.json"
    assert carregar_rascunho(caminho) is None
    salvar_rascunho({"data": "2026-11-02", "agua": "2,5"}, caminho)
    assert carregar_rascunho(caminho)["formulario"]["agua"] == "2,5"
    apagar_rascunho(caminho)
    assert carregar_rascunho(caminho) is None
