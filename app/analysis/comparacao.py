"""Comparação entre dias bons e ruins, correlações e hábitos frequentes.

Princípios, para não "inventar" conclusões:
- todo número vem acompanhado de quantos dias (n) o sustentam;
- abaixo de um mínimo de dias, o resultado é marcado como insuficiente;
- falamos em associação/correlação, nunca em causa.
"""

from dataclasses import dataclass

import pandas as pd

from app.analysis.filtros import normalizar_texto
from app.analysis.metricas import METRICAS, Metrica
from app.models import RegistroDia

GRUPO_BONS = ("excelente", "bom")
GRUPO_RUINS = ("ruim", "pessimo")

# Abaixo destes mínimos, diferenças e correlações são facilmente obra do acaso.
MIN_DIAS_POR_GRUPO = 5
MIN_DIAS_CORRELACAO = 10


# --- Bons x ruins ---------------------------------------------------------

@dataclass
class LinhaComparacao:
    metrica: Metrica
    media_bons: float | None
    n_bons: int
    media_ruins: float | None
    n_ruins: int

    @property
    def diferenca(self) -> float | None:
        if self.media_bons is None or self.media_ruins is None:
            return None
        return self.media_bons - self.media_ruins

    @property
    def suficiente(self) -> bool:
        return self.n_bons >= MIN_DIAS_POR_GRUPO and self.n_ruins >= MIN_DIAS_POR_GRUPO


def separar_grupos(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    return df[df["classificacao"].isin(GRUPO_BONS)], df[df["classificacao"].isin(GRUPO_RUINS)]


def comparar_grupos(df: pd.DataFrame) -> list[LinhaComparacao]:
    bons, ruins = separar_grupos(df)
    linhas = []
    for metrica in METRICAS:
        valores_bons = bons[metrica.chave].dropna()
        valores_ruins = ruins[metrica.chave].dropna()
        linhas.append(LinhaComparacao(
            metrica=metrica,
            media_bons=float(valores_bons.mean()) if len(valores_bons) else None,
            n_bons=len(valores_bons),
            media_ruins=float(valores_ruins.mean()) if len(valores_ruins) else None,
            n_ruins=len(valores_ruins),
        ))
    return linhas


# --- Correlações ----------------------------------------------------------

@dataclass
class Correlacao:
    metrica: Metrica
    rho: float | None  # Spearman, de -1 a +1
    n: int

    @property
    def suficiente(self) -> bool:
        return self.rho is not None and self.n >= MIN_DIAS_CORRELACAO

    @property
    def forca(self) -> str:
        if self.rho is None:
            return "—"
        intensidade = abs(self.rho)
        if intensidade < 0.1:
            return "desprezível"
        if intensidade < 0.3:
            return "fraca"
        if intensidade < 0.5:
            return "moderada"
        return "forte"

    @property
    def leitura(self) -> str:
        if self.rho is None:
            return "Sem variação suficiente para calcular"
        if not self.suficiente:
            return f"Poucos dados (mínimo de {MIN_DIAS_CORRELACAO} dias)"
        if self.forca == "desprezível":
            return "Sem relação aparente"
        tipo_dia = "melhores" if self.rho > 0 else "piores"
        if self.metrica.hora:
            return f"Horários mais tarde aparecem junto de dias {tipo_dia}"
        return f"Valores mais altos aparecem junto de dias {tipo_dia}"


def correlacoes(df: pd.DataFrame) -> list[Correlacao]:
    """Correlação de Spearman de cada métrica com a classificação do dia (1 a 5).

    Spearman compara a ORDEM dos valores (não exige relação em linha reta) e
    é menos sensível a valores extremos, o que combina com notas de 1 a 10.
    Ordenado das relações mais fortes (com dados suficientes) para as mais fracas.
    """
    resultado = []
    for metrica in METRICAS:
        pares = df[[metrica.chave, "classificacao_nota"]].dropna()
        rho = None
        if len(pares) >= 3 and pares[metrica.chave].nunique() > 1 and pares["classificacao_nota"].nunique() > 1:
            # Spearman = Pearson aplicado às posições (ranks) dos valores.
            # Calculado assim para não depender da biblioteca scipy.
            posicoes = pares.rank()
            rho = float(posicoes[metrica.chave].corr(posicoes["classificacao_nota"]))
        resultado.append(Correlacao(metrica, rho, len(pares)))
    return sorted(resultado, key=lambda c: (not c.suficiente, -abs(c.rho or 0)))


# --- Hábitos --------------------------------------------------------------

@dataclass
class FrequenciaHabito:
    item: str
    dias_bons: int
    total_bons: int
    dias_ruins: int
    total_ruins: int

    @property
    def pct_bons(self) -> float | None:
        return self.dias_bons / self.total_bons * 100 if self.total_bons else None

    @property
    def pct_ruins(self) -> float | None:
        return self.dias_ruins / self.total_ruins * 100 if self.total_ruins else None


def _habitos_do_dia(registro: RegistroDia, nomes: dict[str, str]) -> set[str]:
    """Itens presentes no dia. `nomes` guarda a 1ª grafia vista de cada item,
    para "Energético" e "energetico" contarem como a mesma coisa."""
    def item(prefixo: str, texto: str) -> str:
        chave = f"{prefixo}:{normalizar_texto(texto.strip())}"
        nomes.setdefault(chave, f"{prefixo}: {texto.strip()}")
        return chave

    itens = set()
    cafe = registro.rotina.alimentacao.cafe_da_manha
    if cafe.descricao or cafe.horario:
        itens.add(item("Refeição", "café da manhã"))
    for bebida in registro.rotina.bebidas:
        if bebida.tipo:
            itens.add(item("Bebida", bebida.tipo))
    for remedio in registro.rotina.medicamentos:
        if remedio.nome:
            itens.add(item("Medicamento", remedio.nome))
    for agente in registro.valorant.agentes:
        itens.add(item("Agente", agente))
    return itens


def frequencias_habitos(registros: list[RegistroDia]) -> list[FrequenciaHabito]:
    """Em que % dos dias bons e dos dias ruins cada item apareceu.

    Só entram itens vistos em pelo menos 2 dias (bons + ruins). Ordenado pela
    maior diferença entre os grupos.
    """
    bons = [r for r in registros if r.classificacao in GRUPO_BONS]
    ruins = [r for r in registros if r.classificacao in GRUPO_RUINS]
    nomes: dict[str, str] = {}
    contagem_bons: dict[str, int] = {}
    contagem_ruins: dict[str, int] = {}
    for grupo, contagem in ((bons, contagem_bons), (ruins, contagem_ruins)):
        for registro in grupo:
            for chave in _habitos_do_dia(registro, nomes):
                contagem[chave] = contagem.get(chave, 0) + 1

    resultado = []
    for chave in nomes:
        dias_bons, dias_ruins = contagem_bons.get(chave, 0), contagem_ruins.get(chave, 0)
        if dias_bons + dias_ruins >= 2:
            resultado.append(FrequenciaHabito(nomes[chave], dias_bons, len(bons), dias_ruins, len(ruins)))
    return sorted(resultado, key=lambda h: -abs((h.pct_bons or 0) - (h.pct_ruins or 0)))
