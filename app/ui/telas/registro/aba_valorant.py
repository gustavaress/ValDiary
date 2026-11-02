"""Aba Valorant: sessão (jogou? horários) e autoavaliação."""

import customtkinter as ctk

from app.analysis.medicacao import medicamentos_antes_do_horario
from app.ui import tema
from app.ui.componentes import CampoHorario, CampoNota, Secao, SeletorBotoes


class AbaValorant:
    def __init__(self, tela, area):
        self._campos = tela.campos

        secao = Secao(area, "Sessão", "As partidas em si são registradas na aba Partidas.")
        secao.pack(fill="x", pady=(0, 10))
        rotulo = ctk.CTkFrame(secao.conteudo, fg_color="transparent")
        ctk.CTkLabel(rotulo, text="Jogou hoje?", font=tema.fonte_pequena(),
                     text_color=tema.COR_TEXTO_SECUNDARIO).pack(anchor="w")
        jogou = SeletorBotoes(rotulo, [("sim", "Sim"), ("nao", "Não")], largura_botao=60)
        jogou.pack(anchor="w")
        rotulo.grid(row=0, column=0, sticky="w", padx=(0, 18), pady=4)
        self._campos["jogou"] = jogou
        inicio = CampoHorario(secao.conteudo, "Começou às", ao_mudar=self.atualizar)
        fim = CampoHorario(secao.conteudo, "Parou às")
        inicio.grid(row=0, column=1, sticky="w", padx=(0, 18), pady=4)
        fim.grid(row=0, column=2, sticky="w", pady=4)
        self._campos["jogo_inicio"] = inicio
        self._campos["jogo_fim"] = fim
        # Cruzamento com a aba Rotina: quanto tempo antes do jogo cada medicamento foi tomado.
        self.rotulo_medicacao = ctk.CTkLabel(secao.conteudo, text="", justify="left", anchor="w",
                                             font=tema.fonte_pequena(), text_color=tema.COR_TEXTO_SECUNDARIO)
        self.rotulo_medicacao.grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))

        secao = Secao(area, "Autoavaliação")
        secao.pack(fill="x", pady=10)
        tela.grade(secao, [
            ("mira", CampoNota(secao.conteudo, "Sensação da mira")),
            ("movimentacao", CampoNota(secao.conteudo, "Qualidade da movimentação")),
            ("tomada_decisao", CampoNota(secao.conteudo, "Tomada de decisão")),
            ("concentracao", CampoNota(secao.conteudo, "Concentração")),
            ("consistencia", CampoNota(secao.conteudo, "Consistência")),
        ], colunas=1)

    def atualizar(self) -> None:
        """Refaz o cruzamento medicamento x início do jogo."""
        inicio = self._campos["jogo_inicio"].get()
        medicamentos = [(m.get("nome"), m.get("horario")) for m in self._campos["medicamentos"].get()]
        antes = medicamentos_antes_do_horario(inicio, medicamentos)
        if antes:
            texto = "Medicamentos antes do jogo:  " + "   ·   ".join(m.texto for m in antes)
        elif inicio and any(h for _, h in medicamentos):
            texto = "Nenhum medicamento foi tomado antes do início do jogo."
        else:
            texto = ""
        self.rotulo_medicacao.configure(text=texto)
