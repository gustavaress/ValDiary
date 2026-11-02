"""Blocos de formulário. Todos os campos têm get() e set(valor), e set(None) limpa."""

import customtkinter as ctk

from app.ui import tema
from app.ui.componentes.seletor import SeletorNota
from app.ui.componentes.seletor_hora import SeletorHora


def _rotulo(master, texto: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(master, text=texto, font=tema.fonte_pequena(),
                        text_color=tema.COR_TEXTO_SECUNDARIO)


def nova_entrada(master, largura: int, placeholder: str = "") -> ctk.CTkEntry:
    return ctk.CTkEntry(master, width=largura, height=34, placeholder_text=placeholder,
                        fg_color=tema.COR_FUNDO, border_color=tema.COR_BORDA,
                        text_color=tema.COR_TEXTO, font=tema.fonte_normal())


class Secao(ctk.CTkFrame):
    """Cartão com título. Os campos vão dentro de self.conteudo."""

    def __init__(self, master, titulo: str, descricao: str = ""):
        super().__init__(master, fg_color=tema.COR_CARTAO, corner_radius=12,
                         border_width=1, border_color=tema.COR_BORDA)
        ctk.CTkLabel(self, text=titulo, font=tema.fonte_secao(),
                     text_color=tema.COR_TEXTO).pack(anchor="w", padx=18, pady=(14, 0))
        if descricao:
            _rotulo(self, descricao).pack(anchor="w", padx=18)
        self.conteudo = ctk.CTkFrame(self, fg_color="transparent")
        self.conteudo.pack(fill="x", padx=18, pady=(8, 16))


class CampoEntrada(ctk.CTkFrame):
    def __init__(self, master, rotulo: str, largura: int = 120, placeholder: str = ""):
        super().__init__(master, fg_color="transparent")
        _rotulo(self, rotulo).pack(anchor="w")
        self.entrada = nova_entrada(self, largura, placeholder)
        self.entrada.pack(anchor="w")

    def get(self) -> str:
        return self.entrada.get().strip()

    def set(self, valor: str | None) -> None:
        # Um campo desabilitado não aceita texto; liberamos só durante a troca.
        estado = self.entrada.cget("state")
        self.entrada.configure(state="normal")
        self.entrada.delete(0, "end")
        if valor:
            self.entrada.insert(0, valor)
        self.entrada.configure(state=estado)

    def ao_digitar(self, callback) -> None:
        self.entrada.bind("<KeyRelease>", lambda _: callback(), add="+")

    def habilitar(self, ativo: bool) -> None:
        self.entrada.configure(state="normal" if ativo else "disabled",
                               text_color=tema.COR_TEXTO if ativo else tema.COR_TEXTO_SECUNDARIO)


class CampoHorario(ctk.CTkFrame):
    def __init__(self, master, rotulo: str, ao_mudar=None):
        super().__init__(master, fg_color="transparent")
        _rotulo(self, rotulo).pack(anchor="w")
        self.seletor = SeletorHora(self, ao_mudar=ao_mudar)
        self.seletor.pack(anchor="w")

    def get(self) -> str:
        return self.seletor.get()

    def set(self, valor: str | None) -> None:
        self.seletor.set(valor)

    def habilitar(self, ativo: bool) -> None:
        self.seletor.habilitar(ativo)


class CampoMarcacao(ctk.CTkFrame):
    """Caixa de marcação com get() -> bool, no mesmo padrão dos outros campos.

    Envolve um CTkCheckBox em vez de herdar dele: o CTkCheckBox já tem um
    método set() interno com outra assinatura, que não podemos sobrescrever.
    """

    def __init__(self, master, rotulo: str, ao_mudar=None):
        super().__init__(master, fg_color="transparent")
        self._ao_mudar = ao_mudar
        self.caixa = ctk.CTkCheckBox(self, text=rotulo, font=tema.fonte_normal(), text_color=tema.COR_TEXTO,
                                     fg_color=tema.COR_DESTAQUE, hover_color=tema.COR_DESTAQUE_HOVER,
                                     border_color=tema.COR_BORDA, command=ao_mudar)
        self.caixa.pack(anchor="w")

    def get(self) -> bool:
        return bool(self.caixa.get())

    def set(self, valor: bool | None) -> None:
        self.caixa.select() if valor else self.caixa.deselect()
        if self._ao_mudar:
            self._ao_mudar()


class CampoNota(ctk.CTkFrame):
    def __init__(self, master, rotulo: str):
        super().__init__(master, fg_color="transparent")
        _rotulo(self, rotulo).pack(anchor="w")
        self.seletor = SeletorNota(self)
        self.seletor.pack(anchor="w")

    def get(self) -> int | None:
        return self.seletor.get()

    def set(self, valor: int | None) -> None:
        self.seletor.set(valor)


class CampoTextoLongo(ctk.CTkFrame):
    def __init__(self, master, rotulo: str, altura: int = 140):
        super().__init__(master, fg_color="transparent")
        if rotulo:
            _rotulo(self, rotulo).pack(anchor="w")
        self.caixa = ctk.CTkTextbox(self, height=altura, fg_color=tema.COR_FUNDO,
                                    border_color=tema.COR_BORDA, border_width=1,
                                    text_color=tema.COR_TEXTO, font=tema.fonte_normal(),
                                    wrap="word")
        self.caixa.pack(fill="x")

    def get(self) -> str:
        return self.caixa.get("1.0", "end-1c").strip()

    def set(self, valor: str | None) -> None:
        self.caixa.delete("1.0", "end")
        if valor:
            self.caixa.insert("1.0", valor)
