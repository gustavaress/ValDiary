"""Aba Partidas: aquecimento, resumo do dia (com ranking) e a lista de partidas."""

import customtkinter as ctk

from app.models.ranking import aplicar_partidas, variacao_real
from app.ui import conversao, tema
from app.ui.componentes import CampoTextoLongo, ListaPartidas, Secao, SeletorBotoes
from app.ui.componentes.emblema_rank import imagem_rank
from app.ui.formatacao import numero
from app.ui.mapeamento_registro import resumo_ao_vivo


class AbaPartidas:
    def __init__(self, tela, area):
        self._tela = tela
        self._campos = tela.campos

        secao = Secao(area, "Aquecimento", "Aquecimento logo antes das partidas (range, DM, bots...).")
        secao.pack(fill="x", pady=(0, 10))
        linha = ctk.CTkFrame(secao.conteudo, fg_color="transparent")
        linha.pack(anchor="w", fill="x")
        ctk.CTkLabel(linha, text="Fez aquecimento?", font=tema.fonte_pequena(),
                     text_color=tema.COR_TEXTO_SECUNDARIO).pack(anchor="w")
        self._campos["aquecimento"] = SeletorBotoes(linha, [("sim", "Sim"), ("nao", "Não")], largura_botao=60,
                                                    ao_mudar=lambda _: self._atualizar_aquecimento())
        self._campos["aquecimento"].pack(anchor="w", pady=(0, 8))
        self._campos["aquecimento_descricao"] = CampoTextoLongo(secao.conteudo, "Como foi o aquecimento", altura=80)
        self._campos["aquecimento_descricao"].pack(fill="x")

        secao = Secao(area, "Resumo do dia", "Calculado automaticamente a partir das partidas abaixo. "
                                             "O ranking vem da aba Ranking + o RR de cada partida, na ordem.")
        secao.pack(fill="x", pady=10)
        # Ranking no início do dia -> ranking com as partidas abaixo, cada um com o emblema.
        linha = ctk.CTkFrame(secao.conteudo, fg_color="transparent")
        linha.pack(anchor="w", pady=(0, 8))
        self.rotulo_ranking = ctk.CTkLabel(linha, text="", justify="left", anchor="w", compound="left",
                                           font=tema.fonte_normal(), text_color=tema.COR_TEXTO_SECUNDARIO)
        self.rotulo_ranking.pack(side="left")
        self.rotulo_ranking_final = ctk.CTkLabel(linha, text="", justify="left", anchor="w", compound="left",
                                                 font=tema.fonte_forte(), text_color=tema.COR_TEXTO)
        self.rotulo_ranking_final.pack(side="left", padx=(14, 0))
        self.rotulo_resumo = ctk.CTkLabel(secao.conteudo, text="", justify="left", anchor="w",
                                          font=tema.fonte_normal(), text_color=tema.COR_TEXTO)
        self.rotulo_resumo.pack(anchor="w")
        self._rotulo_legado = ctk.CTkLabel(secao.conteudo, text="", justify="left", anchor="w", wraplength=760,
                                           font=tema.fonte_pequena(), text_color=tema.COR_AVISO)
        self._rotulo_legado.pack(anchor="w", pady=(6, 0))

        secao = Secao(area, "Partidas", "Uma partida por cartão. Clique em \"Escolher agente\" para abrir a "
                                        "bandeja de agentes.")
        secao.pack(fill="x", pady=10)
        self._campos["partidas"] = ListaPartidas(secao.conteudo, ao_mudar=self.atualizar)
        self._campos["partidas"].pack(fill="x")

    def atualizar(self) -> None:
        self._atualizar_aquecimento()
        self._atualizar_resumo()

    def _atualizar_aquecimento(self) -> None:
        self._campos["aquecimento_descricao"].habilitar(self._campos["aquecimento"].get() == "sim")

    def mostrar_ranking_inicio(self) -> None:
        ranking = self._tela.ranking_inicio
        if ranking is None:
            self.rotulo_ranking.configure(
                text="Ranking não calculado: defina seu elo e RR na aba Ranking (menu ao lado).", image=None)
        else:
            self.rotulo_ranking.configure(text=f"  Início do dia: {ranking.texto}",
                                          image=imagem_rank(ranking.elo, 36))

    def _atualizar_resumo(self) -> None:
        formulario = self._tela.ler()
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
            self.rotulo_resumo.configure(text="\n".join(linhas), text_color=tema.COR_TEXTO)
        else:
            self.rotulo_resumo.configure(text="Adicione partidas para ver o resumo do dia.",
                                         text_color=tema.COR_TEXTO_SECUNDARIO)

        tem_partidas = any(p.get("agente") or p.get("abates") or p.get("resultado")
                           for p in formulario.get("partidas") or [])
        if self._tela.legado and not tem_partidas:
            self._rotulo_legado.configure(text=(
                "Este dia foi registrado antes do registro por partida: o resumo acima vem dos totais "
                "digitados na época. Se você adicionar partidas, elas passam a valer no lugar desses totais."))
        else:
            self._rotulo_legado.configure(text="")

    def _texto_ranking(self, formulario: dict, rr_do_dia: int | None) -> str:
        """Devolve "RR das partidas: -20, +17" e mostra, ao lado do ranking do
        início do dia, o ranking com essas partidas:
        "→  Ascendente 3 · 17 RR  (+16 RR)"
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
        inicio = self._tela.ranking_inicio
        linhas = []
        self.rotulo_ranking_final.configure(text="", image=None)
        if variacoes:
            partidas = ", ".join(f"{v:+d}" for v in variacoes)
            # Sem ranking definido não dá para aplicar a proteção: mostramos a soma.
            sufixo = "" if inicio is not None else f"  (soma {rr_do_dia:+d})"
            linhas.append(f"RR das partidas: {partidas}{sufixo}")
        if inicio is not None and variacoes:
            final = aplicar_partidas(inicio, variacoes)
            self.rotulo_ranking_final.configure(
                text=f"  {final.texto}  ({variacao_real(inicio, final):+d} RR)",
                image=imagem_rank(final.elo, 36))
            self.rotulo_ranking.configure(text=f"  Início do dia: {inicio.texto}   →")
        elif inicio is not None:
            self.rotulo_ranking.configure(text=f"  Início do dia: {inicio.texto}")
        return "\n".join(linhas)
