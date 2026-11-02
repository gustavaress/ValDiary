"""Catálogo de agentes (nome, função e imagem), lido de assets/agentes/agentes.json.

O arquivo é gerado por scripts/baixar_agentes.py. Se ele não existir, o
catálogo fica vazio e a tela avisa como gerá-lo.
"""

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from app import config

ORDEM_FUNCOES = ["Duelista", "Iniciador", "Controlador", "Sentinela"]


@dataclass(frozen=True)
class AgenteInfo:
    nome: str
    funcao: str
    imagem: Path


@cache
def carregar_agentes(pasta: Path = config.PASTA_AGENTES) -> tuple[AgenteInfo, ...]:
    try:
        dados = json.loads((pasta / "agentes.json").read_text(encoding="utf-8"))
        return tuple(
            AgenteInfo(a["nome"], a.get("funcao") or "Outros", pasta / a["arquivo"])
            for a in dados.get("agentes", [])
        )
    except (OSError, ValueError, KeyError, TypeError):
        return ()


def agrupar_por_funcao(agentes: tuple[AgenteInfo, ...]) -> list[tuple[str, list[AgenteInfo]]]:
    """[(função, agentes em ordem alfabética), ...] na ordem Duelista → Sentinela."""
    funcoes = ORDEM_FUNCOES + sorted({a.funcao for a in agentes} - set(ORDEM_FUNCOES))
    grupos = []
    for funcao in funcoes:
        membros = sorted((a for a in agentes if a.funcao == funcao), key=lambda a: a.nome.lower())
        if membros:
            grupos.append((funcao, membros))
    return grupos
