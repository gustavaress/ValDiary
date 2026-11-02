"""Regras de datas: semanas (domingo a sábado) e escolha de data para um registro novo.

Um registro novo só pode ir para um dia que ainda não tem registro e que não
está no futuro. Para mudar um dia já registrado, edita-se o registro dele.
"""

from datetime import date, timedelta

LIMITE_BUSCA_DIAS = 3660  # ~10 anos: evita laço infinito se tudo estiver preenchido


# --- Semanas ----------------------------------------------------------------
# A semana vai de domingo a sábado. Numeração: a semana 1 é a primeira semana
# com pelo menos 4 dias no ano novo (mesma ideia do padrão ISO, mas começando
# no domingo). Truque: a semana de domingo de uma data é a semana ISO do dia
# seguinte, porque deslocar um dia transforma "domingo a sábado" em
# "segunda a domingo".

def semana_da_data(data: date) -> tuple[int, int]:
    """(ano da semana, número da semana). Define em qual arquivo o dia é salvo."""
    ano, semana, _ = (data + timedelta(days=1)).isocalendar()
    return ano, semana


def periodo_semana(ano: int, semana: int) -> tuple[date, date]:
    """(domingo, sábado) da semana."""
    domingo = date.fromisocalendar(ano, semana, 1) - timedelta(days=1)
    return domingo, domingo + timedelta(days=6)


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
