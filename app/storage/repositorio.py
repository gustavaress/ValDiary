"""Repositório: a única porta de entrada para ler e gravar registros.

A interface nunca mexe em arquivos diretamente; ela chama os métodos daqui.
Isso concentra todas as regras de segurança dos dados num só lugar.
"""

import json
from datetime import date, datetime
from pathlib import Path

from app import config
from app.models import RegistroDia
from app.storage.escrita_segura import escrever_json_atomico, fazer_backup
from app.storage.semanas import (
    caminho_semana,
    periodo_semana,
    semana_da_data,
    semanas_existentes,
)


class ArquivoCorrompidoError(Exception):
    """O arquivo existe mas não pôde ser lido. Nunca o sobrescrevemos."""

    def __init__(self, caminho: Path, motivo: str):
        self.caminho = caminho
        self.motivo = motivo
        super().__init__(f"Arquivo corrompido: {caminho} ({motivo})")


class VersaoIncompativelError(Exception):
    """O arquivo foi criado por uma versão mais nova do aplicativo."""


class RegistroDuplicadoError(Exception):
    """Já existe um registro para essa data."""

    def __init__(self, data: date):
        self.data = data
        super().__init__(f"Já existe um registro para {data.strftime('%d/%m/%Y')}.")


class RepositorioDiario:
    def __init__(
        self,
        pasta_dados: Path = config.PASTA_DADOS,
        pasta_backups: Path = config.PASTA_BACKUPS,
        max_backups: int = config.MAX_BACKUPS_POR_SEMANA,
    ):
        # Os caminhos são parâmetros para os testes poderem usar uma pasta temporária.
        self.pasta_dados = pasta_dados
        self.pasta_backups = pasta_backups
        self.max_backups = max_backups

    # --- Leitura ----------------------------------------------------------

    def carregar_semana(self, ano: int, semana: int) -> list[RegistroDia]:
        """Registros da semana, em ordem de data. Semana sem arquivo -> lista vazia."""
        caminho = caminho_semana(self.pasta_dados, ano, semana)
        if not caminho.exists():
            return []

        try:
            with open(caminho, encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
            versao = dados.get("versao_schema", 1)
            if versao > config.VERSAO_SCHEMA:
                raise VersaoIncompativelError(
                    f"{caminho.name} usa o formato v{versao}, mas este app só entende "
                    f"até a v{config.VERSAO_SCHEMA}. Atualize o aplicativo."
                )
            return [RegistroDia.from_dict(d) for d in dados.get("dias", [])]
        except VersaoIncompativelError:
            raise
        except (json.JSONDecodeError, KeyError, ValueError, TypeError, AttributeError) as erro:
            raise ArquivoCorrompidoError(caminho, str(erro)) from erro

    def carregar_todos(self) -> tuple[list[RegistroDia], list[ArquivoCorrompidoError]]:
        """Todos os registros, em ordem de data, e a lista de arquivos que falharam.

        Um arquivo com problema não impede a leitura dos outros.
        """
        registros: list[RegistroDia] = []
        problemas: list[ArquivoCorrompidoError] = []
        for ano, semana in semanas_existentes(self.pasta_dados):
            try:
                registros.extend(self.carregar_semana(ano, semana))
            except ArquivoCorrompidoError as erro:
                problemas.append(erro)
            except VersaoIncompativelError as erro:
                problemas.append(ArquivoCorrompidoError(caminho_semana(self.pasta_dados, ano, semana), str(erro)))
        registros.sort(key=lambda r: r.data)
        return registros, problemas

    def obter_dia(self, data: date) -> RegistroDia | None:
        for registro in self.carregar_semana(*semana_da_data(data)):
            if registro.data == data:
                return registro
        return None

    def listar_semanas(self) -> list[tuple[int, int]]:
        return semanas_existentes(self.pasta_dados)

    # --- Escrita ----------------------------------------------------------

    def salvar_dia(self, registro: RegistroDia, sobrescrever: bool = False) -> None:
        """Adiciona ou atualiza um dia no arquivo da semana correspondente.

        sobrescrever=False: se a data já existir, lança RegistroDuplicadoError.
        sobrescrever=True: substitui o registro existente (edição).
        """
        self.salvar_lote([registro], sobrescrever)

    def salvar_lote(self, registros: list[RegistroDia], sobrescrever: bool = False) -> None:
        """Salva vários dias gravando cada arquivo semanal uma única vez.

        Assim uma importação de 7 dias gera 1 backup da semana, e não 7
        (o que empurraria os backups antigos para fora do limite).
        Tudo é verificado antes de gravar: se um dia falhar, nada é gravado.
        """
        por_semana: dict[tuple[int, int], list[RegistroDia]] = {}
        for registro in registros:
            por_semana.setdefault(registro.semana_iso, []).append(registro)

        agora = datetime.now().replace(microsecond=0)
        a_gravar: dict[tuple[int, int], list[RegistroDia]] = {}
        for (ano, semana), novos in por_semana.items():
            # Se o arquivo estiver corrompido, carregar_semana lança erro e
            # nada é gravado. Isso protege os dados que ainda podem ser recuperados.
            existentes = {r.data: r for r in self.carregar_semana(ano, semana)}
            for registro in novos:
                anterior = existentes.get(registro.data)
                if anterior:
                    if not sobrescrever:
                        raise RegistroDuplicadoError(registro.data)
                    registro.criado_em = anterior.criado_em or agora
                    registro.editado_em = agora
                else:
                    registro.criado_em = registro.criado_em or agora
                existentes[registro.data] = registro
            a_gravar[(ano, semana)] = list(existentes.values())

        for (ano, semana), registros_semana in a_gravar.items():
            self._gravar_semana(ano, semana, registros_semana)

    def excluir_dia(self, data: date) -> bool:
        ano, semana = semana_da_data(data)
        registros = self.carregar_semana(ano, semana)
        restantes = [r for r in registros if r.data != data]
        if len(restantes) == len(registros):
            return False
        self._gravar_semana(ano, semana, restantes)
        return True

    def _gravar_semana(self, ano: int, semana: int, registros: list[RegistroDia]) -> None:
        caminho = caminho_semana(self.pasta_dados, ano, semana)
        fazer_backup(caminho, self.pasta_backups, self.max_backups)
        escrever_json_atomico(caminho, self.montar_documento_semana(ano, semana, registros))

    @staticmethod
    def montar_documento_semana(ano: int, semana: int, registros: list[RegistroDia]) -> dict:
        inicio, fim = periodo_semana(ano, semana)
        return {
            "versao_schema": config.VERSAO_SCHEMA,
            "ano": ano,
            "semana": semana,
            "periodo": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
            "atualizado_em": datetime.now().isoformat(timespec="seconds"),
            "dias": [r.to_dict() for r in sorted(registros, key=lambda r: r.data)],
        }
