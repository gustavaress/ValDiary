"""Regras de organização dos arquivos por semana ISO.

Semana ISO: começa na segunda-feira; a semana 1 é a que contém a primeira
quinta-feira do ano. Por isso alguns dias do início de janeiro pertencem ao
ano ISO anterior (ex.: 01/01/2027 -> semana 53 de 2026).
"""

import re
from datetime import date
from pathlib import Path

_NOME_ARQUIVO = re.compile(r"^semana_(\d{2})\.json$")


def semana_da_data(data: date) -> tuple[int, int]:
    ano, semana, _ = data.isocalendar()
    return ano, semana


def periodo_semana(ano: int, semana: int) -> tuple[date, date]:
    """(segunda-feira, domingo) da semana ISO."""
    return date.fromisocalendar(ano, semana, 1), date.fromisocalendar(ano, semana, 7)


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
