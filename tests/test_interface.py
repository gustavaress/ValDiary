"""Testes da interface: abrem o app de verdade (numa pasta temporária) e percorrem
os fluxos principais. As caixas de mensagem são simuladas e registradas em `avisos`,
para o teste não ficar esperando um clique.
"""

from datetime import date, timedelta
from tkinter import messagebox

import pytest

pytestmark = pytest.mark.interface

from app.models import Partida, RegistroDia
from app.models.ranking import Ranking
from app.storage import RepositorioDiario
from app.storage.repositorio_aim import ROTINA_INICIAL
from app.ui.janela_principal import TELAS, JanelaPrincipal

HOJE = date.today()


@pytest.fixture
def avisos(monkeypatch):
    registradas = []
    for nome in ("showinfo", "showwarning", "showerror"):
        monkeypatch.setattr(messagebox, nome, lambda titulo, texto, n=nome, **_: registradas.append((n, texto)))
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)
    monkeypatch.setattr(messagebox, "askyesnocancel", lambda *a, **k: True)
    return registradas


@pytest.fixture
def janela(tmp_path, avisos):
    repositorio = RepositorioDiario(tmp_path / "dados", tmp_path / "dados" / "_backups")
    janela = JanelaPrincipal(repositorio, tmp_path / "dados" / "_rascunho.json")
    janela.withdraw()  # não precisa aparecer na tela
    yield janela
    janela.destroy()


def _registro(janela):
    janela.mostrar_tela("registro")
    return janela._telas["registro"]


def _adicionar_partidas(tela, *rrs):
    lista = tela.campos["partidas"]
    for rr in rrs:
        lista.adicionar()
        lista._cartoes[-1]._entradas["rr"].insert(0, rr)
    lista.mudou()


def test_todas_as_telas_abrem(janela):
    for chave, _, _ in TELAS:
        janela.mostrar_tela(chave)


def test_registrar_e_salvar_um_dia_novo(janela):
    tela = _registro(janela)
    assert tela.modo == "novo" and tela.data == HOJE
    tela.campos["classificacao"].set("bom")
    tela.campos["agua_litros"].set("2,5")
    _adicionar_partidas(tela, "+18")
    tela.salvar()

    dia = janela.repositorio.obter_dia(HOJE)
    assert dia.classificacao == "bom" and dia.rotina.agua_litros == 2.5
    assert dia.valorant.resumo.rr == 18
    assert tela.modo == "edicao"


def test_trocar_data_mantem_conteudo_e_bloqueia_dia_registrado(janela, avisos):
    ontem, anteontem = HOJE - timedelta(days=1), HOJE - timedelta(days=2)
    janela.repositorio.salvar_dia(RegistroDia(data=ontem))
    tela = _registro(janela)
    tela.ao_exibir()  # recarrega a lista de dias já registrados
    tela.campos["agua_litros"].set("3")

    tela.mudar_data(ontem)  # já tem registro: recusado
    assert tela.data == HOJE and "já tem um registro" in avisos[-1][1]

    tela.mudar_data(anteontem)
    assert tela.data == anteontem and tela.campos["agua_litros"].get() == "3"


def test_ranking_e_atualizado_ao_salvar(janela):
    janela.repositorio_ranking.definir(HOJE, "Ascendente 3", 1)
    tela = _registro(janela)
    _adicionar_partidas(tela, "-20", "+17")
    assert "(+16 RR)" in tela.aba_partidas.rotulo_resumo.cget("text")
    tela.salvar()
    assert janela.repositorio_ranking.carregar_atual().ranking == Ranking("Ascendente 3", 17)
    assert "Ascendente 3 · 17 RR" in tela.rotulo_status.cget("text")


def test_editar_dia_existente_trava_a_data(janela):
    dia = HOJE - timedelta(days=3)
    registro = RegistroDia(data=dia)
    registro.valorant.partidas = [Partida("Jett", "vitoria")]
    janela.repositorio.salvar_dia(registro)

    janela.abrir_registro(dia)
    tela = janela._telas["registro"]
    assert tela.modo == "edicao" and tela.data == dia
    assert tela._botao_anterior.cget("state") == "disabled"
    tela.campos["observacoes"].set("Editado pelo teste")
    tela.salvar()
    assert janela.repositorio.obter_dia(dia).rotina.observacoes == "Editado pelo teste"


def test_aim_routine_vem_da_rotina_padrao_e_e_salva(janela):
    tela = _registro(janela)
    exercicios = tela.campos["aim_exercicios"].get()
    assert [e["nome"] for e in exercicios] == [e.nome for e in ROTINA_INICIAL]

    exercicios[0]["feito"] = True
    tela.campos["aim_exercicios"].set(exercicios)
    tela.salvar()
    aim = janela.repositorio.obter_dia(HOJE).valorant.aim_routine
    assert aim.feita is True and [e.nome for e in aim.exercicios_feitos] == ["Tracking"]


def test_descricao_do_aquecimento_so_habilita_com_sim(janela):
    tela = _registro(janela)
    descricao = tela.campos["aquecimento_descricao"].caixa
    assert descricao.cget("state") == "disabled"
    tela.campos["aquecimento"]._clicar("sim")
    assert descricao.cget("state") == "normal"
