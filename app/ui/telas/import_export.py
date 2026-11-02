"""Importar / Exportar: backup das semanas e pacote para análise no ChatGPT."""

import os
from collections import Counter
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app import config
from app.storage import ArquivoCorrompidoError, VersaoIncompativelError
from app.storage.import_export import (
    PROMPT_CHATGPT,
    ErroImportacao,
    aplicar_importacao,
    exportar,
    ler_arquivo,
    nome_arquivo_sugerido,
    planejar_importacao,
)
from app.storage.semanas import periodo_semana
from app.ui import tema
from app.ui.area_transferencia import copiar_texto
from app.ui.componentes import Secao
from app.ui.telas.base import TelaBase


def _botao_secundario(master, texto: str, comando, largura: int = 90) -> ctk.CTkButton:
    return ctk.CTkButton(master, text=texto, width=largura, height=30, font=tema.fonte_pequena(),
                         fg_color="transparent", border_width=1, border_color=tema.COR_BORDA,
                         text_color=tema.COR_TEXTO_SECUNDARIO, hover_color=tema.COR_CARTAO_HOVER,
                         command=comando)


def _botao_principal(master, texto: str, comando) -> ctk.CTkButton:
    return ctk.CTkButton(master, text=texto, height=40, font=tema.fonte_secao(),
                         fg_color=tema.COR_DESTAQUE, hover_color=tema.COR_DESTAQUE_HOVER,
                         command=comando)


class TelaImportExport(TelaBase):
    titulo = "Importar / Exportar"
    subtitulo = "Backup dos seus dados e envio para análise no ChatGPT"

    def montar(self) -> None:
        self._caixas: dict[tuple[int, int], ctk.CTkCheckBox] = {}
        self.corpo.grid_columnconfigure((0, 1), weight=1, uniform="colunas")
        self.corpo.grid_rowconfigure(0, weight=1)
        self._montar_exportar()
        self._montar_importar()

    @property
    def _pasta_exportacoes(self) -> Path:
        return self.repositorio.pasta_dados / config.PASTA_EXPORTACOES.name

    # --- Exportar ---------------------------------------------------------

    def _montar_exportar(self) -> None:
        secao = Secao(self.corpo, "Exportar semanas",
                      "Gera um único arquivo JSON com as semanas marcadas.")
        secao.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        conteudo = secao.conteudo
        conteudo.pack_configure(fill="both", expand=True)  # a lista ocupa a altura disponível

        atalhos = ctk.CTkFrame(conteudo, fg_color="transparent")
        atalhos.pack(fill="x", pady=(0, 6))
        _botao_secundario(atalhos, "Todas", lambda: self._marcar(lambda i, n: True)).pack(side="left")
        _botao_secundario(atalhos, "Nenhuma", lambda: self._marcar(lambda i, n: False)).pack(side="left", padx=6)
        _botao_secundario(atalhos, "Últimas 4", lambda: self._marcar(lambda i, n: i >= n - 4)).pack(side="left")

        self._lista_semanas = ctk.CTkScrollableFrame(conteudo, fg_color=tema.COR_FUNDO, corner_radius=8)
        self._lista_semanas.pack(fill="both", expand=True, pady=(0, 10))

        _botao_principal(conteudo, "Exportar selecionadas...", self._exportar).pack(fill="x")

        ctk.CTkLabel(conteudo, text="Para analisar no ChatGPT: exporte, copie o prompt abaixo e "
                                    "envie os dois juntos.",
                     font=tema.fonte_pequena(), text_color=tema.COR_TEXTO_SECUNDARIO,
                     wraplength=380, justify="left").pack(anchor="w", pady=(14, 6))
        linha = ctk.CTkFrame(conteudo, fg_color="transparent")
        linha.pack(fill="x")
        _botao_secundario(linha, "Copiar prompt para o ChatGPT", self._copiar_prompt, largura=220).pack(side="left")
        self._status_prompt = ctk.CTkLabel(linha, text="", font=tema.fonte_pequena(), text_color=tema.COR_SUCESSO)
        self._status_prompt.pack(side="left", padx=10)

    def _atualizar_lista(self) -> None:
        marcadas = {s for s, caixa in self._caixas.items() if caixa.get()}
        for filho in self._lista_semanas.winfo_children():
            filho.destroy()
        self._caixas = {}

        registros, _ = self.repositorio.carregar_todos()
        dias_por_semana = Counter(r.semana for r in registros)
        semanas = self.repositorio.listar_semanas()
        if not semanas:
            ctk.CTkLabel(self._lista_semanas, text="Nenhuma semana registrada ainda.",
                         text_color=tema.COR_TEXTO_SECUNDARIO).pack(pady=20)
            return

        for ano, semana in reversed(semanas):  # mais recente primeiro
            inicio, fim = periodo_semana(ano, semana)
            dias = dias_por_semana.get((ano, semana), 0)
            caixa = ctk.CTkCheckBox(
                self._lista_semanas, font=tema.fonte_normal(),
                text=f"Semana {semana:02d}/{ano}   ·   {inicio:%d/%m} a {fim:%d/%m}   ·   "
                     f"{dias} dia{'s' if dias != 1 else ''}",
                fg_color=tema.COR_DESTAQUE, hover_color=tema.COR_DESTAQUE_HOVER,
                border_color=tema.COR_BORDA, text_color=tema.COR_TEXTO,
            )
            caixa.pack(anchor="w", padx=8, pady=4)
            if (ano, semana) in marcadas:
                caixa.select()
            self._caixas[(ano, semana)] = caixa

    def _marcar(self, regra) -> None:
        """regra(indice, total) -> marcar? O índice segue a ordem cronológica."""
        semanas = sorted(self._caixas)
        for indice, semana in enumerate(semanas):
            caixa = self._caixas[semana]
            caixa.select() if regra(indice, len(semanas)) else caixa.deselect()

    def _exportar(self) -> None:
        semanas = sorted(s for s, caixa in self._caixas.items() if caixa.get())
        if not semanas:
            messagebox.showinfo("Exportar", "Marque pelo menos uma semana.", parent=self)
            return
        self._pasta_exportacoes.mkdir(parents=True, exist_ok=True)
        caminho = filedialog.asksaveasfilename(
            parent=self, title="Salvar exportação", defaultextension=".json",
            initialdir=self._pasta_exportacoes, initialfile=nome_arquivo_sugerido(semanas),
            filetypes=[("JSON", "*.json")],
        )
        if not caminho:
            return
        try:
            destino = exportar(self.repositorio, semanas, Path(caminho))
        except (ArquivoCorrompidoError, VersaoIncompativelError, OSError) as erro:
            messagebox.showerror("Não foi possível exportar", str(erro), parent=self)
            return
        if messagebox.askyesno(
            "Exportação concluída",
            f"{len(semanas)} semana{'s' if len(semanas) != 1 else ''} exportada"
            f"{'s' if len(semanas) != 1 else ''} para:\n{destino}\n\nAbrir a pasta?",
            parent=self,
        ):
            os.startfile(destino.parent)

    def _copiar_prompt(self) -> None:
        if copiar_texto(PROMPT_CHATGPT, self.janela):
            self._status_prompt.configure(text="✓ Copiado!", text_color=tema.COR_SUCESSO)
        else:
            self._status_prompt.configure(text="Não foi possível copiar. Tente de novo.",
                                          text_color=tema.COR_AVISO)
        self.after(3000, lambda: self._status_prompt.configure(text=""))

    # --- Importar ---------------------------------------------------------

    def _montar_importar(self) -> None:
        secao = Secao(self.corpo, "Importar arquivo", "Exportações deste app ou arquivos semana_XX.json.")
        secao.grid(row=0, column=1, sticky="new", padx=(8, 0))
        texto = (
            "Antes de gravar, o app mostra o que vai acontecer:\n\n"
            "•  Dias novos são adicionados.\n"
            "•  Dias idênticos aos que você já tem são ignorados.\n"
            "•  Dias com a mesma data e conteúdo diferente: você escolhe\n"
            "    se substitui ou mantém o seu.\n\n"
            "Uma cópia de cada semana alterada vai para _backups."
        )
        ctk.CTkLabel(secao.conteudo, text=texto, justify="left", font=tema.fonte_normal(),
                     text_color=tema.COR_TEXTO_SECUNDARIO).pack(anchor="w", pady=(0, 14))
        _botao_principal(secao.conteudo, "Escolher arquivo JSON...", self._importar).pack(fill="x")

    def _importar(self) -> None:
        caminho = filedialog.askopenfilename(
            parent=self, title="Importar arquivo", initialdir=self._pasta_exportacoes,
            filetypes=[("JSON", "*.json"), ("Todos os arquivos", "*.*")],
        )
        if not caminho:
            return
        try:
            registros = ler_arquivo(Path(caminho))
        except ErroImportacao as erro:
            messagebox.showerror("Arquivo não importado", str(erro), parent=self)
            return

        plano = planejar_importacao(self.repositorio, registros)
        if not plano.novos and not plano.conflitos:
            messagebox.showinfo("Nada a importar",
                                f"Os {plano.total} dias do arquivo já existem exatamente iguais.",
                                parent=self)
            return

        resumo = (f"Dias novos: {len(plano.novos)}\n"
                  f"Mesma data, conteúdo diferente: {len(plano.conflitos)}\n"
                  f"Idênticos (serão ignorados): {len(plano.identicos)}")
        if plano.conflitos:
            datas = ", ".join(r.data.strftime("%d/%m") for r in plano.conflitos[:8])
            if len(plano.conflitos) > 8:
                datas += "..."
            escolha = messagebox.askyesnocancel(
                "Confirmar importação",
                f"{resumo}\n\nDatas em conflito: {datas}\n\n"
                "SIM: substituir esses dias pelos do arquivo\n"
                "NÃO: manter os seus e importar só os novos\n"
                "CANCELAR: não importar nada",
                parent=self,
            )
            if escolha is None:
                return
            substituir = escolha
        else:
            if not messagebox.askyesno("Confirmar importação", f"{resumo}\n\nImportar?", parent=self):
                return
            substituir = False

        try:
            gravados = aplicar_importacao(self.repositorio, plano, substituir)
        except (ArquivoCorrompidoError, VersaoIncompativelError) as erro:
            messagebox.showerror("Importação interrompida", f"{erro}\n\nNada foi gravado.", parent=self)
            return
        messagebox.showinfo("Importação concluída", f"{gravados} dias gravados.", parent=self)
        self._atualizar_lista()

    def ao_exibir(self) -> None:
        self._atualizar_lista()
