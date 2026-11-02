# ValDiary

Diário pessoal de rotina e desempenho no **Valorant**, para Windows.

A ideia é registrar todos os dias como foi a rotina (sono, alimentação, hidratação, disposição, estresse) e como foi o jogo (K/D/A, ACS, ADR, HS%, sensação da mira, concentração...) para, com o tempo, encontrar **padrões** entre hábitos e desempenho:

- o que costuma acontecer nos melhores dias;
- o que muda nos piores dias;
- quais condições parecem favorecer mira, concentração e tomada de decisão.

O app **não inventa relações de causa e efeito**. Ele mostra correlações e avisa quando não há dados suficientes para concluir algo.

Tudo funciona **localmente**: sem servidor, sem conta, sem internet. Os dados ficam em arquivos JSON legíveis, prontos para backup ou para enviar a uma IA (como o ChatGPT) fazer análises mais profundas.

---

## Funcionalidades

| | Funcionalidade | Status |
|---|---|---|
| 📝 | **Registro diário** em abas (Rotina / Valorant / Anotações), com notas de 1 a 10 por clique | ✅ |
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
└── _rascunho.json          ← formulário não salvo (temporário)
```

- As semanas seguem o padrão **ISO 8601** (começam na segunda-feira). Por isso, alguns dias do início de janeiro pertencem à última semana do ano anterior. Exemplo: 01/01/2027 fica em `2026/semana_53.json`.
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
  "versao_schema": 1,
  "ano": 2026,
  "semana": 45,
  "periodo": { "inicio": "2026-11-02", "fim": "2026-11-08" },
  "dias": [
    {
      "data": "2026-11-02",
      "dia_semana": "segunda",
      "classificacao": "bom",
      "rotina": {
        "sono": { "dormiu_as": "23:30", "acordou_as": "07:45", "horas": 8.25, "qualidade": 8 },
        "alimentacao": {
          "cafe_da_manha": { "horario": "08:00", "descricao": "Pão e ovos" },
          "almoco": { "horario": "12:30", "descricao": "Arroz, feijão e frango" },
          "jantar": { "horario": null, "descricao": null },
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
        "partidas": 4, "vitorias": 3, "derrotas": 1, "empates": null,
        "abates": 72, "mortes": 55, "assistencias": 20,
        "acs": 245, "adr": 158.4, "hs_pct": 27.5,
        "agentes": ["Jett", "Raze"],
        "avaliacao": { "mira": 9, "movimentacao": 8, "tomada_decisao": 7, "concentracao": 8, "consistencia": 7 },
        "notas": "Consegui fazer microajustes com facilidade.",
        "derivados": { "kd": 1.31, "kda": 1.67, "kda_texto": "72/55/20", "winrate_pct": 75.0 }
      },
      "criado_em": "2026-11-02T23:40:02",
      "editado_em": null
    }
  ]
}
```

- **K/D/A** são os totais somados do dia. **ACS, ADR e HS%** são médias por partida.
- O bloco `derivados` é calculado automaticamente, nunca digitado.

---

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
tests/                   testes automáticos (pytest)
```

A interface nunca lê ou grava arquivos diretamente: tudo passa pelo `storage`. Isso concentra as regras de segurança dos dados num lugar só e permite testar o armazenamento sem abrir janelas.

## Tecnologias

Python · CustomTkinter · pandas · Matplotlib · pytest
