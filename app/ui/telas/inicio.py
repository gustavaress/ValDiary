"""Tela inicial: status de hoje, resumo da semana e último registro."""

from datetime import date, timedelta

import customtkinter as ctk

from app.analysis.ranking import ranking_atual
from app.analysis.resumo import resumir, sequencia_atual
from app.storage import ArquivoCorrompidoError
from app.storage.semanas import periodo_semana, semana_da_data
from app.ui import tema
from app.ui.componentes.botoes import botao_primario
from app.ui.componentes import CartaoInfo
from app.ui.formatacao import data_extensa, data_tabela, numero
from app.ui.telas.base import TelaBase

# (atributo do ResumoPeriodo, título do cartão, casas decimais, sufixo)
INDICADORES_SEMANA = [
    ("partidas", "Partidas", 0, ""),
    ("winrate_pct", "Winrate", 1, "%"),
    ("kd", "K/D", 2, ""),
    ("kda", "KDA", 2, ""),
    ("acs_medio", "ACS médio", 0, ""),
    ("hs_medio", "HS% médio", 1, "%"),
    ("sono_medio", "Sono médio", 1, "h"),
    ("concentracao_media", "Concentração", 1, ""),
]


class TelaInicio(TelaBase):
    titulo = "Início"
    subtitulo = "Resumo do seu diário"

    def montar(self) -> None:
        area = ctk.CTkScrollableFrame(self.corpo, fg_color="transparent")
        area.pack(fill="both", expand=True)
        area.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="cartoes")

        # Linha 1: situação geral
        self._hoje = CartaoInfo(area, "Hoje")
        self._semana = CartaoInfo(area, "Esta semana")
        self._sequencia = CartaoInfo(area, "Sequência")
        self._ranking = CartaoInfo(area, "Ranking atual")
        for coluna, cartao in enumerate((self._hoje, self._semana, self._sequencia, self._ranking)):
            cartao.grid(row=0, column=coluna, sticky="nsew", padx=6, pady=6)

        self._botao = botao_primario(area, "", lambda: self.janela.abrir_registro(date.today()),
                                     largura=300, altura=46)
        self._botao.grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=(14, 24))

        # Semana atual
        self._titulo_semana = ctk.CTkLabel(area, text="", font=tema.fonte_secao(), text_color=tema.COR_TEXTO)
        self._titulo_semana.grid(row=2, column=0, columnspan=4, sticky="w", padx=6)
        self._classificacoes = ctk.CTkFrame(area, fg_color="transparent")
        self._classificacoes.grid(row=3, column=0, columnspan=4, sticky="w", padx=6, pady=(2, 6))

        self._indicadores: dict[str, CartaoInfo] = {}
        for i, (chave, titulo, _, _) in enumerate(INDICADORES_SEMANA):
            cartao = CartaoInfo(area, titulo)
            cartao.grid(row=4 + i // 4, column=i % 4, sticky="nsew", padx=6, pady=6)
            self._indicadores[chave] = cartao

        # Último registro
        ultimo = ctk.CTkFrame(area, fg_color=tema.COR_CARTAO, corner_radius=tema.RAIO,
                              border_width=1, border_color=tema.COR_BORDA)
        ultimo.grid(row=6, column=0, columnspan=4, sticky="ew", padx=6, pady=(18, 6))
        self._ultimo_titulo = ctk.CTkLabel(ultimo, text="", font=tema.fonte_secao(), text_color=tema.COR_TEXTO)
        self._ultimo_titulo.pack(anchor="w", padx=18, pady=(14, 2))
        self._ultimo_texto = ctk.CTkLabel(ultimo, text="", font=tema.fonte_normal(), justify="left",
                                          text_color=tema.COR_TEXTO_SECUNDARIO, wraplength=800)
        self._ultimo_texto.pack(anchor="w", padx=18, pady=(0, 16))

    def ao_exibir(self) -> None:
        hoje = date.today()
        registros, _ = self.repositorio.carregar_todos()
        self._atualizar_situacao(registros, hoje)
        self._atualizar_semana(registros, hoje)
        self._atualizar_ultimo(registros)

    # --- Partes da tela ---------------------------------------------------

    def _atualizar_situacao(self, registros, hoje: date) -> None:
        registro_hoje = next((r for r in registros if r.data == hoje), None)
        if registro_hoje is None:
            self._hoje.atualizar("Pendente", data_extensa(hoje), tema.COR_AVISO)
            self._botao.configure(text="Registrar o dia de hoje")
        else:
            classificacao = registro_hoje.classificacao
            if classificacao:
                self._hoje.atualizar(tema.ROTULOS_CLASSIFICACAO[classificacao],
                                     data_extensa(hoje), tema.CORES_CLASSIFICACAO[classificacao])
            else:
                self._hoje.atualizar("Registrado", data_extensa(hoje), tema.COR_SUCESSO)
            self._botao.configure(text="Editar o registro de hoje")

        ano, semana = semana_da_data(hoje)
        da_semana = [r for r in registros if r.semana == (ano, semana)]
        self._semana.atualizar(f"{len(da_semana)}/7",
                               f"semana {semana}  ·  {len(registros)} no total")

        sequencia = sequencia_atual(registros, hoje)
        self._sequencia.atualizar(f"{sequencia} dia{'s' if sequencia != 1 else ''}",
                                  "registrando sem falhar")

        try:
            definicoes = self.janela.repositorio_ranking.carregar()
        except ArquivoCorrompidoError:
            definicoes = []
        ranking = ranking_atual(registros, definicoes)
        if ranking is None:
            self._ranking.atualizar("—", "defina seu elo na aba Ranking")
        else:
            rr_semana = resumir(da_semana).rr
            detalhe = f"{ranking.rr} RR"
            if rr_semana is not None:
                detalhe += f"  ·  {rr_semana:+d} RR nesta semana"
            self._ranking.atualizar(ranking.elo, detalhe)

    def _atualizar_semana(self, registros, hoje: date) -> None:
        semana_atual = semana_da_data(hoje)
        semana_passada = semana_da_data(hoje - timedelta(days=7))
        atual = resumir([r for r in registros if r.semana == semana_atual])
        anterior = resumir([r for r in registros if r.semana == semana_passada])

        inicio, fim = periodo_semana(*semana_atual)
        self._titulo_semana.configure(
            text=f"Semana {semana_atual[1]}  ·  {inicio:%d/%m} a {fim:%d/%m}")

        for chave, _, casas, sufixo in INDICADORES_SEMANA:
            valor = getattr(atual, chave)
            valor_anterior = getattr(anterior, chave)
            if chave == "partidas":
                # Partidas: 0 significa "nada registrado", então exibimos como vazio.
                valor = valor or None
                valor_anterior = valor_anterior or None
            detalhe = (f"semana passada: {numero(valor_anterior, casas, sufixo)}"
                       if valor_anterior is not None else "sem dados da semana passada")
            self._indicadores[chave].atualizar(numero(valor, casas, sufixo), detalhe)

        for filho in self._classificacoes.winfo_children():
            filho.destroy()
        if not atual.classificacoes:
            ctk.CTkLabel(self._classificacoes, text="Nenhum dia classificado nesta semana ainda.",
                         font=tema.fonte_pequena(), text_color=tema.COR_TEXTO_SECUNDARIO).pack(side="left")
        for chave, rotulo in tema.ROTULOS_CLASSIFICACAO.items():
            quantidade = atual.classificacoes.get(chave)
            if quantidade:
                ctk.CTkLabel(self._classificacoes, text=f"●  {quantidade} {rotulo}",
                             font=tema.fonte_pequena(),
                             text_color=tema.CORES_CLASSIFICACAO[chave]).pack(side="left", padx=(0, 16))

    def _atualizar_ultimo(self, registros) -> None:
        if not registros:
            self._ultimo_titulo.configure(text="Último registro")
            self._ultimo_texto.configure(text="Você ainda não registrou nenhum dia. Comece pelo botão acima!")
            return
        ultimo = registros[-1]  # carregar_todos já devolve em ordem de data
        classificacao = ultimo.classificacao
        sufixo = f"  ·  {tema.ROTULOS_CLASSIFICACAO[classificacao]}" if classificacao else ""
        self._ultimo_titulo.configure(text=f"Último registro: {data_tabela(ultimo.data)}{sufixo}")

        partes = []
        jogo = ultimo.valorant.resumo
        if jogo.kda_texto:
            partes.append(f"K/D/A {jogo.kda_texto}  (K/D {numero(jogo.kd)})")
        if ultimo.valorant.notas:
            partes.append(f"Partidas: {ultimo.valorant.notas}")
        if ultimo.rotina.observacoes:
            partes.append(f"Dia: {ultimo.rotina.observacoes}")
        self._ultimo_texto.configure(text="\n".join(partes) or "Sem anotações.")
