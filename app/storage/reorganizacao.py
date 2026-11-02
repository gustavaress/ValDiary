"""Reorganização única dos arquivos para semanas de domingo a sábado.

Até a v3, os arquivos semanais iam de segunda a domingo. Na primeira vez que
o app abre depois da mudança:

1. copia todos os arquivos semanais para _backups/antes_semana_domingo_<data>/;
2. lê todos os dias e grava de novo, cada um no arquivo da semana certa
   (primeiro numa pasta temporária, depois troca);
3. grava o marcador dados/_organizacao.json, para não repetir.

Os registros são identificados pela data, então rodar de novo (ex.: se o app
fechou no meio) chega ao mesmo resultado.
"""

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.storage.repositorio import ArquivoCorrompidoError, RepositorioDiario, VersaoIncompativelError
from app.storage.semanas import caminho_semana, semanas_existentes

ARQUIVO_MARCADOR = "_organizacao.json"
INICIO_SEMANA = "domingo"


@dataclass
class ResultadoReorganizacao:
    dias: int
    backup: Path
    ignorados: list[Path] = field(default_factory=list)  # arquivos que não puderam ser lidos


def _marcar(pasta_dados: Path) -> None:
    pasta_dados.mkdir(parents=True, exist_ok=True)
    (pasta_dados / ARQUIVO_MARCADOR).write_text(json.dumps({
        "inicio_semana": INICIO_SEMANA,
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
    }, indent=2), encoding="utf-8")


def reorganizar_se_preciso(repositorio: RepositorioDiario) -> ResultadoReorganizacao | None:
    """Reorganiza os arquivos se ainda estiverem no formato antigo. None = nada a fazer."""
    pasta = repositorio.pasta_dados
    if (pasta / ARQUIVO_MARCADOR).exists():
        return None
    semanas = semanas_existentes(pasta)
    if not semanas:
        _marcar(pasta)  # app novo: já nasce no formato certo
        return None

    # 1. Cópia de segurança de tudo, antes de mexer em qualquer arquivo.
    backup = repositorio.pasta_backups / f"antes_semana_domingo_{datetime.now():%Y%m%d-%H%M%S}"
    arquivos = [caminho_semana(pasta, ano, semana) for ano, semana in semanas]
    for arquivo in arquivos:
        destino = backup / arquivo.parent.name / arquivo.name
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(arquivo, destino)

    # 2. Lê tudo. Arquivos ilegíveis ficam de fora (e seguros no backup).
    por_data = {}
    ignorados = []
    for (ano, semana), arquivo in zip(semanas, arquivos):
        try:
            for registro in repositorio.carregar_semana(ano, semana):
                por_data[registro.data] = registro
        except (ArquivoCorrompidoError, VersaoIncompativelError):
            ignorados.append(arquivo)

    # 3. Grava a nova organização numa pasta temporária...
    temporaria = pasta / "_reorganizando"
    shutil.rmtree(temporaria, ignore_errors=True)
    RepositorioDiario(temporaria, temporaria / "_backups").salvar_lote(list(por_data.values()))

    # ...e só então troca os arquivos antigos pelos novos.
    for arquivo in arquivos:
        arquivo.unlink(missing_ok=True)
    for ano, semana in semanas_existentes(temporaria):
        novo = caminho_semana(temporaria, ano, semana)
        destino = caminho_semana(pasta, ano, semana)
        destino.parent.mkdir(parents=True, exist_ok=True)
        novo.replace(destino)
    shutil.rmtree(temporaria, ignore_errors=True)

    _marcar(pasta)
    return ResultadoReorganizacao(dias=len(por_data), backup=backup, ignorados=ignorados)
