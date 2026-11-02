"""Gravação de arquivos à prova de falhas.

Escrita atômica: escrevemos tudo num arquivo temporário, forçamos o sistema
operacional a gravar no disco (fsync) e só então trocamos pelo arquivo final
com os.replace(). A troca é atômica: ou o arquivo antigo continua lá, ou o
novo está completo. Nunca fica um arquivo "pela metade".
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path


def escrever_json_atomico(caminho: Path, dados: dict) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    try:
        with open(temporario, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, ensure_ascii=False, indent=2)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, caminho)
    finally:
        # Se algo falhou antes do replace, não deixa lixo para trás.
        if temporario.exists():
            temporario.unlink()


def fazer_backup(caminho: Path, pasta_backups: Path, maximo: int) -> Path | None:
    """Copia o arquivo para a pasta de backups e apaga os mais antigos que o limite.

    Ex.: dados/2026/semana_45.json -> _backups/2026/semana_45_20261102-234110.json
    """
    if not caminho.exists():
        return None

    destino_pasta = pasta_backups / caminho.parent.name
    destino_pasta.mkdir(parents=True, exist_ok=True)
    carimbo = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    destino = destino_pasta / f"{caminho.stem}_{carimbo}.json"
    shutil.copy2(caminho, destino)

    # O carimbo no nome faz a ordem alfabética ser também a ordem cronológica.
    backups = sorted(destino_pasta.glob(f"{caminho.stem}_*.json"))
    for antigo in backups[:-maximo]:
        antigo.unlink()
    return destino
