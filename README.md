# ValDiary

Diário pessoal de rotina e desempenho no **Valorant**, para Windows.

A ideia é registrar todos os dias como foi a rotina (sono, alimentação, hidratação, disposição, estresse) e como foi o jogo, partida a partida (agente, resultado, K/D/A, ACS, HS%, RR, sensação da mira, concentração...) para, com o tempo, encontrar **padrões** entre hábitos e desempenho:

- o que costuma acontecer nos melhores dias;
- o que muda nos piores dias;
- quais condições parecem favorecer mira, concentração e tomada de decisão.

O app **não inventa relações de causa e efeito**. Ele mostra correlações e avisa quando não há dados suficientes para concluir algo.

Tudo funciona **localmente**: sem servidor, sem conta, sem internet. Os dados ficam em arquivos JSON legíveis, prontos para backup ou para enviar a uma IA (como o ChatGPT) fazer análises mais profundas.

---

## Funcionalidades

| | Funcionalidade | Status |
|---|---|---|
| 🎨 | **Visual no estilo Valorant** (v3): grafite e vermelho, tipografia condensada, ícone próprio | ✅ |
| 📝 | **Registro diário** em abas (Rotina / Valorant / Partidas / Anotações), com notas de 1 a 10 por clique | ✅ |
| 🕒 | Horários escolhidos em menus (sem digitação) e refeições marcadas por caixa | ✅ |
| 🎮 | **Registro por partida** (agente pela bandeja de fotos, resultado, K/D/A, HS%, ACS) com resumo do dia calculado | ✅ |
| 📅 | Validador de data: não deixa registrar dias já preenchidos nem datas futuras | ✅ |
| 💊 | **Medicamentos × desempenho**: quanto tempo antes do jogo cada medicamento foi tomado e como o desempenho variou | ✅ |
| 🏆 | **Ranking**: aba própria para definir o elo; o app aplica o RR de cada partida (com proteção contra rebaixamento) | ✅ |
| 🧮 | Cálculo automático de horas de sono, K/D, KDA e winrate | ✅ |
| 💾 | **Rascunho automático**: nada se perde se o app fechar antes de salvar | ✅ |
| 📚 | **Histórico** com filtros por classificação, período e busca nas anotações | ✅ |
| 🏠 | **Tela inicial** com resumo da semana comparado à semana anterior | ✅ |
| 📤 | Exportar / importar semanas em JSON, com legenda e prompt pronto para o ChatGPT | ✅ |
| 📈 | Dashboard com evolução no tempo, média móvel e média por tipo de dia | ✅ |
| ⚖️ | Comparação entre dias bons e ruins, correlações e hábitos frequentes | ✅ |
| 📦 | Executável `.exe` para Windows | 🔜 |

---

## Como rodar

Requisitos: **Windows 10/11** e **Python 3.12+** (desenvolvido com Python 3.15).

```powershell
git clone https://github.com/gustavaress/ValDiary.git
cd ValDiary

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

python main.py
```

Para rodar os testes automáticos:

```powershell
python -m pytest
```

---

## Onde ficam os dados

Os registros ficam na pasta `dados/`, dentro do projeto (ou ao lado do `.exe`, quando empacotado). Há um botão **"Abrir pasta de dados"** no menu do app.

```
dados/
├── 2026/
│   ├── semana_44.json      ← um arquivo por semana
│   └── semana_45.json
├── _backups/               ← versões anteriores de cada semana (últimas 10)
├── _exportacoes/
├── ranking.json            ← seu ranking atual + ajustes manuais da aba Ranking
└── _rascunho.json          ← formulário não salvo (temporário)
```

- As semanas vão de **domingo a sábado**. A semana 1 é a primeira com pelo menos 4 dias no ano novo, então alguns dias do início de janeiro pertencem à última semana do ano anterior. Exemplo: 02/01/2027 fica em `2026/semana_53.json`; o domingo 03/01/2027 abre `2027/semana_01.json`.
- Ao atualizar de uma versão com semanas de segunda a domingo, o app reorganiza os arquivos **uma única vez**, guardando antes uma cópia em `_backups/antes_semana_domingo_<data>/`.
- A pasta `dados/` está no `.gitignore`: seus registros pessoais **não vão para o GitHub**.

### Segurança dos dados

- **Escrita atômica:** o arquivo é gravado num temporário e só então substitui o original. Uma queda de energia no meio da gravação não corrompe a semana.
- **Backup automático** antes de cada alteração.
- **Arquivos corrompidos nunca são sobrescritos.** O app avisa, ignora o arquivo e continua funcionando com os outros.
- **Uma data = um registro.** Não há duplicação; salvar de novo a mesma data é uma edição.

### Formato do JSON

Campos não preenchidos ficam como `null` ("não registrado" é diferente de zero). Notas subjetivas vão de 1 a 10 (em `estresse`, 10 = muito estressado).

```json
{
  "versao_schema": 4,
  "ano": 2026,
  "semana": 45,
  "periodo": { "inicio": "2026-11-01", "fim": "2026-11-07" },
  "dias": [
    {
      "data": "2026-11-02",
      "dia_semana": "segunda",
      "classificacao": "bom",
      "rotina": {
        "sono": { "dormiu_as": "23:30", "acordou_as": "07:45", "horas": 8.25, "qualidade": 8 },
        "alimentacao": {
          "cafe_da_manha": { "realizada": true, "horario": "08:00", "descricao": "Pão e ovos" },
          "almoco": { "realizada": true, "horario": "12:30", "descricao": "Arroz, feijão e frango" },
          "jantar": { "realizada": null, "horario": null, "descricao": null },
          "outros": null
        },
        "agua_litros": 2.5,
        "bebidas": [{ "tipo": "café", "quantidade": "1 xícara", "horario": "09:00" }],
        "medicamentos": [],
        "disposicao_fisica": 7,
        "disposicao_mental": 8,
        "estresse": 3,
        "observacoes": "Dia tranquilo."
      },
      "valorant": {
        "jogou": true,
        "horario_inicio": "19:30",
        "horario_fim": "23:00",
        "partidas": [
          { "agente": "Jett", "resultado": "vitoria", "abates": 20, "mortes": 15, "assistencias": 5, "hs_pct": 30.0, "acs": 260, "rr": 21 },
          { "agente": "Raze", "resultado": "derrota", "abates": 14, "mortes": 16, "assistencias": 6, "hs_pct": 22.0, "acs": 190, "rr": -16 }
        ],
        "avaliacao": { "mira": 9, "movimentacao": 8, "tomada_decisao": 7, "concentracao": 8, "consistencia": 7 },
        "notas": "Consegui fazer microajustes com facilidade.",
        "legado": null,
        "resumo": {
          "partidas": 2, "vitorias": 1, "derrotas": 1, "empates": 0,
          "abates": 34, "mortes": 31, "assistencias": 11, "hs_pct": 26.0, "acs": 225.0,
          "agentes": { "Jett": 1, "Raze": 1 }, "partidas_com_resultado": 2, "rr": 5,
          "kd": 1.1, "kda": 1.45, "kda_texto": "34/31/11", "winrate_pct": 50.0
        }
      },
      "criado_em": "2026-11-02T23:40:02",
      "editado_em": null
    }
  ]
}
```

- Cada item de `partidas` é **uma partida**. O bloco `resumo` é **calculado** a partir delas (nunca digitado): K/D/A são totais do dia, ACS e HS% são médias por partida, e o winrate considera só as partidas com resultado marcado.
- `legado`: dias registrados antes do registro por partida guardam ali os totais digitados na época (incluindo o ADR, que não é mais usado). Eles continuam entrando nas análises.
- Refeições: `"realizada": true` quando a caixa foi marcada; `null` quando não (não teve ou não registrou).

### Versões do formato

O campo `versao_schema` indica o formato do arquivo. Quando o formato muda, o app **converte arquivos antigos automaticamente ao ler** (veja `app/storage/migracoes.py`). O arquivo em disco só é atualizado quando aquela semana for salva de novo, e a versão anterior fica guardada em `_backups/`.

| Versão | Mudança |
|---|---|
| 1 | Formato inicial |
| 2 | Refeições ganham `realizada`; `agentes` passa de lista de nomes para `{nome, partidas}` |
| 3 | Valorant registrado **por partida**; totais antigos do dia vão para `legado`; ADR sai das análises |
| 4 | RR por partida (o ranking fica em `dados/ranking.json`); semanas passam a ir de **domingo a sábado** |

## Imagens dos agentes

O app usa miniaturas de 128 px em `assets/agentes/`, geradas a partir das imagens originais em `assets/agentes/originais/` (arquivos `<Nome>_icon.png`). Os originais são grandes e ficam **fora do Git**; só as miniaturas e o catálogo `agentes.json` são versionados.

Para adicionar um agente novo ou trocar uma imagem:

1. Coloque o arquivo em `assets/agentes/originais/` (ex.: `NovoAgente_icon.png`).
2. Inclua a função dele no dicionário `FUNCOES` de `scripts/gerar_agentes.py`.
3. Rode:

```powershell
python scripts/gerar_agentes.py
```

> ValDiary não é endossado pela Riot Games e não reflete as opiniões da Riot Games nem de ninguém oficialmente envolvido na produção ou gestão de propriedades da Riot Games. Riot Games e todas as propriedades associadas são marcas registradas da Riot Games, Inc.

---

## Ranking

- Na aba **Ranking**, ajuste seu **elo e RR** e a data a partir da qual valem. Normalmente isso é feito uma vez; refaça só se o cálculo ficar diferente do jogo.
- **Sempre que um dia é salvo** (ou editado, excluído, importado), o app recalcula e grava o seu ranking ao fim do último dia registrado em `dados/ranking.json` (campo `atual`), junto com os ajustes manuais (campo `definicoes`). A aba Ranking e a tela inicial mostram esse valor.
- No **registro diário**, informe apenas o **RR ganho ou perdido em cada partida** (ex.: `-20`, `+17`). O app calcula o ranking partida a partida, na ordem:
  - chegar a 100 RR promove (o excedente vai para o elo seguinte);
  - **proteção contra rebaixamento**: perder com RR acima de 0 zera os pontos, sem cair de elo;
  - perder já com 0 RR rebaixa para o elo anterior com 100 menos a perda;
  - no Imortal e no Radiante o RR só acumula (a divisão depende do ranking global).
- Exemplo: Ascendente 3 com 1 RR, perde 20 (zera) e ganha 17 → **Ascendente 3 com 17 RR**.
- O ranking é sempre recalculado a partir das definições e das partidas, então registrar um dia antigo ou corrigir um RR ajusta tudo sozinho. É uma estimativa das regras do jogo.

## Como a comparação funciona

- **Dias bons** = Excelente + Bom; **dias ruins** = Ruim + Péssimo. Dias normais ficam de fora.
- Toda média mostra o **n** (quantos dias têm aquele dado). Com menos de **5 dias** em algum grupo, o app avisa que a diferença pode ser acaso.
- As **correlações** usam o coeficiente de Spearman entre cada métrica e a classificação do dia (1 = péssimo ... 5 = excelente) e exigem pelo menos **10 dias**.
- O app fala em **associação**, nunca em causa: dormir mais pode acompanhar dias bons sem ser o motivo deles.

## Analisando no ChatGPT

1. Em **Importar / Exportar**, marque as semanas e clique em **Exportar selecionadas**.
2. Clique em **Copiar prompt para o ChatGPT**.
3. No ChatGPT, anexe o arquivo `.json` e cole o prompt.

O arquivo exportado traz um bloco `_legenda` explicando escalas, unidades e o significado de `null`, para a IA não interpretar nada errado.

## Visual

- **Paleta**: grafite quase preto, cinzas escalonados, texto off-white e o vermelho `#FF4655` como acento (item ativo, ações principais, marcações).
- **Tipografia**: [Bebas Neue](https://fonts.google.com/specimen/Bebas+Neue) nos títulos e números e [Barlow](https://fonts.google.com/specimen/Barlow) no texto. As duas têm licença livre (SIL OFL, arquivos em `assets/fontes/`) e são carregadas pelo próprio app, sem precisar instalar.
- **Gráficos**: uma série usa o vermelho da marca; na comparação, dias bons em azul e dias ruins em vermelho (par validado para daltonismo e contraste).
- Toda a identidade fica em `app/ui/tema.py` (cores, fontes e o tema global do CustomTkinter). Os botões padronizados ficam em `app/ui/componentes/botoes.py`.
- O logo (um "V" angular, desenho próprio) é gerado por código em `app/ui/logo.py`, que também gera `assets/icone.ico`.

## Estrutura do projeto

```
main.py                  ponto de entrada
app/
├── config.py            caminhos, escalas e versão do formato
├── models/              o que são os dados (dataclasses + validação)
├── storage/             como os dados são salvos (única camada que toca o disco)
├── analysis/            filtros e resumos (sem interface)
└── ui/                  interface CustomTkinter
    ├── componentes/     widgets reutilizáveis (seletor de nota, listas...)
    └── telas/           uma tela por arquivo
assets/agentes/          miniaturas dos agentes + catálogo (gerados por scripts/gerar_agentes.py)
assets/fontes/           Bebas Neue e Barlow (licença OFL)
assets/icone.ico         ícone da janela (gerado por app/ui/logo.py)
scripts/                 utilitários de desenvolvimento
tests/                   testes automáticos (pytest)
```

A interface nunca lê ou grava arquivos diretamente: tudo passa pelo `storage`. Isso concentra as regras de segurança dos dados num lugar só e permite testar o armazenamento sem abrir janelas.

## Tecnologias

Python · CustomTkinter · pandas · Matplotlib · Pillow · pytest · fontes Bebas Neue e Barlow (OFL)
