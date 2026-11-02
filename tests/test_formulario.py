from datetime import date

import pytest

from app.models import Bebida, Classificacao, Medicamento, Partida, RegistroDia
from app.ui import conversao
from app.ui.conversao import ErroConversao
from app.ui.mapeamento_registro import (
    formulario_para_registro,
    registro_para_formulario,
    resumo_ao_vivo,
)


@pytest.mark.parametrize("entrada, esperado", [
    ("7:30", "07:30"), ("07:30", "07:30"), ("0730", "07:30"), ("730", "07:30"),
    ("7h30", "07:30"), ("7h", "07:00"), ("23", "23:00"), ("", None), (None, None),
])
def test_hora_aceita_formatos_comuns(entrada, esperado):
    assert conversao.hora(entrada, "x") == esperado


@pytest.mark.parametrize("entrada", ["25:00", "12:75", "abc", "7:3"])
def test_hora_invalida(entrada):
    with pytest.raises(ErroConversao):
        conversao.hora(entrada, "x")


def test_decimal_aceita_virgula():
    assert conversao.decimal("2,5", "x") == 2.5
    assert conversao.decimal("2.5", "x") == 2.5
    assert conversao.decimal("  ", "x") is None


def _registro() -> RegistroDia:
    r = RegistroDia(data=date(2026, 11, 2), classificacao=Classificacao.EXCELENTE)
    r.rotina.sono.dormiu_as = "23:30"
    r.rotina.sono.acordou_as = "07:30"
    r.rotina.sono.qualidade = 8
    r.rotina.alimentacao.almoco.realizada = True
    r.rotina.alimentacao.almoco.horario = "12:30"
    r.rotina.alimentacao.almoco.descricao = "Arroz e frango"
    r.rotina.agua_litros = 2.5
    r.rotina.bebidas = [Bebida("cafe", "1 xícara", "09:00")]
    r.rotina.medicamentos = [Medicamento("Remédio", "10mg", "08:00")]
    r.rotina.estresse = 4
    r.rotina.observacoes = "Dia tranquilo"
    r.valorant.jogou = True
    r.valorant.horario_inicio = "19:00"
    r.valorant.partidas = [
        Partida("Jett", "vitoria", 22, 14, 6, 27.3, 260.5),
        Partida("Raze", "derrota", 13, 16, 3, 21.0, 180),
    ]
    r.valorant.avaliacao.mira = 9
    r.valorant.notas = "Microajustes fáceis"
    return r


def test_ida_e_volta_pelo_formulario_preserva_tudo():
    original = _registro()
    reconstruido, erros = formulario_para_registro(registro_para_formulario(original))
    assert erros == []
    assert reconstruido.to_dict() == original.to_dict()


def test_horas_de_sono_automaticas_ficam_vazias_no_formulario():
    formulario = registro_para_formulario(_registro())
    assert formulario["sono_horas"] == ""  # calculado pelos horários


def test_horas_de_sono_manuais_aparecem_no_formulario():
    r = _registro()
    r.rotina.sono.horas = 6.5
    assert registro_para_formulario(r)["sono_horas"] == "6,5"


def test_formulario_vazio_gera_registro_vazio():
    formulario = registro_para_formulario(RegistroDia(data=date(2026, 11, 2)))
    registro, erros = formulario_para_registro(formulario)
    assert erros == []
    assert registro.to_dict() == RegistroDia(data=date(2026, 11, 2)).to_dict()


def test_erros_sao_acumulados():
    formulario = registro_para_formulario(_registro())
    formulario["sono_dormiu_as"] = "99:99"
    formulario["partidas"][0]["abates"] = "quatro"
    formulario["agua_litros"] = "muito"
    registro, erros = formulario_para_registro(formulario)
    assert registro is None
    assert len(erros) == 3


def test_linhas_vazias_de_lista_sao_ignoradas():
    formulario = registro_para_formulario(_registro())
    formulario["bebidas"].append({"tipo": "", "quantidade": "", "horario": ""})
    registro, _ = formulario_para_registro(formulario)
    assert len(registro.rotina.bebidas) == 1


def _partida_form(**valores) -> dict:
    base = {"agente": "", "resultado": None, "abates": "", "mortes": "", "assistencias": "",
            "hs_pct": "", "acs": ""}
    return base | valores


def test_jogou_e_inferido_quando_ha_partidas():
    formulario = registro_para_formulario(RegistroDia(data=date(2026, 11, 2)))
    formulario["partidas"] = [_partida_form(abates="20")]
    registro, _ = formulario_para_registro(formulario)
    assert registro.valorant.jogou is True


def test_cartao_de_partida_em_branco_e_ignorado():
    formulario = registro_para_formulario(_registro())
    formulario["partidas"].append(_partida_form())
    registro, erros = formulario_para_registro(formulario)
    assert erros == [] and len(registro.valorant.partidas) == 2


def test_resumo_ao_vivo_ignora_valores_invalidos():
    formulario = registro_para_formulario(_registro())
    formulario["partidas"][1]["assistencias"] = "abc"
    resumo = resumo_ao_vivo(formulario)
    assert resumo.partidas == 2
    assert resumo.kda_texto == "35/30/6"  # assistência inválida não soma


def test_legado_atravessa_o_formulario():
    r = RegistroDia(data=date(2026, 11, 2))
    r.valorant.legado = {"partidas": 3, "abates": 40, "mortes": 30, "adr": 140}
    formulario = registro_para_formulario(r)
    assert resumo_ao_vivo(formulario).partidas == 3
    registro, _ = formulario_para_registro(formulario)
    assert registro.valorant.legado == r.valorant.legado  # nada se perde ao salvar


def test_refeicao_desmarcada_ignora_os_campos():
    formulario = registro_para_formulario(_registro())
    assert formulario["almoco_realizada"] is True
    formulario["almoco_realizada"] = False  # desmarcou, mas o texto continua na tela
    registro, _ = formulario_para_registro(formulario)
    almoco = registro.rotina.alimentacao.almoco
    assert (almoco.realizada, almoco.horario, almoco.descricao) == (None, None, None)


def test_refeicao_marcada_sem_detalhes():
    formulario = registro_para_formulario(RegistroDia(data=date(2026, 11, 2)))
    formulario["cafe_realizada"] = True
    registro, _ = formulario_para_registro(formulario)
    assert registro.rotina.alimentacao.cafe_da_manha.realizada is True


def test_ranking_e_rr_atravessam_o_formulario():
    from app.models.ranking import Ranking
    r = _registro()
    r.valorant.ranking_inicio = Ranking("Ouro 2", 85)
    r.valorant.partidas[0].rr = 18
    r.valorant.partidas[1].rr = -14
    formulario = registro_para_formulario(r)
    assert formulario["ranking_elo"] == "Ouro 2" and formulario["ranking_rr"] == "85"
    assert [p["rr"] for p in formulario["partidas"]] == ["+18", "-14"]  # sinal sempre visível

    reconstruido, erros = formulario_para_registro(formulario)
    assert erros == []
    assert reconstruido.valorant.resumo.rr == 4
    assert reconstruido.valorant.ranking_final == Ranking("Ouro 2", 89)


def test_ranking_pela_metade_e_erro():
    from app.models import validar_registro
    formulario = registro_para_formulario(_registro())
    formulario["ranking_elo"] = "Ouro 2"   # sem RR
    registro, _ = formulario_para_registro(formulario)
    assert any("preencha o elo e o RR" in e for e in validar_registro(registro))
