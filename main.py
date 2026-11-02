"""Ponto de entrada do aplicativo."""

import customtkinter as ctk

from app.config import garantir_pastas
from app.storage import RepositorioDiario
from app.ui.janela_principal import JanelaPrincipal


def main() -> None:
    garantir_pastas()
    ctk.set_appearance_mode("dark")
    janela = JanelaPrincipal(RepositorioDiario())
    janela.mainloop()


if __name__ == "__main__":
    main()
