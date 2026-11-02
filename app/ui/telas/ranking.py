"""Tela Ranking: definir o elo/RR e acompanhar a evolução calculada."""

from datetime import date, datetime
from tkinter import messagebox

import customtkinter as ctk

from app.analysis.ranking import evolucao_ranking
from app.models.ranking import ELOS, RR_POR_DIVISAO, TOPO, Ranking, erros_definicao
from app.storage import ArquivoCorrompidoError
from app.ui import conversao, tema
from app.ui.componentes.botoes import botao_primario, botao_secundario
from app.ui.componentes import CampoEntrada, CampoOpcao, CartaoInfo, Secao, Tabela
from app.ui.componentes.emblema_rank import imagem_rank
from app.ui.formatacao import data_curta, data_tabela
from app.ui.telas.base import TelaBase


class CartaoRanking(ctk.CTkFrame):
    """Destaque do topo: emblema grande, elo, barra de RR até a próxima divisão e o próximo elo."""

    def __init__(self, master):
        super().__init__(master, fg_color=tema.COR_CARTAO, corner_radius=tema.RAIO,
                         border_width=1, border_color=tema.COR_BORDA)
        self.grid_columnconfigure(1, weight=1)
        self._emblema = ctk.CTkLabel(self, text="", width=120, height=120)
        self._emblema.grid(row=0, column=0, rowspan=2, padx=(24, 20), pady=20)

        meio = ctk.CTkFrame(self, fg_color="transparent")
        meio.grid(row=0, column=1, sticky="sw", pady=(20, 0))
        ctk.CTkFrame(meio, width=26, height=3, corner_radius=0, fg_color=tema.COR_DESTAQUE).pack(anchor="w")
        ctk.CTkLabel(meio, text="SEU RANKING", font=tema.fonte_rotulo(),
                     text_color=tema.COR_TEXTO_SECUNDARIO).pack(anchor="w", pady=(6, 0))
        self.rotulo_elo = ctk.CTkLabel(meio, text="—", font=tema.fonte_display(44), text_color=tema.COR_TEXTO,
                                       height=48)
        self.rotulo_elo.pack(anchor="w")

        baixo = ctk.CTkFrame(self, fg_color="transparent")
        baixo.grid(row=1, column=1, sticky="nw", pady=(0, 20))
        self._barra = ctk.CTkProgressBar(baixo, width=380, height=8, corner_radius=2,
                                         fg_color=tema.COR_CAMPO, progress_color=tema.COR_DESTAQUE)
        self.rotulo_rr = ctk.CTkLabel(baixo, text="", font=tema.fonte_forte(), text_color=tema.COR_TEXTO)
        self.rotulo_rr.pack(anchor="w")
        self._origem = ctk.CTkLabel(baixo, text="", font=tema.fonte_pequena(),
                                    text_color=tema.COR_TEXTO_SECUNDARIO)
        self._origem.pack(anchor="w")

        self._proximo = ctk.CTkFrame(self, fg_color="transparent")
        self._proximo.grid(row=0, column=2, rowspan=2, padx=(10, 28))
        ctk.CTkLabel(self._proximo, text="PRÓXIMO", font=tema.fonte_rotulo(),
                     text_color=tema.COR_TEXTO_SECUNDARIO).pack()
        self._emblema_proximo = ctk.CTkLabel(self._proximo, text="", width=56, height=56)
        self._emblema_proximo.pack(pady=4)
        self._nome_proximo = ctk.CTkLabel(self._proximo, text="", font=tema.fonte_pequena(),
                                          text_color=tema.COR_TEXTO_SECUNDARIO)
        self._nome_proximo.pack()

    def atualizar(self, ranking: Ranking | None, origem: str) -> None:
        self._origem.configure(text=origem)
        self._barra.pack_forget()
        self._proximo.grid_remove()
        if ranking is None:
            self._emblema.configure(image=None)
            self.rotulo_elo.configure(text="—")
            self.rotulo_rr.configure(text="")
            return

        self._emblema.configure(image=imagem_rank(ranking.elo, 120))
        self.rotulo_elo.configure(text=ranking.elo.upper())
        if ranking.elo in TOPO:
            # Imortal/Radiante: a divisão depende do ranking global do jogo; o RR só acumula.
            self.rotulo_rr.configure(text=f"{ranking.rr} RR acumulados")
            return
        proximo = ELOS[ELOS.index(ranking.elo) + 1]
        self._barra.pack(anchor="w", pady=(4, 6), before=self.rotulo_rr)
        self._barra.set(min(ranking.rr, RR_POR_DIVISAO) / RR_POR_DIVISAO)
        faltam = max(RR_POR_DIVISAO - ranking.rr, 0)
        self.rotulo_rr.configure(text=f"{ranking.rr} / {RR_POR_DIVISAO} RR  ·  faltam {faltam} para {proximo}")
        self._emblema_proximo.configure(image=imagem_rank(proximo, 56))
        self._nome_proximo.configure(text=proximo)
        self._proximo.grid()


class TelaRanking(TelaBase):
    titulo = "Ranking"
    subtitulo = "Seu ranking é atualizado sozinho a cada dia registrado, com o RR de cada partida."

    def montar(self) -> None:
        area = ctk.CTkScrollableFrame(self.corpo, fg_color="transparent")
        area.pack(fill="both", expand=True)
        area.grid_columnconfigure((0, 1), weight=1, uniform="col")

        self.cartao_atual = CartaoRanking(area)
        self.cartao_atual.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=6, pady=6)
        self._cartao_semana = CartaoInfo(area, "RR nos últimos 7 dias")
        self._cartao_definicao = CartaoInfo(area, "Último ajuste manual")
        for coluna, cartao in enumerate((self._cartao_semana, self._cartao_definicao)):
            cartao.grid(row=1, column=coluna, sticky="nsew", padx=6, pady=6)

        secao = Secao(area, "Ajustar ranking manualmente",
                      "Só é preciso ao começar a usar o app ou se o ranking ficar diferente do jogo. "
                      "Vale a partir do INÍCIO do dia escolhido.")
        secao.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=6, pady=6)
        linha = ctk.CTkFrame(secao.conteudo, fg_color="transparent")
        linha.pack(anchor="w")
        self._emblema_ajuste = ctk.CTkLabel(linha, text="", width=52, height=52)
        self._emblema_ajuste.pack(side="left", padx=(0, 10), anchor="s")
        self._elo = CampoOpcao(linha, "Elo", ELOS, largura=170, ao_mudar=self._mostrar_emblema_ajuste)
        self._rr = CampoEntrada(linha, "RR (pontos)", largura=90, placeholder="0 a 99")
        self._data = CampoEntrada(linha, "Vale a partir de", largura=120, placeholder="DD/MM/AAAA")
        for campo in (self._elo, self._rr, self._data):
            campo.pack(side="left", padx=(0, 16))
        botao_primario(linha, "Salvar ranking", self._salvar, largura=160, altura=34).pack(side="left", anchor="s")

        secao = Secao(area, "Evolução dia a dia",
                      "RR de cada partida aplicado na ordem, com proteção contra rebaixamento. "
                      "★ = um ajuste manual passou a valer.")
        secao.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=6, pady=6)
        self._tabela_evolucao = Tabela(secao.conteudo, [
            ("data", "Data", 130, "w"), ("inicio", "Início do dia", 200, "w"),
            ("rr", "RR do dia", 90, "center"), ("fim", "Fim do dia", 200, "w"),
        ], altura_automatica=True)
        self._tabela_evolucao.pack(fill="x")

        secao = Secao(area, "Ajustes manuais feitos")
        secao.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=6, pady=6)
        self._tabela_definicoes = Tabela(secao.conteudo, [
            ("data", "Vale a partir de", 150, "w"), ("ranking", "Ranking", 200, "w"),
            ("definido_em", "Definido em", 160, "w"),
        ], altura_automatica=True)
        self._tabela_definicoes.pack(fill="x")
        botao_secundario(secao.conteudo, "Remover selecionado", self._remover, largura=180, altura=32).pack(
            anchor="w", pady=(10, 0))

    @property
    def _repositorio_ranking(self):
        return self.janela.repositorio_ranking

    def ao_exibir(self) -> None:
        self._data.set(data_curta(date.today()))
        try:
            definicoes = self._repositorio_ranking.carregar()
        except ArquivoCorrompidoError as erro:
            messagebox.showerror("Arquivo de ranking com problema", str(erro), parent=self)
            definicoes = []
        registros, _ = self.repositorio.carregar_todos()
        evolucao = evolucao_ranking(registros, definicoes)

        salvo = self.janela.atualizar_ranking_salvo()
        if salvo is None:
            self.cartao_atual.atualizar(None, "Ajuste seu ranking abaixo para começar.")
        else:
            atual = salvo.ranking
            origem = (f"Calculado no fim do dia {data_curta(salvo.apos_o_dia)}" if salvo.apos_o_dia
                      else "Definido por ajuste manual")
            self.cartao_atual.atualizar(atual, origem)
            self._elo.set(atual.elo)  # sugestão para um eventual ajuste
            self._rr.set(str(atual.rr))
        self._mostrar_emblema_ajuste()

        limite = date.today().toordinal() - 6
        rr_recente = [e.variacao for e in evolucao if e.variacao is not None and e.data.toordinal() >= limite]
        self._cartao_semana.atualizar(f"{sum(rr_recente):+d} RR" if rr_recente else "—",
                                      f"em {len(rr_recente)} dia(s) com RR registrado")

        if definicoes:
            ultima = definicoes[-1]
            self._cartao_definicao.atualizar(ultima.ranking.elo, f"{ultima.rr} RR em {data_curta(ultima.data)}",
                                             imagem=imagem_rank(ultima.ranking.elo, 36))
        else:
            self._cartao_definicao.atualizar("—", "nenhum ainda")

        self._tabela_evolucao.preencher([
            (("★ " if e.redefinido else "") + data_tabela(e.data), e.inicio.texto,
             f"{e.variacao:+d}" if e.variacao is not None else "—", e.final.texto)
            for e in reversed(evolucao)
        ])
        self._definicoes = definicoes
        self._tabela_definicoes.preencher(
            [(data_curta(d.data), d.ranking.texto,
              f"{d.definido_em:%d/%m/%Y %H:%M}" if d.definido_em else "—") for d in reversed(definicoes)],
            ids=[d.data.isoformat() for d in reversed(definicoes)],
        )

    def _mostrar_emblema_ajuste(self) -> None:
        self._emblema_ajuste.configure(image=imagem_rank(self._elo.get(), 52))

    def _salvar(self) -> None:
        elo = self._elo.get()
        try:
            rr = conversao.inteiro(self._rr.get(), "RR")
            data = datetime.strptime(self._data.get(), "%d/%m/%Y").date()
        except conversao.ErroConversao as erro:
            messagebox.showwarning("Revise os campos", str(erro), parent=self)
            return
        except ValueError:
            messagebox.showwarning("Revise os campos", "Data: use o formato DD/MM/AAAA.", parent=self)
            return
        erros = erros_definicao(elo, rr)
        if data > date.today():
            erros.append("A data não pode estar no futuro.")
        if erros:
            messagebox.showwarning("Revise os campos", "\n".join(f"• {e}" for e in erros), parent=self)
            return
        self._repositorio_ranking.definir(data, elo, rr)
        self.ao_exibir()

    def _remover(self) -> None:
        selecao = self._tabela_definicoes.arvore.selection()
        if not selecao:
            messagebox.showinfo("Remover", "Selecione um ajuste na tabela.", parent=self)
            return
        data = date.fromisoformat(selecao[0])
        if messagebox.askyesno("Remover ajuste",
                               f"Remover o ajuste que vale a partir de {data_curta(data)}?", parent=self):
            self._repositorio_ranking.remover(data)
            self.ao_exibir()
