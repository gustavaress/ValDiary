"""Checklist de exercícios da aim routine: marcar o que foi feito e ajustar nome/meta."""

import customtkinter as ctk

from app.ui import tema
from app.ui.componentes.botoes import botao_icone, botao_secundario
from app.ui.componentes.formulario import nova_entrada


class ListaExercicios(ctk.CTkFrame):
    """get() -> [{"nome", "meta", "feito"}, ...]; linhas sem nome são ignoradas."""

    def __init__(self, master, ao_mudar=None):
        super().__init__(master, fg_color="transparent")
        self._ao_mudar = ao_mudar
        self._linhas: list[tuple[ctk.CTkFrame, ctk.CTkCheckBox, ctk.CTkEntry, ctk.CTkEntry]] = []
        self._area = ctk.CTkFrame(self, fg_color="transparent")
        self._area.pack(fill="x")
        botao_secundario(self, "+ Exercício", lambda: self.adicionar(), largura=130, altura=32).pack(
            anchor="w", pady=(6, 0))

    def adicionar(self, valores: dict | None = None) -> None:
        valores = valores or {}
        linha = ctk.CTkFrame(self._area, fg_color="transparent")
        linha.pack(fill="x", pady=2)
        feito = ctk.CTkCheckBox(linha, text="", width=28, command=self._mudou)
        feito.pack(side="left", padx=(0, 8))
        if valores.get("feito"):
            feito.select()
        nome = nova_entrada(linha, 300, "Exercício")
        nome.pack(side="left", padx=(0, 6))
        meta = nova_entrada(linha, 200, "Quantidade / tempo")
        meta.pack(side="left", padx=(0, 6))
        for entrada, valor in ((nome, valores.get("nome")), (meta, valores.get("meta"))):
            if valor:
                entrada.insert(0, valor)
        botao_icone(linha, "✕", lambda: self._remover(linha)).pack(side="left")
        self._linhas.append((linha, feito, nome, meta))

    def _remover(self, linha: ctk.CTkFrame) -> None:
        self._linhas = [item for item in self._linhas if item[0] is not linha]
        linha.destroy()
        self._mudou()

    def _mudou(self) -> None:
        if self._ao_mudar:
            self._ao_mudar()

    def total_feitos(self) -> int:
        return sum(1 for _, feito, nome, _ in self._linhas if feito.get() and nome.get().strip())

    def get(self) -> list[dict]:
        return [{"nome": nome.get().strip(), "meta": meta.get().strip(), "feito": bool(feito.get())}
                for _, feito, nome, meta in self._linhas if nome.get().strip()]

    def set(self, itens: list[dict] | None) -> None:
        for linha, *_ in self._linhas:
            linha.destroy()
        self._linhas = []
        for item in itens or []:
            self.adicionar(item)
