# CLAUDE.md — Medyx / Unimed Natal

Regulamento operacional do Claude Code neste projeto.
Ler integralmente no início de cada sessão antes de tocar em qualquer código.

---

## O que é este projeto

**Medyx** é um app de dados (FastAPI + front vanilla) para a Unimed Natal-RN, foco inicial em Ginecologia &
Obstetrícia (202 cooperados). Fase de MVP — funcionalidades e escopo analítico ainda em definição.

O objetivo analítico: classificar cooperados por **área de atuação**, comparar de forma justa
**dentro de cada peer group**, e identificar **oportunidades de redução de custo** (variação não
justificada). A classificação é a fundação; a inteligência de custo é o produto.

---

## Mapa dos documentos — quem é dono de quê

Cada assunto tem UM dono. Não duplicar conteúdo entre eles; apontar.


| Documento                       | É dono de…                                    | Ler quando                          |
| ------------------------------- | --------------------------------------------- | ----------------------------------- |
| `CLAUDE.md` (este)              | regras operacionais de como construir         | toda sessão                         |
| `CONTEXTO_NEGOCIO.md`           | estratégia, valor, por quê                    | antes de sugerir/avaliar feature    |
| `METODOLOGIA_ANALITICA.md`      | **como calcular** (método, pipeline, regras)  | antes de qualquer cálculo analítico |
| `ESPECIFICACAO_FUNCIONAL_APP.md`| **o que cada página mostra** (elemento←motor) | antes de construir/alterar tela     |
| `DIRETRIZES_PRODUTO_UI.md`      | **padrão de produto e UX do front**           | antes de construir/alterar tela     |
| `LEXICO_PRODUTO.md`             | **vocabulário da UI** (interno → institucional)| antes de escrever rótulo/texto     |
| `config.py`                     | **todos os valores numéricos** (fonte única)  | sempre que precisar de um número    |
| `app/static/css/`               | **o contrato visual** (tokens, componentes)   | toda sessão que toque a camada visual |
| skill `rigor-estatistico`       | reflexo estatístico (armadilhas)              | dispara em cálculo/comparação       |


Regra de ouro da separação: **método** mora no `METODOLOGIA_ANALITICA.md` e nunca contém número;
**valor** mora no `config.py` e nunca é hardcoded fora dele. Os dois se referenciam por nome.

---

## Stack


Streamlit foi **abandonado** (jul/2026). Nenhum código Streamlit vive mais em `app/`.

| Camada         | Tecnologia                      | Notas                                                     |
| -------------- | ------------------------------- | --------------------------------------------------------- |
| API            | **FastAPI**                     | Serve JSON **e** os estáticos — não renderiza HTML        |
| UI             | **HTML/CSS/JS vanilla**         | Sem build, sem npm, sem framework                         |
| Analytics      | **pandas** (DuckDB onde couber) | Motores em `app/utils/pipeline.py`, sobre Parquet         |
| Dados          | CSV brutos → Parquet (marts)    | Raw em `../unimed_natal/dados_iniciais/`, marts a definir |
| Charts         | **ECharts** via CDN             | Configurado a partir dos tokens `--ch-*` do guia          |
| IA             | **Anthropic Claude API**        | Tool calling, respostas em português                      |
| Python         | `global-env` (ver abaixo)       | Python 3.13                                               |
| Cloud (futuro) | AWS S3 + EC2                    | Não é prioridade agora                                    |

**Regra inviolável do front:** JavaScript **não calcula nada**. Todo número exibido vem de
uma função Python do pipeline, via JSON. Valor que não existe no motor não aparece na tela.

## Contrato visual — o repositório é a fonte da verdade (desde 29/ago/2026)

**O Claude Design deixou de ser a fonte da verdade.** Decisão do usuário, 29/ago/2026.

Ele foi a origem do sistema visual e continua sendo a GENEALOGIA de quase tudo que
está em `app/static/css/`. Não é mais o dono: o dono é este repositório.

| | |
| --- | --- |
| Fonte da verdade | `app/static/css/tokens.css` e `app/static/css/components.css` |
| Editar | à mão, aqui, como qualquer outro arquivo do projeto |
| Sincronização | **não existe mais** — nada é sobrescrito, nada precisa ser reaplicado |
| Claude Design | arquivo histórico. `/guia` continua abrindo o projeto de origem |

### O que caducou com a mudança

- **Regra 1 (sincronizar e reler antes de escrever marcação).** Não há mais o que
  sincronizar. Continua valendo a parte útil dela: **ler o CSS antes de montar
  marcação**, porque pode já existir a classe que você ia escrever à mão.
- **Regra 2 (componente que falta: parar e descrever).** Componente ou estado que
  falta agora é **construído aqui**. Não se descreve e encaminha mais.
- **A lista de "desvios autorizados".** Existia para sobreviver à sincronização.
  Sem sincronização, não há desvio: são regras normais do arquivo.

### O que NÃO mudou

1. **Token continua sendo a única origem** de cor, espaço, tipo, raio e sombra.
   Componente novo COMPÕE token existente. Valor solto no meio de uma regra
   (`#17624A`, `13px`, `border-radius:7px`) continua sendo defeito. Token novo é
   decisão consciente, anunciada, não um valor que apareceu.
2. **Um token, um significado.** Continua valendo, e é a razão de o item 8 do
   `PENDENCIAS.md` (o âmbar de `tr.acima`) seguir aberto: agora ele é resolvível
   aqui mesmo, sem ida ao Design.
3. **Não criar duas versões do mesmo componente** (DIRETRIZES §5). Foi por isso
   que `.side-user .av` virou `.av` + `.av-lg` quando a tela de conta precisou do
   mesmo círculo maior, em vez de nascer um `.conta-av`.
4. **JavaScript não decide aparência.** Ele alterna classe e escreve estado ARIA;
   quem desenha é o CSS. Proibido `style=` inline, cor ou medida em JS.

### Componentes escritos neste repositório

Vivem no fim do `components.css`, sob o cabeçalho `COMPONENTES NOVOS`. Hoje:

| Classe | O que é | Nasceu em |
| --- | --- | --- |
| `.av` · `.av-lg` | avatar de iniciais (promovido de `.side-user .av`) | tela de conta |
| `.menu-anc` · `.menu` · `.menu-item` · `.menu-sep` | menu de AÇÕES que sai de um gatilho (diferente do `.pop`, que é ESCOLHA) | bloco de conta |
| `.deflist` · `.def-row` · `.def-k` · `.def-v` · `.def-act` | linha de atributo: rótulo, valor, apoio e ação opcional | tela de conta |
| `.leitura` | coluna estreita (720px) para tela sem tabela nem gráfico | tela de conta |
| `[hidden]` | garante `display:none` contra especificidade acidental | corrigiu o rodapé da lateral e o painel do dossiê |
| `.hd-ctl` | controle na direita de um `.tbl-hd` (só posicionamento; a aparência é do `.seg`) | seletor de medida do gráfico de distribuição |


### Fronteira de responsabilidade do JavaScript

**O CSS é dono dos estados visuais; o JavaScript é dono de QUANDO eles são aplicados.**
A fronteira sobreviveu à mudança de regime: o que mudou foi quem escreve o CSS, não quem
decide aparência.

No JavaScript, nenhuma decisão visual: apenas **alternar classes que existem no CSS**
e **ler tokens** (`--ch-*` para o gráfico). Proibido: `style=` inline, cor, tamanho,
espaçamento ou fonte definidos em JS, e configurar biblioteca de gráfico com os defaults
dela.

Se um estado de interação — **aberto, ativo, selecionado, desabilitado, carregando,
erro** — não tiver classe no CSS, **escreva a classe** (no bloco COMPONENTES NOVOS),
compondo tokens existentes. O que continua proibido é decidir a aparência DENTRO do JS.

Estado que o leitor de tela precisa anunciar mora no ARIA, e o CSS o lê de lá: uma origem
só para "aberto" (`.side-user[aria-expanded="true"] .car` é o exemplo vivo).

O guia não fornece JavaScript, e isso é deliberado: comportamento de componente já está
expresso como classe de estado, e um terceiro artefato para sincronizar reintroduziria a
ambiguidade que a consolidação num guia único acabou de eliminar.

### Ajustes aprovados ao contrato visual

O guia é o contrato; estes pontos foram decididos DEPOIS dele e prevalecem sobre o
que o arquivo mostra. Qualquer outro desvio precisa de aprovação nova.

1. **A etiqueta "não opera" não existe.** Ausência de atributo não vira etiqueta — célula
   vazia. Só atributos presentes aparecem. (handoff sessão 1)
2. **Percentil nunca viaja sem tradução** em linguagem comum, no hover ou ao lado:
   "P92 · acima de 9 em cada 10 colegas da área". (handoff sessão 1)
3. **Controles marcam o padrão como recomendado** ("P90 ✓ recomendado"); ao desviar,
   aviso discreto com ação de restaurar. (handoff sessão 1)
4. **Variação excedente é sempre o valor real** — inclusive para quem está abaixo do
   critério agregado. *Substitui* o travessão do exemplo do guia, que
   assumia que as duas lentes coincidem. Elas não coincidem: o excedente é medido POR
   PROCEDIMENTO, e um cooperado dentro da referência no agregado pode ter procedimentos
   acima do critério daquele procedimento — pares que já passaram os três portões, a
   lente forte do método. **O critério agregado governa o realce da linha, nunca a
   medição.** Travessão só para quem não tem nenhum procedimento sinalizado (ausência de
   par, não zero medido). (jul/2026)
5. **Os chips de recorte são três, definidos por MÉTODO e idênticos em toda área**:
   *Qualificados* (passou toda a cascata — o último degrau, `confianca_calculavel`) ·
   *Com variação persistente* (`persistente`) · *Todos* (`medidos`). São chaves
   estruturais, não recortes escolhidos pelos números de uma área: chip derivado do dado
   de Ginecologia seria outro em GO ou Mastologia, e **a interface não pode se ajustar
   aos dados de uma área**. Os 7 degraus com seus `n` vivem no painel expansível
   "como esta lista foi filtrada", não na barra de chips. (jul/2026)
6. **O chip default depende da TELA, e não do que a API marca como `default`.**
   - **Área de atuação → *Comparáveis*, ordenado por variação excedente.** (Revisto em
     jul/2026; era *Todos*.) O eixo de recorte é ÚNICO e ANINHADO, cada degrau subconjunto
     do anterior: *Todos* · *Comparáveis* · *Com variação persistente* · *Qualificados*.
     O default não é *Todos* porque este inclui quem está abaixo do volume mínimo, que
     entra na tabela sem posição, sem consistência e sem excedente: abrir a tela nele põe
     em cena linhas que não sustentam comparação. *Todos* fica a um clique, e é lá que
     essas linhas aparecem de propósito, com o motivo declarado em cada coluna que não se
     aplica.
   - **Panorama de Oportunidades → *Qualificados*.** Ali a lista é fila de trabalho, e
     fila começa pelo que já passou todos os portões.
   Consequência para o código: `filtros[].default` e `cascata.default` da API marcam o
   default **do método** (o degrau totalmente qualificado), não o da tela. O front NÃO
   deve adotá-lo cegamente — cada página declara o seu. (jul/2026)


---

## Estrutura do projeto

```
medyx/
├── app/
│   ├── static/                 ← o front vanilla (sem build, sem npm)
│   │   ├── index.html          ← o ÚNICO hospedeiro; o servidor o devolve em toda rota
│   │   ├── inicio.js           ← escolhe o módulo da página pela rota
│   │   ├── css/                ← O CONTRATO VISUAL: tokens + componentes (fonte da verdade)
│   │   ├── shell/              ← o chassi: markup, seletores, régua, migalha
│   │   ├── lib/                ← dom, api, vista, pagina, tabelas (não sabem de domínio)
│   │   ├── blocos/             ← um bloco da tela por arquivo; desenham o que recebem
│   │   └── paginas/            ← orquestram: buscam dados, guardam o estado da vista
│   ├── sessao.py               ← fronteira de autenticação: quem está usando o app
│   └── utils/                  ← motores e acesso a dado (nada de apresentação)
│       ├── pipeline.py         ← os 5 motores analíticos (pipeline canônico)
│       ├── preparar_fato.py    ← 6º motor: ingestão CSV bruto → fato + dims + relatório
│       ├── dados.py            ← única porta para dado e cálculo (cargas + motores cacheados)
│       ├── blocos.py           ← monta os BLOCOS DA TELA a partir da saída dos motores
│       └── apresentacao.py     ← textos institucionais puros (carimbo, justificativa, rótulos)
│   └── api.py                  ← FastAPI: JSON dos blocos + estáticos (não calcula nada)
├── smoke_fase3.py              ← prova de que os motores reproduzem o notebook
├── smoke_api.py                ← prova de que a API entrega o gabarito e os blocos concordam
├── config.py                   ← FONTE ÚNICA de todo valor numérico da metodologia
├── CLAUDE.md                   ← você está aqui (regras operacionais)
├── CONTEXTO_NEGOCIO.md         ← estratégia e produto — ler antes de sugerir features
├── METODOLOGIA_ANALITICA.md    ← método de cálculo — ler antes de qualquer análise
├── requirements.txt
└── .claude/                    ← skills e comandos
```

---

## Como rodar

```bash
# Sempre a partir de medyx/
source ~/.venvs/global-env/bin/activate

# Prova de que os motores reproduzem o notebook (rodar antes de confiar em qualquer número)
python smoke_fase3.py

# API (JSON) + estáticos do contrato visual
uvicorn app.api:app --reload --port 8770      # tela em / · docs em /docs
                                              # /guia redireciona ao Claude Design

# Prova de que a API entrega o gabarito e os blocos da tela concordam entre si
python smoke_api.py                            # exige o servidor no ar

# Prova de que as TELAS montam e respondem (erro de console é falha)
python smoke_front.py                          # exige o servidor no ar
```

---

## Ambiente Python

Usar **sempre** o ambiente global `global-env`. Nunca criar `.venv/` local.

```bash
source ~/.venvs/global-env/bin/activate
pip install <pacote>
```

Python: `/Users/pedromedeiros/.venvs/global-env/bin/python`

---

## Dados

- **Raw** (nunca modificar): `../unimed_natal/dados_iniciais/`
  - `base_contas_gineco_obs_202504_202604.csv` — ~1M linhas, sep=`;`, latin1 (lado executante)
  - `base_requisicoes_gineco_obs_202504_202604.csv` — ~1.3M linhas, sep=`;`, latin1 (lado solicitante)
  - Amostra de **1 ano** fornecida para o MVP.
- **Marts** (processados): `../unimed_natal/marts/` — caminhos no `config.py` (`CAMINHO_*`).
  - `fato_solicitacoes.parquet` — já carrega `AREA_ATUACAO` (classificação v1.0) e `elegivel_norma`
  - `contas.parquet`, `dim_classificacao.csv`, `dim_executantes_cooperado.parquet`
  - Gerados pelo notebook `calculos_iniciais.ipynb` (ou `app/utils/preparar_fato.py`, migração fiel).
- **Classificação**: `../unimed_natal/dados/classificacao_v1.csv` (+ LEIAME com a genealogia).
  v1.0 NÃO homologada — banner de homologação obrigatório em toda página.
- **Eixo temporal** de toda análise = **data de solicitação** (`config.COLUNA_DATA_SOLICITACAO`
= `DT_REQUISICAO`, confirmada). Ver `METODOLOGIA_ANALITICA.md` §5.1.

---

## Vocabulário do domínio


| Termo                         | Significado                                                                                                                                                                      |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `cooperado`                   | Médico ginecologista/obstetra cooperado da Unimed                                                                                                                                |
| `área de atuação`             | A ESPECIALIDADE da classificação v1.0 (coluna `AREA_ATUACAO` do fato): Ginecologia, GO, Mastologia, Obstetrícia, Reprodução, Ultrassonografista, Geral — mais o estado INDEFINIDO (sem peer group). GO e Ginecologia SEPARADOS (decisão jul/2026, ratificada pelo Mov 4) |
| `peer group`                  | Conjunto de cooperados da mesma área de atuação (= especialidade) — base de toda comparação justa. **Sub-perfil (opera, alto risco, plantão, PTGI, US) é IDENTIDADE visível, nunca subdivisão de régua**                                                                  |
| `elegivel_norma`              | Flag da classificação: quem FORMA a norma. `False` (INDEFINIDO, confiança baixa, alerta de perfil, ultrassonografista) segue MEDIDO contra ela — só não a define                  |
| `consulta inferida`           | Conjunto de solicitações de um mesmo cooperado, para um mesmo paciente, dentro de uma janela de `config.JANELA_CONSULTA_MINUTOS` entre lançamentos (o dia é fronteira externa). É o denominador das taxas — método em `METODOLOGIA_ANALITICA.md` §3.2 |
| `sadt`                        | Serviço Auxiliar de Diagnóstico e Terapia — exame/procedimento solicitado                                                                                                        |
| `base_contas` / `df_cont`     | Tabela de contas pagas/executadas (lado executante)                                                                                                                              |
| `base_requisicoes` / `df_req` | Tabela de requisições/autorizações (lado solicitante)                                                                                                                            |
| `autorreferência`             | `SOLIC_IGUAL_EXEC == 'S'` — médico que solicita e executa o mesmo procedimento                                                                                                   |


---

## Leis analíticas (inegociáveis)

Estas cinco governam todo código que toca cálculo. Não há zona cinzenta.

0. **Regra do recorte.** *O recorte muda quem está em cena, nunca contra quem se mede —
   régua parada, achado segue o filtro.* Espacialmente, na tela de Área: **acima dos chips,
   a área, fixo; abaixo, a bancada, que segue o filtro.** Régua = prevalência, solicitantes,
   referência, qualidade, mediana, IQR, critério, posição no grupo. Achado = acima do
   critério, variação excedente, R$, % acumulado, os Paretos e a faixa de convergência.
   Filtrar régua reconstruiria a norma sobre os selecionados, e aí o pior dos 21 vira a
   média; filtrar só metade de uma taxa dá numerador e denominador de conjuntos diferentes
   (rigor-estatístico §9). Implementada em `blocos.ids_em_cena` / `_RECORTES`, espelho de
   `RECORTES` em `app/static/blocos/recorte.js`.

1. **Pipeline único.** Todo cálculo analítico (métrica, distribuição, percentil, outlier,
  excedente) passa pelo pipeline canônico descrito em `METODOLOGIA_ANALITICA.md` §3 e
   implementado em `app/utils/`. **Proibido** recalcular distribuição/percentil/excedente à mão
   em qualquer página de UI.
2. **Zero número hardcoded.** Nenhum valor da metodologia existe fora de `config.py` — nem no
  código, nem em documento, nem no default de um controle da UI. Precisa de um
   número? Vem do `config.py`.
3. **Parâmetro de runtime por argumento.** O pipeline recebe gatilho/alvo/janela/peer group/etc.
  **por argumento**. Nunca lê o default do `config.py` no meio do cálculo — `config` define o
   default, a UI passa a escolha, o pipeline recebe.
4. **Documento referencia constante por nome**, nunca por valor.

---

## Verdades estatísticas (reflexos antes de calcular)

Este projeto produz números que vão acusar um médico de "atuar fora do padrão". Cada número será
contestado por um clínico. **Número indefensável é pior que nenhum número.**

Sempre que a tarefa envolver média, mediana, taxa, percentil, benchmark, ranking, outlier ou
comparação entre cooperados, **acionar a skill `rigor-estatistico`** e rodar o checklist dela
ANTES de calcular. Detalhe do método em `METODOLOGIA_ANALITICA.md`.

- **Comparação é SEMPRE dentro do peer group (área de atuação).** Comparar entre áreas é o
pecado capital — destrói a credibilidade. Confirmar o peer group antes de qualquer agregação
que cruze médicos.
- **Distribuição é cauda-longa** (verificar, não assumir). Default: **mediana + IQR**; média só
com simetria comprovada.
- **O outlier é o produto, não ruído.** Para a NORMA, usar estatística robusta (mediana/IQR) que
não é dominada pelo extremo — mas **nunca deletar** o outlier; ele é o candidato a investigação.
- **Denominador pequeno explode a taxa.** Aplicar o piso de consultas (`PISO_CONSULTAS_ANO`, ver
`config.py`) ou exigir volume mínimo no ranking. Sempre mostrar contagem absoluta junto da taxa.
- **Peer groups têm tamanhos diferentes**, alguns pequenos. Abaixo de `N_MINIMO_PEER_GROUP`, não
apresentar percentis como sólidos — mostrar valores brutos e rotular "amostra pequena".
- **Excedente ≠ desperdício.** O que se mede é *oportunidade para revisão*, com evidência
rastreável — nunca veredito. Checar o confundidor (volume, gravidade, subfoco) antes de
sinalizar.
- **Solicitação (SOL) ≠ execução (SAD/HON).** Semânticas e denominadores diferentes. Não misturar
nem inferir uma da outra.
- **Ausência na base ≠ ausência na prática.** Pode ser faturamento em outro lugar (ex.: parto via
maternidade). Tratar como "sem evidência neste dataset", não como "não faz".
- **Há campos de R$ em contas.** como derivá-los em custo defensável ainda não foi verificado — não calcular custo até validar
- **Precisão acima de recall.** Em dúvida, não sinalizar. Falso positivo custa mais caro aqui.

---

## Regras gerais — o que não fazer

- Não criar venv local (`.venv/`, `venv/`)
- Não reintroduzir Streamlit (stack abandonada) — a apresentação é FastAPI + HTML/CSS/JS
- Não calcular nada em JavaScript — todo número vem do pipeline, via JSON
- Não inventar valor de cor, espaço, tipo, raio ou sombra: componente novo COMPÕE token
  existente. Token novo é decisão anunciada, não um número que apareceu no meio de uma regra
- Não criar segunda versão de um componente que já existe (DIRETRIZES §5): promova o que
  está lá (foi o caso de `.side-user .av` → `.av` + `.av-lg`)
- Não escrever marcação sem ter LIDO o `components.css` na sessão: a classe que você ia
  escrever à mão pode já existir
- Não modificar CSVs em `../unimed_natal/dados_iniciais/`
- **Não usar travessão (`—`) em NENHUM texto que chegue à tela.** Vale para rótulo,
  frase, carimbo, mensagem de erro e valor. É tique de texto gerado por máquina, e este
  produto precisa ler como escrito por gente. No lugar: `·` para separar itens de um
  rótulo telegráfico, `,` ou `;` para ligar orações, `:` para introduzir explicação,
  parênteses para aparte. Onde falta um NÚMERO que não pôde ser calculado, use
  `config.SEM_MEDIDA` — nunca um travessão sozinho, que numa célula lê como zero e
  destrói a distinção "ausência de par ≠ zero medido" (ajuste 4). O motivo específico
  viaja sempre ao lado (`traducao`, `motivo`, `title`). Conferência: nenhum endpoint
  pode devolver `—` no JSON. (jul/2026)
- Não responder em inglês nas interfaces voltadas ao usuário
- Não sugerir ou adicionar features sem consultar `CONTEXTO_NEGOCIO.md` e sem instrução explícita
- Não violar as Leis analíticas acima

---

## Skills disponíveis

- `**rigor-estatistico`** → reflexo estatístico; dispara em qualquer cálculo de métrica,
distribuição, percentil, outlier, ranking ou comparação entre cooperados
- FastAPI → `/fastapi` · testes de tela → `/webapp-testing`
- A skill `frontend-design` foi REMOVIDA em 29/ago/2026: ela mandava escolher uma
  estética "ousada/maximalista/inesquecível", o oposto do que `DIRETRIZES_PRODUTO_UI.md`
  pede (calmo, neutro, padrões consolidados). Está no histórico do git se precisar.

---

## Anexo carregado automaticamente

O documento abaixo entra em contexto junto com este arquivo em toda sessão.
Ele é dono do **padrão de produto e UX do front**; a precedência sobre os demais
donos está declarada no §0 dele.

@DIRETRIZES_PRODUTO_UI.md
