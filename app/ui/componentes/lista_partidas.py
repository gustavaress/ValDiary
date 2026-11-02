"""Lista de partidas do dia: um cartão por partida, com agente, resultado e estatísticas."""

import customtkinter as ctk

from app.ui import tema
from app.ui.componentes.botoes import botao_icone, botao_primario
from app.ui.componentes.bandeja_agentes import escolher_agente, imagem_agente
from app.ui.componentes.formulario import nova_entrada
from app.ui.componentes.seletor import SeletorBotoes

RESULTADOS = [("vitoria", "Vitória"), ("derrota", "Derrota"), ("empate", "Empate")]
CORES_RESULTADO = {"vitoria": tema.COR_SUCESSO, "derrota": tema.COR_DESTAQUE, "empate": tema.COR_TEXTO_SECUNDARIO}

# (chave, rótulo, largura)
ESTATISTICAS = [("abates", "K", 58), ("mortes", "D", 58), ("assistencias", "A", 58),
                ("hs_pct", "HS%", 66), ("acs", "ACS", 66), ("rr", "RR ±", 66)]


class CartaoPartida(ctk.CTkFrame):
    def __init__(self, lista: "ListaPartidas", valores: dict):
        super().__init__(lista.area, fg_color=tema.COR_CAMPO, corner_radius=tema.RAIO)
        self._lista = lista
        self._agente: str | None = valores.get("agente") or None
        self.grid_columnconfigure(3, weight=1)

        self._titulo = ctk.CTkLabel(self, text="", width=80, anchor="w", font=tema.fonte_secao(),
                                    text_color=tema.COR_TEXTO)
        self._titulo.grid(row=0, column=0, padx=(14, 6), pady=(10, 4), sticky="w")

        self._botao_agente = ctk.CTkButton(
            self, width=150, height=36, compound="left", anchor="w", font=tema.fonte_normal(),
            fg_color=tema.COR_CARTAO, hover_color=tema.COR_CARTAO_HOVER, border_width=1,
            border_color=tema.COR_BORDA, command=self._escolher_agente,
        )
        self._botao_agente.grid(row=0, column=1, padx=6, pady=(10, 4), sticky="w")

        self._resultado = SeletorBotoes(self, RESULTADOS, cores=CORES_RESULTADO, largura_botao=74,
                                        ao_mudar=lambda _: lista.mudou())
        self._resultado.set(valores.get("resultado"))
        self._resultado.grid(row=0, column=2, padx=6, pady=(10, 4), sticky="w")

        botao_icone(self, "✕", lambda: lista.remover(self)).grid(row=0, column=4, padx=(0, 10), pady=(10, 4))

        estatisticas = ctk.CTkFrame(self, fg_color="transparent")
        estatisticas.grid(row=1, column=0, columnspan=5, sticky="w", padx=14, pady=(0, 12))
        self._entradas: dict[str, ctk.CTkEntry] = {}
        for chave, rotulo, largura in ESTATISTICAS:
            bloco = ctk.CTkFrame(estatisticas, fg_color="transparent")
            bloco.pack(side="left", padx=(0, 8))
            ctk.CTkLabel(bloco, text=rotulo, font=tema.fonte_pequena(),
                         text_color=tema.COR_TEXTO_SECUNDARIO).pack(anchor="w")
            entrada = nova_entrada(bloco, largura)
            entrada.pack()
            if valores.get(chave):
                entrada.insert(0, valores[chave])
            entrada.bind("<KeyRelease>", lambda _: lista.mudou(), add="+")
            self._entradas[chave] = entrada
        self._kd = ctk.CTkLabel(estatisticas, text="", font=tema.fonte_secao(), text_color=tema.COR_DESTAQUE)
        self._kd.pack(side="left", padx=(10, 0), pady=(16, 0))

        self._pintar_agente()

    def numerar(self, numero: int) -> None:
        self._titulo.configure(text=f"Partida {numero}")

    def _escolher_agente(self) -> None:
        escolhido = escolher_agente(self, self._agente)
        if escolhido:
            self._agente = escolhido
            self._pintar_agente()
            self._lista.mudou()

    def _pintar_agente(self) -> None:
        imagem = imagem_agente(self._agente, 26) if self._agente else None
        self._botao_agente.configure(
            text=f"  {self._agente}" if self._agente else "Escolher agente",
            image=imagem, text_color=tema.COR_TEXTO if self._agente else tema.COR_TEXTO_SECUNDARIO,
        )

    def atualizar_kd(self) -> None:
        """K/D desta partida, calculado na hora (vazio se K ou D não forem números)."""
        abates, mortes = self._entradas["abates"].get().strip(), self._entradas["mortes"].get().strip()
        if abates.isdigit() and mortes.isdigit():
            kd = int(abates) / max(int(mortes), 1)
            self._kd.configure(text=f"K/D {kd:.2f}".replace(".", ","))
        else:
            self._kd.configure(text="")

    @property
    def agente(self) -> str | None:
        return self._agente

    def get(self) -> dict:
        dados = {"agente": self._agente or "", "resultado": self._resultado.get()}
        dados.update({chave: entrada.get().strip() for chave, entrada in self._entradas.items()})
        return dados


class ListaPartidas(ctk.CTkFrame):
    """get() -> lista de dicts (um por partida), no formato do formulário."""

    def __init__(self, master, ao_mudar=None):
        super().__init__(master, fg_color="transparent")
        self._ao_mudar = ao_mudar
        self._cartoes: list[CartaoPartida] = []
        self.area = ctk.CTkFrame(self, fg_color="transparent")
        self.area.pack(fill="x")
        self._vazio = ctk.CTkLabel(self.area, text="Nenhuma partida registrada neste dia.",
                                   font=tema.fonte_pequena(), text_color=tema.COR_TEXTO_SECUNDARIO)
        botao_primario(self, "+ Adicionar partida", self.adicionar, largura=200, altura=38).pack(
            anchor="w", pady=(10, 0))
        self._reorganizar()

    def adicionar(self, valores: dict | None = None, avisar: bool = True) -> None:
        if valores is None:
            # Nova partida já vem com o agente da anterior (o mais comum é repetir).
            valores = {"agente": self._cartoes[-1].agente if self._cartoes else None}
        cartao = CartaoPartida(self, valores)
        self._cartoes.append(cartao)
        self._reorganizar()
        if avisar:
            self.mudou()

    def remover(self, cartao: CartaoPartida) -> None:
        self._cartoes.remove(cartao)
        cartao.destroy()
        self._reorganizar()
        self.mudou()

    def _reorganizar(self) -> None:
        for numero, cartao in enumerate(self._cartoes, start=1):
            cartao.numerar(numero)
            cartao.pack(fill="x", pady=4)
        if self._cartoes:
            self._vazio.pack_forget()
        else:
            self._vazio.pack(anchor="w", pady=4)

    def mudou(self) -> None:
        for cartao in self._cartoes:
            cartao.atualizar_kd()
        if self._ao_mudar:
            self._ao_mudar()

    def get(self) -> list[dict]:
        return [cartao.get() for cartao in self._cartoes]

    def set(self, partidas: list[dict] | None) -> None:
        for cartao in self._cartoes:
            cartao.destroy()
        self._cartoes = []
        for valores in partidas or []:
            self.adicionar(valores, avisar=False)
        self._reorganizar()
        for cartao in self._cartoes:
            cartao.atualizar_kd()
