"""Aba Rotina: sono, alimentação, hidratação, medicamentos e disposição."""

import customtkinter as ctk

from app.models import calcular_horas_sono
from app.ui import conversao, tema
from app.ui.componentes import CampoEntrada, CampoHorario, CampoMarcacao, CampoNota, ListaEditavel, Secao
from app.ui.componentes.lista_editavel import HORA, TEXTO
from app.ui.formatacao import numero

REFEICOES = (("cafe", "Café da manhã"), ("almoco", "Almoço"), ("jantar", "Jantar"))


class AbaRotina:
    def __init__(self, tela, area):
        self._campos = tela.campos

        secao = Secao(area, "Sono")
        secao.pack(fill="x", pady=(0, 10))
        dormiu = CampoHorario(secao.conteudo, "Dormiu às", ao_mudar=self._atualizar_horas_auto)
        acordou = CampoHorario(secao.conteudo, "Acordou às", ao_mudar=self._atualizar_horas_auto)
        horas = CampoEntrada(secao.conteudo, "Horas dormidas", placeholder="automático")
        tela.grade(secao, [("sono_dormiu_as", dormiu), ("sono_acordou_as", acordou), ("sono_horas", horas)])
        self._rotulo_horas_auto = ctk.CTkLabel(secao.conteudo, text="", font=tema.fonte_pequena(),
                                               text_color=tema.COR_TEXTO_SECUNDARIO)
        self._rotulo_horas_auto.grid(row=0, column=3, sticky="sw", pady=(0, 10))
        qualidade = CampoNota(secao.conteudo, "Qualidade do sono")
        qualidade.grid(row=1, column=0, columnspan=4, sticky="w", pady=4)
        self._campos["sono_qualidade"] = qualidade

        secao = Secao(area, "Alimentação", "Marque as refeições que você fez para preencher os detalhes.")
        secao.pack(fill="x", pady=10)
        for linha, (chave, nome) in enumerate(REFEICOES):
            marcacao = CampoMarcacao(secao.conteudo, nome, ao_mudar=self._atualizar_refeicoes)
            horario = CampoHorario(secao.conteudo, "Horário")
            descricao = CampoEntrada(secao.conteudo, "O que comeu", largura=400)
            marcacao.grid(row=linha, column=0, sticky="w", padx=(0, 16), pady=(18, 4))
            horario.grid(row=linha, column=1, sticky="w", padx=(0, 12), pady=4)
            descricao.grid(row=linha, column=2, sticky="w", pady=4)
            self._campos[f"{chave}_realizada"] = marcacao
            self._campos[f"{chave}_horario"] = horario
            self._campos[f"{chave}_descricao"] = descricao
        outros = CampoEntrada(secao.conteudo, "Outros (lanches, doces...)", largura=560)
        outros.grid(row=len(REFEICOES), column=0, columnspan=3, sticky="w", pady=(10, 4))
        self._campos["alimentacao_outros"] = outros
        self._atualizar_refeicoes()

        secao = Secao(area, "Hidratação e bebidas")
        secao.pack(fill="x", pady=10)
        agua = CampoEntrada(secao.conteudo, "Água (litros)", placeholder="2,5")
        agua.pack(anchor="w", pady=(0, 8))
        self._campos["agua_litros"] = agua
        ctk.CTkLabel(secao.conteudo, text="Café, energético e outras bebidas",
                     font=tema.fonte_pequena(), text_color=tema.COR_TEXTO_SECUNDARIO).pack(anchor="w")
        self._campos["bebidas"] = ListaEditavel(
            secao.conteudo, [("tipo", "Bebida (ex.: café)", 200, TEXTO), ("quantidade", "Quantidade", 140, TEXTO),
                             ("horario", "", 0, HORA)], "+ Bebida")
        self._campos["bebidas"].pack(anchor="w", fill="x")

        secao = Secao(area, "Medicamentos", "O horário é cruzado com o início do jogo (aba Valorant).")
        secao.pack(fill="x", pady=10)
        self._campos["medicamentos"] = ListaEditavel(
            secao.conteudo, [("nome", "Nome", 220, TEXTO), ("dose", "Dose", 120, TEXTO), ("horario", "", 0, HORA)],
            "+ Medicamento")
        self._campos["medicamentos"].pack(anchor="w", fill="x")

        secao = Secao(area, "Como você estava")
        secao.pack(fill="x", pady=10)
        tela.grade(secao, [
            ("disposicao_fisica", CampoNota(secao.conteudo, "Disposição física")),
            ("disposicao_mental", CampoNota(secao.conteudo, "Disposição mental")),
            ("estresse", CampoNota(secao.conteudo, "Estresse (10 = muito estressado)")),
        ], colunas=1)

    def atualizar(self) -> None:
        self._atualizar_refeicoes()
        self._atualizar_horas_auto()

    def _atualizar_refeicoes(self) -> None:
        """Habilita horário e descrição só das refeições marcadas."""
        for chave, _ in REFEICOES:
            ativa = self._campos[f"{chave}_realizada"].get()
            self._campos[f"{chave}_horario"].habilitar(ativa)
            self._campos[f"{chave}_descricao"].habilitar(ativa)

    def _atualizar_horas_auto(self) -> None:
        try:
            horas = calcular_horas_sono(
                conversao.hora(self._campos["sono_dormiu_as"].get(), ""),
                conversao.hora(self._campos["sono_acordou_as"].get(), ""),
            )
        except conversao.ErroConversao:
            horas = None
        texto = f"≈ {numero(horas)} h pelos horários" if horas is not None else ""
        self._rotulo_horas_auto.configure(text=texto)
