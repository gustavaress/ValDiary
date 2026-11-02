"""Ponto de entrada do aplicativo."""

from app.config import garantir_pastas
from app.storage import RepositorioDiario
from app.ui.janela_principal import JanelaPrincipal


def main() -> None:
    garantir_pastas()
    janela = JanelaPrincipal(RepositorioDiario())
    janela.mainloop()


if __name__ == "__main__":
    main()
