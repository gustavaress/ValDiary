"""Formatação de valores para exibição (sem depender do locale do Windows)."""

from datetime import date

_DIAS = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
         "Sexta-feira", "Sábado", "Domingo"]
_DIAS_ABREV = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def data_curta(data: date) -> str:
    return data.strftime("%d/%m/%Y")


def data_extensa(data: date) -> str:
    return f"{_DIAS[data.weekday()]}, {data_curta(data)}"


def data_tabela(data: date) -> str:
    return f"{_DIAS_ABREV[data.weekday()]} {data_curta(data)}"


def numero(valor, casas: int = 2, sufixo: str = "") -> str:
    """1.35 -> "1,35"; 2.50 -> "2,5"; None -> "—"."""
    if valor is None:
        return "—"
    texto = f"{valor:.{casas}f}".replace(".", ",")
    if "," in texto:
        texto = texto.rstrip("0").rstrip(",")
    return texto + sufixo
