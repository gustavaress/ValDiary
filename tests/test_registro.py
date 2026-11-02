from datetime import date, datetime

from app.models import (
    AgenteJogado,
    Bebida,
    Classificacao,
    RegistroDia,
    calcular_horas_sono,
    validar_registro,
)


def _registro_completo() -> RegistroDia:
    r = RegistroDia(data=date(2026, 11, 2), classificacao=Classificacao.BOM)
    r.rotina.sono.dormiu_as = "23:30"
    r.rotina.sono.acordou_as = "07:45"
    r.rotina.sono.qualidade = 8
    r.rotina.alimentacao.almoco.descricao = "Arroz, feijão, frango"
    r.rotina.agua_litros = 2.5
    r.rotina.bebidas.append(Bebida(tipo="energetico", quantidade="1 lata", horario="20:00"))
    r.rotina.estresse = 3
    r.valorant.jogou = True
    r.valorant.partidas = 4
    r.valorant.vitorias = 3
    r.valorant.derrotas = 1
    r.valorant.abates = 72
    r.valorant.mortes = 55
    r.valorant.assistencias = 20
    r.valorant.acs = 245
    r.valorant.adr = 158.4
    r.valorant.hs_pct = 27.5
    r.valorant.agentes = [AgenteJogado("Jett", 3), AgenteJogado("Raze", 1)]
    r.valorant.avaliacao.mira = 9
    r.criado_em = datetime(2026, 11, 2, 23, 40, 2)
    return r


def test_ida_e_volta_preserva_todos_os_dados():
    original = _registro_completo()
    reconstruido = RegistroDia.from_dict(original.to_dict())
    assert reconstruido.to_dict() == original.to_dict()


def test_campos_nao_preenchidos_viram_null():
    dados = RegistroDia(data=date(2026, 11, 2)).to_dict()
    assert dados["classificacao"] is None
    assert dados["rotina"]["agua_litros"] is None
    assert dados["valorant"]["derivados"]["kd"] is None


def test_chaves_desconhecidas_sao_ignoradas():
    dados = _registro_completo().to_dict()
    dados["campo_do_futuro"] = 123
    dados["valorant"]["outro_campo"] = "x"
    RegistroDia.from_dict(dados)  # não deve lançar erro


def test_sono_atravessando_meia_noite():
    assert calcular_horas_sono("23:30", "07:45") == 8.25
    assert calcular_horas_sono("01:00", "09:00") == 8.0
    assert calcular_horas_sono(None, "09:00") is None


def test_horas_manuais_tem_prioridade():
    r = _registro_completo()
    r.rotina.sono.horas = 6.0
    assert r.to_dict()["rotina"]["sono"]["horas"] == 6.0


def test_derivados_do_valorant():
    v = _registro_completo().valorant
    assert v.kd == round(72 / 55, 2)
    assert v.kda == round((72 + 20) / 55, 2)
    assert v.kda_texto == "72/55/20"
    assert v.winrate_pct == 75.0


def test_kd_com_zero_mortes_nao_quebra():
    v = _registro_completo().valorant
    v.mortes = 0
    assert v.kd == 72


def test_semana_iso_na_virada_do_ano():
    # 31/12/2026 é quinta-feira e pertence à semana 53 de 2026.
    assert RegistroDia(data=date(2026, 12, 31)).semana_iso == (2026, 53)
    # 01/01/2027 é sexta-feira e ainda pertence à semana 53 de 2026.
    assert RegistroDia(data=date(2027, 1, 1)).semana_iso == (2026, 53)


def test_registro_valido_nao_tem_erros():
    assert validar_registro(_registro_completo()) == []


def test_registro_vazio_e_valido():
    assert validar_registro(RegistroDia(data=date(2026, 11, 2))) == []


def test_validacao_detecta_problemas():
    r = _registro_completo()
    r.rotina.sono.qualidade = 11
    r.rotina.sono.dormiu_as = "25:00"
    r.valorant.hs_pct = 120
    r.valorant.vitorias = 5  # 5 + 1 > 4 partidas
    erros = validar_registro(r)
    assert len(erros) == 4
