"""Insights em texto para a tela inicial: o que mais muda entre dias bons e ruins.

Regras para não "inventar" conclusões:
- só com pelo menos MIN_DIAS_POR_GRUPO dias bons E ruins;
- só diferenças relevantes: tamanho de efeito (d de Cohen) de pelo menos 0,5,
  ou 25 pontos percentuais para hábitos (aim routine, aquecimento, café da manhã);
- no máximo MAX_INSIGHTS frases, das diferenças mais fortes;
- sempre como associação ("nos dias bons... "), nunca como causa.
"""

from dataclasses import dataclass

import pandas as pd

from app.analysis.comparacao import GRUPO_BONS, GRUPO_RUINS, MIN_DIAS_POR_GRUPO, separar_grupos
from app.analysis.dataframe import registros_para_dataframe
from app.analysis.metricas import POR_CHAVE
from app.models import RegistroDia

MAX_INSIGHTS = 4
EFEITO_MINIMO = 0.5
DIFERENCA_HABITO_PP = 25

# Só fatores de rotina/preparo: dizer que "dias bons têm K/D maior" seria óbvio.
METRICAS_DE_ROTINA = ["sono_horas", "sono_qualidade", "horario_dormir", "agua_litros", "bebidas_qtd",
                      "disposicao_fisica", "disposicao_mental", "estresse", "inicio_jogo",
                      "medicacao_antes_jogo_h", "concentracao"]


@dataclass
class Insights:
    frases: list[str]
    aviso: str | None = None  # quando ainda não há dados suficientes


def _formatar(metrica, valor: float) -> str:
    from app.ui.formatacao import valor_metrica  # formatação de exibição (evita dependência no topo)
    return valor_metrica(metrica, valor)


def _frase_metrica(chave: str, bons: pd.Series, ruins: pd.Series) -> tuple[float, str] | None:
    if len(bons) < MIN_DIAS_POR_GRUPO or len(ruins) < MIN_DIAS_POR_GRUPO:
        return None
    desvio = pd.concat([bons, ruins]).std()
    if not desvio or desvio != desvio:  # sem variação (ou NaN)
        return None
    efeito = (bons.mean() - ruins.mean()) / desvio
    if abs(efeito) < EFEITO_MINIMO:
        return None
    metrica = POR_CHAVE[chave]
    media_bons, media_ruins = _formatar(metrica, bons.mean()), _formatar(metrica, ruins.mean())
    # Formato neutro ("Métrica: ..."), que funciona com qualquer rótulo sem erro de concordância.
    prefixo = "às " if metrica.hora else ""
    frase = f"{metrica.rotulo}: em média {prefixo}{media_bons} nos dias bons, contra {prefixo}{media_ruins} nos ruins."
    return abs(efeito), frase


def _frase_habito(nome: str, bons: list[RegistroDia], ruins: list[RegistroDia], teste) -> tuple[float, str] | None:
    pct_bons = sum(1 for r in bons if teste(r)) / len(bons) * 100
    pct_ruins = sum(1 for r in ruins if teste(r)) / len(ruins) * 100
    diferenca = pct_bons - pct_ruins
    if abs(diferenca) < DIFERENCA_HABITO_PP:
        return None
    frase = f"Você {nome} em {pct_bons:.0f}% dos dias bons e em {pct_ruins:.0f}% dos dias ruins."
    return abs(diferenca) / 50, frase  # 50 pp equivale a um efeito "forte" (1,0)


def gerar_insights(registros: list[RegistroDia], rr_por_dia: dict | None = None) -> Insights:
    bons = [r for r in registros if r.classificacao in GRUPO_BONS]
    ruins = [r for r in registros if r.classificacao in GRUPO_RUINS]
    if len(bons) < MIN_DIAS_POR_GRUPO or len(ruins) < MIN_DIAS_POR_GRUPO:
        faltam = []
        if len(bons) < MIN_DIAS_POR_GRUPO:
            faltam.append(f"{MIN_DIAS_POR_GRUPO - len(bons)} dia(s) bom(ns)")
        if len(ruins) < MIN_DIAS_POR_GRUPO:
            faltam.append(f"{MIN_DIAS_POR_GRUPO - len(ruins)} dia(s) ruim(ns)")
        return Insights([], f"Os insights aparecem quando houver pelo menos {MIN_DIAS_POR_GRUPO} dias bons e "
                            f"{MIN_DIAS_POR_GRUPO} ruins classificados. Faltam {' e '.join(faltam)}.")

    df_bons, df_ruins = separar_grupos(registros_para_dataframe(registros, rr_por_dia))
    candidatos = []
    for chave in METRICAS_DE_ROTINA:
        resultado = _frase_metrica(chave, df_bons[chave].dropna(), df_ruins[chave].dropna())
        if resultado:
            candidatos.append(resultado)
    for nome, teste in (
        ("fez a aim routine", lambda r: bool(r.valorant.aim_routine.feita)),
        ("fez aquecimento antes de jogar", lambda r: bool(r.valorant.aquecimento)),
        ("tomou café da manhã", lambda r: bool(r.rotina.alimentacao.cafe_da_manha.realizada)),
    ):
        resultado = _frase_habito(nome, bons, ruins, teste)
        if resultado:
            candidatos.append(resultado)

    candidatos.sort(key=lambda c: -c[0])
    frases = [frase for _, frase in candidatos[:MAX_INSIGHTS]]
    aviso = None if frases else "Ainda não apareceu nenhuma diferença clara entre seus dias bons e ruins."
    return Insights(frases, aviso)
