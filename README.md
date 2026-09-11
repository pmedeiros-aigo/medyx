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
    └── classificacao_cooperados.ipynb   a classificação v2 (gera a dim em marts/)
```

O caminho é resolvido em `config.py` como `Path(__file__).parent.parent /
"unimed_natal"`. A aplicação lê **quatro** arquivos, todos em `marts/`:
`fato_solicitacoes.parquet`, `contas.parquet`,
`dim_executantes_cooperado.parquet` e `dim_classificacao_v2.csv`. Os CSVs brutos
de `dados_iniciais/` são insumo do `preparar_fato` (o 6º motor) e não são lidos
em runtime.

Para (re)gerar o fato e as dimensões a partir dos CSVs brutos e da dim v2:

```bash
python preparar_marts.py
```

A dim v2 (`dim_classificacao_v2.csv`) sai do notebook
`unimed_natal/classificacao_cooperados.ipynb` (Parte 15) e está documentada em
`unimed_natal/marts/LEIAME_classificacao_v2.md`. A `AREA_ATUACAO` do fato é a
`area_mvp` dessa dim.

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

**O login existe desde set/2026** (Cognito, fluxo de código de autorização com
PKCE), e **só liga com as variáveis de ambiente abaixo**. Sem elas o app se
comporta como sempre se comportou: aberto, e sem sessão.

```bash
export MEDYX_COGNITO_REGIAO="sa-east-1"
export MEDYX_COGNITO_POOL_ID="sa-east-1_ylgQdMTxL"
export MEDYX_COGNITO_CLIENT_ID="6mk459t02pdg53v3ss816d2h86"
export MEDYX_COGNITO_DOMINIO="sa-east-1ylgqdmtxl.auth.sa-east-1.amazoncognito.com"
export MEDYX_URL_BASE="http://localhost:8770"
export MEDYX_CHAVE_SESSAO="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
```

São **seis, e as seis são obrigatórias**: faltando qualquer uma, o login fica
desligado inteiro. Provedor sem chave de sessão diria quem é a pessoa e não
teria onde guardar a resposta.

Ligado, o app fecha: quem não tem sessão vai para `/entrar`, e `/api/*` responde
401 em vez de redirecionar (o front espera JSON, não HTML). Ficam abertos só
`/entrar`, `/auth/*`, `/static/*` e `/sair`.

`MEDYX_URL_BASE` monta o endereço de retorno, e ele precisa estar cadastrado
nas *callback URLs* do app client, **idêntico até a barra final**. Divergência
aí é o erro mais comum do fluxo, e aparece como `redirect_mismatch` na tela do
Cognito antes mesmo de pedir a senha.

Desligado, o comportamento é o de quem não está autenticado:

- o rodapé da barra lateral fica vazio, **sem bloco de conta**;
- `/conta` monta e declara que não há sessão.

Isso é deliberado, não uma tela pela metade: sem autenticação, um nome fixo na
tela seria ficção, e ficção em produto de auditoria custa confiança.

Para construir ou conferir a tela com uma sessão **sem subir o Cognito**, existe
um override **de desenvolvimento**:

```bash
export MEDYX_SESSAO_DEV="Seu Nome <seu.email@exemplo.com>"
uvicorn app.api:app --reload --port 8770
```

Com ele, o bloco de conta aparece no rodapé da lateral (nome, e-mail, e o menu
com "Minha conta" e "Sair") e `/conta` mostra a tela cheia.

Três coisas que ele NÃO é:

1. **Não é login.** Vale para o servidor inteiro, não para um navegador. Quem
   abrir o app é essa pessoa.
2. **Não prova que o Sair funciona.** A rota limpa a sessão, mas a identidade
   vem da variável de ambiente, que continua lá. Com o Cognito ligado, o Sair
   encerra as duas pontas: a sessão do Medyx e a do provedor.
3. **Não sobrevive ao Cognito.** Sessão real tem precedência no `app/sessao.py`,
   então a variável deixa de ter efeito mesmo se alguém esquecer de removê-la.

## Provas

```bash
python smoke_fase3.py    # os motores reproduzem o notebook de referência
python smoke_api.py      # a API entrega o gabarito (exige o servidor no ar)
python smoke_front.py    # as telas montam sem erro de console (idem)
```

Estado em 11/set/2026 (classificação v2.0): as três suítes **passam inteiras**.
`smoke_front.py` roda as 11 seções; a seção 10 (tela de conta) só passa com o
servidor levantado **sem** `MEDYX_SESSAO_DEV`, porque prova o estado "não
autenticado". Os gabaritos (`config.SMOKE_*`) foram re-baselineados na v2: área
de referência Ginecologia Geral; positivos em Endoscopia Ginecológica.

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
├── sessao.py         quem está usando o app: identidade e duração da sessão
├── cognito.py        o protocolo OAuth com o provedor, e nada além dele
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
