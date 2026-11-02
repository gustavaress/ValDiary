"""Seletor de horário com menus de hora e minuto (sem digitação livre)."""

import customtkinter as ctk

from app.ui import tema

VAZIO = "--"
HORAS = [VAZIO] + [f"{h:02d}" for h in range(24)]
MINUTOS = [VAZIO] + [f"{m:02d}" for m in range(0, 60, 5)]


class SeletorHora(ctk.CTkFrame):
    """Dois menus (hora e minuto, de 5 em 5). get() devolve "HH:MM" ou "" se vazio."""

    def __init__(self, master, ao_mudar=None):
        super().__init__(master, fg_color="transparent")
        self._ao_mudar = ao_mudar
        estilo = dict(width=66, height=34, dynamic_resizing=False, font=tema.fonte_normal(),
                      fg_color=tema.COR_FUNDO, button_color=tema.COR_FUNDO,
                      button_hover_color=tema.COR_BORDA, dropdown_fg_color=tema.COR_CARTAO,
                      text_color=tema.COR_TEXTO, command=lambda _: self._mudou())
        self._hora = ctk.CTkOptionMenu(self, values=HORAS, **estilo)
        self._hora.pack(side="left")
        ctk.CTkLabel(self, text=":", font=tema.fonte_secao(), text_color=tema.COR_TEXTO_SECUNDARIO,
                     width=10).pack(side="left", padx=2)
        self._minuto = ctk.CTkOptionMenu(self, values=MINUTOS, **estilo)
        self._minuto.pack(side="left")

    def _mudou(self) -> None:
        # Escolheu a hora sem minuto: completa com 00. Limpou a hora: limpa o minuto.
        if self._hora.get() != VAZIO and self._minuto.get() == VAZIO:
            self._minuto.set("00")
        if self._hora.get() == VAZIO:
            self._minuto.set(VAZIO)
        if self._ao_mudar:
            self._ao_mudar()

    def get(self) -> str:
        hora, minuto = self._hora.get(), self._minuto.get()
        if hora == VAZIO:
            return ""
        return f"{hora}:{minuto if minuto != VAZIO else '00'}"

    def set(self, valor: str | None) -> None:
        if not valor:
            self._hora.set(VAZIO)
            self._minuto.set(VAZIO)
            return
        hora, minuto = valor.split(":")
        # Registros antigos podem ter minutos fora do passo de 5 (ex.: 07:47).
        valores = MINUTOS if minuto in MINUTOS else [VAZIO] + sorted(set(MINUTOS[1:]) | {minuto})
        self._minuto.configure(values=valores)
        self._hora.set(hora)
        self._minuto.set(minuto)

    def habilitar(self, ativo: bool) -> None:
        estado = "normal" if ativo else "disabled"
        self._hora.configure(state=estado)
        self._minuto.configure(state=estado)
