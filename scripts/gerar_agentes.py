"""Gera as miniaturas dos agentes e o catálogo (assets/agentes/agentes.json).

Fonte: imagens originais em assets/agentes/originais/, no formato
"<Nome>_icon.png" (ex.: Jett_icon.png). Essa pasta fica fora do Git por ser
grande; só as miniaturas geradas aqui são versionadas.

Rode sempre que adicionar ou trocar uma imagem:

    python scripts/gerar_agentes.py

Agente novo: coloque a imagem em originais/ e inclua a função dele em FUNCOES.
"""

import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import PASTA_AGENTES  # noqa: E402

PASTA_ORIGINAIS = PASTA_AGENTES / "originais"
TAMANHO_PX = 128

FUNCOES = {
    "Duelista": ["Hush", "Iso", "Jett", "Neon", "Phoenix", "Raze", "Reyna", "Waylay", "Yoru"],
    "Iniciador": ["Breach", "Fade", "Gekko", "KAY/O", "Skye", "Sova", "Tejo"],
    "Controlador": ["Astra", "Brimstone", "Clove", "Harbor", "Miks", "Omen", "Viper"],
    "Sentinela": ["Chamber", "Cypher", "Deadlock", "Killjoy", "Sage", "Veto", "Vyse"],
}
FUNCAO_POR_AGENTE = {nome: funcao for funcao, nomes in FUNCOES.items() for nome in nomes}

# Nomes que não podem aparecer como estão num nome de arquivo.
NOMES_EXIBICAO = {"KAYO": "KAY/O"}


def _nome_arquivo(nome: str) -> str:
    """ "KAY/O" -> "kayo.png" """
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", sem_acento.lower()) + ".png"


def main() -> None:
    originais = sorted(PASTA_ORIGINAIS.glob("*_icon.png"))
    if not originais:
        sys.exit(f"Nenhuma imagem '<Nome>_icon.png' encontrada em {PASTA_ORIGINAIS}")

    agentes, sem_funcao = [], []
    for caminho in originais:
        nome = caminho.stem.removesuffix("_icon")
        nome = NOMES_EXIBICAO.get(nome, nome)
        funcao = FUNCAO_POR_AGENTE.get(nome, "Outros")
        if funcao == "Outros":
            sem_funcao.append(nome)

        arquivo = _nome_arquivo(nome)
        imagem = Image.open(caminho).convert("RGBA")
        imagem.thumbnail((TAMANHO_PX, TAMANHO_PX), Image.Resampling.LANCZOS)
        imagem.save(PASTA_AGENTES / arquivo, optimize=True)
        agentes.append({"nome": nome, "funcao": funcao, "arquivo": arquivo})
        print(f"  {nome:<12} {funcao}")

    # Remove miniaturas de agentes que não estão mais nos originais.
    gerados = {a["arquivo"] for a in agentes}
    for antiga in PASTA_AGENTES.glob("*.png"):
        if antiga.name not in gerados:
            antiga.unlink()

    agentes.sort(key=lambda a: a["nome"].lower())
    catalogo = {"atualizado_em": date.today().isoformat(), "agentes": agentes}
    (PASTA_AGENTES / "agentes.json").write_text(json.dumps(catalogo, ensure_ascii=False, indent=2),
                                                encoding="utf-8")
    print(f"\n{len(agentes)} agentes gerados em {PASTA_AGENTES}")
    if sem_funcao:
        print(f"ATENÇÃO: sem função cadastrada (aparecem em 'Outros'): {', '.join(sem_funcao)}. "
              "Inclua-os em FUNCOES neste script.")


if __name__ == "__main__":
    main()
