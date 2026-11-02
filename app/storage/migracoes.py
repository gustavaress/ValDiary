"""Migrações do formato dos arquivos semanais.

Cada função converte um documento da versão N para a N+1. Ao ler um arquivo
antigo, aplicamos as migrações em sequência até a versão atual. O arquivo
em disco só muda de versão quando a semana for gravada de novo.
"""

from app import config


def _v1_para_v2(documento: dict) -> dict:
    """v2: refeições ganham "realizada"; agentes viram {"nome", "partidas"}."""
    for dia in documento.get("dias") or []:
        if not isinstance(dia, dict):
            continue
        alimentacao = (dia.get("rotina") or {}).get("alimentacao") or {}
        for chave in ("cafe_da_manha", "almoco", "jantar"):
            refeicao = alimentacao.get(chave)
            if isinstance(refeicao, dict) and "realizada" not in refeicao:
                # Antes não havia a caixa "tive essa refeição": se algo foi
                # preenchido, a refeição aconteceu.
                tem_dados = bool(refeicao.get("horario") or refeicao.get("descricao"))
                refeicao["realizada"] = True if tem_dados else None

        jogo = dia.get("valorant") or {}
        jogo["agentes"] = [
            {"nome": agente, "partidas": None} if isinstance(agente, str) else agente
            for agente in jogo.get("agentes") or []
        ]
    documento["versao_schema"] = 2
    return documento


_MIGRACOES = {1: _v1_para_v2}


def migrar_documento(documento: dict) -> dict:
    """Atualiza um documento semanal para a versão atual (altera e devolve o próprio dict)."""
    versao = documento.get("versao_schema", 1)
    while versao < config.VERSAO_SCHEMA:
        documento = _MIGRACOES[versao](documento)
        versao = documento["versao_schema"]
    return documento
