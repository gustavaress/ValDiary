"""Ranking do jogador (dados/ranking.json).

Guarda duas coisas:
- "definicoes": ajustes manuais feitos na aba Ranking (elo e RR a partir de uma
  data). São o ponto de partida do cálculo.
- "atual": o ranking ao fim do último dia registrado, recalculado e regravado
  sempre que um dia é salvo, editado, excluído ou importado.

Fica separado dos arquivos semanais porque não pertence a um dia. Usa a mesma
escrita segura e backup.
"""

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from app import config
from app.models.ranking import DefinicaoRanking, Ranking
from app.storage.escrita_segura import escrever_json_atomico, fazer_backup
from app.storage.repositorio import ArquivoCorrompidoError

NOME_ARQUIVO = "ranking.json"


@dataclass(frozen=True)
class RankingSalvo:
    ranking: Ranking
    apos_o_dia: date | None  # último dia registrado aplicado (None = só a definição)


class RepositorioRanking:
    def __init__(self, pasta_dados: Path = config.PASTA_DADOS, pasta_backups: Path = config.PASTA_BACKUPS,
                 max_backups: int = config.MAX_BACKUPS_POR_SEMANA):
        self.arquivo = pasta_dados / NOME_ARQUIVO
        self.pasta_backups = pasta_backups
        self.max_backups = max_backups

    # --- Leitura ----------------------------------------------------------

    def _ler(self) -> dict:
        if not self.arquivo.exists():
            return {}
        try:
            dados = json.loads(self.arquivo.read_text(encoding="utf-8"))
            if not isinstance(dados, dict):
                raise ValueError("formato inesperado")
            return dados
        except (json.JSONDecodeError, ValueError) as erro:
            raise ArquivoCorrompidoError(self.arquivo, str(erro)) from erro

    def carregar(self) -> list[DefinicaoRanking]:
        """Definições (ajustes manuais) em ordem de data. Arquivo inexistente -> lista vazia."""
        try:
            definicoes = [DefinicaoRanking.from_dict(d) for d in self._ler().get("definicoes", [])]
        except (KeyError, ValueError, TypeError, AttributeError) as erro:
            raise ArquivoCorrompidoError(self.arquivo, str(erro)) from erro
        return sorted(definicoes, key=lambda d: d.data)

    def carregar_atual(self) -> RankingSalvo | None:
        atual = self._ler().get("atual")
        if not atual:
            return None
        try:
            apos = atual.get("apos_o_dia")
            return RankingSalvo(Ranking(atual["elo"], int(atual["rr"])),
                                date.fromisoformat(apos) if apos else None)
        except (KeyError, ValueError, TypeError) as erro:
            raise ArquivoCorrompidoError(self.arquivo, str(erro)) from erro

    # --- Escrita ----------------------------------------------------------

    def definir(self, data: date, elo: str, rr: int) -> None:
        """Grava um ajuste manual. Um ajuste na mesma data substitui o anterior."""
        definicoes = [d for d in self.carregar() if d.data != data]
        definicoes.append(DefinicaoRanking(data, elo, rr, datetime.now().replace(microsecond=0)))
        self._gravar(definicoes, self._ler().get("atual"))

    def remover(self, data: date) -> None:
        self._gravar([d for d in self.carregar() if d.data != data], self._ler().get("atual"))

    def salvar_atual(self, salvo: RankingSalvo | None) -> bool:
        """Grava o ranking atual calculado. Retorna False se nada mudou (evita backups à toa)."""
        novo = None if salvo is None else {
            "elo": salvo.ranking.elo,
            "rr": salvo.ranking.rr,
            "apos_o_dia": salvo.apos_o_dia.isoformat() if salvo.apos_o_dia else None,
        }
        anterior = self._ler().get("atual")
        if anterior and novo and {k: anterior.get(k) for k in novo} == novo:
            return False
        if anterior is None and novo is None:
            return False
        if novo:
            novo["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
        self._gravar(self.carregar(), novo)
        return True

    def _gravar(self, definicoes: list[DefinicaoRanking], atual: dict | None) -> None:
        fazer_backup(self.arquivo, self.pasta_backups, self.max_backups)
        escrever_json_atomico(self.arquivo, {
            "versao": 1,
            "_explicacao": "'atual' é o ranking ao fim do último dia registrado (recalculado automaticamente). "
                           "'definicoes' são ajustes manuais, valendo a partir do início de 'data'; o ranking "
                           "dos dias seguintes é calculado com o RR de cada partida.",
            "atual": atual,
            "definicoes": [d.to_dict() for d in sorted(definicoes, key=lambda d: d.data)],
        })
