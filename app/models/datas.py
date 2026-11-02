"""Regras de escolha de data para um registro novo.

Um registro novo só pode ir para um dia que ainda não tem registro e que não
está no futuro. Para mudar um dia já registrado, edita-se o registro dele.
"""

from datetime import date, timedelta

LIMITE_BUSCA_DIAS = 3660  # ~10 anos: evita laço infinito se tudo estiver preenchido


def erro_data_nova(data: date, registradas: set[date], hoje: date) -> str | None:
    """Mensagem explicando por que a data não pode receber um registro novo, ou None se pode."""
    if data > hoje:
        return "Não é possível registrar um dia que ainda não aconteceu."
    if data in registradas:
        return (f"{data:%d/%m/%Y} já tem um registro.\n\n"
                "Para alterá-lo, abra o dia pelo Histórico (botão Editar).")
    return None


def proxima_data_livre(inicio: date, passo: int, registradas: set[date], hoje: date) -> date | None:
    """A partir de `inicio`, anda `passo` dias (+1 ou -1) até achar um dia livre e não futuro."""
    dia = inicio
    for _ in range(LIMITE_BUSCA_DIAS):
        if dia > hoje:
            return None
        if dia not in registradas:
            return dia
        dia += timedelta(days=passo)
    return None


def data_livre_mais_recente(registradas: set[date], hoje: date) -> date | None:
    return proxima_data_livre(hoje, -1, registradas, hoje)
