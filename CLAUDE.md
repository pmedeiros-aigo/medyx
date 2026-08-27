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
| `LEXICO_PRODUTO.md`             | **vocabulário da UI** (interno → institucional)| antes de escrever rótulo/texto     |
| `config.py`                     | **todos os valores numéricos** (fonte única)  | sempre que precisar de um número    |
| projeto **Claude Design**       | **o contrato visual** (tokens, componentes)   | toda sessão que toque a camada visual |
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

## Contrato visual — fonte da verdade e sincronização

**A fonte da verdade é o Claude Design, não o disco.**

| | |
| --- | --- |
| Projeto | **Medyx - Style tile Enterprise** |
| `projectId` | `3a94742c-5e71-4672-aaa8-8ac768f9a7fd` |
| Abrir | `https://claude.ai/design/p/3a94742c-5e71-4672-aaa8-8ac768f9a7fd` · ou `/guia` no app |
| Ferramenta | `DesignSync` (se pedir autorização, o usuário roda `/design-login`) |
| Guia canônico | **`Medyx Style Guide.html`** — o único. Confirmado jul/2026 |
| Abrir o guia | `…/p/3a94742c-5e71-4672-aaa8-8ac768f9a7fd?file=Medyx+Style+Guide.html` |

`app/static/css/tokens.css` e `app/static/css/components.css` são **cópia sincronizada**, não
original. Existem em disco por um motivo só: o navegador os busca em `/static` e o
Claude Design não é CDN. **Não editar à mão** — mudança de token ou componente se faz no
Design e desce por sincronização. Cada um carrega no topo um carimbo com origem, data da
última sincronização e desvio conhecido.

Continua valendo: não redesenhar, não trocar tokens, não substituir o CSS — reutilizar as
classes.

O projeto tem outros arquivos (`… (standalone).html`, `Medyx Style Tile.html`,
`Medyx Style Tile.dc.html`, `Area de Atuacao.dc.html`). **Nenhum deles é o contrato** —
são estudos e variantes. Contrato é só o `Medyx Style Guide.html`.

### Regra 1 — sincronizar e RELER, antes de escrever marcação

No início de **qualquer** sessão que toque a camada visual — CSS, HTML, `shell.js`,
qualquer tela — sincronizar o guia **antes da primeira linha de marcação**. Não no meio,
não depois de montar o bloco: antes.

1. `DesignSync` `get_file` em `Medyx Style Guide.html`, `tokens.css` e `components.css`.
2. Gravar as versões remotas em arquivo temporário e `diff` contra `app/static/`.
   Diferença esperada = **só** o carimbo de topo e o desvio autorizado listado abaixo.
3. Qualquer outra diferença é **defasagem**: relatar ao usuário ANTES de codificar, com o
   diff na mão. Não escolher lado sozinho — disco e Design divergindo é sinal de que
   alguém editou no lugar errado.
4. Ao ressincronizar: sobrescrever com a versão do Design, **reaplicar o desvio
   autorizado** e atualizar a data do carimbo.
5. **RELER o guia depois de sincronizar.** Este passo não é opcional e não é o mesmo que
   o passo 1. O guia é vivo: pode ter entrado classe nova exatamente para o componente
   que você ia montar à mão com as classes que já conhecia. Ler antes de construir custa
   uma leitura; descobrir depois custa o bloco inteiro refeito.

### Regra 2 — componente que falta: PARAR e descrever

Ao precisar de um componente ou de um **estado** (aberto, ativo, selecionado,
desabilitado, carregando, vazio, erro) que não existe no guia: **parar**.

Não construir versão provisória. **Não montar com classes existentes "parecidas"** —
essa é a falha específica que esta regra existe para impedir: aproximação com classe
alheia não fica provisória, fica, e vira um segundo contrato visual não documentado que
ninguém sabe que existe.

Em vez disso, descrever ao usuário exatamente o que falta:

- **nome sugerido** para o componente ou estado;
- **para que serve** — o comportamento ou a informação que ele carrega;
- **em qual bloco de qual tela** ele entra.

Depois que o usuário criar no Design: sincronizar de novo, **reler o guia** (Regra 1,
passo 5) e continuar de onde parou.

### Desvio autorizado do disco em relação ao Design

Um só, hoje. Some se for esquecido numa ressincronização — daí o passo 4.

- **`components.css` — acionamento do combobox por CLASSE.** No Design, o componente
  `.cascade`/`.sel`/`.pop` é ligado por IDs do próprio demo
  (`#esp-gyn:checked ~ … .v-esp-gyn`), uma regra por opção. As áreas reais vêm da API e
  mudam com janela e piso, então nenhum CSS estático as cobre. O disco acrescenta quatro
  regras com o MESMO efeito visual, acionadas por `.on`: `.sel-trig .v.on` · `.opt.on` ·
  `.opt.on .ock` · `.pop-grp.on`. Nenhum token, cor ou medida nova. Abrir/fechar continua
  puro CSS pelos ids genéricos `op-esp`/`op-area`. Autorizado.

- **`components.css` — `@import "tokens.css"` na primeira linha. NÃO DECIDIDO.**
  Não existe na origem, e é redundante: `index.html` já carrega `tokens.css` antes de
  `components.css`, então o `@import` só provoca uma segunda busca do mesmo arquivo.
  Mantido como estava (jul/2026) — remover é mudança de comportamento e precisa de
  decisão do usuário. Ou vira desvio autorizado, ou sai na próxima sincronização.

- **`components.css` — `.kpis` com colunas AUTOMÁTICAS.** A origem traz
  `repeat(4,1fr)`. A faixa da tela de Área foi a cinco (26/08) e a do Dossiê a
  sete (27/08), e um número fixo de colunas quebra a cada KPI novo. Trocado por
  `repeat(auto-fit,minmax(150px,1fr))`: com 4, 5 ou 7 itens todos cabem numa
  linha só, e não há mais um valor para reajustar. Único valor alterado, nenhum
  token novo. Autorizado pelo usuário em 27/08. **Sai na próxima sincronização
  se a regra não for atualizada no Claude Design.**

- **`components.css` — campo de busca ATIVO no `.search`.** A origem traz o
  `.search` como caixa de EXIBIÇÃO, feita de `<span>`; não há no guia um campo
  digitável, e o `.field` é gatilho de combobox (`cursor:pointer`), não entrada
  de texto. O disco acrescenta as regras do `input` (sem moldura própria, herda
  a do `.search`), o placeholder, o anel de foco no `:focus-within`, e
  `position:relative`/`overflow:visible` para um popover poder ancorar dentro.
  **Nenhum token novo, nenhuma cor nova.** Autorizado pelo usuário em 27/08, com
  a instrução de usar as cores e o padrão do app atual. Usado hoje pela tela de
  Cooperados; esteve na barra superior por algumas horas em 27/08 e saiu de lá
  por decisão de produto (busca não é régua).

- ~~**`@font-face` removidas do `components.css`.**~~ **Encerrado (jul/2026).** A origem
  no Design já não traz as regras — não há o que reaplicar por este caminho. Volta a
  valer só se o CSS for reextraído do HTML do guia, que aponta para `.woff2` inexistentes
  e gera 404 em toda carga.

### Fronteira de responsabilidade do JavaScript

**O Claude Design é dono dos estados visuais; este repositório é dono de quando eles são
aplicados.**

No JavaScript, nenhuma decisão visual: apenas **alternar classes que já existem no guia**
e **ler tokens** (`--ch-*` para o gráfico). Proibido: `style=` inline, cor, tamanho,
espaçamento ou fonte definidos em JS, e configurar biblioteca de gráfico com os defaults
dela.

Se um estado de interação — **aberto, ativo, selecionado, desabilitado, carregando,
erro** — não tiver classe no guia, **pare e pergunte; não invente**.

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
│   │   ├── css/                ← CÓPIA SINCRONIZADA do contrato (original no Claude Design)
│   │   ├── shell/              ← o chassi: markup, seletores, régua, migalha
│   │   ├── lib/                ← dom, api, vista, pagina, tabelas (não sabem de domínio)
│   │   ├── blocos/             ← um bloco da tela por arquivo; desenham o que recebem
│   │   └── paginas/            ← orquestram: buscam dados, guardam o estado da vista
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
| `consulta inferida`           | Conjunto de solicitações de um mesmo cooperado, para um mesmo paciente, na mesma data de solicitação. É o denominador das taxas                                                  |
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
- Não redesenhar o contrato visual; componente ou estado que falta no guia → **Regra 2**
  (parar e descrever), nunca improvisar com classe "parecida"
- Não escrever marcação sem ter sincronizado e **relido** o guia na sessão → **Regra 1**
- Não editar `app/static/css/tokens.css` nem `css/components.css` à mão — são cópia sincronizada
  do Claude Design; mudança se faz lá e desce por sincronização
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
- FastAPI → `/fastapi` · front/design → `/frontend-design` · testes de tela → `/webapp-testing`

