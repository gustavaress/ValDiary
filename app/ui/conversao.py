"""Conversão do texto digitado nos campos para valores tipados.

Campo vazio sempre vira None. Erros viram ErroConversao com uma mensagem
pronta para mostrar ao usuário.
"""

import re


class ErroConversao(ValueError):
    pass


def texto(valor: str | None) -> str | None:
    valor = (valor or "").strip()
    return valor or None


def inteiro(valor: str | None, rotulo: str) -> int | None:
    valor = texto(valor)
    if valor is None:
        return None
    try:
        return int(valor)
    except ValueError:
        raise ErroConversao(f"{rotulo}: digite um número inteiro.") from None


def decimal(valor: str | None, rotulo: str) -> float | None:
    """Aceita vírgula ou ponto: "2,5" e "2.5" viram 2.5."""
    valor = texto(valor)
    if valor is None:
        return None
    try:
        return float(valor.replace(",", "."))
    except ValueError:
        raise ErroConversao(f"{rotulo}: digite um número (ex.: 2,5).") from None


# Aceita "7:30", "07:30", "0730", "730", "7h30", "7h" e "23".
_HORA = re.compile(r"^(\d{1,2})(?:[:h])?(\d{2})?$")


def hora(valor: str | None, rotulo: str) -> str | None:
    """Normaliza horários para "HH:MM"."""
    valor = texto(valor)
    if valor is None:
        return None
    correspondencia = _HORA.match(valor.lower())
    if correspondencia:
        horas = int(correspondencia.group(1))
        minutos = int(correspondencia.group(2) or 0)
        if horas < 24 and minutos < 60:
            return f"{horas:02d}:{minutos:02d}"
    raise ErroConversao(f"{rotulo}: horário inválido (use HH:MM, ex.: 07:30).")


def lista_de_nomes(valor: str | None) -> list[str]:
    """ "Jett, Raze; Omen" -> ["Jett", "Raze", "Omen"] (sem repetidos)."""
    nomes = []
    for parte in re.split(r"[,;]", valor or ""):
        nome = parte.strip()
        if nome and nome.lower() not in (n.lower() for n in nomes):
            nomes.append(nome)
    return nomes


def para_campo(valor) -> str:
    """Valor -> texto para exibir num campo editável (None -> "", 2.5 -> "2,5")."""
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return str(valor).replace(".", ",")
