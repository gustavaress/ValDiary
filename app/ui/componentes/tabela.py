"""Tabela estilizada (Treeview do Tkinter com o tema escuro do app).

O CustomTkinter não tem tabela própria. O Treeview aguenta milhares de linhas
sem ficar lento; só precisamos estilizá-lo para combinar com o resto.
"""

from tkinter import ttk

import customtkinter as ctk

from app.ui import tema

_ESTILO = "Diario.Treeview"


def _configurar_estilo(widget, escala: float) -> None:
    estilo = ttk.Style(widget)
    estilo.theme_use("clam")
    estilo.configure(_ESTILO, background=tema.COR_CARTAO, fieldbackground=tema.COR_CARTAO,
                     foreground=tema.COR_TEXTO, borderwidth=0, rowheight=int(32 * escala),
                     font=(tema.FONTE_TEXTO, 10))
    estilo.configure(f"{_ESTILO}.Heading", background=tema.COR_CAMPO,
                     foreground=tema.COR_TEXTO_SECUNDARIO, borderwidth=0, relief="flat",
                     font=(tema.FONTE_TEXTO_FORTE, 9), padding=(6, int(7 * escala)))
    estilo.map(_ESTILO, background=[("selected", tema.COR_DESTAQUE_SUAVE)],
               foreground=[("selected", tema.COR_TEXTO)])
    estilo.map(f"{_ESTILO}.Heading", background=[("active", tema.COR_CARTAO_HOVER)])
    estilo.layout(_ESTILO, [("Treeview.treearea", {"sticky": "nswe"})])


class Tabela(ctk.CTkFrame):
    def __init__(self, master, colunas: list[tuple[str, str, int, str]], altura_automatica: bool = False):
        """colunas: (chave, título, largura, alinhamento "w"/"center"/"e").

        altura_automatica=True: a tabela cresce para mostrar todas as linhas
        (sem barra de rolagem). Útil dentro de telas que já rolam.
        """
        super().__init__(master, fg_color="transparent")
        self._altura_automatica = altura_automatica
        escala = ctk.ScalingTracker.get_widget_scaling(self)
        _configurar_estilo(self, escala)

        self.arvore = ttk.Treeview(self, style=_ESTILO, show="headings", selectmode="browse",
                                   columns=[c[0] for c in colunas])
        for chave, titulo, largura, alinhamento in colunas:
            self.arvore.heading(chave, text=titulo.upper(), anchor=alinhamento)
            self.arvore.column(chave, width=int(largura * escala), minwidth=40, anchor=alinhamento,
                               stretch=True)
        self.arvore.tag_configure("par", background=tema.COR_CARTAO_HOVER)
        self.arvore.pack(side="left", fill="both", expand=True)

        if not altura_automatica:
            rolagem = ctk.CTkScrollbar(self, command=self.arvore.yview)
            rolagem.pack(side="right", fill="y", padx=(4, 0))
            self.arvore.configure(yscrollcommand=rolagem.set)

    def preencher(self, linhas: list[tuple], ids: list[str] | None = None) -> None:
        self.arvore.delete(*self.arvore.get_children())
        for i, valores in enumerate(linhas):
            self.arvore.insert("", "end", iid=ids[i] if ids else None, values=valores,
                               tags=("par",) if i % 2 else ())
        if self._altura_automatica:
            self.arvore.configure(height=max(1, len(linhas)))
