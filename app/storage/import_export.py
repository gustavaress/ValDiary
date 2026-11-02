"""Exportação e importação de semanas em JSON.

O arquivo exportado é um "pacote" com uma ou mais semanas e uma legenda
explicando os campos, para que tanto você quanto uma IA (ex.: ChatGPT)
consigam interpretá-lo sem ambiguidade.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from app import config
from app.models import RegistroDia, validar_registro
from app.analysis.ranking import evolucao_ranking
from app.models.ranking import DefinicaoRanking
from app.storage.escrita_segura import escrever_json_atomico
from app.storage.migracoes import migrar_documento
from app.storage.repositorio import RepositorioDiario

FORMATO = "valdiary-exportacao"

LEGENDA = {
    "sobre": "Diário pessoal de rotina e desempenho no jogo Valorant. Cada item de 'dias' é um dia registrado.",
    "campos_vazios": "null significa que o dado NÃO foi registrado naquele dia (não significa zero).",
    "escalas": "Notas subjetivas vão de 1 (muito ruim) a 10 (excelente). "
               "Exceção: 'estresse', em que 10 = muito estressado.",
    "classificacao": "Avaliação subjetiva do próprio jogador sobre o dia: "
                     "excelente, bom, normal, ruim ou pessimo.",
    "valorant": "'partidas' lista cada partida do dia (agente, resultado, abates, mortes, "
                "assistencias, hs_pct e acs). 'resumo' é CALCULADO a partir delas: abates, mortes e "
                "assistencias são totais do dia; hs_pct e acs são médias por partida; 'agentes' conta "
                "em quantas partidas cada agente foi jogado. Dias antigos podem ter só 'legado' "
                "(totais do dia digitados antes do registro por partida), sem a lista de partidas.",
    "ranking": "Cada partida tem 'rr' = pontos de ranking ganhos (+) ou perdidos (-); 'resumo.rr' é a "
               "soma simples do dia. O bloco 'ranking' no topo traz as definições feitas pelo jogador (elo "
               "e RR a partir de uma data) e a evolução por dia, aplicando o RR partida a partida com a "
               "proteção contra rebaixamento (perder com RR acima de 0 só zera os pontos). Por isso "
               "'rr_variacao_no_ranking' (quanto o ranking realmente mudou) pode diferir de "
               "'rr_soma_partidas': ex. 1 RR, -20 e +17 = soma -3, mas variação real +16. "
               "Use a variação real para avaliar o progresso. É uma estimativa.",
    "refeicoes": "'realizada': true = teve a refeição; null = não marcada (não teve ou não registrou).",
    "horarios": "Formato HH:MM (24h). 'dormiu_as' pode ser depois da meia-noite "
                "(ex.: 01:30 = foi dormir de madrugada).",
    "semanas": "Semanas de domingo a sábado. A semana 1 é a primeira com pelo menos 4 dias no ano novo.",
}

PROMPT_CHATGPT = """Vou te enviar um arquivo JSON exportado do meu diário de rotina e desempenho no Valorant. O bloco "_legenda" do arquivo explica cada campo e as escalas usadas.

Analise os registros e responda:
1. Quais foram meus melhores dias? O que aconteceu neles?
2. Quais características se repetiram nos dias bons?
3. O que mudou nos meus piores dias?
4. Existe alguma relação entre meu sono e meu desempenho?
5. Minha alimentação parece influenciar minha disposição?
6. Existem padrões relacionados aos horários em que jogo?
7. Quais fatores merecem ser observados nas próximas semanas?

Regras importantes:
- Diferencie correlação de causa. Não afirme que um fator CAUSA outro.
- Diga claramente quando houver poucos dados para concluir algo.
- Campos null significam "não registrado", não zero: ignore-os nos cálculos.
- Cite datas e números concretos dos registros para sustentar cada observação."""


class ErroImportacao(Exception):
    pass


# --- Exportação -----------------------------------------------------------

def montar_pacote(repositorio: RepositorioDiario, semanas: list[tuple[int, int]],
                  definicoes_ranking: list[DefinicaoRanking] | None = None) -> dict:
    documentos = [
        repositorio.montar_documento_semana(ano, semana, repositorio.carregar_semana(ano, semana))
        for ano, semana in sorted(semanas)
    ]
    pacote = {
        "formato": FORMATO,
        "versao_schema": config.VERSAO_SCHEMA,
        "exportado_em": datetime.now().isoformat(timespec="seconds"),
        "_legenda": LEGENDA,
        "semanas": documentos,
    }
    if definicoes_ranking:
        # Evolução calculada com TODOS os dias (o ranking depende dos dias anteriores),
        # mas só os dias exportados entram no pacote.
        datas = {dia["data"] for documento in documentos for dia in documento["dias"]}
        evolucao = evolucao_ranking(repositorio.carregar_todos()[0], definicoes_ranking)
        pacote["ranking"] = {
            "definicoes": [d.to_dict() for d in definicoes_ranking],
            "evolucao_por_dia": [
                {"data": e.data.isoformat(), "inicio": asdict(e.inicio), "rr_soma_partidas": e.rr,
                 "rr_variacao_no_ranking": e.variacao,
                 "fim": asdict(e.final)}
                for e in evolucao if e.data.isoformat() in datas
            ],
        }
    return pacote


def nome_arquivo_sugerido(semanas: list[tuple[int, int]]) -> str:
    semanas = sorted(semanas)
    primeira = f"{semanas[0][0]}-S{semanas[0][1]:02d}"
    if len(semanas) == 1:
        return f"valdiary_{primeira}.json"
    ultima = f"{semanas[-1][0]}-S{semanas[-1][1]:02d}"
    return f"valdiary_{primeira}_a_{ultima}.json"


def exportar(repositorio: RepositorioDiario, semanas: list[tuple[int, int]], destino: Path,
             definicoes_ranking: list[DefinicaoRanking] | None = None) -> Path:
    if not semanas:
        raise ValueError("Nenhuma semana selecionada.")
    escrever_json_atomico(destino, montar_pacote(repositorio, semanas, definicoes_ranking))
    return destino


# --- Importação -----------------------------------------------------------

def ler_arquivo(caminho: Path) -> list[RegistroDia]:
    """Lê um pacote exportado ou um arquivo semanal. Valida tudo antes de retornar."""
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ErroImportacao(f"Não foi possível ler o arquivo como JSON.\n\n{erro}") from erro

    if isinstance(dados, dict) and isinstance(dados.get("semanas"), list):
        documentos = dados["semanas"]          # pacote exportado
    elif isinstance(dados, dict) and isinstance(dados.get("dias"), list):
        documentos = [dados]                   # arquivo semanal cru
    else:
        raise ErroImportacao("Este arquivo não parece ser uma exportação do ValDiary.")

    registros: list[RegistroDia] = []
    for documento in documentos:
        versao = documento.get("versao_schema", 1) if isinstance(documento, dict) else 1
        if versao > config.VERSAO_SCHEMA:
            raise ErroImportacao(
                f"O arquivo usa o formato v{versao}, mas este app só entende até a "
                f"v{config.VERSAO_SCHEMA}. Atualize o aplicativo."
            )
        if isinstance(documento, dict):
            documento = migrar_documento(documento)
        for dia in (documento.get("dias") or []) if isinstance(documento, dict) else []:
            rotulo = dia.get("data", "sem data") if isinstance(dia, dict) else "?"
            try:
                registro = RegistroDia.from_dict(dia)
            except (KeyError, ValueError, TypeError, AttributeError) as erro:
                raise ErroImportacao(f"Dia inválido no arquivo ({rotulo}): {erro}") from erro
            erros = validar_registro(registro)
            if erros:
                raise ErroImportacao(f"Dia {rotulo} tem valores inválidos:\n" + "\n".join(f"• {e}" for e in erros))
            registros.append(registro)
    return registros


@dataclass
class PlanoImportacao:
    novos: list[RegistroDia] = field(default_factory=list)       # datas que você não tem
    conflitos: list[RegistroDia] = field(default_factory=list)   # mesma data, conteúdo diferente
    identicos: list[RegistroDia] = field(default_factory=list)   # já existem iguais

    @property
    def total(self) -> int:
        return len(self.novos) + len(self.conflitos) + len(self.identicos)


def _conteudo(registro: RegistroDia) -> dict:
    """Conteúdo do dia sem os carimbos de data/hora (que não contam como 'diferença')."""
    dados = registro.to_dict()
    dados.pop("criado_em")
    dados.pop("editado_em")
    return dados


def planejar_importacao(repositorio: RepositorioDiario, registros: list[RegistroDia]) -> PlanoImportacao:
    existentes = {r.data: r for r in repositorio.carregar_todos()[0]}
    plano = PlanoImportacao()
    for registro in registros:
        atual = existentes.get(registro.data)
        if atual is None:
            plano.novos.append(registro)
        elif _conteudo(atual) == _conteudo(registro):
            plano.identicos.append(registro)
        else:
            plano.conflitos.append(registro)
    return plano


def aplicar_importacao(repositorio: RepositorioDiario, plano: PlanoImportacao,
                       substituir_conflitos: bool) -> int:
    """Grava o plano e retorna quantos dias foram gravados."""
    a_gravar = plano.novos + (plano.conflitos if substituir_conflitos else [])
    if a_gravar:
        repositorio.salvar_lote(a_gravar, sobrescrever=substituir_conflitos)
    return len(a_gravar)
