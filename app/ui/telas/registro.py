"""Tela de registro diário: criar um registro novo ou editar um existente.

Dois modos:
- NOVO: a data é só "a que dia este registro pertence". Trocá-la mantém o que
  foi preenchido, mas só são aceitos dias sem registro e que não estão no futuro.
- EDIÇÃO: aberto pelo Histórico ou por "Editar o registro de hoje". A data fica
  travada; "+ Novo registro" volta ao modo novo.
"""

from datetime import date, datetime, timedelta
from tkinter import messagebox

import customtkinter as ctk

from app.analysis.ranking import ranking_no_inicio_do_dia
from app.models import RegistroDia, calcular_horas_sono, validar_registro
from app.models.datas import data_livre_mais_recente, erro_data_nova, proxima_data_livre
from app.models.ranking import Ranking, aplicar_partidas, variacao_real
from app.storage import ArquivoCorrompidoError, RegistroDuplicadoError, VersaoIncompativelError
from app.storage.rascunho import apagar_rascunho, salvar_rascunho
from app.ui import conversao, tema
from app.ui.componentes.botoes import botao_icone, botao_primario, botao_secundario
from app.ui.componentes import (
    CampoEntrada,
    CampoHorario,
    CampoMarcacao,
    CampoNota,
    CampoTextoLongo,
    ListaEditavel,
    ListaPartidas,
    Secao,
    SeletorBotoes,
    SeletorClassificacao,
)
from app.ui.componentes.lista_editavel import HORA, TEXTO
from app.ui.formatacao import data_curta, data_extensa, numero
from app.ui.mapeamento_registro import (
    formulario_para_registro,
    registro_para_formulario,
    resumo_ao_vivo,
)
from app.ui.telas.base import TelaBase

INTERVALO_AUTOSAVE_MS = 3000
REFEICOES = (("cafe", "Café da manhã"), ("almoco", "Almoço"), ("jantar", "Jantar"))
NOVO, EDICAO = "novo", "edicao"


def _sem_data(formulario: dict) -> dict:
    """Conteúdo do formulário sem a data (trocar a data não é "alterar o registro")."""
    return {chave: valor for chave, valor in formulario.items() if chave != "data"}


class TelaRegistro(TelaBase):
    titulo = "Registro diário"
    subtitulo = "Preencha só o que lembrar. Nenhum campo é obrigatório."

    def montar(self) -> None:
        # Cada campo da tela, pela mesma chave usada no dicionário do formulário.
        self._campos: dict = {}
        self._data = date.today()
        self._modo = NOVO
        self._legado: dict | None = None  # totais antigos do dia (sem campo na tela)
        self._ranking_inicio: Ranking | None = None  # calculado; vem da aba Ranking
        self._registradas: set[date] = set()
        self._carregado = False
        self._base: dict = {}             # conteúdo quando foi carregado/salvo
        self._ultimo_rascunho: dict | None = None

        self.corpo.grid_columnconfigure(0, weight=1)
        self.corpo.grid_rowconfigure(2, weight=1)

        self._montar_barra_superior()
        self._montar_classificacao()

        abas = ctk.CTkTabview(
            self.corpo, fg_color="transparent", corner_radius=tema.RAIO,
            segmented_button_fg_color=tema.COR_CARTAO,
            segmented_button_selected_color=tema.COR_DESTAQUE,
            segmented_button_selected_hover_color=tema.COR_DESTAQUE_HOVER,
            segmented_button_unselected_color=tema.COR_CARTAO,
            segmented_button_unselected_hover_color=tema.COR_CARTAO_HOVER,
            anchor="w",
        )
        # O CTkTabview não expõe a fonte/altura das abas no construtor: ajustamos o
        # botão segmentado interno para seguir a tipografia display do app.
        abas._segmented_button.configure(font=tema.fonte_display(20), height=36)
        abas.grid(row=2, column=0, sticky="nsew")
        self._abas = abas
        self._areas: dict[str, ctk.CTkScrollableFrame] = {}
        for nome, montar in (("Rotina", self._montar_aba_rotina),
                             ("Valorant", self._montar_aba_valorant),
                             ("Partidas", self._montar_aba_partidas),
                             ("Anotações", self._montar_aba_anotacoes)):
            abas.add(nome)
            # Respiro lateral em cada aba (o texto em Bebas é estreito).
            abas._segmented_button._buttons_dict[nome].configure(width=120)
            area = ctk.CTkScrollableFrame(abas.tab(nome), fg_color="transparent")
            area.pack(fill="both", expand=True)
            self._areas[nome] = area
            montar(area)

        self.after(INTERVALO_AUTOSAVE_MS, self._autosave)

    # --- Montagem ---------------------------------------------------------

    def _montar_barra_superior(self) -> None:
        barra = ctk.CTkFrame(self.corpo, fg_color=tema.COR_CARTAO, corner_radius=tema.RAIO,
                             border_width=1, border_color=tema.COR_BORDA)
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        barra.grid_columnconfigure(5, weight=1)

        def botao(texto, comando, largura=36):
            return botao_icone(barra, texto, comando, largura=largura, destaque=True)

        self._botao_anterior = botao("◀", lambda: self._andar_data(-1))
        self._botao_anterior.grid(row=0, column=0, padx=(14, 4), pady=14)
        self._entrada_data = ctk.CTkEntry(barra, width=120, height=34, justify="center",
                                          fg_color=tema.COR_CAMPO, border_color=tema.COR_BORDA,
                                          font=tema.fonte_normal())
        self._entrada_data.grid(row=0, column=1, padx=4)
        self._entrada_data.bind("<Return>", lambda _: self._data_digitada())
        self._entrada_data.bind("<FocusOut>", lambda _: self._data_digitada())
        self._botao_proximo = botao("▶", lambda: self._andar_data(+1))
        self._botao_proximo.grid(row=0, column=2, padx=4)
        self._botao_hoje = botao("Hoje", lambda: self._mudar_data(date.today()), largura=60)
        self._botao_hoje.grid(row=0, column=3, padx=(4, 14))

        textos = ctk.CTkFrame(barra, fg_color="transparent")
        textos.grid(row=0, column=4, sticky="w")
        self._rotulo_dia = ctk.CTkLabel(textos, text="", font=tema.fonte_secao(), text_color=tema.COR_TEXTO)
        self._rotulo_dia.pack(anchor="w")
        self._rotulo_modo = ctk.CTkLabel(textos, text="", font=tema.fonte_pequena(),
                                         text_color=tema.COR_TEXTO_SECUNDARIO)
        self._rotulo_modo.pack(anchor="w")

        # Linha própria abaixo dos controles (só aparece quando há algo a dizer):
        # na mesma linha dos botões não sobra espaço para mensagens mais longas.
        self._rotulo_status = ctk.CTkLabel(barra, text="", font=tema.fonte_pequena(), anchor="w",
                                           text_color=tema.COR_TEXTO_SECUNDARIO)
        botao_secundario(barra, "+ Novo registro", self.novo_registro, largura=140, altura=40).grid(
            row=0, column=6, padx=(0, 8))
        botao_primario(barra, "Salvar", self.salvar, largura=120, altura=40).grid(row=0, column=7, padx=(0, 14))

    def _montar_classificacao(self) -> None:
        linha = ctk.CTkFrame(self.corpo, fg_color="transparent")
        linha.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkLabel(linha, text="Como foi o dia?", font=tema.fonte_secao(),
                     text_color=tema.COR_TEXTO).pack(side="left", padx=(4, 14))
        self._campos["classificacao"] = SeletorClassificacao(linha)
        self._campos["classificacao"].pack(side="left")

    def _grade(self, secao: Secao, campos: list[tuple[str, ctk.CTkFrame]], colunas: int = 4) -> None:
        """Registra os campos e os distribui em grade dentro da seção."""
        for i, (chave, campo) in enumerate(campos):
            campo.grid(row=i // colunas, column=i % colunas, sticky="w", padx=(0, 18), pady=4)
            self._campos[chave] = campo

    def _montar_aba_rotina(self, area) -> None:
        secao = Secao(area, "Sono")
        secao.pack(fill="x", pady=(0, 10))
        dormiu = CampoHorario(secao.conteudo, "Dormiu às", ao_mudar=self._atualizar_horas_auto)
        acordou = CampoHorario(secao.conteudo, "Acordou às", ao_mudar=self._atualizar_horas_auto)
        horas = CampoEntrada(secao.conteudo, "Horas dormidas", placeholder="automático")
        self._grade(secao, [("sono_dormiu_as", dormiu), ("sono_acordou_as", acordou), ("sono_horas", horas)])
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

        secao = Secao(area, "Medicamentos")
        secao.pack(fill="x", pady=10)
        self._campos["medicamentos"] = ListaEditavel(
            secao.conteudo, [("nome", "Nome", 220, TEXTO), ("dose", "Dose", 120, TEXTO), ("horario", "", 0, HORA)],
            "+ Medicamento")
        self._campos["medicamentos"].pack(anchor="w", fill="x")

        secao = Secao(area, "Como você estava")
        secao.pack(fill="x", pady=10)
        self._grade(secao, [
            ("disposicao_fisica", CampoNota(secao.conteudo, "Disposição física")),
            ("disposicao_mental", CampoNota(secao.conteudo, "Disposição mental")),
            ("estresse", CampoNota(secao.conteudo, "Estresse (10 = muito estressado)")),
        ], colunas=1)

    def _montar_aba_valorant(self, area) -> None:
        secao = Secao(area, "Sessão", "As partidas em si são registradas na aba Partidas.")
        secao.pack(fill="x", pady=(0, 10))
        rotulo = ctk.CTkFrame(secao.conteudo, fg_color="transparent")
        ctk.CTkLabel(rotulo, text="Jogou hoje?", font=tema.fonte_pequena(),
                     text_color=tema.COR_TEXTO_SECUNDARIO).pack(anchor="w")
        jogou = SeletorBotoes(rotulo, [("sim", "Sim"), ("nao", "Não")], largura_botao=60)
        jogou.pack(anchor="w")
        rotulo.grid(row=0, column=0, sticky="w", padx=(0, 18), pady=4)
        self._campos["jogou"] = jogou
        inicio = CampoHorario(secao.conteudo, "Começou às")
        fim = CampoHorario(secao.conteudo, "Parou às")
        inicio.grid(row=0, column=1, sticky="w", padx=(0, 18), pady=4)
        fim.grid(row=0, column=2, sticky="w", pady=4)
        self._campos["jogo_inicio"] = inicio
        self._campos["jogo_fim"] = fim

        secao = Secao(area, "Autoavaliação")
        secao.pack(fill="x", pady=10)
        self._grade(secao, [
            ("mira", CampoNota(secao.conteudo, "Sensação da mira")),
            ("movimentacao", CampoNota(secao.conteudo, "Qualidade da movimentação")),
            ("tomada_decisao", CampoNota(secao.conteudo, "Tomada de decisão")),
            ("concentracao", CampoNota(secao.conteudo, "Concentração")),
            ("consistencia", CampoNota(secao.conteudo, "Consistência")),
        ], colunas=1)

    def _montar_aba_partidas(self, area) -> None:
        secao = Secao(area, "Resumo do dia", "Calculado automaticamente a partir das partidas abaixo. "
                                             "O ranking vem da aba Ranking + o RR de cada partida, na ordem.")
        secao.pack(fill="x", pady=(0, 10))
        self._rotulo_ranking = ctk.CTkLabel(secao.conteudo, text="", justify="left", anchor="w",
                                            font=tema.fonte_pequena(), text_color=tema.COR_TEXTO_SECUNDARIO)
        self._rotulo_ranking.pack(anchor="w", pady=(0, 6))
        self._rotulo_resumo = ctk.CTkLabel(secao.conteudo, text="", justify="left", anchor="w",
                                           font=tema.fonte_normal(), text_color=tema.COR_TEXTO)
        self._rotulo_resumo.pack(anchor="w")
        self._rotulo_legado = ctk.CTkLabel(secao.conteudo, text="", justify="left", anchor="w", wraplength=760,
                                           font=tema.fonte_pequena(), text_color=tema.COR_AVISO)
        self._rotulo_legado.pack(anchor="w", pady=(6, 0))

        secao = Secao(area, "Partidas", "Uma partida por cartão. Clique em \"Escolher agente\" para abrir a "
                                        "bandeja de agentes.")
        secao.pack(fill="x", pady=10)
        self._campos["partidas"] = ListaPartidas(secao.conteudo, ao_mudar=self._atualizar_resumo)
        self._campos["partidas"].pack(fill="x")

    def _montar_aba_anotacoes(self, area) -> None:
        secao = Secao(area, "Situações nas partidas",
                      'Ex.: "Consegui fazer microajustes com facilidade." / '
                      '"Estava muito ansioso durante os confrontos."')
        secao.pack(fill="x", pady=(0, 10))
        self._campos["notas_jogo"] = CampoTextoLongo(secao.conteudo, "", altura=180)
        self._campos["notas_jogo"].pack(fill="x")

        secao = Secao(area, "Observações gerais sobre o dia")
        secao.pack(fill="x", pady=10)
        self._campos["observacoes"] = CampoTextoLongo(secao.conteudo, "", altura=180)
        self._campos["observacoes"].pack(fill="x")

    # --- Leitura e preenchimento -----------------------------------------

    def _ler(self) -> dict:
        formulario = {chave: campo.get() for chave, campo in self._campos.items()}
        formulario["data"] = self._data.isoformat()
        formulario["legado"] = self._legado
        return formulario

    def _preencher(self, formulario: dict) -> None:
        self._legado = formulario.get("legado")
        for chave, campo in self._campos.items():
            campo.set(formulario.get(chave))
        self._atualizar_horas_auto()
        self._atualizar_resumo()

    def _formulario_vazio(self, data: date) -> dict:
        return registro_para_formulario(RegistroDia(data=data))

    def _tem_alteracoes(self) -> bool:
        return self._carregado and _sem_data(self._ler()) != self._base

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

    def _atualizar_resumo(self) -> None:
        formulario = self._ler()
        resumo = resumo_ao_vivo(formulario)
        linhas = []
        if resumo.partidas:
            resultados = [f"{n} {letra}" for n, letra in ((resumo.vitorias, "V"), (resumo.derrotas, "D"),
                                                         (resumo.empates, "E")) if n is not None]
            linha1 = [f"{resumo.partidas} partida(s)", *resultados]
            if resumo.winrate_pct is not None:
                linha1.append(f"Winrate {numero(resumo.winrate_pct, 1)}%")
            linha2 = []
            if resumo.kda_texto:
                linha2 += [f"K/D/A {resumo.kda_texto}", f"K/D {numero(resumo.kd)}", f"KDA {numero(resumo.kda)}"]
            if resumo.hs_pct is not None:
                linha2.append(f"HS% médio {numero(resumo.hs_pct, 1)}%")
            if resumo.acs is not None:
                linha2.append(f"ACS médio {numero(resumo.acs, 0)}")
            agentes = "  ·  ".join(f"{nome} ×{n}" if n else nome for nome, n in resumo.agentes.items())
            linhas += ["  ·  ".join(linha1), "  ·  ".join(linha2), f"Agentes: {agentes}" if agentes else ""]
        linhas.append(self._texto_ranking(formulario, resumo.rr))

        linhas = [linha for linha in linhas if linha]
        if linhas:
            self._rotulo_resumo.configure(text="\n".join(linhas), text_color=tema.COR_TEXTO)
        else:
            self._rotulo_resumo.configure(text="Adicione partidas para ver o resumo do dia.",
                                          text_color=tema.COR_TEXTO_SECUNDARIO)

        tem_partidas = any(p.get("agente") or p.get("abates") or p.get("resultado")
                           for p in formulario.get("partidas") or [])
        if self._legado and not tem_partidas:
            self._rotulo_legado.configure(text=(
                "Este dia foi registrado antes do registro por partida: o resumo acima vem dos totais "
                "digitados na época. Se você adicionar partidas, elas passam a valer no lugar desses totais."))
        else:
            self._rotulo_legado.configure(text="")

    def _texto_ranking(self, formulario: dict, rr_do_dia: int | None) -> str:
        """Duas linhas:
        "RR das partidas: -20, +17"
        "Ranking: Ascendente 3 · 1 RR  →  Ascendente 3 · 17 RR  (+16 RR)"
        A variação no ranking pode diferir da soma das partidas por causa da
        proteção contra rebaixamento (no exemplo, a soma seria -3).
        """
        variacoes = []
        for partida in formulario.get("partidas") or []:
            try:
                rr = conversao.inteiro(partida.get("rr"), "")
            except conversao.ErroConversao:
                rr = None
            if rr is not None:
                variacoes.append(rr)
        linhas = []
        if variacoes:
            partidas = ", ".join(f"{v:+d}" for v in variacoes)
            # Sem ranking definido não dá para aplicar a proteção: mostramos a soma.
            sufixo = "" if self._ranking_inicio is not None else f"  (soma {rr_do_dia:+d})"
            linhas.append(f"RR das partidas: {partidas}{sufixo}")
        if self._ranking_inicio is not None:
            final = aplicar_partidas(self._ranking_inicio, variacoes)
            ganho = f"  ({variacao_real(self._ranking_inicio, final):+d} RR)" if variacoes else ""
            linhas.append(f"Ranking: {self._ranking_inicio.texto}  →  {final.texto}{ganho}")
        return "\n".join(linhas)

    def _calcular_ranking_inicio(self) -> None:
        """Ranking ao começar o dia aberto: definição (aba Ranking) + RR dos dias anteriores."""
        try:
            registros, _ = self.repositorio.carregar_todos()
            definicoes = self.janela.repositorio_ranking.carregar()
        except ArquivoCorrompidoError:
            definicoes = []
        self._ranking_inicio = ranking_no_inicio_do_dia(self._data, registros, definicoes)
        if self._ranking_inicio is None:
            self._rotulo_ranking.configure(
                text="Ranking não calculado: defina seu elo e RR na aba Ranking (menu ao lado).")
        else:
            self._rotulo_ranking.configure(text=f"Ranking ao começar o dia: {self._ranking_inicio.texto}")

    def _atualizar_cabecalho(self) -> None:
        self._entrada_data.configure(state="normal")
        self._entrada_data.delete(0, "end")
        self._entrada_data.insert(0, data_curta(self._data))
        self._rotulo_dia.configure(text=data_extensa(self._data))

        novo = self._modo == NOVO
        estado = "normal" if novo else "disabled"
        for controle in (self._botao_anterior, self._botao_proximo, self._botao_hoje, self._entrada_data):
            controle.configure(state=estado)
        if novo:
            self._rotulo_modo.configure(text="Novo registro  ·  trocar a data mantém o conteúdo",
                                        text_color=tema.COR_TEXTO_SECUNDARIO)
        else:
            self._rotulo_modo.configure(text="Editando  ·  data travada",
                                        text_color=tema.COR_AVISO)

    def _status(self, texto: str, cor: str = tema.COR_TEXTO_SECUNDARIO) -> None:
        self._rotulo_status.configure(text=texto, text_color=cor)
        if texto:
            self._rotulo_status.grid(row=1, column=0, columnspan=8, sticky="w", padx=16, pady=(0, 10))
        else:
            self._rotulo_status.grid_remove()

    # --- Abrir registros --------------------------------------------------

    def _atualizar_registradas(self) -> None:
        registros, _ = self.repositorio.carregar_todos()
        self._registradas = {r.data for r in registros}

    def ao_exibir(self) -> None:
        self._atualizar_registradas()
        if not self._carregado:
            hoje = date.today()
            if hoje in self._registradas:
                self._abrir_edicao(hoje)
            else:
                self._iniciar_novo(hoje)
        else:
            if self._modo == EDICAO and self._data not in self._registradas:
                # O dia foi excluído no Histórico: o conteúdo continua aqui como registro novo.
                self._modo = NOVO
                self._atualizar_cabecalho()
            # O ranking pode ter sido redefinido na aba Ranking enquanto esta tela estava fechada.
            self._calcular_ranking_inicio()
            self._atualizar_resumo()

    def _pode_descartar(self) -> bool:
        if not self._tem_alteracoes():
            return True
        return messagebox.askyesno(
            "Alterações não salvas",
            f"O registro de {data_curta(self._data)} tem alterações não salvas.\n\nDescartá-las?",
            parent=self,
        )

    def abrir_registro(self, data: date) -> None:
        """Usado pelo Histórico e pela tela inicial: edita o dia, ou começa um novo nele."""
        self._atualizar_registradas()
        if self._carregado and data == self._data and (data in self._registradas) == (self._modo == EDICAO):
            return
        if not self._pode_descartar():
            return
        if data in self._registradas:
            self._abrir_edicao(data)
        else:
            self._iniciar_novo(min(data, date.today()))

    def novo_registro(self) -> None:
        if not self._pode_descartar():
            return
        self._atualizar_registradas()
        data = data_livre_mais_recente(self._registradas, date.today())
        if data is None:
            messagebox.showinfo("Novo registro", "Todos os dias até hoje já têm registro.", parent=self)
            return
        self._iniciar_novo(data)

    def _iniciar_novo(self, data: date, formulario: dict | None = None) -> None:
        self._modo = NOVO
        self._data = data
        self._calcular_ranking_inicio()
        self._preencher(self._formulario_vazio(data))
        self._base = _sem_data(self._ler())  # base = formulário em branco
        if formulario:
            self._preencher(formulario)
        self._carregado = True
        self._descartar_rascunho()
        self._atualizar_cabecalho()
        self._status("")

    def _abrir_edicao(self, data: date) -> None:
        try:
            existente = self.repositorio.obter_dia(data)
        except (ArquivoCorrompidoError, VersaoIncompativelError) as erro:
            messagebox.showerror("Não foi possível ler a semana", str(erro), parent=self)
            return
        if existente is None:
            self._iniciar_novo(data)
            return
        self._modo = EDICAO
        self._data = data
        self._calcular_ranking_inicio()
        self._preencher(registro_para_formulario(existente))
        # A base é lida de volta da tela, para comparar sempre "igual com igual".
        self._base = _sem_data(self._ler())
        self._carregado = True
        self._descartar_rascunho()
        self._atualizar_cabecalho()
        self._status("")

    def recuperar_rascunho(self, formulario: dict) -> None:
        """Chamado pela janela ao abrir o app, se o usuário aceitar recuperar."""
        self._atualizar_registradas()
        data = date.fromisoformat(formulario["data"])
        if data in self._registradas:
            self._abrir_edicao(data)
            self._preencher(formulario)
        else:
            self._iniciar_novo(data, formulario)
        self._salvar_rascunho_se_preciso()

    # --- Troca de data (só no modo novo) ----------------------------------

    def _mudar_data(self, data: date) -> None:
        """Muda a data do registro novo mantendo tudo o que foi preenchido."""
        if self._modo != NOVO or data == self._data:
            self._atualizar_cabecalho()
            return
        erro = erro_data_nova(data, self._registradas, date.today())
        if erro:
            messagebox.showwarning("Data indisponível", erro, parent=self)
            self._atualizar_cabecalho()
            return
        self._data = data
        self._calcular_ranking_inicio()
        self._atualizar_resumo()
        self._atualizar_cabecalho()

    def _andar_data(self, passo: int) -> None:
        """Setas: vão para o dia livre mais próximo, pulando os já registrados."""
        destino = proxima_data_livre(self._data + timedelta(days=passo), passo, self._registradas, date.today())
        if destino is None:
            self._status("Não há dias livres nessa direção.", tema.COR_AVISO)
            return
        self._mudar_data(destino)

    def _data_digitada(self) -> None:
        texto = self._entrada_data.get().strip()
        if self._modo != NOVO or texto == data_curta(self._data):
            return
        try:
            data = datetime.strptime(texto, "%d/%m/%Y").date()
        except ValueError:
            messagebox.showwarning("Data inválida", "Use o formato DD/MM/AAAA.", parent=self)
            self._atualizar_cabecalho()
            return
        self._mudar_data(data)

    # --- Salvar -----------------------------------------------------------

    def salvar(self) -> None:
        formulario = self._ler()
        registro, erros = formulario_para_registro(formulario)
        if not erros:
            erros = validar_registro(registro)
        if erros:
            messagebox.showwarning("Revise os campos", "\n".join(f"• {e}" for e in erros), parent=self)
            return

        try:
            self.repositorio.salvar_dia(registro, sobrescrever=self._modo == EDICAO)
        except RegistroDuplicadoError:
            # Só acontece se o dia foi registrado por outro caminho (ex.: importação) depois.
            messagebox.showerror(
                "Data indisponível",
                f"{data_curta(registro.data)} já tem um registro. Escolha outra data ou edite "
                "aquele dia pelo Histórico.",
                parent=self,
            )
            self._atualizar_registradas()
            return
        except (ArquivoCorrompidoError, VersaoIncompativelError) as erro:
            messagebox.showerror("Não foi possível salvar", str(erro), parent=self)
            return

        self._modo = EDICAO
        self._registradas.add(registro.data)
        # Reexibe os valores normalizados (ex.: horas manuais "6.0" viram "6").
        self._preencher(registro_para_formulario(registro))
        self._base = _sem_data(self._ler())
        self._descartar_rascunho()
        self._atualizar_cabecalho()
        status = f"✓ Salvo às {datetime.now():%H:%M}"
        salvo = self.janela.atualizar_ranking_salvo()
        if salvo is not None:
            status += f"  ·  Ranking atualizado: {salvo.ranking.texto}"
        self._status(status, tema.COR_SUCESSO)

    # --- Rascunho automático ----------------------------------------------

    def _autosave(self) -> None:
        try:
            self._salvar_rascunho_se_preciso()
        finally:
            self.after(INTERVALO_AUTOSAVE_MS, self._autosave)

    def _salvar_rascunho_se_preciso(self) -> None:
        if not self._carregado:
            return
        atual = self._ler()
        if _sem_data(atual) == self._base:
            if self._ultimo_rascunho is not None:
                self._descartar_rascunho()
                self._status("")
            return
        if atual != self._ultimo_rascunho:
            salvar_rascunho(atual, self.janela.arquivo_rascunho)
            self._ultimo_rascunho = atual
        self._status("● Não salvo · rascunho guardado", tema.COR_AVISO)

    def salvar_rascunho_agora(self) -> None:
        """Chamado ao fechar o app."""
        self._salvar_rascunho_se_preciso()

    def _descartar_rascunho(self) -> None:
        apagar_rascunho(self.janela.arquivo_rascunho)
        self._ultimo_rascunho = None
