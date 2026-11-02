from datetime import date, datetime

from app.models import (
    Bebida,
    Classificacao,
    Partida,
    RegistroDia,
    calcular_horas_sono,
    validar_registro,
)
from app.models.registro import Valorant


def _partidas() -> list[Partida]:
    return [
        Partida("Jett", "vitoria", 20, 15, 5, 30.0, 260),
        Partida("Jett", "vitoria", 18, 12, 4, 25.0, 240),
        Partida("Jett", "derrota", 14, 16, 6, 22.0, 190),
        Partida("Raze", "vitoria", 20, 12, 5, 33.0, 290),
    ]


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
    r.valorant.partidas = _partidas()
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
    assert dados["valorant"]["resumo"]["kd"] is None
    assert dados["valorant"]["partidas"] == []


def test_chaves_desconhecidas_sao_ignoradas():
    dados = _registro_completo().to_dict()
    dados["campo_do_futuro"] = 123
    dados["valorant"]["outro_campo"] = "x"
    dados["valorant"]["partidas"][0]["mapa"] = "Ascent"
    RegistroDia.from_dict(dados)  # não deve lançar erro


def test_sono_atravessando_meia_noite():
    assert calcular_horas_sono("23:30", "07:45") == 8.25
    assert calcular_horas_sono("01:00", "09:00") == 8.0
    assert calcular_horas_sono(None, "09:00") is None


def test_horas_manuais_tem_prioridade():
    r = _registro_completo()
    r.rotina.sono.horas = 6.0
    assert r.to_dict()["rotina"]["sono"]["horas"] == 6.0


def test_resumo_calculado_a_partir_das_partidas():
    resumo = _registro_completo().valorant.resumo
    assert resumo.partidas == 4
    assert (resumo.vitorias, resumo.derrotas, resumo.empates) == (3, 1, 0)
    assert resumo.kda_texto == "72/55/20"
    assert resumo.kd == round(72 / 55, 2)
    assert resumo.kda == round((72 + 20) / 55, 2)
    assert resumo.winrate_pct == 75.0
    assert resumo.hs_pct == 27.5
    assert resumo.acs == 245.0
    assert resumo.agentes == {"Jett": 3, "Raze": 1}


def test_vitorias_nunca_passam_do_total():
    # Antes dava para digitar 5 vitórias em 4 partidas; agora elas são contadas.
    resumo = _registro_completo().valorant.resumo
    assert resumo.vitorias + resumo.derrotas + resumo.empates <= resumo.partidas


def test_partidas_sem_resultado_nao_contam_no_winrate():
    jogo = Valorant(partidas=[Partida(resultado="vitoria"), Partida(resultado="derrota"), Partida()])
    assert jogo.resumo.partidas == 3
    assert jogo.resumo.winrate_pct == 50.0


def test_kd_com_zero_mortes_nao_quebra():
    jogo = Valorant(partidas=[Partida(abates=12, mortes=0)])
    assert jogo.resumo.kd == 12


def test_resumo_vem_do_legado_quando_nao_ha_partidas():
    jogo = Valorant(legado={"partidas": 4, "vitorias": 3, "derrotas": 1, "abates": 70, "mortes": 50,
                            "acs": 240, "adr": 150, "agentes": [{"nome": "Omen", "partidas": 4}]})
    assert jogo.resumo.partidas == 4
    assert jogo.resumo.kd == 1.4
    assert jogo.resumo.agentes == {"Omen": 4}
    # Com partidas registradas, elas passam a valer no lugar do legado.
    jogo.partidas = [Partida(abates=10, mortes=10)]
    assert jogo.resumo.partidas == 1 and jogo.resumo.kd == 1.0


def test_semana_comeca_no_domingo():
    # Domingo 01/11/2026 e sábado 07/11/2026 estão na mesma semana; domingo 08/11 abre a próxima.
    assert RegistroDia(data=date(2026, 11, 1)).semana == (2026, 45)
    assert RegistroDia(data=date(2026, 11, 7)).semana == (2026, 45)
    assert RegistroDia(data=date(2026, 11, 8)).semana == (2026, 46)


def test_semana_na_virada_do_ano():
    # A semana de 27/12/2026 a 02/01/2027 tem 5 dias em 2026: é a semana 53 de 2026.
    assert RegistroDia(data=date(2027, 1, 2)).semana == (2026, 53)
    # Domingo 03/01/2027 abre a semana 1 de 2027.
    assert RegistroDia(data=date(2027, 1, 3)).semana == (2027, 1)


def test_registro_valido_nao_tem_erros():
    assert validar_registro(_registro_completo()) == []


def test_registro_vazio_e_valido():
    assert validar_registro(RegistroDia(data=date(2026, 11, 2))) == []


def test_validacao_detecta_problemas():
    r = _registro_completo()
    r.rotina.sono.qualidade = 11
    r.rotina.sono.dormiu_as = "25:00"
    r.valorant.partidas[0].hs_pct = 120
    r.valorant.partidas[1].abates = -3
    erros = validar_registro(r)
    assert len(erros) == 4
    assert any("Partida 1 (HS%)" in e for e in erros)
    assert any("Partida 2 (abates)" in e for e in erros)
