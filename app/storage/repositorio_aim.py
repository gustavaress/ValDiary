"""Rotina de aim padrão do jogador (dados/aim_routine.json).

É a lista de exercícios que aparece pronta na aba Aim Routine de cada dia, para
só marcar o que foi feito. Pode ser trocada pela própria tela
("Salvar como minha rotina padrão").
"""

import json
from pathlib import Path

from app import config
from app.models import ExercicioAim
from app.storage.escrita_segura import escrever_json_atomico

NOME_ARQUIVO = "aim_routine.json"

# Rotina inicial (a que o jogador usava quando a funcionalidade foi criada).
ROTINA_INICIAL = [
    ExercicioAim("Tracking", "5 minutos"),
    ExercicioAim("Bots parados", "2 séries de 100"),
    ExercicioAim("Bots andando", "2 séries de 100"),
    ExercicioAim("Hard Bots", "10"),
    ExercicioAim("Hard Bots em curta distância", "5"),
    ExercicioAim("Deathmatch de qualidade", "5"),
]


class RepositorioAim:
    def __init__(self, pasta_dados: Path = config.PASTA_DADOS):
        self.arquivo = pasta_dados / NOME_ARQUIVO

    def carregar_padrao(self) -> list[ExercicioAim]:
        """Exercícios da rotina padrão (a inicial, se o arquivo não existir ou estiver ilegível)."""
        try:
            dados = json.loads(self.arquivo.read_text(encoding="utf-8"))
            exercicios = [ExercicioAim(e["nome"], e.get("meta")) for e in dados.get("exercicios", []) if e.get("nome")]
            return exercicios or [ExercicioAim(e.nome, e.meta) for e in ROTINA_INICIAL]
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return [ExercicioAim(e.nome, e.meta) for e in ROTINA_INICIAL]

    def salvar_padrao(self, exercicios: list[ExercicioAim]) -> None:
        escrever_json_atomico(self.arquivo, {
            "versao": 1,
            "exercicios": [{"nome": e.nome, "meta": e.meta} for e in exercicios if e.nome],
        })
