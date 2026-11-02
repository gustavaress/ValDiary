"""Tela de registro diário: criar um registro novo ou editar um existente.

Dois modos:
- NOVO: a data é só "a que dia este registro pertence". Trocá-la mantém o que
  foi preenchido, mas só são aceitos dias sem registro e que não estão no futuro.
- EDIÇÃO: aberto pelo Histórico ou por "Editar o registro de hoje". A data fica
  travada; "+ Novo registro" volta ao modo novo.

Cada aba fica no seu próprio arquivo (aba_*.py) e registra seus campos em
`self.campos`. Esta classe cuida do que é comum: data, carregar, salvar e rascunho.
"""

from datetime import date, datetime, timedelta
from tkinter import messagebox

import customtkinter as ctk

from app.analysis.ranking import ranking_no_inicio_do_dia
from app.models import RegistroDia, validar_registro
from app.models.datas import data_livre_mais_recente, erro_data_nova, proxima_data_livre
from app.models.ranking import Ranking
from app.storage import ArquivoCorrompidoError, RegistroDuplicadoError, VersaoIncompativelError
from app.storage.rascunho import apagar_rascunho, salvar_rascunho
from app.ui import tema
from app.ui.componentes import Secao, SeletorClassificacao
from app.ui.componentes.botoes import botao_icone, botao_primario, botao_secundario
from app.ui.formatacao import data_curta, data_extensa
from app.ui.mapeamento_registro import formulario_para_registro, registro_para_formulario
from app.ui.telas.base import TelaBase
from app.ui.telas.registro.aba_aim import AbaAim, itens_da_rotina_padrao
from app.ui.telas.registro.aba_anotacoes import AbaAnotacoes
from app.ui.telas.registro.aba_partidas import AbaPartidas
from app.ui.telas.registro.aba_rotina import AbaRotina
from app.ui.telas.registro.aba_valorant import AbaValorant

INTERVALO_AUTOSAVE_MS = 3000
NOVO, EDICAO = "novo", "edicao"

# (nome da aba, classe). A ordem aqui é a ordem das abas na tela.
ABAS = [
    ("Rotina", AbaRotina),
    ("Valorant", AbaValorant),
    ("Partidas", AbaPartidas),
    ("Aim Routine", AbaAim),
    ("Anotações", AbaAnotacoes),
]


def _sem_data(formulario: dict) -> dict:
    """Conteúdo do formulário sem a data (trocar a data não é "alterar o registro")."""
    return {chave: valor for chave, valor in formulario.items() if chave != "data"}


class TelaRegistro(TelaBase):
    titulo = "Registro diário"
    subtitulo = "Preencha só o que lembrar. Nenhum campo é obrigatório."

    def montar(self) -> None:
        # Cada campo da tela, pela mesma chave usada no dicionário do formulário.
        self.campos: dict = {}
        self.legado: dict | None = None             # totais antigos do dia (sem campo na tela)
        self.ranking_inicio: Ranking | None = None  # calculado; vem da aba Ranking
        self._data = date.today()
        self._modo = NOVO
        self._registradas: set[date] = set()
        self._carregado = False
        self._base: dict = {}             # conteúdo quando foi carregado/salvo
        self._ultimo_rascunho: dict | None = None

        self.corpo.grid_columnconfigure(0, weight=1)
        self.corpo.grid_rowconfigure(2, weight=1)

        self._montar_barra_superior()
        self._montar_classificacao()

        self.abas = ctk.CTkTabview(
            self.corpo, fg_color="transparent", corner_radius=tema.RAIO,
            segmented_button_fg_color=tema.COR_CARTAO,
            segmented_button_selected_color=tema.COR_DESTAQUE,
            segmented_button_selected_hover_color=tema.COR_DESTAQUE_HOVER,
            segmented_button_unselected_color=tema.COR_CARTAO,
            segmented_button_unselected_hover_color=tema.COR_CARTAO_HOVER,
            anchor="w",
            # Medicamentos são editados na aba Rotina: o cruzamento com o jogo é refeito ao trocar de aba.
            command=lambda: self.aba_valorant.atualizar(),
        )
        # O CTkTabview não expõe a fonte/altura das abas no construtor: ajustamos o
        # botão segmentado interno para seguir a tipografia display do app.
        self.abas._segmented_button.configure(font=tema.fonte_display(20), height=36)
        self.abas.grid(row=2, column=0, sticky="nsew")
        self.areas: dict[str, ctk.CTkScrollableFrame] = {}
        self._abas_montadas = []
        for nome, classe in ABAS:
            self.abas.add(nome)
            # Respiro lateral em cada aba (o texto em Bebas é estreito).
            self.abas._segmented_button._buttons_dict[nome].configure(width=130)
            area = ctk.CTkScrollableFrame(self.abas.tab(nome), fg_color="transparent")
            area.pack(fill="both", expand=True)
            self.areas[nome] = area
            self._abas_montadas.append(classe(self, area))
        self.aba_rotina, self.aba_valorant, self.aba_partidas, self.aba_aim, self.aba_anotacoes = self._abas_montadas

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
        self._botao_hoje = botao("Hoje", lambda: self.mudar_data(date.today()), largura=60)
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
        self.rotulo_status = ctk.CTkLabel(barra, text="", font=tema.fonte_pequena(), anchor="w",
                                          text_color=tema.COR_TEXTO_SECUNDARIO)
        botao_secundario(barra, "+ Novo registro", self.novo_registro, largura=140, altura=40).grid(
            row=0, column=6, padx=(0, 8))
        botao_primario(barra, "Salvar", self.salvar, largura=120, altura=40).grid(row=0, column=7, padx=(0, 14))

    def _montar_classificacao(self) -> None:
        linha = ctk.CTkFrame(self.corpo, fg_color="transparent")
        linha.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkLabel(linha, text="Como foi o dia?", font=tema.fonte_secao(),
                     text_color=tema.COR_TEXTO).pack(side="left", padx=(4, 14))
        self.campos["classificacao"] = SeletorClassificacao(linha)
        self.campos["classificacao"].pack(side="left")

    def grade(self, secao: Secao, campos: list[tuple[str, ctk.CTkFrame]], colunas: int = 4) -> None:
        """Usado pelas abas: registra os campos e os distribui em grade dentro da seção."""
        for i, (chave, campo) in enumerate(campos):
            campo.grid(row=i // colunas, column=i % colunas, sticky="w", padx=(0, 18), pady=4)
            self.campos[chave] = campo

    # --- Leitura e preenchimento -----------------------------------------

    @property
    def data(self) -> date:
        return self._data

    @property
    def modo(self) -> str:
        return self._modo

    def ler(self) -> dict:
        formulario = {chave: campo.get() for chave, campo in self.campos.items()}
        formulario["data"] = self._data.isoformat()
        formulario["legado"] = self.legado
        return formulario

    def _preencher(self, formulario: dict) -> None:
        self.legado = formulario.get("legado")
        for chave, campo in self.campos.items():
            campo.set(formulario.get(chave))
        # A rotina padrão de aim aparece em todo dia que ainda não tem exercícios.
        if not self.campos["aim_exercicios"].get():
            self.campos["aim_exercicios"].set(itens_da_rotina_padrao(self))
        for aba in self._abas_montadas:
            aba.atualizar()

    def tem_alteracoes(self) -> bool:
        return self._carregado and _sem_data(self.ler()) != self._base

    def _calcular_ranking_inicio(self) -> None:
        """Ranking ao começar o dia aberto: definição (aba Ranking) + RR dos dias anteriores."""
        registros, _ = self.repositorio.carregar_todos()
        self.ranking_inicio = ranking_no_inicio_do_dia(self._data, registros, self.janela.definicoes_ranking())
        self.aba_partidas.mostrar_ranking_inicio()

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
            self._rotulo_modo.configure(text="Editando  ·  data travada", text_color=tema.COR_AVISO)

    def _status(self, texto: str, cor: str = tema.COR_TEXTO_SECUNDARIO) -> None:
        self.rotulo_status.configure(text=texto, text_color=cor)
        if texto:
            self.rotulo_status.grid(row=1, column=0, columnspan=8, sticky="w", padx=16, pady=(0, 10))
        else:
            self.rotulo_status.grid_remove()

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
            self.aba_partidas.atualizar()

    def _pode_descartar(self) -> bool:
        if not self.tem_alteracoes():
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
        self._preencher(registro_para_formulario(RegistroDia(data=data)))
        self._base = _sem_data(self.ler())  # base = formulário em branco
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
        self._base = _sem_data(self.ler())
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

    def mudar_data(self, data: date) -> None:
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
        self.aba_partidas.atualizar()
        self._atualizar_cabecalho()

    def _andar_data(self, passo: int) -> None:
        """Setas: vão para o dia livre mais próximo, pulando os já registrados."""
        destino = proxima_data_livre(self._data + timedelta(days=passo), passo, self._registradas, date.today())
        if destino is None:
            self._status("Não há dias livres nessa direção.", tema.COR_AVISO)
            return
        self.mudar_data(destino)

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
        self.mudar_data(data)

    # --- Salvar -----------------------------------------------------------

    def salvar(self) -> None:
        formulario = self.ler()
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
        self._base = _sem_data(self.ler())
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
        atual = self.ler()
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
