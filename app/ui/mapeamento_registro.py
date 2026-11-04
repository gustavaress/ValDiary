"""Tradução entre o RegistroDia e o "formulário".

O formulário é um dicionário simples (textos, notas, listas) com uma chave
por campo da tela. Ele serve para três coisas:
- preencher a tela a partir de um registro salvo;
- ler a tela e montar um RegistroDia para salvar;
- guardar o rascunho automático (inclusive com valores ainda inválidos).

Este módulo não depende da interface, por isso pode ser testado sozinho.
"""

from datetime import date

from app.models import (
    ExercicioAim,
    Bebida,
    Classificacao,
    Medicamento,
    Partida,
    RegistroDia,
    ResumoJogo,
    Valorant,
    calcular_horas_sono,
    resumir_partidas,
)
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
        "aquecimento": {True: "sim", False: "nao"}.get(jogo.aquecimento),
        "aquecimento_descricao": jogo.aquecimento_descricao or "",
        "aim_feita": {True: "sim", False: "nao"}.get(jogo.aim_routine.feita),
        "aim_duracao": para_campo(jogo.aim_routine.duracao_min),
        "aim_exercicios": [{"nome": e.nome, "meta": e.meta or "", "feito": e.feito}
                           for e in jogo.aim_routine.exercicios],
        "aim_observacoes": jogo.aim_routine.observacoes or "",
        "partidas": [
            {"agente": p.agente or "", "mapa": p.mapa, "resultado": p.resultado, "abates": para_campo(p.abates),
             "mortes": para_campo(p.mortes), "assistencias": para_campo(p.assistencias),
             "hs_pct": para_campo(p.hs_pct), "acs": para_campo(p.acs), "rr": _rr_para_campo(p.rr),
             "smurf": p.smurf, "elo_inimigos": p.elo_inimigos}
            for p in jogo.partidas
        ],
        # Não tem campo na tela: só atravessa o formulário para não se perder ao salvar.
        "legado": jogo.legado,
        "notas_jogo": jogo.notas or "",
    }
    for chave, atributo, _ in _REFEICOES:
        refeicao = getattr(rotina.alimentacao, atributo)
        formulario[f"{chave}_realizada"] = bool(refeicao.realizada)
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

    def inteiro_valor(self, valor: str, rotulo: str) -> int | None:
        return self._converter(conversao.inteiro, valor, rotulo)

    def decimal_valor(self, valor: str, rotulo: str) -> float | None:
        return self._converter(conversao.decimal, valor, rotulo)


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
        # Refeição desmarcada: horário e descrição são ignorados (ficam null).
        if not formulario.get(f"{chave}_realizada"):
            continue
        refeicao = getattr(rotina.alimentacao, atributo)
        refeicao.realizada = True
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
    jogo.partidas = _ler_partidas(formulario.get("partidas") or [], ler)
    jogo.legado = formulario.get("legado")
    _ler_treino(jogo, formulario, ler)
    for nota in _NOTAS_AVALIACAO:
        setattr(jogo.avaliacao, nota, formulario.get(nota))
    jogo.notas = ler.texto("notas_jogo")

    # Registrou partidas mas não marcou "jogou": é óbvio que jogou.
    if jogo.jogou is None and jogo.partidas:
        jogo.jogou = True
    # Marcou que NÃO jogou: o que ficou nos campos de jogo (desabilitados na tela) é
    # descartado. A aim routine é treino, não partida, e continua valendo.
    if jogo.jogou is False:
        jogo.horario_inicio = jogo.horario_fim = None
        jogo.partidas = []
        jogo.aquecimento = jogo.aquecimento_descricao = None
        for nota in _NOTAS_AVALIACAO:
            setattr(jogo.avaliacao, nota, None)
        jogo.notas = None

    if ler.erros:
        return None, ler.erros
    return registro, []


def _rr_para_campo(rr: int | None) -> str:
    """Variação de RR com sinal explícito: 18 -> "+18", -14 -> "-14"."""
    return "" if rr is None else f"{rr:+d}"


def _partida_vazia(dados: dict) -> bool:
    return not any(conversao.texto(v) if isinstance(v, str) else v for v in dados.values())


def _ler_treino(jogo, formulario: dict, ler: _Leitor) -> None:
    """Aquecimento e aim routine."""
    jogo.aquecimento = {"sim": True, "nao": False}.get(formulario.get("aquecimento"))
    # A descrição só vale se o aquecimento foi feito (o campo fica desabilitado nos outros casos).
    jogo.aquecimento_descricao = ler.texto("aquecimento_descricao") if jogo.aquecimento else None

    aim = jogo.aim_routine
    aim.feita = {"sim": True, "nao": False}.get(formulario.get("aim_feita"))
    aim.duracao_min = ler.inteiro("aim_duracao", "Aim routine (duração em minutos)")
    aim.observacoes = ler.texto("aim_observacoes")
    exercicios = [
        ExercicioAim(nome=conversao.texto(e.get("nome")), meta=conversao.texto(e.get("meta")), feito=bool(e.get("feito")))
        for e in formulario.get("aim_exercicios") or [] if conversao.texto(e.get("nome"))
    ]
    if aim.feita is None and any(e.feito for e in exercicios):
        aim.feita = True  # marcou exercícios: é óbvio que fez
    # A lista da rotina padrão aparece em todo dia; só vale guardar se o treino aconteceu.
    aim.exercicios = exercicios if aim.feita else []


def _ler_partidas(lista: list[dict], ler: _Leitor) -> list[Partida]:
    partidas = []
    for dados in lista:
        if _partida_vazia(dados):  # cartão adicionado e deixado em branco
            continue
        rotulo = f"Partida {len(partidas) + 1}"
        partidas.append(Partida(
            agente=conversao.texto(dados.get("agente")),
            mapa=conversao.texto(dados.get("mapa")),
            resultado=dados.get("resultado"),
            abates=ler.inteiro_valor(dados.get("abates"), f"{rotulo} (abates)"),
            mortes=ler.inteiro_valor(dados.get("mortes"), f"{rotulo} (mortes)"),
            assistencias=ler.inteiro_valor(dados.get("assistencias"), f"{rotulo} (assistências)"),
            hs_pct=ler.decimal_valor(dados.get("hs_pct"), f"{rotulo} (HS%)"),
            acs=ler.decimal_valor(dados.get("acs"), f"{rotulo} (ACS)"),
            # Na smurf o RR não vale para o ranking (o campo fica desativado na tela).
            rr=None if dados.get("smurf") else ler.inteiro_valor(dados.get("rr"), f"{rotulo} (RR)"),
            smurf=bool(dados.get("smurf")),
            elo_inimigos=dados.get("elo_inimigos") or None,
        ))
    return partidas


def resumo_ao_vivo(formulario: dict) -> ResumoJogo:
    """Resumo do dia enquanto o usuário digita (valores inválidos são ignorados)."""
    partidas = _ler_partidas(formulario.get("partidas") or [], _Leitor(formulario))
    if partidas:
        return resumir_partidas(partidas)
    return Valorant(legado=formulario.get("legado")).resumo
