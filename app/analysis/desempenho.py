"""Desempenho agrupado por mapa ou por agente (a partir das partidas registradas).

Dias antigos registrados só com os totais do dia ("legado") não têm mapa nem
agente por partida, então não entram aqui.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from app.models import Partida, RegistroDia
from app.models.datas import semana_da_data


@dataclass
class LinhaDesempenho:
    nome: str
    partidas: int
    vitorias: int
    com_resultado: int
    abates: int
    mortes: int
    soma_acs: float
    n_acs: int
    soma_hs: float
    n_hs: int
    rr: int
    n_rr: int

    @property
    def winrate_pct(self) -> float | None:
        return self.vitorias / self.com_resultado * 100 if self.com_resultado else None

    @property
    def kd(self) -> float | None:
        return round(self.abates / max(self.mortes, 1), 2) if (self.abates or self.mortes) else None

    @property
    def acs(self) -> float | None:
        return self.soma_acs / self.n_acs if self.n_acs else None

    @property
    def hs_pct(self) -> float | None:
        return self.soma_hs / self.n_hs if self.n_hs else None

    @property
    def rr_medio(self) -> float | None:
        """RR médio por partida (soma das partidas; não considera a proteção do ranking)."""
        return self.rr / self.n_rr if self.n_rr else None


def desempenho_por(registros: list[RegistroDia], atributo: str) -> list[LinhaDesempenho]:
    """atributo: "mapa" ou "agente". Ordenado pelo número de partidas (mais jogados primeiro)."""
    grupos: dict[str, list[Partida]] = {}
    for registro in registros:
        for partida in registro.valorant.partidas:
            nome = getattr(partida, atributo)
            if nome:
                grupos.setdefault(nome, []).append(partida)

    linhas = []
    for nome, partidas in grupos.items():
        com_kd = [p for p in partidas if p.abates is not None and p.mortes is not None]
        acs = [p.acs for p in partidas if p.acs is not None]
        hs = [p.hs_pct for p in partidas if p.hs_pct is not None]
        rr = [p.rr for p in partidas if p.rr is not None]
        linhas.append(LinhaDesempenho(
            nome=nome, partidas=len(partidas),
            vitorias=sum(1 for p in partidas if p.resultado == "vitoria"),
            com_resultado=sum(1 for p in partidas if p.resultado),
            abates=sum(p.abates for p in com_kd), mortes=sum(p.mortes for p in com_kd),
            soma_acs=sum(acs), n_acs=len(acs), soma_hs=sum(hs), n_hs=len(hs), rr=sum(rr), n_rr=len(rr),
        ))
    return sorted(linhas, key=lambda l: (-l.partidas, l.nome))


# --- Aim routine ------------------------------------------------------------

def fez_aim_routine(registro: RegistroDia) -> bool:
    return bool(registro.valorant.aim_routine.feita)


def aim_routines_por_semana(registros: list[RegistroDia], hoje: date, semanas: int = 8) -> list[tuple[str, int]]:
    """[(rótulo da semana, quantos dias com aim routine)], da mais antiga para a atual."""
    contagem: dict[tuple[int, int], int] = {}
    for registro in registros:
        if fez_aim_routine(registro):
            semana = semana_da_data(registro.data)
            contagem[semana] = contagem.get(semana, 0) + 1
    resultado = []
    for i in range(semanas - 1, -1, -1):
        ano, numero = semana_da_data(hoje - timedelta(weeks=i))
        resultado.append((f"S{numero:02d}", contagem.get((ano, numero), 0)))
    return resultado
