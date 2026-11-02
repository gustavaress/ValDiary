import json
from datetime import date

from app import config
from app.storage import RepositorioDiario
from app.storage.import_export import ler_arquivo
from app.storage.migracoes import migrar_documento


def _documento_v1() -> dict:
    """Arquivo semanal exatamente como a V1 do app gravava."""
    return {
        "versao_schema": 1,
        "ano": 2026,
        "semana": 45,
        "dias": [{
            "data": "2026-11-02",
            "rotina": {"alimentacao": {
                "cafe_da_manha": {"horario": "08:00", "descricao": "Pão"},
                "almoco": {"horario": None, "descricao": None},
                "jantar": {"horario": None, "descricao": "Pizza"},
            }},
            "valorant": {"partidas": 3, "agentes": ["Jett", "Omen"]},
        }],
    }


def test_migracao_v1_para_atual():
    documento = migrar_documento(_documento_v1())
    assert documento["versao_schema"] == config.VERSAO_SCHEMA
    dia = documento["dias"][0]
    alimentacao = dia["rotina"]["alimentacao"]
    assert alimentacao["cafe_da_manha"]["realizada"] is True
    assert alimentacao["almoco"]["realizada"] is None   # nada preenchido
    assert alimentacao["jantar"]["realizada"] is True
    assert dia["valorant"]["agentes"] == [{"nome": "Jett", "partidas": None},
                                          {"nome": "Omen", "partidas": None}]


def test_documento_atual_nao_e_alterado():
    documento = migrar_documento(_documento_v1())
    copia = json.loads(json.dumps(documento))
    assert migrar_documento(documento) == copia


def test_repositorio_le_arquivo_v1_e_grava_como_atual(tmp_path):
    repo = RepositorioDiario(tmp_path / "dados", tmp_path / "dados" / "_backups")
    arquivo = repo.pasta_dados / "2026" / "semana_45.json"
    arquivo.parent.mkdir(parents=True)
    arquivo.write_text(json.dumps(_documento_v1()), encoding="utf-8")

    dia = repo.obter_dia(date(2026, 11, 2))
    assert dia.valorant.nomes_agentes == ["Jett", "Omen"]
    assert dia.rotina.alimentacao.cafe_da_manha.realizada is True

    repo.salvar_dia(dia, sobrescrever=True)
    gravado = json.loads(arquivo.read_text(encoding="utf-8"))
    assert gravado["versao_schema"] == config.VERSAO_SCHEMA
    # A versão v1 original continua guardada no backup.
    backup = next((repo.pasta_backups / "2026").glob("semana_45_*.json"))
    assert json.loads(backup.read_text(encoding="utf-8"))["versao_schema"] == 1


def test_importacao_aceita_exportacao_v1(tmp_path):
    arquivo = tmp_path / "antigo.json"
    arquivo.write_text(json.dumps({"versao_schema": 1, "semanas": [_documento_v1()]}), encoding="utf-8")
    registros = ler_arquivo(arquivo)
    assert registros[0].valorant.nomes_agentes == ["Jett", "Omen"]
