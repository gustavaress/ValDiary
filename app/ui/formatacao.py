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
    """1.35 -> "1,35"; 2.50 -> "2,5"; None ou NaN -> "—"."""
    if valor is None or valor != valor:  # NaN é o único valor diferente de si mesmo
        return "—"
    texto = f"{valor:.{casas}f}".replace(".", ",")
    if "," in texto:
        texto = texto.rstrip("0").rstrip(",")
    return texto + sufixo


def hora_texto(valor: float) -> str:
    """Hora decimal -> "HH:MM" (25.5 -> "01:30", pois horários noturnos passam de 24)."""
    valor = valor % 24
    horas = int(valor)
    minutos = int(round((valor - horas) * 60))
    if minutos == 60:
        horas, minutos = (horas + 1) % 24, 0
    return f"{horas:02d}:{minutos:02d}"


def valor_metrica(metrica, valor) -> str:
    """Formata o valor conforme a métrica (horários como HH:MM, notas, %...)."""
    if valor is None or valor != valor:
        return "—"
    if metrica.hora:
        return hora_texto(valor)
    return numero(valor, metrica.casas, metrica.sufixo)
