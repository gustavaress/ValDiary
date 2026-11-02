"""Configurações centrais do aplicativo.

Tudo que é "constante do projeto" (caminhos, escalas, versão do formato JSON)
fica aqui, para não ficar espalhado pelo código.
"""

import sys
from pathlib import Path

NOME_APP = "ValDiary · Diário de Performance"
VERSAO_APP = "4.1"

# Versão do formato dos arquivos JSON. Sempre que a estrutura mudar de forma
# incompatível, incrementamos este número e escrevemos uma migração.
VERSAO_SCHEMA = 5

# Escala usada em todas as notas subjetivas (sono, disposição, mira...).
ESCALA_MIN = 1
ESCALA_MAX = 10

# --- Caminhos -------------------------------------------------------------
# Rodando pelo VS Code: a base é a pasta do projeto.
# Rodando como .exe (PyInstaller): a base é a pasta onde o .exe está.
# Não usamos a pasta interna do PyInstaller porque ela é temporária e apagada
# ao fechar o programa.
if getattr(sys, "frozen", False):
    PASTA_BASE = Path(sys.executable).resolve().parent
    # Recursos (imagens) vão empacotados dentro do .exe, que os extrai aqui.
    PASTA_RECURSOS = Path(sys._MEIPASS) / "assets"
else:
    PASTA_BASE = Path(__file__).resolve().parent.parent
    PASTA_RECURSOS = PASTA_BASE / "assets"

PASTA_AGENTES = PASTA_RECURSOS / "agentes"
PASTA_RANKS = PASTA_RECURSOS / "ranks"

PASTA_DADOS = PASTA_BASE / "dados"
PASTA_BACKUPS = PASTA_DADOS / "_backups"
PASTA_EXPORTACOES = PASTA_DADOS / "_exportacoes"
ARQUIVO_RASCUNHO = PASTA_DADOS / "_rascunho.json"

# Quantas versões antigas de cada arquivo semanal manter em _backups.
MAX_BACKUPS_POR_SEMANA = 10


def garantir_pastas() -> None:
    """Cria as pastas de dados caso ainda não existam."""
    for pasta in (PASTA_DADOS, PASTA_BACKUPS, PASTA_EXPORTACOES):
        pasta.mkdir(parents=True, exist_ok=True)
