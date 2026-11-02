"""Tela inicial: resumo de hoje e números gerais."""

from datetime import date

import customtkinter as ctk

from app.storage.semanas import semana_da_data
from app.ui import tema
from app.ui.componentes import CartaoInfo
from app.ui.formatacao import data_extensa
from app.ui.telas.base import TelaBase


class TelaInicio(TelaBase):
    titulo = "Início"
    subtitulo = "Resumo do seu diário"

    def montar(self) -> None:
        self.corpo.grid_columnconfigure((0, 1, 2), weight=1, uniform="cartoes")

        self._hoje = CartaoInfo(self.corpo, "Hoje")
        self._hoje.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._semana = CartaoInfo(self.corpo, "Esta semana")
        self._semana.grid(row=0, column=1, sticky="nsew", padx=8)
        self._total = CartaoInfo(self.corpo, "Total registrado")
        self._total.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

        self._botao = ctk.CTkButton(
            self.corpo, height=44, width=260, font=tema.fonte_secao(),
            fg_color=tema.COR_DESTAQUE, hover_color=tema.COR_DESTAQUE_HOVER,
            command=lambda: self.janela.mostrar_tela("registro"),
        )
        self._botao.grid(row=1, column=0, sticky="w", pady=24)

    def ao_exibir(self) -> None:
        hoje = date.today()
        registros, _ = self.repositorio.carregar_todos()
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

        semana_atual = semana_da_data(hoje)
        dias_semana = sum(1 for r in registros if r.semana_iso == semana_atual)
        self._semana.atualizar(f"{dias_semana}/7", f"dias registrados na semana {semana_atual[1]}")

        semanas = len(self.repositorio.listar_semanas())
        self._total.atualizar(str(len(registros)),
                              f"dias em {semanas} semana{'s' if semanas != 1 else ''}")
