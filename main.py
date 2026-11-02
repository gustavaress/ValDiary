"""Ponto de entrada do aplicativo."""

import customtkinter as ctk

from app.config import NOME_APP, garantir_pastas


def main() -> None:
    garantir_pastas()

    ctk.set_appearance_mode("dark")
    janela = ctk.CTk()
    janela.title(NOME_APP)
    janela.geometry("1100x700")

    # Placeholder até a Etapa 3 (esqueleto da interface).
    ctk.CTkLabel(janela, text=NOME_APP, font=ctk.CTkFont(size=24, weight="bold")).pack(expand=True)

    janela.mainloop()


if __name__ == "__main__":
    main()
