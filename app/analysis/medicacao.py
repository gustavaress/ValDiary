"""Medicamentos x desempenho: quanto tempo antes do jogo cada medicamento foi tomado.

Cruza o horário de cada medicamento com o horário de início da sessão de
Valorant ("Começou às"). Só conta como "antes do jogo" o que foi tomado no
mesmo dia, até o início da sessão; o que foi tomado depois não entra.

Os resultados são associações: indicam que o desempenho PODE ter relação com
o momento do medicamento, nunca que ele causou a diferença.
"""

from dataclasses import dataclass, field

import pandas as pd

from app.analysis.filtros import normalizar_texto
from app.models import RegistroDia

MIN_DIAS_POR_FAIXA = 5

# (rótulo, de, até) em minutos antes do início do jogo; até=None = sem limite.
FAIXAS = [
    ("Até 2h antes", 0, 120),
    ("2h a 4h antes", 120, 240),
    ("Mais de 4h antes", 240, None),
]
SEM_MEDICAMENTO = "Não tomou antes do jogo"

# Métricas comparadas entre as faixas (chaves do DataFrame de análise).
METRICAS_COMPARADAS = ["kd", "acs", "hs_pct", "winrate_pct", "mira", "concentracao"]


def _minutos(hhmm: str) -> int:
    horas, minutos = hhmm.split(":")
    return int(horas) * 60 + int(minutos)


@dataclass(frozen=True)
class MedicamentoAntesDoJogo:
    nome: str
    minutos_antes: int

    @property
    def texto(self) -> str:
        horas, minutos = divmod(self.minutos_antes, 60)
        if not horas:
            tempo = f"{minutos} min"
        else:
            tempo = f"{horas}h{minutos:02d}" if minutos else f"{horas}h"
        return f"{self.nome}: tomado {tempo} antes do início"


def medicamentos_antes_do_horario(inicio: str | None,
                                  medicamentos: list[tuple[str | None, str | None]]) -> list[MedicamentoAntesDoJogo]:
    """medicamentos: (nome, horário "HH:MM"). Só os tomados até `inicio` entram."""
    if not inicio:
        return []
    resultado = []
    for nome, horario in medicamentos:
        if nome and nome.strip() and horario:
            antes = _minutos(inicio) - _minutos(horario)
            if antes >= 0:
                resultado.append(MedicamentoAntesDoJogo(nome.strip(), antes))
    return resultado


def medicamentos_antes_do_jogo(registro: RegistroDia) -> list[MedicamentoAntesDoJogo]:
    """Medicamentos tomados antes do início da sessão do dia (vazio se faltar algum horário)."""
    return medicamentos_antes_do_horario(registro.valorant.horario_inicio,
                                         [(m.nome, m.horario) for m in registro.rotina.medicamentos])


def horas_desde_ultimo_medicamento(registro: RegistroDia) -> float | None:
    """Horas entre o medicamento mais próximo do jogo e o início da sessão."""
    antes = medicamentos_antes_do_jogo(registro)
    return round(min(m.minutos_antes for m in antes) / 60, 2) if antes else None


def faixa(minutos: int) -> str:
    for rotulo, de, ate in FAIXAS:
        if minutos >= de and (ate is None or minutos < ate):
            return rotulo
    return FAIXAS[-1][0]


@dataclass
class GrupoFaixa:
    faixa: str
    dias: int
    medias: dict = field(default_factory=dict)  # métrica -> média (None se nenhum dia tem o dado)

    @property
    def suficiente(self) -> bool:
        return self.dias >= MIN_DIAS_POR_FAIXA


@dataclass
class ComparacaoMedicamento:
    nome: str
    grupos: list[GrupoFaixa]


def _jogou(registro: RegistroDia) -> bool:
    return bool(registro.valorant.partidas or registro.valorant.legado or registro.valorant.jogou)


def comparar_medicamentos(registros: list[RegistroDia], rr_por_dia: dict | None = None) -> list[ComparacaoMedicamento]:
    """Para cada medicamento, o desempenho nos dias jogados agrupado pela janela de tempo.

    Só entram dias em que houve jogo e o horário de início da sessão foi registrado
    (sem ele não dá para saber se o medicamento foi antes ou depois).
    """
    from app.analysis.dataframe import registros_para_dataframe  # aqui para evitar import circular

    dias = [r for r in registros if _jogou(r) and r.valorant.horario_inicio]
    if not dias:
        return []
    df = registros_para_dataframe(dias, rr_por_dia).set_index("data")

    # Nome normalizado -> primeira grafia vista ("Ritalina" e "ritalina" são o mesmo).
    nomes: dict[str, str] = {}
    faixas_por_dia: dict[str, dict] = {}
    for registro in dias:
        for medicamento in medicamentos_antes_do_jogo(registro):
            chave = normalizar_texto(medicamento.nome)
            nomes.setdefault(chave, medicamento.nome)
            # Se tomou o mesmo remédio duas vezes antes do jogo, vale a dose mais próxima.
            atual = faixas_por_dia.setdefault(chave, {}).get(registro.data)
            if atual is None or medicamento.minutos_antes < atual:
                faixas_por_dia[chave][registro.data] = medicamento.minutos_antes

    resultado = []
    for chave, nome in sorted(nomes.items(), key=lambda item: item[1].lower()):
        rotulos = {pd.Timestamp(data): faixa(minutos) for data, minutos in faixas_por_dia[chave].items()}
        grupo_do_dia = df.index.map(lambda data: rotulos.get(data, SEM_MEDICAMENTO))
        grupos = []
        for rotulo in [f[0] for f in FAIXAS] + [SEM_MEDICAMENTO]:
            parte = df[grupo_do_dia == rotulo]
            if parte.empty:
                continue
            medias = {m: (float(parte[m].mean()) if parte[m].notna().any() else None) for m in METRICAS_COMPARADAS}
            grupos.append(GrupoFaixa(rotulo, len(parte), medias))
        resultado.append(ComparacaoMedicamento(nome, grupos))
    return resultado
