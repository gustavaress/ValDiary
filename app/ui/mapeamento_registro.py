"""Tradução entre o RegistroDia e o "formulário".

O formulário é um dicionário simples (textos, notas, listas) com uma chave
por campo da tela. Ele serve para três coisas:
- preencher a tela a partir de um registro salvo;
- ler a tela e montar um RegistroDia para salvar;
- guardar o rascunho automático (inclusive com valores ainda inválidos).

Este módulo não depende da interface, por isso pode ser testado sozinho.
"""

from datetime import date

from app.models import Bebida, Classificacao, Medicamento, RegistroDia, Valorant, calcular_horas_sono
from app.ui import conversao
from app.ui.conversao import ErroConversao, para_campo

_REFEICOES = (
    ("cafe", "cafe_da_manha", "Café da manhã"),
    ("almoco", "almoco", "Almoço"),
    ("jantar", "jantar", "Jantar"),
)

_NOTAS_AVALIACAO = ("mira", "movimentacao", "tomada_decisao", "concentracao", "consistencia")


def registro_para_formulario(registro: RegistroDia) -> dict:
    rotina, jogo = registro.rotina, registro.valorant
    sono = rotina.sono

    # Se as horas salvas são as calculadas pelos horários, o campo fica vazio
    # (modo automático). Só mostramos quando o valor foi digitado à mão.
    horas_auto = calcular_horas_sono(sono.dormiu_as, sono.acordou_as)
    horas = "" if sono.horas is None or sono.horas == horas_auto else para_campo(sono.horas)

    formulario = {
        "data": registro.data.isoformat(),
        "classificacao": registro.classificacao.value if registro.classificacao else None,
        "sono_dormiu_as": sono.dormiu_as or "",
        "sono_acordou_as": sono.acordou_as or "",
        "sono_horas": horas,
        "sono_qualidade": sono.qualidade,
        "alimentacao_outros": rotina.alimentacao.outros or "",
        "agua_litros": para_campo(rotina.agua_litros),
        "bebidas": [
            {"tipo": b.tipo or "", "quantidade": b.quantidade or "", "horario": b.horario or ""}
            for b in rotina.bebidas
        ],
        "medicamentos": [
            {"nome": m.nome or "", "dose": m.dose or "", "horario": m.horario or ""}
            for m in rotina.medicamentos
        ],
        "disposicao_fisica": rotina.disposicao_fisica,
        "disposicao_mental": rotina.disposicao_mental,
        "estresse": rotina.estresse,
        "observacoes": rotina.observacoes or "",
        "jogou": {True: "sim", False: "nao"}.get(jogo.jogou),
        "jogo_inicio": jogo.horario_inicio or "",
        "jogo_fim": jogo.horario_fim or "",
        "partidas": para_campo(jogo.partidas),
        "vitorias": para_campo(jogo.vitorias),
        "derrotas": para_campo(jogo.derrotas),
        "empates": para_campo(jogo.empates),
        "abates": para_campo(jogo.abates),
        "mortes": para_campo(jogo.mortes),
        "assistencias": para_campo(jogo.assistencias),
        "acs": para_campo(jogo.acs),
        "adr": para_campo(jogo.adr),
        "hs_pct": para_campo(jogo.hs_pct),
        "agentes": ", ".join(jogo.agentes),
        "notas_jogo": jogo.notas or "",
    }
    for chave, atributo, _ in _REFEICOES:
        refeicao = getattr(rotina.alimentacao, atributo)
        formulario[f"{chave}_horario"] = refeicao.horario or ""
        formulario[f"{chave}_descricao"] = refeicao.descricao or ""
    for nota in _NOTAS_AVALIACAO:
        formulario[nota] = getattr(jogo.avaliacao, nota)
    return formulario


class _Leitor:
    """Converte campos acumulando os erros em vez de parar no primeiro."""

    def __init__(self, formulario: dict):
        self.formulario = formulario
        self.erros: list[str] = []

    def _converter(self, funcao, valor, rotulo):
        try:
            return funcao(valor, rotulo)
        except ErroConversao as erro:
            self.erros.append(str(erro))
            return None

    def texto(self, chave: str) -> str | None:
        return conversao.texto(self.formulario.get(chave))

    def inteiro(self, chave: str, rotulo: str) -> int | None:
        return self._converter(conversao.inteiro, self.formulario.get(chave), rotulo)

    def decimal(self, chave: str, rotulo: str) -> float | None:
        return self._converter(conversao.decimal, self.formulario.get(chave), rotulo)

    def hora(self, chave: str, rotulo: str) -> str | None:
        return self._converter(conversao.hora, self.formulario.get(chave), rotulo)

    def hora_valor(self, valor: str, rotulo: str) -> str | None:
        return self._converter(conversao.hora, valor, rotulo)


def formulario_para_registro(formulario: dict) -> tuple[RegistroDia | None, list[str]]:
    """Retorna (registro, []) se tudo foi convertido, ou (None, erros)."""
    ler = _Leitor(formulario)
    registro = RegistroDia(data=date.fromisoformat(formulario["data"]))
    classificacao = formulario.get("classificacao")
    registro.classificacao = Classificacao(classificacao) if classificacao else None

    # Rotina
    rotina = registro.rotina
    rotina.sono.dormiu_as = ler.hora("sono_dormiu_as", "Horário que dormiu")
    rotina.sono.acordou_as = ler.hora("sono_acordou_as", "Horário que acordou")
    rotina.sono.horas = ler.decimal("sono_horas", "Horas dormidas")
    rotina.sono.qualidade = formulario.get("sono_qualidade")

    for chave, atributo, nome in _REFEICOES:
        refeicao = getattr(rotina.alimentacao, atributo)
        refeicao.horario = ler.hora(f"{chave}_horario", f"{nome} (horário)")
        refeicao.descricao = ler.texto(f"{chave}_descricao")
    rotina.alimentacao.outros = ler.texto("alimentacao_outros")

    rotina.agua_litros = ler.decimal("agua_litros", "Água (litros)")
    rotina.bebidas = [
        Bebida(
            tipo=conversao.texto(b.get("tipo")),
            quantidade=conversao.texto(b.get("quantidade")),
            horario=ler.hora_valor(b.get("horario"), f"Bebida '{b.get('tipo') or '?'}' (horário)"),
        )
        for b in formulario.get("bebidas") or []
        if any(conversao.texto(v) for v in b.values())
    ]
    rotina.medicamentos = [
        Medicamento(
            nome=conversao.texto(m.get("nome")),
            dose=conversao.texto(m.get("dose")),
            horario=ler.hora_valor(m.get("horario"), f"Medicamento '{m.get('nome') or '?'}' (horário)"),
        )
        for m in formulario.get("medicamentos") or []
        if any(conversao.texto(v) for v in m.values())
    ]
    rotina.disposicao_fisica = formulario.get("disposicao_fisica")
    rotina.disposicao_mental = formulario.get("disposicao_mental")
    rotina.estresse = formulario.get("estresse")
    rotina.observacoes = ler.texto("observacoes")

    # Valorant
    jogo = registro.valorant
    jogo.jogou = {"sim": True, "nao": False}.get(formulario.get("jogou"))
    jogo.horario_inicio = ler.hora("jogo_inicio", "Início do jogo")
    jogo.horario_fim = ler.hora("jogo_fim", "Fim do jogo")
    jogo.partidas = ler.inteiro("partidas", "Partidas")
    jogo.vitorias = ler.inteiro("vitorias", "Vitórias")
    jogo.derrotas = ler.inteiro("derrotas", "Derrotas")
    jogo.empates = ler.inteiro("empates", "Empates")
    jogo.abates = ler.inteiro("abates", "Abates")
    jogo.mortes = ler.inteiro("mortes", "Mortes")
    jogo.assistencias = ler.inteiro("assistencias", "Assistências")
    jogo.acs = ler.decimal("acs", "ACS")
    jogo.adr = ler.decimal("adr", "ADR")
    jogo.hs_pct = ler.decimal("hs_pct", "HS%")
    jogo.agentes = conversao.lista_de_nomes(formulario.get("agentes"))
    for nota in _NOTAS_AVALIACAO:
        setattr(jogo.avaliacao, nota, formulario.get(nota))
    jogo.notas = ler.texto("notas_jogo")

    # Se preencheu estatísticas mas não marcou "jogou", é óbvio que jogou.
    estatisticas = (jogo.partidas, jogo.abates, jogo.acs, jogo.adr, jogo.hs_pct)
    if jogo.jogou is None and any(v is not None for v in estatisticas):
        jogo.jogou = True

    if ler.erros:
        return None, ler.erros
    return registro, []


def derivados_ao_vivo(formulario: dict) -> Valorant:
    """Valorant só com os campos usados nos cálculos de K/D, KDA e winrate.

    Valores inválidos são ignorados (é só uma prévia enquanto o usuário digita).
    """
    def seguro(chave):
        try:
            return conversao.inteiro(formulario.get(chave), chave)
        except ErroConversao:
            return None

    return Valorant(
        partidas=seguro("partidas"),
        vitorias=seguro("vitorias"),
        abates=seguro("abates"),
        mortes=seguro("mortes"),
        assistencias=seguro("assistencias"),
    )
