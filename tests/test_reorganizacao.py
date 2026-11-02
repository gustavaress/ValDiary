import json
from datetime import date

from app.models import RegistroDia
from app.storage import RepositorioDiario
from app.storage.reorganizacao import ARQUIVO_MARCADOR, reorganizar_se_preciso


def _arquivo_antigo(repo: RepositorioDiario, ano: int, semana: int, datas: list[date]) -> None:
    """Grava um arquivo semanal como a v3 gravava (semana de segunda a domingo)."""
    arquivo = repo.pasta_dados / str(ano) / f"semana_{semana:02d}.json"
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    dias = []
    for d in datas:
        dia = RegistroDia(data=d).to_dict()
        dia["valorant"]["notas"] = f"dia {d.day}"
        dias.append(dia)
    arquivo.write_text(json.dumps({"versao_schema": 3, "ano": ano, "semana": semana, "dias": dias}),
                       encoding="utf-8")


def _repo(tmp_path) -> RepositorioDiario:
    return RepositorioDiario(tmp_path / "dados", tmp_path / "dados" / "_backups")


def test_reorganiza_domingos_para_a_semana_seguinte(tmp_path):
    repo = _repo(tmp_path)
    # Semana ISO 44 de 2026 = seg 26/10 a dom 01/11. O domingo 01/11 agora é da semana 45.
    _arquivo_antigo(repo, 2026, 44, [date(2026, 10, 26), date(2026, 11, 1)])
    _arquivo_antigo(repo, 2026, 45, [date(2026, 11, 2)])

    resultado = reorganizar_se_preciso(repo)
    assert resultado.dias == 3 and not resultado.ignorados

    assert [r.data.day for r in repo.carregar_semana(2026, 44)] == [26]
    assert [r.data.day for r in repo.carregar_semana(2026, 45)] == [1, 2]
    assert repo.obter_dia(date(2026, 11, 1)).valorant.notas == "dia 1"  # conteúdo preservado
    # Backup com os arquivos originais e marcador gravado.
    assert len(list(resultado.backup.rglob("semana_*.json"))) == 2
    assert (repo.pasta_dados / ARQUIVO_MARCADOR).exists()
    assert not (repo.pasta_dados / "_reorganizando").exists()


def test_roda_uma_vez_so(tmp_path):
    repo = _repo(tmp_path)
    _arquivo_antigo(repo, 2026, 45, [date(2026, 11, 2)])
    assert reorganizar_se_preciso(repo) is not None
    assert reorganizar_se_preciso(repo) is None


def test_app_novo_so_grava_o_marcador(tmp_path):
    repo = _repo(tmp_path)
    assert reorganizar_se_preciso(repo) is None
    assert (repo.pasta_dados / ARQUIVO_MARCADOR).exists()


def test_arquivo_corrompido_fica_no_backup_e_e_informado(tmp_path):
    repo = _repo(tmp_path)
    _arquivo_antigo(repo, 2026, 45, [date(2026, 11, 2)])
    corrompido = repo.pasta_dados / "2026" / "semana_46.json"
    corrompido.write_text("{ quebrado", encoding="utf-8")

    resultado = reorganizar_se_preciso(repo)
    assert resultado.dias == 1
    assert [a.name for a in resultado.ignorados] == ["semana_46.json"]
    assert (resultado.backup / "2026" / "semana_46.json").read_text(encoding="utf-8") == "{ quebrado"
