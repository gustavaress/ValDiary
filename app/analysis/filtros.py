"""Filtros sobre a lista de registros (usados no histórico)."""

import unicodedata
from datetime import date, timedelta

from app.models import RegistroDia


def normalizar_texto(texto: str) -> str:
    """Minúsculas e sem acentos: "Ansioso" e "ansiôso" combinam."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


def texto_pesquisavel(registro: RegistroDia) -> str:
    """Todo o texto livre de um dia, junto, para a busca."""
    rotina = registro.rotina
    partes = [
        rotina.observacoes, registro.valorant.notas, rotina.alimentacao.outros,
        rotina.alimentacao.cafe_da_manha.descricao, rotina.alimentacao.almoco.descricao,
        rotina.alimentacao.jantar.descricao, " ".join(registro.valorant.agentes),
    ]
    return normalizar_texto(" ".join(p for p in partes if p))


def filtrar(
    registros: list[RegistroDia],
    classificacao: str | None = None,
    ultimos_dias: int | None = None,
    busca: str = "",
    hoje: date | None = None,
) -> list[RegistroDia]:
    """Aplica os filtros e devolve do mais recente para o mais antigo."""
    hoje = hoje or date.today()
    termo = normalizar_texto(busca.strip())
    resultado = []
    for registro in registros:
        if classificacao and registro.classificacao != classificacao:
            continue
        if ultimos_dias and registro.data <= hoje - timedelta(days=ultimos_dias):
            continue
        if termo and termo not in texto_pesquisavel(registro):
            continue
        resultado.append(registro)
    return sorted(resultado, key=lambda r: r.data, reverse=True)
