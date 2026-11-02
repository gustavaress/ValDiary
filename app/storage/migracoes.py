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


_CAMPOS_DIA_V2 = ("partidas", "vitorias", "derrotas", "empates", "abates", "mortes", "assistencias",
                  "acs", "adr", "hs_pct", "agentes")


def _v2_para_v3(documento: dict) -> dict:
    """v3: o Valorant passa a ser registrado por partida.

    Os totais do dia da v2 não viram partidas (seria inventar dados): vão
    intactos para "legado" e continuam aparecendo nas análises.
    """
    for dia in documento.get("dias") or []:
        if not isinstance(dia, dict) or not isinstance(dia.get("valorant"), dict):
            continue
        jogo = dia["valorant"]
        jogo.pop("derivados", None)
        legado = {campo: jogo.pop(campo) for campo in _CAMPOS_DIA_V2 if campo in jogo}
        tem_dados = any(v not in (None, []) for v in legado.values())
        jogo["legado"] = legado if tem_dados else None
        jogo["partidas"] = []
    documento["versao_schema"] = 3
    return documento


def _v3_para_v4(documento: dict) -> dict:
    """v4: RR por partida (campo novo, vazio nos dias antigos; o ranking em si
    fica em ranking.json) e semanas de domingo a sábado (a reorganização dos arquivos é feita à parte,
    em reorganizacao.py, porque muda dias de arquivo)."""
    documento["versao_schema"] = 4
    return documento


def _v4_para_v5(documento: dict) -> dict:
    """v5: mapa por partida, aquecimento e aim routine (campos novos, vazios nos dias antigos)."""
    documento["versao_schema"] = 5
    return documento


_MIGRACOES = {1: _v1_para_v2, 2: _v2_para_v3, 3: _v3_para_v4, 4: _v4_para_v5}


def migrar_documento(documento: dict) -> dict:
    """Atualiza um documento semanal para a versão atual (altera e devolve o próprio dict)."""
    versao = documento.get("versao_schema", 1)
    while versao < config.VERSAO_SCHEMA:
        documento = _MIGRACOES[versao](documento)
        versao = documento["versao_schema"]
    return documento
