"""Tela Ranking: definir o elo/RR e acompanhar a evolução calculada."""

from datetime import date, datetime
from tkinter import messagebox

import customtkinter as ctk

from app.analysis.ranking import evolucao_ranking
from app.models.ranking import ELOS, erros_definicao
from app.storage import ArquivoCorrompidoError
from app.ui import conversao, tema
from app.ui.componentes.botoes import botao_primario, botao_secundario
from app.ui.componentes import CampoEntrada, CampoOpcao, CartaoInfo, Secao, Tabela
from app.ui.formatacao import data_curta, data_tabela
from app.ui.telas.base import TelaBase


class TelaRanking(TelaBase):
    titulo = "Ranking"
    subtitulo = "Seu ranking é atualizado sozinho a cada dia registrado, com o RR de cada partida."

    def montar(self) -> None:
        area = ctk.CTkScrollableFrame(self.corpo, fg_color="transparent")
        area.pack(fill="both", expand=True)
        area.grid_columnconfigure((0, 1, 2), weight=1, uniform="col")

        self._cartao_atual = CartaoInfo(area, "Seu ranking")
        self._cartao_semana = CartaoInfo(area, "RR nos últimos 7 dias")
        self._cartao_definicao = CartaoInfo(area, "Último ajuste manual")
        for coluna, cartao in enumerate((self._cartao_atual, self._cartao_semana, self._cartao_definicao)):
            cartao.grid(row=0, column=coluna, sticky="nsew", padx=6, pady=6)

        secao = Secao(area, "Ajustar ranking manualmente",
                      "Só é preciso ao começar a usar o app ou se o ranking ficar diferente do jogo. "
                      "Vale a partir do INÍCIO do dia escolhido.")
        secao.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=6, pady=6)
        linha = ctk.CTkFrame(secao.conteudo, fg_color="transparent")
        linha.pack(anchor="w")
        self._elo = CampoOpcao(linha, "Elo", ELOS, largura=170)
        self._rr = CampoEntrada(linha, "RR (pontos)", largura=90, placeholder="0 a 99")
        self._data = CampoEntrada(linha, "Vale a partir de", largura=120, placeholder="DD/MM/AAAA")
        for campo in (self._elo, self._rr, self._data):
            campo.pack(side="left", padx=(0, 16))
        botao_primario(linha, "Salvar ranking", self._salvar, largura=160, altura=34).pack(side="left", anchor="s")

        secao = Secao(area, "Evolução dia a dia",
                      "RR de cada partida aplicado na ordem, com proteção contra rebaixamento. "
                      "★ = um ajuste manual passou a valer.")
        secao.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=6, pady=6)
        self._tabela_evolucao = Tabela(secao.conteudo, [
            ("data", "Data", 130, "w"), ("inicio", "Início do dia", 200, "w"),
            ("rr", "RR do dia", 90, "center"), ("fim", "Fim do dia", 200, "w"),
        ], altura_automatica=True)
        self._tabela_evolucao.pack(fill="x")

        secao = Secao(area, "Ajustes manuais feitos")
        secao.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=6, pady=6)
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
            self._cartao_atual.atualizar("—", "ajuste seu ranking abaixo para começar")
        else:
            atual = salvo.ranking
            origem = (f"fim do dia {data_curta(salvo.apos_o_dia)}" if salvo.apos_o_dia
                      else "ajuste manual")
            self._cartao_atual.atualizar(atual.elo, f"{atual.rr} RR  ·  {origem}")
            self._elo.set(atual.elo)  # sugestão para um eventual ajuste
            self._rr.set(str(atual.rr))

        limite = date.today().toordinal() - 6
        rr_recente = [e.variacao for e in evolucao if e.variacao is not None and e.data.toordinal() >= limite]
        self._cartao_semana.atualizar(f"{sum(rr_recente):+d} RR" if rr_recente else "—",
                                      f"em {len(rr_recente)} dia(s) com RR registrado")

        if definicoes:
            ultima = definicoes[-1]
            self._cartao_definicao.atualizar(ultima.ranking.elo, f"{ultima.rr} RR em {data_curta(ultima.data)}")
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
