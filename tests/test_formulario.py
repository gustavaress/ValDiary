from datetime import date

import pytest

from app.models import AgenteJogado, Bebida, Classificacao, Medicamento, RegistroDia, validar_registro
from app.ui import conversao
from app.ui.conversao import ErroConversao
from app.ui.mapeamento_registro import (
    derivados_ao_vivo,
    formulario_para_registro,
    registro_para_formulario,
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
    r.valorant.partidas = 4
    r.valorant.vitorias = 3
    r.valorant.derrotas = 1
    r.valorant.abates = 70
    r.valorant.mortes = 50
    r.valorant.assistencias = 18
    r.valorant.acs = 240.5
    r.valorant.adr = 150
    r.valorant.hs_pct = 27.3
    r.valorant.agentes = [AgenteJogado("Jett", 3), AgenteJogado("Raze", 1)]
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
    formulario["partidas"] = "quatro"
    formulario["agua_litros"] = "muito"
    registro, erros = formulario_para_registro(formulario)
    assert registro is None
    assert len(erros) == 3


def test_linhas_vazias_de_lista_sao_ignoradas():
    formulario = registro_para_formulario(_registro())
    formulario["bebidas"].append({"tipo": "", "quantidade": "", "horario": ""})
    registro, _ = formulario_para_registro(formulario)
    assert len(registro.rotina.bebidas) == 1


def test_jogou_e_inferido_quando_ha_estatisticas():
    formulario = registro_para_formulario(RegistroDia(data=date(2026, 11, 2)))
    formulario["abates"] = "20"
    registro, _ = formulario_para_registro(formulario)
    assert registro.valorant.jogou is True


def test_derivados_ao_vivo_ignoram_valores_invalidos():
    formulario = registro_para_formulario(_registro())
    formulario["assistencias"] = "abc"
    jogo = derivados_ao_vivo(formulario)
    assert jogo.kd == 1.4
    assert jogo.kda == 1.4  # assistências inválidas contam como 0


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


def test_total_de_partidas_vazio_usa_soma_dos_agentes():
    formulario = registro_para_formulario(RegistroDia(data=date(2026, 11, 2)))
    formulario["agentes"] = [{"nome": "Jett", "partidas": "2"}, {"nome": "Omen", "partidas": "1"}]
    registro, _ = formulario_para_registro(formulario)
    assert registro.valorant.partidas == 3
    assert registro.valorant.nomes_agentes == ["Jett", "Omen"]


def test_soma_dos_agentes_maior_que_total_e_erro():
    r = _registro()  # 4 partidas no total
    r.valorant.agentes = [AgenteJogado("Jett", 3), AgenteJogado("Raze", 2)]
    erros = validar_registro(r)
    assert any("soma das partidas por agente" in e for e in erros)
