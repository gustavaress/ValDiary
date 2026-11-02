"""Tela de registro diário: criar e editar o registro de uma data."""

from datetime import date, datetime, timedelta
from tkinter import messagebox

import customtkinter as ctk

from app.models import RegistroDia, calcular_horas_sono, validar_registro
from app.storage import ArquivoCorrompidoError, RegistroDuplicadoError, VersaoIncompativelError
from app.storage.rascunho import apagar_rascunho, salvar_rascunho
from app.ui import conversao, tema
from app.ui.componentes import (
    CampoEntrada,
    CampoNota,
    CampoTextoLongo,
    ListaEditavel,
    Secao,
    SeletorBotoes,
    SeletorClassificacao,
)
from app.ui.formatacao import data_curta, data_extensa, numero
from app.ui.mapeamento_registro import (
    derivados_ao_vivo,
    formulario_para_registro,
    registro_para_formulario,
)
from app.ui.telas.base import TelaBase

INTERVALO_AUTOSAVE_MS = 3000


class TelaRegistro(TelaBase):
    titulo = "Registro diário"
    subtitulo = "Preencha só o que lembrar. Nenhum campo é obrigatório."

    def montar(self) -> None:
        # Cada campo da tela, pela mesma chave usada no dicionário do formulário.
        self._campos: dict = {}
        self._data = date.today()
        self._editando = False
        self._carregado = False
        self._base: dict = {}             # estado do formulário quando foi carregado/salvo
        self._ultimo_rascunho: dict | None = None

        self.corpo.grid_columnconfigure(0, weight=1)
        self.corpo.grid_rowconfigure(2, weight=1)

        self._montar_barra_superior()
        self._montar_classificacao()

        abas = ctk.CTkTabview(
            self.corpo, fg_color="transparent", corner_radius=12,
            segmented_button_fg_color=tema.COR_CARTAO,
            segmented_button_selected_color=tema.COR_DESTAQUE,
            segmented_button_selected_hover_color=tema.COR_DESTAQUE_HOVER,
            segmented_button_unselected_color=tema.COR_CARTAO,
            segmented_button_unselected_hover_color=tema.COR_CARTAO_HOVER,
            anchor="w",
        )
        abas.grid(row=2, column=0, sticky="nsew")
        for nome, montar in (("Rotina", self._montar_aba_rotina),
                             ("Valorant", self._montar_aba_valorant),
                             ("Anotações", self._montar_aba_anotacoes)):
            abas.add(nome)
            area = ctk.CTkScrollableFrame(abas.tab(nome), fg_color="transparent")
            area.pack(fill="both", expand=True)
            montar(area)

        self.after(INTERVALO_AUTOSAVE_MS, self._autosave)

    # --- Montagem ---------------------------------------------------------

    def _montar_barra_superior(self) -> None:
        barra = ctk.CTkFrame(self.corpo, fg_color=tema.COR_CARTAO, corner_radius=12,
                             border_width=1, border_color=tema.COR_BORDA)
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        barra.grid_columnconfigure(5, weight=1)

        def botao(texto, comando, largura=36):
            return ctk.CTkButton(barra, text=texto, width=largura, height=34,
                                 fg_color=tema.COR_FUNDO, hover_color=tema.COR_BORDA,
                                 border_width=1, border_color=tema.COR_BORDA,
                                 text_color=tema.COR_TEXTO, command=comando)

        botao("◀", lambda: self.abrir_data(self._data - timedelta(days=1))).grid(
            row=0, column=0, padx=(14, 4), pady=14)
        self._entrada_data = ctk.CTkEntry(barra, width=120, height=34, justify="center",
                                          fg_color=tema.COR_FUNDO, border_color=tema.COR_BORDA,
                                          font=tema.fonte_normal())
        self._entrada_data.grid(row=0, column=1, padx=4)
        self._entrada_data.bind("<Return>", lambda _: self._data_digitada())
        self._entrada_data.bind("<FocusOut>", lambda _: self._data_digitada())
        botao("▶", lambda: self.abrir_data(self._data + timedelta(days=1))).grid(row=0, column=2, padx=4)
        botao("Hoje", lambda: self.abrir_data(date.today()), largura=60).grid(row=0, column=3, padx=(4, 14))

        textos = ctk.CTkFrame(barra, fg_color="transparent")
        textos.grid(row=0, column=4, sticky="w")
        self._rotulo_dia = ctk.CTkLabel(textos, text="", font=tema.fonte_secao(), text_color=tema.COR_TEXTO)
        self._rotulo_dia.pack(anchor="w")
        self._rotulo_modo = ctk.CTkLabel(textos, text="", font=tema.fonte_pequena(),
                                         text_color=tema.COR_TEXTO_SECUNDARIO)
        self._rotulo_modo.pack(anchor="w")

        self._rotulo_status = ctk.CTkLabel(barra, text="", font=tema.fonte_pequena(),
                                           text_color=tema.COR_TEXTO_SECUNDARIO)
        self._rotulo_status.grid(row=0, column=5, sticky="e", padx=12)
        ctk.CTkButton(barra, text="Salvar", width=120, height=38, font=tema.fonte_secao(),
                      fg_color=tema.COR_DESTAQUE, hover_color=tema.COR_DESTAQUE_HOVER,
                      command=self.salvar).grid(row=0, column=6, padx=(0, 14))

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
        dormiu = CampoEntrada(secao.conteudo, "Dormiu às", placeholder="23:30")
        acordou = CampoEntrada(secao.conteudo, "Acordou às", placeholder="07:30")
        horas = CampoEntrada(secao.conteudo, "Horas dormidas", placeholder="automático")
        self._grade(secao, [("sono_dormiu_as", dormiu), ("sono_acordou_as", acordou), ("sono_horas", horas)])
        self._rotulo_horas_auto = ctk.CTkLabel(secao.conteudo, text="", font=tema.fonte_pequena(),
                                               text_color=tema.COR_TEXTO_SECUNDARIO)
        self._rotulo_horas_auto.grid(row=0, column=3, sticky="sw", pady=(0, 10))
        dormiu.ao_digitar(self._atualizar_horas_auto)
        acordou.ao_digitar(self._atualizar_horas_auto)
        qualidade = CampoNota(secao.conteudo, "Qualidade do sono")
        qualidade.grid(row=1, column=0, columnspan=4, sticky="w", pady=4)
        self._campos["sono_qualidade"] = qualidade

        secao = Secao(area, "Alimentação")
        secao.pack(fill="x", pady=10)
        for linha, (chave, nome) in enumerate((("cafe", "Café da manhã"), ("almoco", "Almoço"),
                                               ("jantar", "Jantar"))):
            horario = CampoEntrada(secao.conteudo, f"{nome} – horário", largura=90, placeholder="HH:MM")
            descricao = CampoEntrada(secao.conteudo, "O que comeu", largura=440)
            horario.grid(row=linha, column=0, sticky="w", padx=(0, 12), pady=4)
            descricao.grid(row=linha, column=1, sticky="w", pady=4)
            self._campos[f"{chave}_horario"] = horario
            self._campos[f"{chave}_descricao"] = descricao
        outros = CampoEntrada(secao.conteudo, "Outros (lanches, doces...)", largura=542)
        outros.grid(row=3, column=0, columnspan=2, sticky="w", pady=4)
        self._campos["alimentacao_outros"] = outros

        secao = Secao(area, "Hidratação e bebidas")
        secao.pack(fill="x", pady=10)
        agua = CampoEntrada(secao.conteudo, "Água (litros)", placeholder="2,5")
        agua.pack(anchor="w", pady=(0, 8))
        self._campos["agua_litros"] = agua
        ctk.CTkLabel(secao.conteudo, text="Café, energético e outras bebidas",
                     font=tema.fonte_pequena(), text_color=tema.COR_TEXTO_SECUNDARIO).pack(anchor="w")
        self._campos["bebidas"] = ListaEditavel(
            secao.conteudo, [("tipo", "Bebida (ex.: café)", 200), ("quantidade", "Quantidade", 140),
                             ("horario", "HH:MM", 80)], "+ Bebida")
        self._campos["bebidas"].pack(anchor="w", fill="x")

        secao = Secao(area, "Medicamentos")
        secao.pack(fill="x", pady=10)
        self._campos["medicamentos"] = ListaEditavel(
            secao.conteudo, [("nome", "Nome", 220), ("dose", "Dose", 120), ("horario", "HH:MM", 80)],
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
        secao = Secao(area, "Sessão")
        secao.pack(fill="x", pady=(0, 10))
        rotulo = ctk.CTkFrame(secao.conteudo, fg_color="transparent")
        ctk.CTkLabel(rotulo, text="Jogou hoje?", font=tema.fonte_pequena(),
                     text_color=tema.COR_TEXTO_SECUNDARIO).pack(anchor="w")
        jogou = SeletorBotoes(rotulo, [("sim", "Sim"), ("nao", "Não")], largura_botao=60)
        jogou.pack(anchor="w")
        rotulo.grid(row=0, column=0, sticky="w", padx=(0, 18), pady=4)
        self._campos["jogou"] = jogou
        inicio = CampoEntrada(secao.conteudo, "Começou às", placeholder="19:00")
        fim = CampoEntrada(secao.conteudo, "Parou às", placeholder="23:00")
        inicio.grid(row=0, column=1, sticky="w", padx=(0, 18), pady=4)
        fim.grid(row=0, column=2, sticky="w", pady=4)
        self._campos["jogo_inicio"] = inicio
        self._campos["jogo_fim"] = fim

        secao = Secao(area, "Resultados e estatísticas",
                      "K/D/A: totais somados do dia. ACS, ADR e HS%: médias por partida.")
        secao.pack(fill="x", pady=10)
        campos = [
            ("partidas", CampoEntrada(secao.conteudo, "Partidas", largura=100)),
            ("vitorias", CampoEntrada(secao.conteudo, "Vitórias", largura=100)),
            ("derrotas", CampoEntrada(secao.conteudo, "Derrotas", largura=100)),
            ("empates", CampoEntrada(secao.conteudo, "Empates", largura=100)),
            ("abates", CampoEntrada(secao.conteudo, "Abates (K)", largura=100)),
            ("mortes", CampoEntrada(secao.conteudo, "Mortes (D)", largura=100)),
            ("assistencias", CampoEntrada(secao.conteudo, "Assistências (A)", largura=100)),
            ("acs", CampoEntrada(secao.conteudo, "ACS médio", largura=100)),
            ("adr", CampoEntrada(secao.conteudo, "ADR médio", largura=100)),
            ("hs_pct", CampoEntrada(secao.conteudo, "HS%", largura=100)),
        ]
        self._grade(secao, campos, colunas=4)
        for chave in ("partidas", "vitorias", "abates", "mortes", "assistencias"):
            self._campos[chave].ao_digitar(self._atualizar_derivados)
        self._rotulo_derivados = ctk.CTkLabel(secao.conteudo, text="", font=tema.fonte_secao(),
                                              text_color=tema.COR_DESTAQUE)
        self._rotulo_derivados.grid(row=3, column=0, columnspan=4, sticky="w", pady=(10, 0))

        agentes = CampoEntrada(secao.conteudo, "Agentes usados (separe por vírgula)",
                               largura=440, placeholder="Jett, Raze")
        agentes.grid(row=4, column=0, columnspan=4, sticky="w", pady=(10, 4))
        self._campos["agentes"] = agentes

        secao = Secao(area, "Autoavaliação")
        secao.pack(fill="x", pady=10)
        self._grade(secao, [
            ("mira", CampoNota(secao.conteudo, "Sensação da mira")),
            ("movimentacao", CampoNota(secao.conteudo, "Qualidade da movimentação")),
            ("tomada_decisao", CampoNota(secao.conteudo, "Tomada de decisão")),
            ("concentracao", CampoNota(secao.conteudo, "Concentração")),
            ("consistencia", CampoNota(secao.conteudo, "Consistência")),
        ], colunas=1)

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
        return formulario

    def _preencher(self, formulario: dict) -> None:
        for chave, campo in self._campos.items():
            campo.set(formulario.get(chave))
        self._atualizar_horas_auto()
        self._atualizar_derivados()

    def _tem_alteracoes(self) -> bool:
        return self._carregado and self._ler() != self._base

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

    def _atualizar_derivados(self) -> None:
        jogo = derivados_ao_vivo(self._ler())
        partes = []
        if jogo.kd is not None:
            partes += [f"K/D {numero(jogo.kd)}", f"KDA {numero(jogo.kda)}"]
        if jogo.winrate_pct is not None:
            partes.append(f"Winrate {numero(jogo.winrate_pct, 1)}%")
        self._rotulo_derivados.configure(text="   ·   ".join(partes))

    def _atualizar_cabecalho(self) -> None:
        self._entrada_data.delete(0, "end")
        self._entrada_data.insert(0, data_curta(self._data))
        self._rotulo_dia.configure(text=data_extensa(self._data))
        if self._editando:
            self._rotulo_modo.configure(text="Editando registro existente", text_color=tema.COR_AVISO)
        else:
            self._rotulo_modo.configure(text="Novo registro", text_color=tema.COR_TEXTO_SECUNDARIO)

    def _status(self, texto: str, cor: str = tema.COR_TEXTO_SECUNDARIO) -> None:
        self._rotulo_status.configure(text=texto, text_color=cor)

    # --- Carregar datas ---------------------------------------------------

    def ao_exibir(self) -> None:
        if not self._carregado:
            self._carregar(date.today())

    def abrir_data(self, data: date) -> None:
        """Abre uma data no formulário, confirmando se há alterações não salvas."""
        if self._carregado and data == self._data:
            return
        if self._tem_alteracoes() and not messagebox.askyesno(
            "Alterações não salvas",
            f"Há alterações não salvas em {data_curta(self._data)}.\n\nDescartar e abrir outra data?",
            parent=self,
        ):
            self._atualizar_cabecalho()
            return
        self._carregar(data)

    def _data_digitada(self) -> None:
        texto = self._entrada_data.get().strip()
        if texto == data_curta(self._data):
            return
        try:
            data = datetime.strptime(texto, "%d/%m/%Y").date()
        except ValueError:
            messagebox.showwarning("Data inválida", "Use o formato DD/MM/AAAA.", parent=self)
            self._atualizar_cabecalho()
            return
        self.abrir_data(data)

    def _carregar(self, data: date) -> None:
        try:
            existente = self.repositorio.obter_dia(data)
        except (ArquivoCorrompidoError, VersaoIncompativelError) as erro:
            messagebox.showerror("Não foi possível ler a semana", str(erro), parent=self)
            existente = None

        self._data = data
        self._editando = existente is not None
        self._preencher(registro_para_formulario(existente or RegistroDia(data=data)))
        # A base é lida de volta da tela, para comparar sempre "igual com igual".
        self._base = self._ler()
        self._carregado = True
        self._descartar_rascunho()
        self._atualizar_cabecalho()
        self._status("")

    def recuperar_rascunho(self, formulario: dict) -> None:
        """Chamado pela janela ao abrir o app, se o usuário aceitar recuperar."""
        self._carregar(date.fromisoformat(formulario["data"]))
        self._preencher(formulario)
        self._salvar_rascunho_se_preciso()

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
            try:
                self.repositorio.salvar_dia(registro, sobrescrever=self._editando)
            except RegistroDuplicadoError:
                # Acontece se o dia foi criado em outro lugar depois de abrirmos o formulário.
                if not messagebox.askyesno(
                    "Registro já existe",
                    f"Já existe um registro em {data_curta(registro.data)}.\n\n"
                    "Substituir pelo que está no formulário?",
                    parent=self,
                ):
                    return
                self.repositorio.salvar_dia(registro, sobrescrever=True)
        except (ArquivoCorrompidoError, VersaoIncompativelError) as erro:
            messagebox.showerror("Não foi possível salvar", str(erro), parent=self)
            return

        self._editando = True
        # Reexibe os valores normalizados (ex.: "730" vira "07:30").
        self._preencher(registro_para_formulario(registro))
        self._base = self._ler()
        self._descartar_rascunho()
        self._atualizar_cabecalho()
        self._status(f"✓ Salvo às {datetime.now():%H:%M}", tema.COR_SUCESSO)

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
        if atual == self._base:
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
