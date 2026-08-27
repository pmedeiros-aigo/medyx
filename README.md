# Medyx

Plataforma de análise de utilização de SADT para a **Unimed Natal-RN**, com
foco inicial em Ginecologia e Obstetrícia.

O objetivo: classificar cooperados por **área de atuação**, comparar cada um
**dentro do seu grupo de pares**, e identificar variação não justificada que
mereça revisão. A classificação é a fundação; a inteligência de custo é o
produto.

> **Estado: em desenvolvimento.** A classificação de áreas está na versão 1.0 e
> **não foi homologada clinicamente**. Os valores em R$ usam preços internos
> provisórios, apurados nas contas, ainda não confrontados com a tabela
> contratual. Nenhum número desta aplicação deve ser usado como veredito.

---

## Antes de rodar: os dados ficam FORA do repositório

Este repositório contém **apenas código e documentação**. Nenhuma base de
beneficiários ou de cooperados sobe para o git.

A aplicação espera encontrar os dados numa pasta **irmã** do repositório:

```
<pasta-de-trabalho>/
├── medyx/            ← este repositório
└── unimed_natal/     ← os dados (NÃO versionado, ~1 GB)
    ├── dados_iniciais/    bases brutas em CSV
    ├── marts/             fato e dimensões em Parquet
    └── dados/             classificacao_v1.csv
```

O caminho é resolvido em `config.py` como `Path(__file__).parent.parent /
"unimed_natal"`. Sem essa pasta no lugar, a aplicação sobe e falha na primeira
consulta.

Os arquivos são obtidos com a equipe responsável; não há download automatizado.

---

## Ambiente

Python 3.13, no ambiente global `global-env`. **Não criar venv local** (ver
`CLAUDE.md`).

```bash
source ~/.venvs/global-env/bin/activate
pip install -r requirements.txt
```

## Rodar

Sempre a partir da raiz deste repositório.

```bash
uvicorn app.api:app --reload --port 8770
```

- Aplicação: <http://127.0.0.1:8770>
- Documentação da API: <http://127.0.0.1:8770/docs>

A primeira requisição após subir o servidor custa de 20 a 60 segundos: os
motores leem o Parquet e calculam a norma de todas as áreas. As seguintes são
servidas de cache. **Editar um arquivo `.py` reinicia o servidor e zera esse
cache**, então a requisição seguinte volta a pagar o custo integral.

## Provas

```bash
python smoke_fase3.py    # os motores reproduzem o notebook de referência
python smoke_api.py      # a API entrega o gabarito (exige o servidor no ar)
python smoke_front.py    # as telas montam sem erro de console (idem)
```

`smoke_fase3.py` está em dia. `smoke_api.py` e `smoke_front.py` estão
**desatualizados** em relação à reestruturação de agosto e falham em pontos que
mudaram por decisão de produto; ver `PENDENCIAS.md`.

---

## Arquitetura

| Camada | Tecnologia |
| --- | --- |
| API | FastAPI, serve JSON **e** os estáticos |
| Interface | HTML/CSS/JS puro, sem build e sem npm |
| Análise | pandas, sobre Parquet |
| Contrato visual | projeto no Claude Design, sincronizado para `app/static/css/` |

```
app/
├── api.py            FastAPI: entrega os blocos da tela; não calcula nada
├── utils/
│   ├── pipeline.py       os motores analíticos
│   ├── preparar_fato.py  ingestão CSV bruto → fato + dimensões
│   ├── dados.py          única porta para dado e cálculo (cargas memoizadas)
│   ├── cascata.py        a qualificação em degraus
│   ├── blocos.py         monta os blocos da tela
│   └── apresentacao.py   textos institucionais
└── static/           o front: shell, blocos, páginas, lib
```

**Duas regras invioláveis**, detalhadas no `CLAUDE.md`:

1. **O JavaScript não calcula.** Todo número exibido vem de uma função Python.
2. **Nenhum valor da metodologia fora do `config.py`.**

---

## Documentação

Cada assunto tem um dono. Não duplicar conteúdo entre eles.

| Documento | É dono de |
| --- | --- |
| `CLAUDE.md` | regras operacionais de como construir |
| `CONTEXTO_NEGOCIO.md` | estratégia, valor, por quê |
| `METODOLOGIA_ANALITICA.md` | como calcular (método, sem números) |
| `ESPECIFICACAO_FUNCIONAL_APP.md` | o que cada tela mostra |
| `LEXICO_PRODUTO.md` | vocabulário da interface |
| `PENDENCIAS.md` | o que está em aberto |
| `config.py` | todos os valores numéricos da metodologia |

Regra da separação: **método** mora no `METODOLOGIA_ANALITICA.md` e nunca
contém número; **valor** mora no `config.py` e nunca é escrito fora dele.

---

## Privacidade

- Nenhum dado de beneficiário ou de cooperado entra neste repositório.
- Cooperados são identificados por rótulo pseudonimizado (`cooperado_N`); não
  há nome, CRM nem CPF no código.
- As leituras por paciente são sempre **contagens agregadas**. A aplicação não
  expõe análise individual de beneficiário.
