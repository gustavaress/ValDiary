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

@dataclass
class AgenteJogado:
    nome: str
    partidas: int | None = None


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

    partidas: int | None = None
    vitorias: int | None = None
    derrotas: int | None = None
    empates: int | None = None

    # Totais somados de todas as partidas do dia.
    abates: int | None = None
    mortes: int | None = None
    assistencias: int | None = None

    # Médias por partida.
    acs: float | None = None
    adr: float | None = None
    hs_pct: float | None = None

    agentes: list[AgenteJogado] = field(default_factory=list)
    avaliacao: AvaliacaoJogo = field(default_factory=AvaliacaoJogo)
    notas: str | None = None

    # Valores derivados: calculados, nunca digitados. Com 0 mortes,
    # dividimos por 1 (convenção usada pelos trackers).
    @property
    def kd(self) -> float | None:
        if self.abates is None or self.mortes is None:
            return None
        return round(self.abates / max(self.mortes, 1), 2)

    @property
    def kda(self) -> float | None:
        if self.abates is None or self.mortes is None:
            return None
        return round((self.abates + (self.assistencias or 0)) / max(self.mortes, 1), 2)

    @property
    def kda_texto(self) -> str | None:
        if self.abates is None or self.mortes is None:
            return None
        return f"{self.abates}/{self.mortes}/{self.assistencias or 0}"

    @property
    def nomes_agentes(self) -> list[str]:
        return [a.nome for a in self.agentes]

    @property
    def winrate_pct(self) -> float | None:
        if not self.partidas or self.vitorias is None:
            return None
        return round(self.vitorias / self.partidas * 100, 1)

    def to_dict(self) -> dict:
        dados = asdict(self)
        # Os derivados vão para o JSON para facilitar a leitura humana e pela IA,
        # mas são ignorados ao carregar (sempre recalculados).
        dados["derivados"] = {
            "kd": self.kd,
            "kda": self.kda,
            "kda_texto": self.kda_texto,
            "winrate_pct": self.winrate_pct,
        }
        return dados

    @classmethod
    def from_dict(cls, dados: dict | None) -> "Valorant":
        dados = dict(dados or {})
        avaliacao = _simples(AvaliacaoJogo, dados.pop("avaliacao", None))
        agentes = dados.pop("agentes", None) or []
        objeto = _simples(cls, dados)
        objeto.avaliacao = avaliacao
        objeto.agentes = [_simples(AgenteJogado, a) for a in agentes]
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
    def semana_iso(self) -> tuple[int, int]:
        """(ano ISO, semana ISO). Define em qual arquivo o dia é salvo."""
        ano, semana, _ = self.data.isocalendar()
        return ano, semana

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
