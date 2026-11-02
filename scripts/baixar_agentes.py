"""Baixa os ícones dos agentes do Valorant para assets/agentes/.

Fonte: https://valorant-api.com (API pública mantida pela comunidade).
O app em si não acessa a internet: ele só lê a pasta gerada por este script.
Rode de novo quando sair um agente novo:

    python scripts/baixar_agentes.py
"""

import io
import json
import re
import sys
import unicodedata
import urllib.request
from datetime import date
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import PASTA_AGENTES  # noqa: E402

URL = "https://valorant-api.com/v1/agents?isPlayableCharacter=true&language=pt-BR"
TAMANHO_PX = 128


def _baixar(url: str) -> bytes:
    pedido = urllib.request.Request(url, headers={"User-Agent": "ValDiary/2.0"})
    with urllib.request.urlopen(pedido, timeout=30) as resposta:
        return resposta.read()


def _nome_arquivo(nome: str) -> str:
    """ "KAY/O" -> "kayo.png" """
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", sem_acento.lower()) + ".png"


def main() -> None:
    PASTA_AGENTES.mkdir(parents=True, exist_ok=True)
    dados = json.loads(_baixar(URL))["data"]

    agentes, vistos = [], set()
    for agente in dados:
        nome = agente["displayName"]
        if nome in vistos:  # a API às vezes repete agentes
            continue
        vistos.add(nome)
        arquivo = _nome_arquivo(nome)
        imagem = Image.open(io.BytesIO(_baixar(agente["displayIcon"]))).convert("RGBA")
        imagem.thumbnail((TAMANHO_PX, TAMANHO_PX))
        imagem.save(PASTA_AGENTES / arquivo, optimize=True)
        funcao = (agente.get("role") or {}).get("displayName") or "Outros"
        agentes.append({"nome": nome, "funcao": funcao, "arquivo": arquivo})
        print(f"  {nome:<12} {funcao}")

    agentes.sort(key=lambda a: a["nome"].lower())
    catalogo = {"fonte": "https://valorant-api.com", "atualizado_em": date.today().isoformat(),
                "agentes": agentes}
    (PASTA_AGENTES / "agentes.json").write_text(json.dumps(catalogo, ensure_ascii=False, indent=2),
                                                encoding="utf-8")
    print(f"\n{len(agentes)} agentes salvos em {PASTA_AGENTES}")


if __name__ == "__main__":
    main()
