"""Formatação de valores para exibição (sem depender do locale do Windows)."""

from datetime import date

_DIAS = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
         "Sexta-feira", "Sábado", "Domingo"]


def data_curta(data: date) -> str:
    return data.strftime("%d/%m/%Y")


def data_extensa(data: date) -> str:
    return f"{_DIAS[data.weekday()]}, {data_curta(data)}"
