"""Seleção de agentes por imagem, com contador de partidas por agente."""

import customtkinter as ctk
from PIL import Image, ImageEnhance

from app.analysis.filtros import normalizar_texto
from app.storage.catalogo_agentes import AgenteInfo, agrupar_por_funcao
from app.ui import tema

TAMANHO_FOTO = 52
TAMANHO_MINI = 26
AGENTES_POR_LINHA = 8

_PLURAL_FUNCAO = {"Duelista": "Duelistas", "Iniciador": "Iniciadores",
                  "Controlador": "Controladores", "Sentinela": "Sentinelas"}


def _imagens(agente: AgenteInfo) -> tuple[ctk.CTkImage, ctk.CTkImage, ctk.CTkImage]:
    """(colorida, esmaecida, miniatura). A esmaecida é para agentes não selecionados."""
    original = Image.open(agente.imagem).convert("RGBA")
    cinza = ImageEnhance.Brightness(ImageEnhance.Color(original).enhance(0.0)).enhance(0.55)
    tamanho = (TAMANHO_FOTO, TAMANHO_FOTO)
    return (ctk.CTkImage(original, size=tamanho), ctk.CTkImage(cinza, size=tamanho),
            ctk.CTkImage(original, size=(TAMANHO_MINI, TAMANHO_MINI)))


class SeletorAgentes(ctk.CTkFrame):
    """get() -> [{"nome": "Jett", "partidas": "2"}, ...] na ordem em que foram selecionados."""

    def __init__(self, master, catalogo: tuple[AgenteInfo, ...], ao_mudar=None):
        super().__init__(master, fg_color="transparent")
        self._ao_mudar = ao_mudar
        self._catalogo = {a.nome: a for a in catalogo}
        self._por_nome_normalizado = {normalizar_texto(a.nome): a.nome for a in catalogo}
        self._selecionados: dict[str, int | None] = {}
        self._botoes: dict[str, ctk.CTkButton] = {}
        self._imagens: dict[str, tuple] = {}

        if not catalogo:
            ctk.CTkLabel(self, text="Imagens dos agentes não encontradas. Para gerá-las, rode no terminal:\n"
                                    "python scripts/gerar_agentes.py",
                         justify="left", font=tema.fonte_normal(), text_color=tema.COR_AVISO).pack(anchor="w")

        grade = ctk.CTkFrame(self, fg_color="transparent")
        grade.pack(anchor="w")
        linha_grade = 0
        for funcao, agentes in agrupar_por_funcao(catalogo):
            ctk.CTkLabel(grade, text=_PLURAL_FUNCAO.get(funcao, funcao).upper(), font=tema.fonte_pequena(),
                         text_color=tema.COR_TEXTO_SECUNDARIO).grid(row=linha_grade, column=0, columnspan=8,
                                                                    sticky="w", pady=(8, 2))
            linha_grade += 1
            for i, agente in enumerate(agentes):
                self._imagens[agente.nome] = _imagens(agente)
                botao = ctk.CTkButton(
                    grade, text=agente.nome, image=self._imagens[agente.nome][1], compound="top",
                    width=74, height=84, corner_radius=10, border_width=2, font=tema.fonte_pequena(),
                    fg_color="transparent", hover_color=tema.COR_CARTAO_HOVER,
                    command=lambda n=agente.nome: self._alternar(n),
                )
                botao.grid(row=linha_grade + i // AGENTES_POR_LINHA, column=i % AGENTES_POR_LINHA,
                           padx=(0, 6), pady=3)
                self._botoes[agente.nome] = botao
            linha_grade += (len(agentes) - 1) // AGENTES_POR_LINHA + 1

        ctk.CTkLabel(self, text="PARTIDAS COM CADA AGENTE", font=tema.fonte_pequena(),
                     text_color=tema.COR_TEXTO_SECUNDARIO).pack(anchor="w", pady=(14, 2))
        self._lista = ctk.CTkFrame(self, fg_color="transparent")
        self._lista.pack(anchor="w", fill="x")
        self._resumo = ctk.CTkLabel(self, text="", font=tema.fonte_pequena(),
                                    text_color=tema.COR_TEXTO_SECUNDARIO)
        self._resumo.pack(anchor="w", pady=(4, 0))
        self._redesenhar()

    # --- Interação --------------------------------------------------------

    def _alternar(self, nome: str) -> None:
        if nome in self._selecionados:
            del self._selecionados[nome]
        else:
            self._selecionados[nome] = 1  # se selecionou, jogou pelo menos 1 partida
        self._mudou()

    def _ajustar(self, nome: str, delta: int) -> None:
        self._selecionados[nome] = max(1, (self._selecionados[nome] or 0) + delta)
        self._mudou()

    def _mudou(self) -> None:
        self._redesenhar()
        if self._ao_mudar:
            self._ao_mudar()

    def _redesenhar(self) -> None:
        for nome, botao in self._botoes.items():
            ativo = nome in self._selecionados
            botao.configure(image=self._imagens[nome][0 if ativo else 1],
                            border_color=tema.COR_DESTAQUE if ativo else tema.COR_CARTAO,
                            text_color=tema.COR_TEXTO if ativo else tema.COR_TEXTO_SECUNDARIO)

        for filho in self._lista.winfo_children():
            filho.destroy()
        if not self._selecionados:
            ctk.CTkLabel(self._lista, text="Clique nas fotos acima para marcar quem você jogou.",
                         font=tema.fonte_pequena(), text_color=tema.COR_TEXTO_SECUNDARIO).pack(anchor="w")

        for nome, partidas in self._selecionados.items():
            linha = ctk.CTkFrame(self._lista, fg_color=tema.COR_FUNDO, corner_radius=8)
            linha.pack(anchor="w", pady=2)
            imagem = self._imagens.get(nome, (None, None, None))[2]
            ctk.CTkLabel(linha, text="", image=imagem, width=TAMANHO_MINI).pack(side="left", padx=(8, 6), pady=4)
            ctk.CTkLabel(linha, text=nome, width=90, anchor="w", font=tema.fonte_normal(),
                         text_color=tema.COR_TEXTO).pack(side="left")
            for texto, delta in (("−", -1), (None, 0), ("+", 1)):
                if texto is None:
                    ctk.CTkLabel(linha, text=str(partidas or "—"), width=34, font=tema.fonte_secao(),
                                 text_color=tema.COR_TEXTO).pack(side="left")
                    continue
                ctk.CTkButton(linha, text=texto, width=30, height=28, font=tema.fonte_secao(),
                              fg_color=tema.COR_CARTAO, hover_color=tema.COR_BORDA,
                              command=lambda n=nome, d=delta: self._ajustar(n, d)).pack(side="left", padx=2)
            ctk.CTkLabel(linha, text="partida(s)", font=tema.fonte_pequena(),
                         text_color=tema.COR_TEXTO_SECUNDARIO).pack(side="left", padx=(6, 4))
            ctk.CTkButton(linha, text="✕", width=30, height=28, fg_color="transparent",
                          hover_color=tema.COR_BORDA, text_color=tema.COR_TEXTO_SECUNDARIO,
                          command=lambda n=nome: self._alternar(n)).pack(side="left", padx=(0, 6))

        total = sum(p or 0 for p in self._selecionados.values())
        self._resumo.configure(text=f"Soma: {total} partida(s) com agentes" if self._selecionados else "")

    # --- Valor ------------------------------------------------------------

    def total_partidas(self) -> int:
        return sum(p or 0 for p in self._selecionados.values())

    def get(self) -> list[dict]:
        return [{"nome": nome, "partidas": str(p) if p else ""} for nome, p in self._selecionados.items()]

    def set(self, itens: list[dict] | None) -> None:
        self._selecionados = {}
        for item in itens or []:
            # Associa grafias antigas ("jett") ao nome do catálogo ("Jett").
            nome = self._por_nome_normalizado.get(normalizar_texto(item["nome"]), item["nome"])
            partidas = str(item.get("partidas") or "")
            self._selecionados[nome] = int(partidas) if partidas.isdigit() else None
        self._redesenhar()
