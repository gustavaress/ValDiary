"""Aba Aim Routine: se fez o treino de mira, o que fez e por quanto tempo."""

from tkinter import messagebox

import customtkinter as ctk

from app.models import ExercicioAim
from app.ui import tema
from app.ui.componentes import CampoEntrada, CampoTextoLongo, ListaExercicios, Secao, SeletorBotoes
from app.ui.componentes.botoes import botao_secundario


class AbaAim:
    def __init__(self, tela, area):
        self._tela = tela
        self._campos = tela.campos

        secao = Secao(area, "Aim Routine de hoje",
                      "A lista de exercícios vem da sua rotina padrão: marque o que fez e ajuste se fez diferente.")
        secao.pack(fill="x", pady=(0, 10))
        linha = ctk.CTkFrame(secao.conteudo, fg_color="transparent")
        linha.pack(anchor="w", fill="x")
        bloco = ctk.CTkFrame(linha, fg_color="transparent")
        bloco.pack(side="left", padx=(0, 24))
        ctk.CTkLabel(bloco, text="Fez a aim routine hoje?", font=tema.fonte_pequena(),
                     text_color=tema.COR_TEXTO_SECUNDARIO).pack(anchor="w")
        self._campos["aim_feita"] = SeletorBotoes(bloco, [("sim", "Sim"), ("nao", "Não")], largura_botao=60,
                                                  ao_mudar=lambda _: self.atualizar())
        self._campos["aim_feita"].pack(anchor="w")
        self._campos["aim_duracao"] = CampoEntrada(linha, "Duração total (minutos)", largura=110, placeholder="45")
        self._campos["aim_duracao"].pack(side="left", padx=(0, 24))
        self._contador = ctk.CTkLabel(linha, text="", font=tema.fonte_display(26), text_color=tema.COR_TEXTO)
        self._contador.pack(side="left", anchor="s")

        secao = Secao(area, "Exercícios")
        secao.pack(fill="x", pady=10)
        self._campos["aim_exercicios"] = ListaExercicios(secao.conteudo, ao_mudar=self.atualizar)
        self._campos["aim_exercicios"].pack(fill="x")
        botoes = ctk.CTkFrame(secao.conteudo, fg_color="transparent")
        botoes.pack(anchor="w", pady=(10, 0))
        botao_secundario(botoes, "Salvar como minha rotina padrão", self._salvar_padrao, largura=250,
                         altura=32).pack(side="left", padx=(0, 8))
        botao_secundario(botoes, "Restaurar rotina padrão", self._restaurar_padrao, largura=200,
                         altura=32).pack(side="left")

        secao = Secao(area, "Observações do treino")
        secao.pack(fill="x", pady=10)
        self._campos["aim_observacoes"] = CampoTextoLongo(secao.conteudo, "", altura=110)
        self._campos["aim_observacoes"].pack(fill="x")

    def atualizar(self) -> None:
        lista = self._campos["aim_exercicios"]
        total = len(lista.get())
        self._contador.configure(text=f"{lista.total_feitos()} / {total} EXERCÍCIOS" if total else "")

    def _salvar_padrao(self) -> None:
        exercicios = [ExercicioAim(e["nome"], e["meta"] or None) for e in self._campos["aim_exercicios"].get()]
        if not exercicios:
            messagebox.showinfo("Rotina padrão", "Adicione pelo menos um exercício.", parent=self._tela)
            return
        self._tela.janela.repositorio_aim.salvar_padrao(exercicios)
        messagebox.showinfo("Rotina padrão", "Rotina padrão atualizada. Ela aparecerá nos próximos dias.",
                            parent=self._tela)

    def _restaurar_padrao(self) -> None:
        self._campos["aim_exercicios"].set(itens_da_rotina_padrao(self._tela))
        self.atualizar()


def itens_da_rotina_padrao(tela) -> list[dict]:
    """Rotina padrão no formato do formulário (nada marcado como feito)."""
    return [{"nome": e.nome, "meta": e.meta or "", "feito": False}
            for e in tela.janela.repositorio_aim.carregar_padrao()]
