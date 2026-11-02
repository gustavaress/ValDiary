"""Catálogo das métricas numéricas analisáveis.

Cada métrica vira uma coluna do DataFrame (ver dataframe.py) e aparece no
dashboard e na comparação. Para analisar um campo novo, basta incluí-lo aqui
e em registros_para_dataframe().
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Metrica:
    chave: str          # nome da coluna no DataFrame
    rotulo: str         # nome exibido na tela
    grupo: str          # "Rotina" ou "Valorant"
    casas: int = 1
    sufixo: str = ""
    nota: bool = False  # escala 1-10
    hora: bool = False  # hora do dia em formato decimal (exibida como HH:MM)


METRICAS = [
    Metrica("sono_horas", "Horas de sono", "Rotina", 1, "h"),
    Metrica("sono_qualidade", "Qualidade do sono", "Rotina", nota=True),
    Metrica("horario_dormir", "Horário que dormiu", "Rotina", hora=True),
    Metrica("agua_litros", "Água", "Rotina", 1, " L"),
    Metrica("bebidas_qtd", "Bebidas (café, energético...)", "Rotina", 1),
    Metrica("disposicao_fisica", "Disposição física", "Rotina", nota=True),
    Metrica("disposicao_mental", "Disposição mental", "Rotina", nota=True),
    Metrica("estresse", "Estresse", "Rotina", nota=True),
    Metrica("inicio_jogo", "Horário que começou a jogar", "Valorant", hora=True),
    Metrica("partidas", "Partidas", "Valorant", 1),
    Metrica("winrate_pct", "Winrate", "Valorant", 1, "%"),
    Metrica("kd", "K/D", "Valorant", 2),
    Metrica("kda", "KDA", "Valorant", 2),
    Metrica("acs", "ACS", "Valorant", 0),
    Metrica("adr", "ADR", "Valorant", 0),
    Metrica("hs_pct", "HS%", "Valorant", 1, "%"),
    Metrica("mira", "Sensação da mira", "Valorant", nota=True),
    Metrica("movimentacao", "Movimentação", "Valorant", nota=True),
    Metrica("tomada_decisao", "Tomada de decisão", "Valorant", nota=True),
    Metrica("concentracao", "Concentração", "Valorant", nota=True),
    Metrica("consistencia", "Consistência", "Valorant", nota=True),
]

POR_CHAVE = {m.chave: m for m in METRICAS}
