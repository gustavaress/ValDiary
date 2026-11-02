"""Rascunho do formulário de registro (autosave).

Guarda o estado "cru" do formulário (inclusive valores ainda inválidos), para
recuperar o que foi digitado caso o app feche antes de salvar.
"""

import json
from datetime import datetime
from pathlib import Path

from app import config
from app.storage.escrita_segura import escrever_json_atomico


def salvar_rascunho(formulario: dict, caminho: Path = config.ARQUIVO_RASCUNHO) -> None:
    escrever_json_atomico(caminho, {
        "salvo_em": datetime.now().isoformat(timespec="seconds"),
        "formulario": formulario,
    })


def carregar_rascunho(caminho: Path = config.ARQUIVO_RASCUNHO) -> dict | None:
    """Retorna {"salvo_em": ..., "formulario": {...}} ou None se não houver rascunho válido."""
    if not caminho.exists():
        return None
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        return dados if isinstance(dados.get("formulario"), dict) else None
    except (json.JSONDecodeError, AttributeError):
        return None


def apagar_rascunho(caminho: Path = config.ARQUIVO_RASCUNHO) -> None:
    caminho.unlink(missing_ok=True)
