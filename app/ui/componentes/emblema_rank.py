"""Emblemas dos ranks (assets/ranks): elo em português -> imagem do arquivo."""

from functools import cache
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from app import config

# Os arquivos usam os nomes em inglês: "Ascendant_3_Rank.png", "Radiant_Rank.png".
_TIERS_EM_INGLES = {
    "Ferro": "Iron", "Bronze": "Bronze", "Prata": "Silver", "Ouro": "Gold", "Platina": "Platinum",
    "Diamante": "Diamond", "Ascendente": "Ascendant", "Imortal": "Immortal", "Radiante": "Radiant",
}


def arquivo_rank(elo: str, pasta: Path = config.PASTA_RANKS) -> Path | None:
    """Caminho do emblema de um elo ("Ascendente 3"), ou None se o elo for desconhecido."""
    tier, _, divisao = elo.partition(" ")
    nome = _TIERS_EM_INGLES.get(tier)
    if nome is None:
        return None
    return pasta / (f"{nome}_{divisao}_Rank.png" if divisao else f"{nome}_Rank.png")


@cache
def imagem_rank(elo: str | None, tamanho: int) -> ctk.CTkImage | None:
    """Emblema no tamanho pedido, centralizado num quadrado (algumas imagens não são
    quadradas). Carregado uma vez e reaproveitado; None se faltar a imagem."""
    caminho = arquivo_rank(elo) if elo else None
    if caminho is None or not caminho.exists():
        return None
    original = Image.open(caminho).convert("RGBA")
    lado = max(original.size)
    quadrado = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    quadrado.paste(original, ((lado - original.width) // 2, (lado - original.height) // 2))
    return ctk.CTkImage(quadrado, size=(tamanho, tamanho))
