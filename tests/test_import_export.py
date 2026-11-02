import json
from datetime import date

import pytest

from app.models import Classificacao, Partida, RegistroDia
from app.storage import RepositorioDiario
from app.storage.import_export import (
    ErroImportacao,
    aplicar_importacao,
    exportar,
    ler_arquivo,
    nome_arquivo_sugerido,
    planejar_importacao,
)


def _repo(pasta) -> RepositorioDiario:
    return RepositorioDiario(pasta / "dados", pasta / "dados" / "_backups")


def _dia(dia: int, abates=None, classificacao=None) -> RegistroDia:
    r = RegistroDia(data=date(2026, 11, dia), classificacao=classificacao)
    r.valorant.partidas = [Partida(abates=abates)] if abates is not None else []
    return r


@pytest.fixture
def origem(tmp_path) -> RepositorioDiario:
    repo = _repo(tmp_path / "origem")
    for dia in (2, 3, 10):  # semanas 45 e 46
        repo.salvar_dia(_dia(dia, abates=dia * 10, classificacao=Classificacao.BOM))
    return repo


def test_exportar_gera_pacote_com_legenda(origem, tmp_path):
    destino = exportar(origem, [(2026, 45), (2026, 46)], tmp_path / "pacote.json")
    pacote = json.loads(destino.read_text(encoding="utf-8"))
    assert pacote["formato"] == "valdiary-exportacao"
    assert "_legenda" in pacote
    assert [s["semana"] for s in pacote["semanas"]] == [45, 46]
    assert len(pacote["semanas"][0]["dias"]) == 2


def test_nome_sugerido():
    assert nome_arquivo_sugerido([(2026, 45)]) == "valdiary_2026-S45.json"
    assert nome_arquivo_sugerido([(2026, 46), (2026, 5)]) == "valdiary_2026-S05_a_2026-S46.json"


def test_exportar_e_importar_em_repositorio_vazio(origem, tmp_path):
    arquivo = exportar(origem, [(2026, 45), (2026, 46)], tmp_path / "pacote.json")
    destino = _repo(tmp_path / "destino")

    plano = planejar_importacao(destino, ler_arquivo(arquivo))
    assert len(plano.novos) == 3 and not plano.conflitos and not plano.identicos
    assert aplicar_importacao(destino, plano, substituir_conflitos=False) == 3

    registros, _ = destino.carregar_todos()
    assert [r.valorant.resumo.abates for r in registros] == [20, 30, 100]


def test_importar_de_novo_nao_duplica(origem, tmp_path):
    arquivo = exportar(origem, [(2026, 45)], tmp_path / "pacote.json")
    plano = planejar_importacao(origem, ler_arquivo(arquivo))
    assert len(plano.identicos) == 2 and not plano.novos and not plano.conflitos


def test_conflitos_respeitam_a_escolha(origem, tmp_path):
    arquivo = exportar(origem, [(2026, 45)], tmp_path / "pacote.json")
    destino = _repo(tmp_path / "destino")
    destino.salvar_dia(_dia(2, abates=999))

    plano = planejar_importacao(destino, ler_arquivo(arquivo))
    assert len(plano.conflitos) == 1 and len(plano.novos) == 1

    aplicar_importacao(destino, plano, substituir_conflitos=False)
    assert destino.obter_dia(date(2026, 11, 2)).valorant.resumo.abates == 999  # manteve o seu
    assert destino.obter_dia(date(2026, 11, 3)) is not None

    plano = planejar_importacao(destino, ler_arquivo(arquivo))
    aplicar_importacao(destino, plano, substituir_conflitos=True)
    assert destino.obter_dia(date(2026, 11, 2)).valorant.resumo.abates == 20   # substituiu


def test_importa_arquivo_semanal_cru(origem):
    arquivo = origem.pasta_dados / "2026" / "semana_45.json"
    assert len(ler_arquivo(arquivo)) == 2


def test_importacao_gera_um_backup_por_semana(origem, tmp_path):
    arquivo = exportar(origem, [(2026, 45)], tmp_path / "pacote.json")
    destino = _repo(tmp_path / "destino")
    destino.salvar_dia(_dia(4))  # cria a semana 45 no destino
    aplicar_importacao(destino, planejar_importacao(destino, ler_arquivo(arquivo)), False)
    assert len(list((destino.pasta_backups / "2026").glob("semana_45_*.json"))) == 1


@pytest.mark.parametrize("conteudo", ["isso não é json", '{"outra": "coisa"}', "[1, 2, 3]"])
def test_arquivos_invalidos_sao_recusados(tmp_path, conteudo):
    arquivo = tmp_path / "x.json"
    arquivo.write_text(conteudo, encoding="utf-8")
    with pytest.raises(ErroImportacao):
        ler_arquivo(arquivo)


def test_dia_com_valor_invalido_e_recusado(tmp_path):
    arquivo = tmp_path / "x.json"
    dia = _dia(2).to_dict()
    dia["rotina"]["estresse"] = 50
    arquivo.write_text(json.dumps({"dias": [dia]}), encoding="utf-8")
    with pytest.raises(ErroImportacao, match="Estresse"):
        ler_arquivo(arquivo)


def test_versao_futura_e_recusada(tmp_path):
    arquivo = tmp_path / "x.json"
    arquivo.write_text(json.dumps({"versao_schema": 99, "dias": []}), encoding="utf-8")
    with pytest.raises(ErroImportacao, match="v99"):
        ler_arquivo(arquivo)
