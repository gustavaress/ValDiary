"""Modelos de dados do diário.

Cada classe representa um bloco do JSON. Regras gerais:
- Campo não preenchido = None (vira null no JSON), nunca zero.
  "Não registrei a água" é diferente de "bebi 0 litros".
- to_dict() gera o dicionário que vai para o arquivo.
- from_dict() reconstrói o objeto a partir do arquivo e ignora chaves
  desconhecidas, para que arquivos de versões futuras não quebrem o app.
"""

from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime
from enum import StrEnum

from app.models.datas import semana_da_data

DIAS_SEMANA = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]


class Classificacao(StrEnum):
    EXCELENTE = "excelente"
    BOM = "bom"
    NORMAL = "normal"
    RUIM = "ruim"
    PESSIMO = "pessimo"


def _simples(cls, dados: dict | None):
    """Cria uma dataclass sem sub-objetos a partir de um dict, ignorando chaves extras."""
    dados = dados or {}
    nomes = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in dados.items() if k in nomes})


def _minutos(hhmm: str) -> int:
    horas, minutos = hhmm.split(":")
    return int(horas) * 60 + int(minutos)


def calcular_horas_sono(dormiu_as: str | None, acordou_as: str | None) -> float | None:
    """Horas dormidas a partir de "HH:MM", tratando a virada da meia-noite.

    Ex.: dormiu 23:30, acordou 07:00 -> 7.5
    """
    if not dormiu_as or not acordou_as:
        return None
    diferenca = (_minutos(acordou_as) - _minutos(dormiu_as)) % (24 * 60)
    return round(diferenca / 60, 2)


# --- Rotina ---------------------------------------------------------------

@dataclass
class Sono:
    dormiu_as: str | None = None
    acordou_as: str | None = None
    horas: float | None = None  # se vazio, é calculado pelos horários
    qualidade: int | None = None

    @property
    def horas_efetivas(self) -> float | None:
        if self.horas is not None:
            return self.horas
        return calcular_horas_sono(self.dormiu_as, self.acordou_as)

    def to_dict(self) -> dict:
        dados = asdict(self)
        dados["horas"] = self.horas_efetivas
        return dados


@dataclass
class Refeicao:
    realizada: bool | None = None  # True = teve a refeição; None = não marcada
    horario: str | None = None
    descricao: str | None = None


@dataclass
class Alimentacao:
    cafe_da_manha: Refeicao = field(default_factory=Refeicao)
    almoco: Refeicao = field(default_factory=Refeicao)
    jantar: Refeicao = field(default_factory=Refeicao)
    outros: str | None = None

    @classmethod
    def from_dict(cls, dados: dict | None) -> "Alimentacao":
        dados = dados or {}
        return cls(
            cafe_da_manha=_simples(Refeicao, dados.get("cafe_da_manha")),
            almoco=_simples(Refeicao, dados.get("almoco")),
            jantar=_simples(Refeicao, dados.get("jantar")),
            outros=dados.get("outros"),
        )


@dataclass
class Bebida:
    tipo: str | None = None        # ex.: "cafe", "energetico", "refrigerante"
    quantidade: str | None = None  # texto livre: "1 lata", "2 xícaras"
    horario: str | None = None


@dataclass
class Medicamento:
    nome: str | None = None
    dose: str | None = None
    horario: str | None = None


@dataclass
class Rotina:
    sono: Sono = field(default_factory=Sono)
    alimentacao: Alimentacao = field(default_factory=Alimentacao)
    agua_litros: float | None = None
    bebidas: list[Bebida] = field(default_factory=list)
    medicamentos: list[Medicamento] = field(default_factory=list)
    disposicao_fisica: int | None = None
    disposicao_mental: int | None = None
    estresse: int | None = None  # atenção: aqui 10 = muito estressado
    observacoes: str | None = None

    def to_dict(self) -> dict:
        dados = asdict(self)
        dados["sono"] = self.sono.to_dict()
        return dados

    @classmethod
    def from_dict(cls, dados: dict | None) -> "Rotina":
        dados = dados or {}
        return cls(
            sono=_simples(Sono, dados.get("sono")),
            alimentacao=Alimentacao.from_dict(dados.get("alimentacao")),
            agua_litros=dados.get("agua_litros"),
            bebidas=[_simples(Bebida, b) for b in dados.get("bebidas") or []],
            medicamentos=[_simples(Medicamento, m) for m in dados.get("medicamentos") or []],
            disposicao_fisica=dados.get("disposicao_fisica"),
            disposicao_mental=dados.get("disposicao_mental"),
            estresse=dados.get("estresse"),
            observacoes=dados.get("observacoes"),
        )


# --- Valorant -------------------------------------------------------------

RESULTADOS = ("vitoria", "derrota", "empate")


@dataclass
class Partida:
    agente: str | None = None
    resultado: str | None = None  # "vitoria", "derrota" ou "empate"
    abates: int | None = None
    mortes: int | None = None
    assistencias: int | None = None
    hs_pct: float | None = None
    acs: float | None = None
    rr: int | None = None  # pontos de ranking ganhos (+) ou perdidos (-) na partida

    @property
    def kd(self) -> float | None:
        if self.abates is None or self.mortes is None:
            return None
        return round(self.abates / max(self.mortes, 1), 2)


def _razao(numerador: int | None, mortes: int | None) -> float | None:
    # Com 0 mortes, dividimos por 1 (convenção usada pelos trackers).
    if numerador is None or mortes is None:
        return None
    return round(numerador / max(mortes, 1), 2)


@dataclass(frozen=True)
class ResumoJogo:
    """Números do dia, sempre CALCULADOS (a partir das partidas ou do legado)."""
    partidas: int | None = None
    vitorias: int | None = None
    derrotas: int | None = None
    empates: int | None = None
    abates: int | None = None          # totais do dia
    mortes: int | None = None
    assistencias: int | None = None
    hs_pct: float | None = None        # médias por partida
    acs: float | None = None
    agentes: dict = field(default_factory=dict)  # {"Jett": 3, ...}
    rr: int | None = None              # soma do RR das partidas do dia
    # Base do winrate: partidas com resultado conhecido (partidas sem resultado
    # marcado não contam como derrota).
    partidas_com_resultado: int | None = None

    @property
    def kd(self) -> float | None:
        return _razao(self.abates, self.mortes)

    @property
    def kda(self) -> float | None:
        if self.abates is None:
            return None
        return _razao(self.abates + (self.assistencias or 0), self.mortes)

    @property
    def kda_texto(self) -> str | None:
        if self.abates is None or self.mortes is None:
            return None
        return f"{self.abates}/{self.mortes}/{self.assistencias or 0}"

    @property
    def winrate_pct(self) -> float | None:
        if self.vitorias is None or not self.partidas_com_resultado:
            return None
        return round(self.vitorias / self.partidas_com_resultado * 100, 1)

    def to_dict(self) -> dict:
        dados = asdict(self)
        dados.update(kd=self.kd, kda=self.kda, kda_texto=self.kda_texto, winrate_pct=self.winrate_pct)
        return dados


def _soma(valores) -> int | None:
    presentes = [v for v in valores if v is not None]
    return sum(presentes) if presentes else None


def _media(valores) -> float | None:
    presentes = [v for v in valores if v is not None]
    return round(sum(presentes) / len(presentes), 1) if presentes else None


def resumir_partidas(partidas: list[Partida]) -> ResumoJogo:
    resultados = [p.resultado for p in partidas if p.resultado]
    contar = (lambda r: resultados.count(r)) if resultados else (lambda r: None)
    agentes: dict[str, int] = {}
    for partida in partidas:
        if partida.agente:
            agentes[partida.agente] = agentes.get(partida.agente, 0) + 1
    return ResumoJogo(
        partidas=len(partidas) or None,
        vitorias=contar("vitoria"),
        derrotas=contar("derrota"),
        empates=contar("empate"),
        abates=_soma(p.abates for p in partidas),
        mortes=_soma(p.mortes for p in partidas),
        assistencias=_soma(p.assistencias for p in partidas),
        hs_pct=_media(p.hs_pct for p in partidas),
        acs=_media(p.acs for p in partidas),
        agentes=agentes,
        partidas_com_resultado=len(resultados) or None,
        rr=_soma(p.rr for p in partidas),
    )


def resumir_legado(legado: dict) -> ResumoJogo:
    """Dias registrados antes do registro por partida (formato v2: totais do dia)."""
    agentes = {a["nome"]: a.get("partidas") for a in legado.get("agentes") or [] if isinstance(a, dict)}
    return ResumoJogo(
        partidas=legado.get("partidas"),
        vitorias=legado.get("vitorias"),
        derrotas=legado.get("derrotas"),
        empates=legado.get("empates"),
        abates=legado.get("abates"),
        mortes=legado.get("mortes"),
        assistencias=legado.get("assistencias"),
        hs_pct=legado.get("hs_pct"),
        acs=legado.get("acs"),
        agentes=agentes,
        # Regra do formato antigo: winrate = vitórias ÷ partidas do dia.
        partidas_com_resultado=legado.get("partidas") if legado.get("vitorias") is not None else None,
    )


@dataclass
class AvaliacaoJogo:
    """Percepções subjetivas, escala 1-10."""
    mira: int | None = None
    movimentacao: int | None = None
    tomada_decisao: int | None = None
    concentracao: int | None = None
    consistencia: int | None = None


@dataclass
class Valorant:
    jogou: bool | None = None
    horario_inicio: str | None = None
    horario_fim: str | None = None

    partidas: list[Partida] = field(default_factory=list)
    avaliacao: AvaliacaoJogo = field(default_factory=AvaliacaoJogo)
    notas: str | None = None
    # Totais do dia no formato antigo (antes do registro por partida). Guardado
    # como veio, sem perder nada; usado no resumo só quando não há partidas.
    legado: dict | None = None

    @property
    def resumo(self) -> ResumoJogo:
        if self.partidas:
            return resumir_partidas(self.partidas)
        if self.legado:
            return resumir_legado(self.legado)
        return ResumoJogo()

    @property
    def nomes_agentes(self) -> list[str]:
        return list(self.resumo.agentes)

    def to_dict(self) -> dict:
        dados = asdict(self)
        # O resumo vai para o JSON para facilitar a leitura humana e pela IA,
        # mas é ignorado ao carregar (sempre recalculado).
        dados["resumo"] = self.resumo.to_dict()
        return dados

    @classmethod
    def from_dict(cls, dados: dict | None) -> "Valorant":
        dados = dict(dados or {})
        avaliacao = _simples(AvaliacaoJogo, dados.pop("avaliacao", None))
        partidas = dados.pop("partidas", None) or []
        objeto = _simples(cls, dados)
        objeto.avaliacao = avaliacao
        objeto.partidas = [_simples(Partida, p) for p in partidas]
        return objeto


# --- Dia ------------------------------------------------------------------

@dataclass
class RegistroDia:
    data: date
    classificacao: Classificacao | None = None
    rotina: Rotina = field(default_factory=Rotina)
    valorant: Valorant = field(default_factory=Valorant)
    criado_em: datetime | None = None
    editado_em: datetime | None = None

    @property
    def semana(self) -> tuple[int, int]:
        """(ano, número da semana de domingo a sábado). Define em qual arquivo o dia é salvo."""
        return semana_da_data(self.data)

    def to_dict(self) -> dict:
        return {
            "data": self.data.isoformat(),
            "dia_semana": DIAS_SEMANA[self.data.weekday()],
            "classificacao": self.classificacao.value if self.classificacao else None,
            "rotina": self.rotina.to_dict(),
            "valorant": self.valorant.to_dict(),
            "criado_em": self.criado_em.isoformat(timespec="seconds") if self.criado_em else None,
            "editado_em": self.editado_em.isoformat(timespec="seconds") if self.editado_em else None,
        }

    @classmethod
    def from_dict(cls, dados: dict) -> "RegistroDia":
        classificacao = dados.get("classificacao")
        criado_em = dados.get("criado_em")
        editado_em = dados.get("editado_em")
        return cls(
            data=date.fromisoformat(dados["data"]),
            classificacao=Classificacao(classificacao) if classificacao else None,
            rotina=Rotina.from_dict(dados.get("rotina")),
            valorant=Valorant.from_dict(dados.get("valorant")),
            criado_em=datetime.fromisoformat(criado_em) if criado_em else None,
            editado_em=datetime.fromisoformat(editado_em) if editado_em else None,
        )
