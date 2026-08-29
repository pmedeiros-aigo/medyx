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
"unimed_natal"`. A aplicação lê **quatro** arquivos, todos em `marts/`:
`fato_solicitacoes.parquet`, `contas.parquet`,
`dim_executantes_cooperado.parquet` e `dim_classificacao.csv`. Os CSVs brutos
de `dados_iniciais/` são insumo do `preparar_fato` (o 6º motor) e não são lidos
em runtime.

Se algum dos quatro faltar, o servidor **não sobe**: `dados.verificar_marts()`
roda no boot e diz exatamente o que está faltando.

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

### Entrar com uma sessão (tela Minha conta)

**O app ainda não tem login.** O Cognito é a decisão tomada, e ainda não foi
ligado. Enquanto isso, o comportamento normal é o de quem não está autenticado:

- o rodapé da barra lateral fica vazio, **sem bloco de conta**;
- `/conta` monta e declara que não há sessão.

Isso é deliberado, não uma tela pela metade: sem autenticação, um nome fixo na
tela seria ficção, e ficção em produto de auditoria custa confiança.

Para construir ou conferir a tela com uma sessão, existe um override **de
desenvolvimento**:

```bash
export MEDYX_SESSAO_DEV="Seu Nome <seu.email@exemplo.com>"
uvicorn app.api:app --reload --port 8770
```

Com ele, o bloco de conta aparece no rodapé da lateral (nome, e-mail, e o menu
com "Minha conta" e "Sair") e `/conta` mostra a tela cheia.

Três coisas que ele NÃO é:

1. **Não é login.** Vale para o servidor inteiro, não para um navegador. Quem
   abrir o app é essa pessoa.
2. **Não prova que o Sair funciona.** A rota apaga o cookie de sessão, mas a
   identidade vem da variável de ambiente, que continua lá. O logout de verdade
   só existe com o provedor de identidade.
3. **Não sobrevive ao Cognito.** Sessão real tem precedência no `app/sessao.py`,
   então a variável deixa de ter efeito mesmo se alguém esquecer de removê-la.

## Provas

```bash
python smoke_fase3.py    # os motores reproduzem o notebook de referência
python smoke_api.py      # a API entrega o gabarito (exige o servidor no ar)
python smoke_front.py    # as telas montam sem erro de console (idem)
```

Estado em 29/ago/2026: `smoke_fase3.py` e `smoke_api.py` **passam inteiros**.

`smoke_front.py` **aborta na seção 2** e por isso as seções 3 a 11 não chegam a
rodar. A causa está nas seções 1 e 2, da tela de Área: a suíte procura elementos
(`.stats`, `.selperfil`, os chips de recorte) que a reestruturação de agosto
tirou da página, e o clique num chip que não existe estoura por timeout. É o
teste que está atrasado em relação à tela, não a tela que quebrou.

Consequência prática: **hoje o `smoke_front.py` não prova nada além da seção 1.**
A seção 10 (tela de conta) foi conferida à parte, com um script equivalente, nos
dois estados (com e sem sessão). Destravar a suíte pede atualizar as seções 1 e
2 para a tela de Área como ela ficou.

---

## Arquitetura

| Camada | Tecnologia |
| --- | --- |
| API | FastAPI, serve JSON **e** os estáticos |
| Interface | HTML/CSS/JS puro, sem build e sem npm |
| Análise | pandas, sobre Parquet |
| Contrato visual | `app/static/css/`, editado aqui (o Claude Design foi a origem, não é mais a fonte da verdade) |

```
app/
├── api.py            FastAPI: entrega os blocos da tela; não calcula nada
├── sessao.py         quem está usando o app; o Cognito entra só aqui
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
| `ESPECIFICACAO_FUNCIONAL_APP.md` | o que cada tela de ANÁLISE mostra |
| `DIRETRIZES_PRODUTO_UI.md` | padrão de produto e UX do front |
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
