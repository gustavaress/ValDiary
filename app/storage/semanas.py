"""Organização dos arquivos por semana (domingo a sábado).

A regra de qual semana é cada data fica em app/models/datas.py. Alguns dias
do início de janeiro pertencem à última semana do ano anterior
(ex.: 01/01/2027 -> semana 53 de 2026).
"""

import re
from pathlib import Path

from app.models.datas import periodo_semana, semana_da_data  # noqa: F401 (reexportados)

_NOME_ARQUIVO = re.compile(r"^semana_(\d{2})\.json$")


def caminho_semana(pasta_dados: Path, ano: int, semana: int) -> Path:
    return pasta_dados / str(ano) / f"semana_{semana:02d}.json"


def semanas_existentes(pasta_dados: Path) -> list[tuple[int, int]]:
    """Lista (ano, semana) de todos os arquivos semanais, em ordem cronológica."""
    encontradas = []
    if not pasta_dados.exists():
        return encontradas
    for pasta_ano in pasta_dados.iterdir():
        # Ignora _backups, _exportacoes e qualquer pasta que não seja um ano.
        if not (pasta_ano.is_dir() and pasta_ano.name.isdigit()):
            continue
        for arquivo in pasta_ano.iterdir():
            correspondencia = _NOME_ARQUIVO.match(arquivo.name)
            if correspondencia:
                encontradas.append((int(pasta_ano.name), int(correspondencia.group(1))))
    return sorted(encontradas)
