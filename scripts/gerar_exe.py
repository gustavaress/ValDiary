"""Gera o executável do ValDiary para Windows (pasta dist/ValDiary/ValDiary.exe).

    python scripts/gerar_exe.py

Formato "pasta" (onedir): abre bem mais rápido que um .exe único, porque não
precisa descompactar pandas/Matplotlib a cada abertura. Os dados do usuário
ficam numa pasta "dados" ao lado do ValDiary.exe (ver app/config.py).

Requer o PyInstaller instalado: pip install -r requirements-dev.txt
"""

from pathlib import Path

import PyInstaller.__main__

RAIZ = Path(__file__).resolve().parent.parent
SEPARADOR = ";"  # separador de --add-data no Windows

# (origem no projeto, destino dentro do pacote). As imagens originais dos
# agentes (assets/agentes/originais, ~22 MB) ficam de fora de propósito.
RECURSOS = [
    ("assets/fontes", "assets/fontes"),
    ("assets/icone.ico", "assets"),
    ("assets/agentes/agentes.json", "assets/agentes"),
]


def main() -> None:
    dados = [f"{RAIZ / origem}{SEPARADOR}{destino}" for origem, destino in RECURSOS]
    dados += [f"{png}{SEPARADOR}assets/agentes" for png in sorted((RAIZ / "assets/agentes").glob("*.png"))]

    argumentos = [
        str(RAIZ / "main.py"),
        "--name=ValDiary",
        "--onedir",
        "--windowed",                      # sem janela de terminal
        f"--icon={RAIZ / 'assets/icone.ico'}",
        "--collect-data=customtkinter",    # temas e imagens internas do CustomTkinter
        f"--distpath={RAIZ / 'dist'}",
        f"--workpath={RAIZ / 'build'}",
        f"--specpath={RAIZ / 'build'}",
        "--noconfirm",
        "--clean",
        # Bibliotecas que o app não usa, mas que o PyInstaller puxaria junto.
        "--exclude-module=pytest",
        "--exclude-module=IPython",
        "--exclude-module=PyQt5",
        "--exclude-module=PySide6",
    ]
    for item in dados:
        argumentos.append(f"--add-data={item}")

    PyInstaller.__main__.run(argumentos)

    pasta = RAIZ / "dist" / "ValDiary"
    tamanho = sum(f.stat().st_size for f in pasta.rglob("*") if f.is_file()) / 1024 / 1024
    print(f"\nPronto: {pasta / 'ValDiary.exe'}  ({tamanho:.0f} MB no total)")
    print("Os dados serão criados em", pasta / "dados")


if __name__ == "__main__":
    main()
