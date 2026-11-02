"""Validação de um RegistroDia antes de salvar.

Retorna uma lista de mensagens legíveis. Lista vazia = registro válido.
Campos vazios (None) nunca são erro, porque nada é obrigatório além da data.
"""

import re

from app.config import ESCALA_MAX, ESCALA_MIN
from app.models.registro import RegistroDia

_FORMATO_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _checar_nota(erros: list[str], rotulo: str, valor) -> None:
    if valor is not None and not (ESCALA_MIN <= valor <= ESCALA_MAX):
        erros.append(f"{rotulo}: a nota deve estar entre {ESCALA_MIN} e {ESCALA_MAX}.")


def _checar_hora(erros: list[str], rotulo: str, valor) -> None:
    if valor is not None and not _FORMATO_HORA.match(valor):
        erros.append(f"{rotulo}: use o formato HH:MM (ex.: 07:30).")


def _checar_nao_negativo(erros: list[str], rotulo: str, valor) -> None:
    if valor is not None and valor < 0:
        erros.append(f"{rotulo}: não pode ser negativo.")


def validar_registro(registro: RegistroDia) -> list[str]:
    erros: list[str] = []
    rotina = registro.rotina
    jogo = registro.valorant

    # Notas 1-10
    _checar_nota(erros, "Qualidade do sono", rotina.sono.qualidade)
    _checar_nota(erros, "Disposição física", rotina.disposicao_fisica)
    _checar_nota(erros, "Disposição mental", rotina.disposicao_mental)
    _checar_nota(erros, "Estresse", rotina.estresse)
    _checar_nota(erros, "Mira", jogo.avaliacao.mira)
    _checar_nota(erros, "Movimentação", jogo.avaliacao.movimentacao)
    _checar_nota(erros, "Tomada de decisão", jogo.avaliacao.tomada_decisao)
    _checar_nota(erros, "Concentração", jogo.avaliacao.concentracao)
    _checar_nota(erros, "Consistência", jogo.avaliacao.consistencia)

    # Horários
    _checar_hora(erros, "Horário que dormiu", rotina.sono.dormiu_as)
    _checar_hora(erros, "Horário que acordou", rotina.sono.acordou_as)
    for nome, refeicao in (
        ("Café da manhã", rotina.alimentacao.cafe_da_manha),
        ("Almoço", rotina.alimentacao.almoco),
        ("Jantar", rotina.alimentacao.jantar),
    ):
        _checar_hora(erros, f"{nome} (horário)", refeicao.horario)
    for bebida in rotina.bebidas:
        _checar_hora(erros, f"Bebida '{bebida.tipo or '?'}' (horário)", bebida.horario)
    for remedio in rotina.medicamentos:
        _checar_hora(erros, f"Medicamento '{remedio.nome or '?'}' (horário)", remedio.horario)
    _checar_hora(erros, "Início do jogo", jogo.horario_inicio)
    _checar_hora(erros, "Fim do jogo", jogo.horario_fim)

    # Números não negativos
    _checar_nao_negativo(erros, "Horas de sono", rotina.sono.horas)
    if rotina.sono.horas is not None and rotina.sono.horas > 24:
        erros.append("Horas de sono: não pode passar de 24.")
    _checar_nao_negativo(erros, "Água (litros)", rotina.agua_litros)
    for rotulo, valor in (
        ("Partidas", jogo.partidas),
        ("Vitórias", jogo.vitorias),
        ("Derrotas", jogo.derrotas),
        ("Empates", jogo.empates),
        ("Abates", jogo.abates),
        ("Mortes", jogo.mortes),
        ("Assistências", jogo.assistencias),
        ("ACS", jogo.acs),
        ("ADR", jogo.adr),
    ):
        _checar_nao_negativo(erros, rotulo, valor)

    if jogo.hs_pct is not None and not (0 <= jogo.hs_pct <= 100):
        erros.append("HS%: deve estar entre 0 e 100.")

    # Coerência entre resultado e número de partidas
    resultados = [v for v in (jogo.vitorias, jogo.derrotas, jogo.empates) if v is not None]
    if jogo.partidas is not None and sum(resultados) > jogo.partidas:
        erros.append("Vitórias + derrotas + empates não pode ser maior que o número de partidas.")

    for agente in jogo.agentes:
        _checar_nao_negativo(erros, f"Partidas com {agente.nome}", agente.partidas)
    soma_agentes = sum(a.partidas or 0 for a in jogo.agentes)
    if jogo.partidas is not None and soma_agentes > jogo.partidas:
        erros.append(f"A soma das partidas por agente ({soma_agentes}) é maior que o total "
                     f"de partidas do dia ({jogo.partidas}).")

    return erros
