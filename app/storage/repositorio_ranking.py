"""Definições de ranking feitas pelo jogador (dados/ranking.json).

Fica separado dos arquivos semanais porque não pertence a um dia: é o ponto de
partida para calcular o ranking. Usa a mesma escrita segura e backup.
"""

import json
from datetime import date, datetime
from pathlib import Path

from app import config
from app.models.ranking import DefinicaoRanking
from app.storage.escrita_segura import escrever_json_atomico, fazer_backup
from app.storage.repositorio import ArquivoCorrompidoError

NOME_ARQUIVO = "ranking.json"


class RepositorioRanking:
    def __init__(self, pasta_dados: Path = config.PASTA_DADOS, pasta_backups: Path = config.PASTA_BACKUPS,
                 max_backups: int = config.MAX_BACKUPS_POR_SEMANA):
        self.arquivo = pasta_dados / NOME_ARQUIVO
        self.pasta_backups = pasta_backups
        self.max_backups = max_backups

    def carregar(self) -> list[DefinicaoRanking]:
        """Definições em ordem de data. Arquivo inexistente -> lista vazia."""
        if not self.arquivo.exists():
            return []
        try:
            dados = json.loads(self.arquivo.read_text(encoding="utf-8"))
            definicoes = [DefinicaoRanking.from_dict(d) for d in dados.get("definicoes", [])]
        except (json.JSONDecodeError, KeyError, ValueError, TypeError, AttributeError) as erro:
            raise ArquivoCorrompidoError(self.arquivo, str(erro)) from erro
        return sorted(definicoes, key=lambda d: d.data)

    def definir(self, data: date, elo: str, rr: int) -> None:
        """Grava uma definição. Uma definição na mesma data substitui a anterior."""
        definicoes = [d for d in self.carregar() if d.data != data]
        definicoes.append(DefinicaoRanking(data, elo, rr, datetime.now().replace(microsecond=0)))
        self._gravar(definicoes)

    def remover(self, data: date) -> None:
        self._gravar([d for d in self.carregar() if d.data != data])

    def _gravar(self, definicoes: list[DefinicaoRanking]) -> None:
        fazer_backup(self.arquivo, self.pasta_backups, self.max_backups)
        escrever_json_atomico(self.arquivo, {
            "versao": 1,
            "_explicacao": "Ranking informado pelo jogador, valendo a partir do início de 'data'. "
                           "O ranking dos dias seguintes é calculado com o RR de cada partida.",
            "definicoes": [d.to_dict() for d in sorted(definicoes, key=lambda d: d.data)],
        })
