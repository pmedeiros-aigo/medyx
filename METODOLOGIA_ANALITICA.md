# METODOLOGIA ANALÍTICA — Medyx / Unimed

Fonte da verdade sobre **como este projeto calcula qualquer métrica, norma, outlier e
oportunidade de redução** — e por quê.

> **Regra zero deste documento:** ele não contém nenhum número empírico. Todo valor
> (piso, n mínimo, percentil-gatilho, nível de confiança, janela) vive em `config.py` e é
> referenciado aqui **pelo nome da constante**. Se aparecer um dígito de medição neste
> documento, é erro de documentação. O documento descreve o *método*; o `config.py` guarda o
> *valor*. Os dois se apontam por nome, nunca duplicam.

---

## 1. O que este documento é (e o que não é)

**É:** a especificação atemporal do método. As regras de decisão, o pipeline canônico, os
princípios de tratamento, e a instrução de como cada constante é calibrada.

**Não é:** um relatório de dados. Não afirma quanto é o piso, qual a forma de uma distribuição,
ou quantos cooperados há numa área. Esses são resultados de medição — vivem no `config.py`
(quando são política calibrada) ou são calculados em runtime (quando são resultado de análise).

**Consequência prática:** este documento **não precisa ser reescrito quando chega dado novo**.
Ele só muda quando a *metodologia* muda — o que é raro e consciente. Recalibrar um valor é
editar o `config.py`, não este arquivo. É isso que o mantém confiável como fonte da verdade.

---

## 2. Princípios inegociáveis

1. **Comparação só dentro do peer group.** Toda norma, ranking, percentil e comparação é
   feita entre cooperados da mesma **área de atuação**. Comparar entre áreas é o pecado capital —
   destrói a credibilidade perante o corpo clínico.
2. **Nenhum número aqui.** Ver regra zero. Valores vêm de `config.py` por nome.
3. **Excedente não é desperdício.** O método mede *excedente de solicitação em relação à norma
   da área* — uma **oportunidade identificada para revisão**, nunca um veredito de desperdício.
   Essa distinção de linguagem é proteção política, não preciosismo.
4. **Confundidor antes de conclusão.** Nenhum excedente é contado como oportunidade antes de
   nomear e descartar a explicação plausível (volume, gravidade, subfoco).
5. **Precisão acima de recall.** Em dúvida, não sinalizar. Falso positivo custa mais caro que
   falso negativo neste contexto.
6. **Mesmo pipeline para tudo.** Toda métrica passa pelo pipeline canônico (§3). Nada de
   recalcular distribuição à mão em página de UI nenhuma.

---

## 3. O pipeline canônico

Não existem várias análises. Existe **uma análise parametrizada**. "Custo", "exames por
consulta" e "taxa de solicitação" são a mesma máquina com uma *função de valor* diferente.

### 3.1 A métrica é um plug-in

A métrica de um cooperado, para um procedimento, numa janela, é sempre da forma:

```
valor_por_consulta(cooperado, procedimento, janela)
  = função_de_valor(quantidade) / consultas_inferidas(cooperado, janela)
```

A `função_de_valor` é o único componente que muda entre análises:
- **quantidade de solicitações** → `função_de_valor(q) = q`
- **custo** → `função_de_valor(q) = q × preço_do_procedimento`

Tudo o mais no pipeline — janela, coorte, piso, norma, outlier, excedente — é **idêntico**
para qualquer função de valor. Por isso a metodologia é única.

### 3.2 Consulta inferida

`consultas_inferidas` é o denominador. Uma consulta é o conjunto de solicitações feitas
por um mesmo cooperado, para um mesmo paciente, cujos lançamentos consecutivos distam no
máximo `config.JANELA_CONSULTA_MINUTOS` (60 min). O dia é fronteira externa: uma consulta
não atravessa a meia-noite, porque o eixo temporal de toda análise é a data de solicitação.
O denominador é a contagem dessas consultas distintas na janela.

A regra anterior — "mesma data", sem hora — era aproximação forçada: a ingestão descartava
o horário e não havia como separar dois atendimentos no mesmo dia. Revisto em ago/2026,
quando o horário passou a ser preservado (`TS_REQUISICAO`). Efeito medido: +4,21% de
consultas (188.605 -> 196.542), taxa mediana por cooperado de 5,124 -> 4,925, com o
ranking preservado (Spearman 0,978). Calibração e ressalva clínica pendente: `config.py`,
junto da constante.

### 3.3 Os parâmetros do pipeline

Toda execução do pipeline recebe explicitamente:

| Parâmetro | Natureza | Origem |
|---|---|---|
| `função_de_valor` | métrica a analisar (quantidade, custo…) | escolha de runtime |
| `janela` | intervalo temporal de análise | escolha de runtime (UI) |
| `modo_da_norma` | recalculada ou baseline congelado (§5.4) | escolha de runtime (UI) |
| `peer_group` | área de atuação sob análise | escolha de runtime (UI) |
| `gatilho` | percentil que define outlier | runtime; default `GATILHO_DEFAULT` |
| `alvo` | nível-alvo de redução | runtime; default `ALVO_DEFAULT` |
| `nível_confiança` | para a faixa de incerteza (§8) | runtime; default `NIVEL_CONFIANCA_DEFAULT` |

> Os *defaults* dos parâmetros de runtime são constantes do `config.py`. Mas o pipeline **recebe
> o valor por argumento** — nunca lê o default direto do config no meio do cálculo. Config define
> o default; a UI passa a escolha; o pipeline recebe. Isso impede caminhos fantasmas onde a UI
> perde o controle.

### 3.4 Sequência determinística

Para uma dada combinação de parâmetros, o pipeline executa **sempre** nesta ordem:

1. **Filtrar a janela** pela **data de solicitação** (§5.1).
2. **Aplicar o contexto de PS** (`incluir_ps`, default excluir): a consulta-PS sai inteira —
   numerador e denominador juntos; toda saída carrega o carimbo `base` (§5.6).
3. **Definir a coorte** de cooperados do `peer_group` válidos na janela (§7.2).
4. **Inferir consultas** por cooperado na janela (§3.2).
5. **Calcular `valor_por_consulta`** por cooperado e procedimento (§3.1).
6. **Aplicar o piso** `PISO_CONSULTAS_ANO[área]` (escalado à janela): cooperados abaixo do piso
   **não entram na construção da norma**, mas podem ser avaliados contra ela com flag de baixa
   confiança (§5.2).
7. **Verificar n do peer group** contra `N_MINIMO_PEER_GROUP`: abaixo disso, a distribuição
   não é apresentada como sólida (§5.3).
8. **Verificar a forma da distribuição** e resumir com a tendência central robusta (§5.5).
9. **Calcular o corte de outlier** no `gatilho` (percentil da distribuição corrente) (§6).
10. **Calcular o excedente** de cada cooperado acima do corte, em relação ao `alvo` (§7).
11. **Sinalizar confundidores** antes de classificar o excedente como oportunidade (§7.3).
12. **Anexar a faixa de incerteza** no `nível_confiança` (§8).
13. **Priorizar por Pareto** quando o pedido for "onde agir" (§9).

---

## 4. Granularidade: o nível do peer group

A norma e **todas as constantes dela** são definidas no nível de **área de atuação dentro da
especialidade** — não no nível da especialidade inteira. Comparar um reprodutivo com um
obstetra geral, ambos "ginecologistas", viola o Princípio 1.

Implicação direta: as constantes calibradas (piso, e o que mais a calibração mostrar) são
**indexadas por área de atuação**, não escalares globais. Quando o projeto ganhar novas
especialidades e áreas, o método (este documento) não muda — só entram **novas entradas no
`config.py`**. O documento sobreviver à expansão sem uma linha alterada é a prova de que a
separação está correta.

> Princípio de parcimônia (herdado da skill `rigor-estatistico`): só criar valor por área
> quando a calibração **mostrar** que as áreas diferem. Se o funil de estabilização fechar no
> mesmo ponto para todas, um valor compartilhado basta. Não fabricar diferença por área que o
> dado não sustenta.

### 4.1 A especialidade é o peer group; a fronteira entre especialidades é decidida por dado

O grupo de pares de sinalização é a **área de atuação registrada na classificação vigente** — a
especialidade daquela classificação, e nada mais fino que ela. Sub-áreas e sub-perfis não criam
grupos próprios (ver §5.8).

**Classificação vigente (v2.0, set/2026).** A área não vem mais de um rótulo dado por médico: cada
consulta recebe uma **família de atendimento** pelo pacote de procedimentos que contém (pré-natal,
rotina, cirurgia, dor pélvica, mama…), consultas próximas da mesma paciente formam um atendimento,
e o cooperado é a **mistura** das suas consultas. A área principal é a maior família específica com
pelo menos 15% das consultas; sem nenhuma, o cooperado é "Ginecologia Geral". A `area_mvp` agrupa
as áreas finas em nomes de especialidade (`config.ESPECIALIDADES`) e é o peer group do app. A
mistura, as áreas secundárias e a execução são identidade visível, nunca subdivisão de régua. A
regra completa e reproduzível está em `unimed_natal/classificacao_cooperados.ipynb`; o dicionário
das colunas em `unimed_natal/marts/LEIAME_classificacao_v2.md`. A decisão GO × Ginecologia abaixo
é história da v1 e permanece registrada como método.

Quando duas especialidades vizinhas são candidatas a fusão — o caso de Ginecologia e
Obstetrícia/Ginecologia (GO) —, a decisão não se toma por conveniência nem por julgamento
isolado: compara-se, para os procedimentos de maior volume comuns às duas, a razão entre as
medianas de cada grupo. Perfis indistinguíveis na prática justificam uma régua única; perfis
distintos justificam réguas separadas. É o dado que decide a fronteira, não a nomenclatura.

**Decisão vigente (jul/2026): GO e Ginecologia permanecem separados.** A evidência: as medianas
agregadas dos dois grupos são quase idênticas, mas apenas uma minoria dos procedimentos
principais tem razão de medianas dentro da faixa de equivalência — muito aquém do critério de
fusão. Os mixes diferem e somam no mesmo total; a coincidência agregada era pista falsa. A
separação, portanto, não é preferência: é achado. *(Faixa de equivalência e critério de fusão
registrados no `config.py` junto às constantes de peer group.)*

---

## 5. Construção da norma

### 5.1 Eixo temporal

O eixo do tempo é a **data de solicitação** — a data do evento clínico que gera o custo, não a
data de pagamento nem de autorização. **A norma e o indivíduo são sempre calculados na mesma
janela.** Comparar a taxa do cooperado numa janela contra uma norma de outra janela é viés
garantido.

### 5.2 Piso de consultas

O piso existe porque a taxa de um cooperado com poucas consultas é dominada por ruído amostral.
Abaixo do piso, a taxa oscila; acima, estabiliza.

- **Quem calibra:** o piso é o ponto onde a taxa individual para de oscilar — identificado pela
  **análise do funil de estabilização** (plotar taxa individual contra nº de consultas e achar
  onde o funil "fecha"). Calibrado uma vez, por área de atuação.
- **Constante:** `PISO_CONSULTAS_ANO[área]`.
- **Escala por janela:** o piso é declarado por ano e **escalado proporcionalmente à duração da
  janela** analisada. Senão, em janelas curtas, a área "esvazia" e a norma fica instável.
- **Uso:** quem está abaixo do piso **não entra na construção da norma**, mas pode ser avaliado
  contra ela com flag de baixa confiança.

### 5.3 n mínimo do peer group

Percentis de um grupo minúsculo são instáveis (um cooperado muda tudo). Abaixo de
`N_MINIMO_PEER_GROUP` cooperados válidos, a distribuição **não é apresentada como sólida** —
mostram-se os valores individuais brutos, rotulados "amostra pequena, não conclusivo".

### 5.4 Modo da norma: recalculada vs baseline congelado

Duas perguntas de negócio diferentes, **nunca misturadas**:

- **Norma recalculada** (sai dos dados da própria janela) → responde *"quem está fora do padrão
  agora"*. Usada na **detecção de outlier**. Cuidado: se a área inteira melhora, a régua desce
  junto e o excedente "some" sem ninguém mudar de posição relativa — por isso não serve para
  medir progresso.
- **Baseline congelado** (a norma de uma janela de referência vira régua fixa para as seguintes)
  → responde *"estamos melhorando em relação ao ponto de partida"*. Usada no **acompanhamento de
  economia / efeito da ferramenta**. É calculado uma vez e **persistido**.

Usar norma recalculada para medir progresso faz o número mentir. Esta é provavelmente a decisão
mais importante do documento.

#### 5.4.1 Régua anual, apuração trimestral (revisto em 13/set/2026)

A primeira versão desta seção (set/2026) tinha duas réguas: recalculada por trimestre para a
consistência, congelada no ano para o dinheiro. Em 13/set/2026 a decisão passou a ser UMA regra,
sem divergência em nenhuma tela:

**Critério e referência saem do ano. O excedente é apurado por trimestre, com a régua do ano,
truncado em zero. Tudo o mais é soma.**

| Grandeza | Onde é calculada |
| --- | --- |
| referência de cada (área, procedimento): mediana, P75, P90 | janela inteira (§5) |
| cesta: pares que passam os três portões (piso, n mínimo, acima do critério) | janela inteira (§6, §7) |
| preço de cada procedimento | janela inteira |
| excedente de um par | por fatia de `config.APURACAO_EXCEDENTE_MESES` meses, somado |
| excedente do cooperado, do procedimento, da área | soma dos pares |
| consistência (persistência) | fatias em que o excedente do par é positivo |

> excedente da fatia = max(0, itens da fatia − referência anual × consultas da fatia) × preço anual

A fatia é a mesma unidade da janela mínima (§5.1): o trimestre. Os dias que sobram no fim de uma
janela livre formam uma fatia parcial, apurada com a mesma fórmula e declarada como parcial. A
persistência conta só as fatias completas; o dinheiro conta todas.

**Por que truncar em zero por trimestre.** Decisão de produto, não de estatística: a unidade de
cobrança é o trimestre, e um trimestre abaixo da referência não abate os que ficaram acima. O
custo declarado dessa escolha: o número é maior ou igual ao anual (o anual é o caso de uma fatia
só), e a diferença é maior em quem está perto da referência, porque é ali que a oscilação cruza a
linha com mais frequência. Medido na área de Endoscopia Ginecológica, janela de 12 meses: +9% no
total da área, +4% no maior caso, ordem do topo inalterada
(`unimed_natal/verificacao_excedente_trimestral.ipynb`). A tela diz o que o número é: soma dos
trimestres acima da referência do período.

**Identidades que valem por construção.** A soma das fatias é o excedente do par; a soma dos
pares é o do cooperado; a soma dos cooperados é o da área. A série trimestral do dossiê e a da
Área são essas somas, e nenhum trimestre é negativo. Régua única também para a consistência: um
par é "sinalizado no trimestre" quando o excedente da fatia é positivo, e persistente quando
todas as fatias completas são positivas. Não existe mais referência recalculada por trimestre nem
portão de n mínimo por trimestre.

Ressalva aceita: com régua anual, a sazonalidade da área é atribuída ao cooperado. É o custo de
qualquer baseline fixo, e é preferível ao inverso (a régua descer junto com o consumo da área,
mostrando melhora onde não houve). Se um dia incomodar, o caminho é uma referência anual
sazonalizada, não a volta da régua móvel.

**O piso de consultas não se aplica às fatias.** O piso decide se uma TAXA anual é comparável
(§5.2); a fatia não compara nada, só apura. Um trimestre de volume baixo continua com o custo e
o excedente apurados; a ressalva "volume baixo" qualifica as taxas daquele período (SADT e custo
por consulta), nunca o dinheiro. Trimestre sem barra só existe quando não há preço apurado.

**Arredondamento.** As barras são publicadas com duas casas; quatro arredondamentos
independentes somariam até dois centavos fora do total. A sobra é aplicada à MAIOR barra, onde é
imperceptível, em vez de ficar visível na conta de quem soma.

Aceite permanente: a soma das fatias tem de bater com o excedente do par, do cooperado e da área
**na casa do centavo**, e nenhuma fatia pode ser negativa. Cobrado em `smoke_fase3.py` (motor,
contra o gabarito do notebook) e em `smoke_api.py` (telas).

#### 5.4.2 A granularidade mensal do custo, e por que o excedente não desce a ela (set/2026)

A tela de Área e o dossiê do cooperado mostram a mesma série em **duas unidades**, e a fronteira
entre elas é de método, não de desenho:

| Grandeza | Unidade | Por quê |
| --- | --- | --- |
| custo das solicitações | **mês** | é uma soma, e soma desce a qualquer granularidade sem deixar de ser o mesmo número |
| excedente | **trimestre** | é a diferença entre o solicitado e o que a referência previa para as CONSULTAS do período, e a unidade de apuração é `config.JANELA_MINIMA` |

O custo do mês é `Σ solicitações do mês × preço mediano da JANELA`. O preço é o da janela
inteira, o mesmo que §5.4.1 congela para o trimestre, e é isso que torna a decomposição exata:
solicitação é aditiva sobre os meses e o preço não varia entre eles, então **os três meses de um
trimestre somam o trimestre na casa do centavo**, sem nada ser medido duas vezes. Preço por mês
faria uma barra maior poder ser reajuste de tabela em vez de mais solicitação.

Um **excedente mensal** seria uma medida que a metodologia não fez: o denominador passaria a ser
um mês de consultas, exatamente o que o piso de volume (§5.2) existe para impedir.

**A série mensal não passa pelo portão da persistência.** Janela que não fecha nenhum trimestre
(a de 3m) continua com as barras de custo, que são dado real, e sem a faixa de fechamento, cuja
ausência é declarada. Esconder o custo conhecido deixava a tela muda justamente onde a
exploração começa: em 3m a Área e o dossiê ficavam os dois sem série nenhuma.

**O sujeito é argumento, não é uma segunda função.** `pipeline.custo_mensal` recorta por área ou
por cooperado; o bloco recebe a faixa trimestral pronta de quem sabe montá-la. A identidade que
faz os meses somarem o trimestre não depende de quem está em cena, só de o preço ser o da janela,
e dois motores dariam duas chances de divergir.

**Mês parcial não vira barra.** A janela é ancorada no fim da amostra e pode começar no meio de
um mês (a de 3m começa dia 31). Um mês coberto por um dia desenharia uma barra rasteira que se
lê como queda de custo, e não como recorte de calendário. Entram só os meses completos dentro da
janela; os dias das pontas são declarados, como em `fatiar_trimestres`.

**A identidade é verificada, nunca assumida.** Quando a janela não começa no dia 1, os trimestres
da persistência não caem sobre meses de calendário e a soma das barras de um grupo não é o custo
da célula abaixo dele. O bloco confere par a par e só AFIRMA a identidade quando ela vale; quando
não vale, diz que o fechamento cobre um período deslocado.

Aceite permanente: com a identidade afirmada, a soma dos meses de cada grupo tem de devolver o
custo do trimestre na casa do centavo, e nenhum mês pode carregar excedente. Ambos cobrados em
`smoke_api.py` (seção 2b1).

### 5.5 Forma da distribuição e tendência central

A forma é **verificada a cada análise** (faz parte do pipeline, passo 8) — nunca assumida, nunca
fixada no documento. A regra de decisão é fixa: se a distribuição for assimétrica, resume-se com
**mediana e IQR**; média só com simetria comprovada. Como custo/utilização em saúde tende a
cauda-longa, a mediana é o default esperado — mas a verificação manda, não a suposição.

### 5.6 Contexto de PS: a base da norma é eletiva

Plantão de pronto-socorro tem padrão de solicitação próprio (pacote de urgência, bateria de
entrada) que não é comparável com prática de consultório. A regra é por **contexto**, não por
pessoa: o **episódio-PS é identificável no próprio dado**.

- **A unidade é o dia de atendimento** — o mesmo cooperado, o mesmo beneficiário, a mesma data.
  O dia é de PS quando **qualquer** item dele tem regime de pronto socorro (`REGIME_PS`) OU é o
  pacote de urgência (`CD_PACOTE_URGENCIA`). Todos os itens do dia recebem a marca.
- **O sinal é o REGIME, não o caráter** (17/set/2026). Até então o dia era PS pelo caráter de
  urgência (`STRING_URGENCIA`). Os dois concordam em 96,2% dos dias de PS; nos 4% em que
  discordam, o caráter erra nos dois sentidos — deixa na base eletiva a taxa da passagem pelo
  PS (aplicação de injeção, sala de medicação, lançadas como eletivas) e tira dela o exame
  ginecológico de rotina feito em consultório com caráter marcado como urgente (coleta,
  colposcopia, US transvaginal). Em R$ as duas regras quase empatam; em composição não. O
  caráter segue existindo só como descritor (`pct_urgencia`, §7.3). Proveniência:
  `unimed_natal/verificacao_pronto_socorro.ipynb` §1, §2 e §6.
- **O dia de PS é consulta PRÓPRIA.** Ele não se funde com atendimento eletivo: não abre uma
  consulta que um dia seguinte fecharia como retorno, nem entra como retorno de uma consulta
  eletiva aberta. Os dias eletivos seguem a regra dos 30 dias (§3.2) entre si, pulando os
  dias de PS. Nenhuma consulta mistura os dois tipos; a marca do item é a marca da consulta.
- **O retorno depois do PS** (mesmo notebook, §3 a §5): 17,1% dos dias de PS têm outro
  atendimento da mesma paciente com o mesmo cooperado em 30 dias (dias eletivos: 44,5%).
  Desses, 73,6% voltam ao PS e 26,4% ao consultório. O retorno em consultório é
  acompanhamento do episódio (US obstétrica com doppler, HCG, toxoplasmose), com 3,3 itens
  contra 5,8 do retorno eletivo comum — é trabalho de consultório, entra na base eletiva como
  consulta própria e **não** carrega a marca de PS. O retorno PS → PS **não é pareado**: se a
  regra dos 30 dias da operadora vale para pronto socorro é pergunta de negócio, pendente com
  a Unimed; até lá cada dia de PS é uma consulta, que é o conservador e não altera comparação
  nenhuma, porque o PS está fora da norma.
- **Dias mistos** (item de PS e item ambulatorial na mesma data): 137 em 13.819, com 391
  itens eletivos que saem junto com o dia. Perda pequena e declarada; regra própria custaria
  mais do que rende.
- **Onde a marca nasce:** no `preparar_fato`, coluna `EPISODIO_PS`, uma vez, na origem. É
  fato sobre o dado, não análise. O fato carrega `DS_REGIME_ATENDIMENTO` desde 17/set/2026.
- **Como o filtro age:** a consulta-PS sai **inteira** — numerador e denominador caem juntos
  (armadilha 9 do rigor estatístico). Norma e indivíduo são calculados sobre as consultas
  não-PS **de todo mundo**; o plantonista permanece na norma com sua prática de consultório.
- **Parâmetro:** `incluir_ps`, default `INCLUIR_PS_DEFAULT` (excluir). Todo motor o recebe por
  argumento e **toda saída carrega o carimbo `base`** declarando sobre qual base foi calculada —
  o filtro que muda todos os números se anuncia em todos os números.
- **O que sai da comparação NÃO sai da contagem** (Lei 5 do `CLAUDE.md`): o volume e o custo do
  PS são dado observado e aparecem na tela como magnitude, ao lado da base eletiva, com o
  motivo de não serem medidos. Pendente de implementação na tela (set/2026).
- **Exceção deliberada:** confundidores e perfis descritivos (ex.: `pct_urgencia`) são
  calculados na base **completa** da janela — numa base eletiva o percentual de urgência é zero
  por construção; o confundidor descreve a pessoa, o filtro se aplica à análise.
- **Proveniência original:** teste pré-comprometido de marcadores (notebook
  `calculos_iniciais.ipynb` §12, jul/2026) — coerência entre marcadores, separação
  plantonista×demais e custo do filtro registrados no `config.py` junto às constantes. Flag de
  plantonista da classificação é **informativa**; validação clínica da lista de plantonistas
  **pendente** — até lá, a regra é "adotada", nunca "validada".

### 5.7 Quem FORMA a norma ≠ quem é MEDIDO contra ela

A referência de um grupo é construída **apenas** com os cooperados marcados como elegíveis na
classificação vigente (`elegivel_norma`). Na v2.1 são inelegíveis: quem não tem área principal
(volume insuficiente, prática pouco visível, só pronto-socorro), quem tem a execução como prática
principal (realiza mais do que solicita) e classificação de confiança baixa (menos de 100 consultas
com pedido). A regra do cadastro agregado (fração de pacientes homens) foi retirada em 13/set/2026:
a fração fica na dim como descrição, sem efeito na referência.

**Todos os demais continuam sendo medidos contra essa referência** — inclusive os inelegíveis.
Formar a régua e ser avaliado por ela são coisas separadas: a inelegibilidade tira o cooperado da
*construção* da régua; excluí-lo da medição o tornaria invisível, o que o método não admite.

Consequência de exibição: nenhum cooperado desaparece. Quem não forma a referência aparece com o
**motivo** — e o motivo distingue a natureza da exclusão (definitiva por desenho, como perfil de
execução; ou provisória e pendente de triagem clínica).

### 5.8 Exclusão por par: o sub-perfil retira o portador apenas da cesta que ele explica

Sub-perfis (na v2: faz cirurgia, faz mastologia, área secundária, executa, carteira jovem ou de
climatério) **não subdividem o peer group** — subdividir produziria grupos pequenos demais para
sustentar qualquer referência.

O sub-perfil age no nível do **par (cooperado × procedimento)**: quem tem o sub-perfil X é
retirado da *construção* da referência **apenas dos procedimentos que X explica**, e continua
formando a referência de todos os demais. Um cooperado que opera sai da referência de peça
cirúrgica e do pré-operatório; permanece na de exames de rotina — operar não explica pedir mais
rotina.

O corte só é ativado onde o dado mostra distorção: compara-se a referência do procedimento com e
sem os portadores do sub-perfil, e ativa-se apenas onde a mediana se desloca materialmente
(`LIMIAR_DISTORCAO_EXCLUSAO`; os pares ativos vivem em `EXCLUSOES_SUBPERFIL`). Corte sem
evidência de distorção não se aplica. **Na v2.0 a lista está vazia**: as áreas já separam as
práticas que a v1 tratava por exclusão (cirurgia em Endoscopia Ginecológica, alto risco em
Obstetrícia). O mecanismo permanece no motor.

Na interface, o sub-perfil é **exibição de identidade**, nunca recorte nem base de comparação: ele
aparece como etiqueta na linha do cooperado, com a explicação no hover, e não troca a régua.

Houve um **filtro por sub-perfil** na tela de Área até set/2026, que recortava a lista e
acrescentava o posto interno ao grupo. Foi removido a pedido do médico que auditou a tela, e o
motivo é o mesmo do primeiro parágrafo desta seção: ele subdividia o grupo. Não na construção da
referência — aí a regra sempre valeu —, mas nos **blocos de achado**, que reagregavam sobre os 2 a
7 portadores e publicavam concentração e Pareto sobre eles. "1 de 2 cooperados concentram 98% do
valor" é a frase que a tela chegou a imprimir. Grupo pequeno demais para sustentar referência é
também pequeno demais para sustentar achado.

---

## 6. Detecção de outlier

O corte de outlier é o `gatilho` aplicado à distribuição corrente — **sempre recalculado**,
porque é literalmente um percentil daquela métrica, naquela janela, naquele peer group. O
analista escolhe *qual* percentil na UI; o *valor* do corte é resultado do pipeline. Default em
`GATILHO_DEFAULT`.

### 6.1 O critério só vale onde o grupo o sustenta — e nunca é substituído por outro

Um percentil só é usado como critério de revisão quando o número de formadores da referência o
sustenta (`N_MINIMO_P90`, `N_MINIMO_P75` no `config.py`). Abaixo do mínimo **não há sinalização**
— apenas leitura descritiva por posto — e a tela declara o estado "grupo insuficiente".

**Decisão (set/2026): o critério que o analista escolhe é o que se calcula, em toda área e em
todo procedimento.** A versão anterior degradava P90 para P75 em grupos de 10 a 19 formadores;
isso mostrava uma régua no controle e aplicava outra no cálculo, e foi removido. A justificativa
do mínimo é aritmética: o percentil extremo de um grupo muito pequeno é, na prática, o segundo
maior valor do grupo — sorteio, não régua; alguém seria apontado por construção.

O critério aplicado (`gatilho_usado`: o pedido, ou nenhum) viaja com todo resultado.
**No nível do procedimento, a degradação usa o n daquele procedimento**, não o da área: uma área
grande pode ter procedimentos com poucos solicitantes.

### 6.2 Estados de disponibilidade de referência

Nem todo grupo sustenta comparação. O método distingue três situações, e o sistema declara qual
está em vigor:

1. **Referência plena** — número de formadores suficiente: percentil, critério e sinalização
   completos.
2. **Referência insuficiente** — há formadores, mas poucos demais para sinalizar: leitura
   descritiva por posto, sem percentil e sem sinalização. Inclui o caso-limite de **zero
   formadores** (a área existe, a referência não).
   **Segundo nível, por procedimento (13/set/2026):** quando a ÁREA não tem
   `N_MINIMO_PEER_GROUP` solicitantes de um exame, a referência aplicada passa a ser a da
   **especialidade inteira** (todas as áreas, entre quem forma norma e solicita o exame), desde
   que ela tenha `N_MINIMO_REFERENCIA_ESPECIALIDADE` solicitantes. O par carrega
   `nivel_referencia` e a tela carrega a etiqueta "referência da especialidade" em todo lugar
   onde o número aparece, com a composição da referência por área. É comparação que cruza
   áreas com práticas diferentes: entra como oportunidade, sempre identificada, nunca somada a um
   total sem a divisão por nível ao lado. Abaixo do mínimo nos dois níveis, "referência não
   conclusiva": o custo aparece, o excedente não.
3. **Sem grupo de pares** — o cooperado não tem área de atuação atribuída: nenhuma
   comparação é aplicada; restam apenas as leituras que não dependem de grupo (concentração,
   trajetória própria, coerência de cascata clínica).

Em nenhum desses estados o cooperado desaparece do sistema; muda o que o sistema se permite
afirmar sobre ele.

O mesmo vale para qualquer **grandeza**, não só para a pessoa (Lei 5 do `CLAUDE.md`, set/2026):
um procedimento sem referência apresentável não some da leitura de custo. O custo dele é dado
observado e aparece; o que não aparece é o excedente, e a ausência é declarada com o motivo
("sem padrão na área para comparar"). Toda decomposição fecha com o total: custo com referência
mais custo sem referência é o custo do cooperado, sem resto.

---

## 7. Excedente / oportunidade de redução

### 7.1 Gatilho e alvo são parâmetros SEPARADOS (revisto em 13/set/2026)

São duas perguntas diferentes, e por isso dois parâmetros:

- **`gatilho`** = quem é atípico o suficiente para entrar na lista (um percentil alto da área).
- **`alvo`** = o nível contra o qual se mede quanto ele pediu a mais.

O gatilho decide QUEM; o alvo decide QUANTO. Trocar o alvo não muda a lista; trocar o gatilho muda.

**O que o alvo responde, conforme onde está:**

| Alvo | Pergunta | Leitura |
| --- | --- | --- |
| igual ao critério (ex.: P90) | quanto ele pediu além do limite que a área aceita | o **piso**: o número mínimo, o que sobra mesmo trazendo cada um só até a borda |
| na referência típica (ex.: mediana) | quanto ele pediria a menos se praticasse como o colega típico | o **teto**: o que sobraria se cada um convergisse ao padrão |

As duas leituras são legítimas e o app calcula as duas como uma faixa (piso e teto). O
**padrão do produto é o piso** (`ALVO_DEFAULT` = `GATILHO_DEFAULT`, decisão de 11/set/2026: o que
o controle mostra é o que se calcula), coerente com a regra de precisão acima de recall: o
primeiro número que chega a um médico é o menor defensável. Quem quiser o teto troca o alvo na
tela, e a faixa se abre.

**O que esta seção dizia antes, e por que caiu.** A versão anterior mandava que gatilho e alvo
nunca coincidissem, com o argumento de que "trazer todos acima do P-corte para o próprio P-corte
condena o quartil superior por construção". O "por construção" é propriedade do critério por
percentil: com gatilho P90 os 10% do topo entram na lista sempre, numa área eficiente ou não, com
qualquer alvo. O argumento descrevia um problema real do gatilho e o atribuía ao alvo. A defesa
contra esse problema não é o alvo, é a cascata (§8 e `cascata.py`: persistência, contexto,
intervalo de confiança), que existe exatamente para separar posição em percentil de evidência.

Ressalva técnica que continua valendo: com alvo igual ao critério, o excedente de quem está logo
acima do corte é pequeno e quase todo oscilação amostral. Esses casos pesam pouco em R$, e o
degrau de confiança da cascata os filtra. Não é motivo para proibir a coincidência; é motivo para
nunca apresentar o excedente sem o intervalo de confiança ao lado.

### 7.2 Cálculo (em palavras, sem número)

Para cada cooperado **acima do `gatilho`** em um procedimento (portões: piso de consultas, n
mínimo de solicitantes, taxa anual acima do critério anual), a oportunidade é apurada **por fatia
de tempo** (§5.4.1): em cada fatia, o excedente de itens acima do que a referência anual (`alvo`)
previa para as consultas daquela fatia, truncado em zero, valorado pela `função_de_valor`. O
excedente do par é a soma das fatias. Some-se por cooperado, por procedimento e por área conforme
a pergunta, lembrando que somar entre cooperados é legítimo, mas somar entre áreas exige cuidado
(peer groups distintos). Não existe outra medida de excedente: toda tela lê esta soma.

**Coorte entre períodos:** comparações temporais usam a **mesma coorte** de cooperados presente
nas duas janelas. Caso a população mude (entrada/saída/reclassificação de cooperados), isso é
explicitado, senão se atribui à ferramenta um efeito que foi só rotatividade.

### 7.3 Confundidor antes de oportunidade

Antes de um excedente virar oportunidade, sinalizar se o cooperado é também outlier em **volume**
ou em **complexidade** (proxy disponível) ou tem **subfoco** dentro da área. Excedente que se
explica por confundidor **não** entra na conta de oportunidade. Sem este passo, o primeiro caso
levado à Unimed pode ser justamente o que tem a melhor defesa clínica — e aí se perde a sala.

### 7.4 Enquadramento

O resultado é sempre **"oportunidade identificada para revisão"**, acompanhada da evidência
rastreável até o procedimento. Nunca "desperdício comprovado". É um teto teórico de economia
(hipótese), não uma economia realizada.

---

## 8. Controlador de confiabilidade

O excedente não é um ponto, é uma faixa (por tamanho de amostra e variância). O controlador da
UI escolhe quão conservador é o número reportado: *"com `nível_confiança` de confiança, a
oportunidade é **pelo menos** Y"*. Calculado por intervalo de confiança / bootstrap sobre o
excedente. Default em `NIVEL_CONFIANCA_DEFAULT`.

O excedente reamostrado segue a MESMA definição da tela (§7.2): apurado por fatia, com a
referência anual e truncado em zero, sobre o volume real de consultas de cada fatia. Um piso
calculado sobre o excedente anual se referiria a outro número.

**Como o controle funciona na tela (revisto em 13/set/2026).** Por padrão o excedente exibido é
o **valor medido**, sem ajuste (`AJUSTE_CONFIANCA_DEFAULT`). Quando o analista escolhe um nível
no controle "Ajuste de confiança", o excedente de cada par sinalizado passa a ser o valor
conservador nesse nível, e tudo o que soma pares (R$, Paretos, totais, Panorama) segue; a
ficha do número mostra o medido ao lado. O ajuste só é possível onde o exame tem
`MIN_PACIENTES_AJUSTE_CONFIANCA` ou mais pacientes recebendo; abaixo disso o par fica com o
valor medido e é declarado na tela ("sem ajuste de confiança"), sem citar o mínimo, que é
critério interno. A série por trimestre não recebe o ajuste, porque o sorteio produz um valor
por período inteiro: a nota do bloco declara. O degrau "com confiança estatística" da cascata
continua com o próprio sorteio interno (`NIVEL_CONFIANCA_DEFAULT`, `MIN_PACIENTES_BOOTSTRAP`),
pendência registrada.

> Este controlador é **incerteza estatística**, não desconto de realização. "Que fração da
> oportunidade é capturável na prática" é uma premissa de negócio separada, assumida
> explicitamente pela diretoria — **nunca** embutida dentro deste slider. Misturar as duas
> esconde se o desconto é estatístico ou comercial.

---

## 9. Priorização (Pareto)

A oportunidade se concentra: poucos procedimentos (de alto custo e/ou alto volume) respondem pela
maior parte do total. O entregável central do degrau de inteligência de custo é o **ranking de
onde agir** por oportunidade total na área — não uma lista exaustiva de procedimentos. O Pareto
não é faxina; é a feature. *(Roda em volume de excedente enquanto não há R$; em reais quando a
tabela chegar.)*

---

## 10. Generalização: o que muda e o que não muda

| Quando entra… | O método (este doc) | O `config.py` |
|---|---|---|
| nova métrica (custo, outra taxa) | não muda — é nova `função_de_valor` | nada, ou tabela de preço |
| nova área de atuação | não muda | novas entradas indexadas por área |
| nova especialidade | não muda | novas entradas indexadas por área |
| dado novo (novo período) | não muda | recalibrar valores se necessário |

As regras temporais, de coorte e de piso são **as mesmas para todas as métricas**. Só a
`função_de_valor` muda entre métricas.

---

## 11. Constantes que o `config.py` deve declarar

Este documento nomeia; o `config.py` valoriza. Lista do contrato:

| Constante | O que é | Como se obtém | Status |
|---|---|---|---|
| `PISO_CONSULTAS_ANO[área]` | piso de consultas/ano para entrar na norma | calibração via funil de estabilização (§5.2), por área | **a calibrar** (medição) |
| `N_MINIMO_PEER_GROUP` | nº mínimo de cooperados para distribuição sólida | calibração / política (§5.3) | **a calibrar** (medição/decisão) |
| `N_MINIMO_P90` | nº mínimo de formadores que sustenta o percentil padrão | decisão de método (§6.1) | decisão |
| `N_MINIMO_P75` | nº mínimo de formadores que sustenta o percentil degradado | decisão de método (§6.1) | decisão |
| `EXCLUSOES_SUBPERFIL` | pares (sub-perfil, área, cesta) com exclusão por par ativa | teste de distorção da mediana (§5.8) | decisão (medição ativa cada entrada) |
| `LIMIAR_DISTORCAO_EXCLUSAO` | deslocamento de mediana que ativa a exclusão por par | decisão de método (§5.8) | decisão |
| `JANELA_MINIMA` | menor janela analisável | decisão de método (§5.1) | decisão |
| `GATILHO_DEFAULT` | percentil-gatilho default de outlier | decisão de método (§6, §7.1) | decisão |
| `ALVO_DEFAULT` | nível-alvo default de redução | decisão de método (§7.1) | decisão |
| `NIVEL_CONFIANCA_DEFAULT` | confiança default do controlador | decisão de método (§8) | decisão |
| `STRING_URGENCIA` | literal de caráter de urgência na base de requisições | contrato de dados (§5.6, §7.3) | decisão |
| `CD_PACOTE_URGENCIA` | código do pacote de atendimento de urgência | contrato de dados (§5.6) | decisão |
| `INCLUIR_PS_DEFAULT` | default do contexto de PS (excluir episódios da norma) | teste pré-comprometido (§5.6) | decisão |

Constantes de **medição** nascem sem valor (`None`) até a exploração calibrá-las — não se inventa
valor de amostra não vista. Constantes de **decisão** carregam o valor decidido, marcado como tal.

---

## 12. Por que percentis e robustez, e não teste de significância

O método não usa teste de hipótese nem p-valor. A escolha é deliberada e tem três razões:

1. **Multiplicidade.** Avaliamos centenas de pares (cooperado × procedimento). Um arcabouço de
   significância exigiria correção de multiplicidade, que tornaria o resultado tecnicamente frágil
   e comunicacionalmente inacessível. Nossa resposta ao acaso é a **persistência**: o sinal precisa
   sobreviver a janelas sucessivas com a referência recalculada em cada uma.
2. **Confundimento.** Em dado observacional, "estatisticamente significante" não significa
   "injustificado". O método ataca a pergunta certa antes: fatores de contexto são medidos e
   anexados **antes** de qualquer excedente ser chamado de oportunidade (§7.3).
3. **A afirmação do produto não é de teste.** Nunca dizemos "provamos desvio"; dizemos "acima do
   critério do próprio grupo, de forma repetida, com piso de confiança declarado". Isso é
   estimação + robustez + repetição.

A medida formal de incerteza existe e é o **controlador de confiabilidade** (§8): o bootstrap com
reamostragem por paciente devolve um piso ("é pelo menos Y, com X de confiança") — mais útil e
mais honesto, no contexto, que um p-valor.

---

## 13. Regras operacionais (lei do projeto)

- **Pipeline único.** Todo cálculo analítico passa pelo pipeline canônico (§3). Proibido
  recalcular distribuição/percentil/excedente à mão em qualquer página de UI.
- **Zero número hardcoded.** Em lugar nenhum — nem no código, nem neste documento, nem no
  default de um controle da UI. Todo valor vem do `config.py`.
- **Parâmetro de runtime por argumento.** O pipeline recebe gatilho/alvo/janela/etc. por
  argumento; nunca lê o default do config no meio do cálculo.
- **Documento referencia constante por nome.** Nunca por valor.
