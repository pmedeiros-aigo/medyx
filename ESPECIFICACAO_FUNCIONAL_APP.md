# ESPECIFICAÇÃO FUNCIONAL — APP MEDYX (MVP v3, jul/2026)

MVP = **3 páginas + Nota Metodológica**, derivadas do fluxo do auditor:
onde está a oportunidade? → fora do padrão em relação a quem? → com que evidência converso?
Cada elemento: O QUE mostra ← QUAL motor alimenta. **Páginas nunca calculam.**
**[v0]** agora · **[v1]** fase seguinte.

Contrato visual: projeto **Medyx - Style tile Enterprise** no Claude Design (fonte da
verdade). `app/static/tokens.css` e `components.css` são cópia sincronizada — ver
`CLAUDE.md` § Contrato visual.
Método: `METODOLOGIA_ANALITICA.md`. Vocabulário: `LEXICO_PRODUTO.md`.
Valores: `config.py`. Regras de construção: `CLAUDE.md`.

---

## REGRAS DE COMPARAÇÃO (valem em todas as páginas — são O PRODUTO)

1. **Peer group de sinalização = especialidade** (`classificacao_v1.csv`). GO e
  Ginecologia **separados** — decisão corroborada por dado (só 30% dos 30
   procedimentos principais têm medianas equivalentes entre os dois grupos).
2. **Sub-perfil é recorte de leitura, nunca base de comparação.** Filtrar por um
  sub-perfil destaca os membros e acrescenta o **posto interno** ("3º de 12"); a
   régua continua sendo a da especialidade e nenhuma coluna vira travessão.
3. **Norma construída só com** `elegivel_norma=True`**; todos são MEDIDOS contra ela.**
  Quem não forma aparece com o **motivo**, e o motivo distingue exclusão definitiva
   (perfil de execução) de provisória (alerta de perfil — triagem pendente).
4. **Base eletiva por padrão** (`incluir_ps=False`); carimbo BASE_ELETIVA visível.
5. **Critério degradado pelo n**: pleno → percentil padrão; intermediário → percentil
  inferior com o rótulo "critério ajustado ao tamanho do grupo"; abaixo do mínimo →
   **posto descritivo, sem percentil, sem sinalização, sem gráfico de distribuição**.
   `gatilho_usado` sempre exibido. No nível do procedimento, degrada pelo n **daquele
   procedimento**.
6. **Três estados de disponibilidade de referência**, dois tratamentos visuais:
  - *referência plena* — tela completa;
  - *referência insuficiente* — inclui a variante **sem formadores** (a área existe,
  a referência não). Mesmo componente visual; muda a frase de apoio e os motivos;
  - *sem grupo de pares* (classificação pendente) — sem comparativos; valem as
  análises intra-cooperado.
7. **Excedente sempre visível, inclusive abaixo do critério agregado.** O critério
  agregado governa o **realce da linha**, nunca a medição — o excedente é medido por
   procedimento, e um cooperado dentro da referência no agregado pode ter
   procedimentos acima do critério daquele procedimento. Travessão só na ausência de
   par sinalizado, nunca como "zero medido". Chips: *acima do critério agregado* ·
   *com procedimento em revisão* (**default**) · *todos*.
8. **Linha de justificativa em toda tela**: "Comparado com: <área> · n= elegíveis ·
  base eletiva · exclusões: <...>" — a categorização condensada, sempre visível.
9. Todo valor carrega período colado, selo de quarentena no R$, e o carimbo de
  proveniência com a versão da classificação (v1.0, não homologada).
10. **Percentil nunca sem tradução** ("P92 · acima de 9 em cada 10 colegas da área").
  **Ausência de atributo não vira etiqueta.** **Padrão marcado como recomendado**,
    com aviso e ação de restaurar ao desviar.

---



## ELEMENTOS GLOBAIS [v0]

Shell: barra lateral clara (navegação separada dos parâmetros da análise) + barra
superior fixa com busca e chips de critério ativo. Parâmetros: janela · critério de
revisão · referência de adequação · confiança · (avançado) volume mínimo e n mínimo —
todos por argumento, nunca lidos do config dentro de função. Banner de homologação em
toda página. Estado da tela na URL. Cache no servidor, não no navegador.

## 1. PANORAMA DA ESPECIALIDADE (página inicial)

Pergunta: **"onde está o custo excedente, e por onde começar?"** É o nível acima da
Área: primeiro se escolhe ONDE olhar, depois se olha.

**A regra que governa a página inteira: junta pessoas e valores, NUNCA réguas.** Todo
excedente que chega aqui foi medido contra a referência da área do próprio cooperado,
e é por isso que a unidade comum entre áreas é o excesso (solicitações e R$) e não a
posição. Percentil comparando médicos de áreas diferentes é o pecado capital do
método, e o smoke cobra estruturalmente que nenhuma chave de posição atravesse o
payload desta tela.

Construída em quatro etapas. **Etapa 1 entregue**; as demais estão declaradas na
própria tela, no rodapé, até entrarem.

### Etapa 1 · escopo, onde o excesso está, e quem não pode ser medido [v1]

- **Linha de contexto** sob o título, mesma construção da tela de Área:
  `200 cooperados · 118 comparáveis em 2 áreas com referência · 72 em classificação
  pendente · 9 em áreas sem referência · 172.141 solicitações excedentes de 118
  cooperados · R$ 5,3 mi`. Cada parte carrega a própria definição no hover.
- **Um cartão por ÁREA DE ATUAÇÃO, todas elas, do MESMO tamanho.** A tela é o catálogo
  da especialidade, e área que não aparece é área que ninguém lembra de classificar. O
  que separa as duas famílias é o CONTEÚDO do cartão, não a presença nem o tamanho:
  - **com régua** (2 de 7): custo excedente em destaque, solicitações, barra da fatia
    no excedente da especialidade, população e casos qualificados.
  - **sem régua** (5 de 7): a população no lugar do valor e o motivo de não sinalizar
    no lugar da fatia. **Não imprime zero** — zero afirmaria ausência de variação onde
    o que falta é contra quem medir.
  - **Uma grade, um tamanho.** Houve uma versão com dois cartões grandes para as áreas
    com régua: eles prometiam responder "onde o excesso está", e essa é pergunta de
    Pareto, que tem seção própria na etapa 3. Cartão grande sobre uma lista de áreas
    afirma concentração onde o desenho só cataloga. O que distingue as áreas é o
    conteúdo do cartão e o recuo de quem não tem régua.
  - O **título da seção é "Áreas de atuação"**, não "Onde o excesso está", pelo mesmo
    motivo: um título que promete concentração sobre uma grade que lista faz o leitor
    procurar ali uma resposta que o desenho não dá.
  - A **barra é a fatia da área no excedente da especialidade**, não a fatia da maior:
    a pergunta é quanto do problema mora ali, e normalizar pela maior faria a segunda
    área parecer maior sempre que a primeira encolhesse.
  - O motivo é **redigido no bloco do Panorama**, não herdado do estado da área: a
    frase de lá termina em "motivos abaixo", apontando para a barra de composição, que
    só existe na tela de Área.
- **Classificação pendente em faixa própria.** 72 dos 200 cooperados, 36% da
  especialidade, e é o único número da tela cuja ação não passa por comitê: é triagem
  clínica, trabalho de cadastro. Como mais um cartão entre as áreas ele vira nota de
  rodapé, e some justamente o que dá para resolver.
- **Componentes reusados, nenhum novo**: o cartão é o `.kpi` do contrato (virou link e
  ganhou barra de proporção), a faixa de pendência é a `.res-destaque` da Leitura da
  área, e a linha de contexto é a mesma marcação do cabeçalho da Área.

**Motor.** `blocos.panorama_da_especialidade` monta o bloco; `/api/panorama` agrega.
**Nada nasce no endpoint**: o catálogo de áreas é o MESMO de `/api/meta`
(`_areas_resolvidas`) e o excedente de cada área é o da cascata daquela área, pela
mesma `_cascata_area` que a tela de Área usa. O smoke cobra a igualdade: o excedente
do cartão de Ginecologia é, caractere a caractere, o destaque da Leitura da área.

**Custo.** Paga a cascata de cada área COM RÉGUA, e só delas. São duas nesta base, e
as duas ficam memoizadas — a tela de Área que o analista abrir em seguida não paga de
novo. Escala com o número de áreas comparáveis, não com o total de áreas nem de
cooperados.

**"Acima do critério" não entra no cartão.** Esse degrau alcança 63 dos 63 comparáveis
em Ginecologia e 55 dos 55 em GO, por construção do método (são centenas de percentis
testados por área). Um cartão dizendo "63 de 63" não separa uma área da outra; o
cartão traz o último degrau, que é o que sobra para trabalhar e o mesmo conjunto que a
fila vai listar.

### Etapa 2 · fila de casos cruzando as áreas [pendente]

Chips de recorte, cards do recorte e a tabela com os cooperados de todas as áreas
juntas, ordenada por excedente em R$. **A unidade é o COOPERADO**, e é isso que a
distingue do bloco "Principais oportunidades" da Área, cuja unidade é o par: Panorama
responde *com quem eu converso*, a Área responde *sobre o quê*.

Sutileza a declarar na tela: o recorte é aplicado DENTRO de cada área e depois unido.
"Qualificado" quer dizer qualificado na própria área, e o degrau "material" é o Pareto
de 80% de cada área, não da especialidade.

### Etapa 3 · procedimentos transversais [pendente]

Procedimentos ordenados por excedente somado, com **em quantas áreas cada um aparece**.
É a seção que só o Panorama pode dar: dos 259 procedimentos com excedente, 213 estão
nas duas áreas e carregam **94% do excedente**. Muda a ação — excedente alto nas duas
áreas é conversa de protocolo, não conversa individual.

### Etapa 4 · funil da especialidade [pendente]

Os degraus somados das áreas com régua, cada um clicável aplicando o recorte na fila.

### Fora desta página

Comparação entre especialidades (só há uma), posição ou percentil cruzando áreas
(proibido pelo método), deltas contra o período anterior (a janela tem um ano),
estados de caso e economia realizada [v1].

## 2. ÁREA DE ATUAÇÃO (o peer group visível) [sessão 1 — em construção]

Pergunta: "o que é normal aqui, e quem está fora?"

- Título + contexto → linha de justificativa → **barra de composição segmentada**
(formam · abaixo do volume · fora da construção, com nome e motivo ao expandir) →
**faixa de estatísticas sem moldura** (acima do critério · consistência · variação
excedente · impacto estimado · peso na especialidade). [v0]
- **Principais oportunidades** (entre a Leitura da área e as abas): uma linha por
PAR (cooperado × procedimento), do maior custo excedente ao menor, entre os casos
qualificados. [v1]
  - **O degrau que faltava.** O guia de produto (§9) lista cinco perguntas que toda
    página deve responder, e esta parava na quarta: o que está acontecendo (a
    Leitura), por que (os gráficos), onde (as tabelas) e o que investigar (as
    gavetas). "O que fazer agora" é este bloco.
  - **O cruzamento que não existia.** O app já ordenava cooperados DENTRO de um
    procedimento (o painel lateral) e procedimentos DENTRO de um cooperado (a tabela
    do dossiê). Os pares de toda a área numa lista só não existiam em superfície
    nenhuma.
  - **Nenhuma medida nova.** Os pares, o custo excedente de cada um e a régua de cada
    procedimento já viajavam prontos no mesmo endpoint. O bloco junta e ordena.
  - **É uma TABELA**, com a moldura e os rótulos que a página já usa. A primeira
    versão usou a entrada da gaveta lateral (um cartão de leitura vertical) e destoava
    de tudo em volta: tipografia diferente, linhas altas demais, e três fatos
    empilhados por caso onde a página inteira usa colunas.
  - **Cada coluna argumenta a oportunidade**, e é só isso que entra: Cooperado ·
    Procedimento · **Razão** (quanto está fora do padrão) · **Excesso de solicitações**
    (quanto disso é volume) · **Excesso em R$** (quanto vale, e a ordem) · **% do
    excedente da área** (quanto este caso move do problema inteiro).
    - A última é a que separa o bloco de mais uma lista ordenada: R$ 47 mil não diz
      por si se vale uma conversa, 1,1% do excedente da área diz.
    - Saíram Consultas, Frequência e Referência, que a primeira versão copiou da
      tabela do dossiê. Lá elas são o diagnóstico de um cooperado e a tela inteira é
      sobre ele; aqui a pergunta é "vale trabalhar este caso", e três colunas para
      reconstruir uma divisão que a quarta já entrega faziam o bloco ler como uma
      quarta tabela da mesma família. As três viajam na **leitura da célula da
      Razão**: o guia pede o denominador ALCANÇÁVEL no momento da leitura (§13), não
      ocupando coluna própria.
  - **Sem ordenação no cabeçalho**: a lista JÁ é a ordem por custo excedente, e é ela
    que define quais casos entram. Uma seta prometeria reordenar o conjunto que foi
    escolhido por essa ordem.
  - **Só CASOS QUALIFICADOS**, o último degrau da cascata. Uma lista de todos os que
    passam o critério poria em primeiro lugar o cooperado cujo fator de contexto
    explica o volume, que é o pior caso para abrir uma conversa (rigor §4). Como a
    condição vale para todas as linhas, ela é dita UMA VEZ no rodapé, nomeando o
    critério ativo, e não repetida linha a linha.
  - **As duas lentes e o denominador.** Ordem pelo custo excedente (magnitude) com a
    razão na linha (intensidade), porque razão sozinha traz procedimento raro e custo
    sozinho traz volume clínico (rigor §3). Frequência, referência da área e consultas
    ao lado: número de indivíduo não se publica sem a referência do grupo (LEXICO,
    princípio 6) nem sem o denominador (rigor §1).
  - **As três células fecham na linha**: frequência ÷ referência é a razão impressa ao
    lado, e o smoke cobra isso. Foi o que expôs o formatador: com três casas fixas
    abaixo de 0,1, uma referência de 0,0038 saía "0,004" e a divisão errava 6%.
    `fmt_frequencia` passou a manter três algarismos significativos em qualquer escala,
    o que corrige junto a mesma coluna na tabela do dossiê.
  - **Carga limitada** a `N_OPORTUNIDADES_MAX`, visíveis `N_OPORTUNIDADES_VISIVEIS`.
    São 228 casos qualificados em Ginecologia, e uma lista desse tamanho num cartão
    acima das abas viraria uma terceira tabela fora do lugar onde as tabelas moram. O
    total vai declarado no cabeçalho ("5 de 228"), e a superfície exaustiva é a aba
    Cooperados.
  - **O cabeçalho acompanha a lista.** Ele soma o custo excedente do que está em cena
    e o põe sobre o da área ("5 de 228 casos qualificados · R$ 356 mil, 9% do custo
    excedente da área"); revelar o resto reescreve a frase ("20 de 228 · R$ 742 mil,
    19%"). As duas versões vêm PRONTAS do motor e o front alterna a string: a soma e a
    fração são números do método, e recalculá-las no navegador seria o segundo lugar
    em que elas nascem (Lei 1). A leitura da frase declara a base do percentual.
  - **Ressalva de preço com contagem**: a ordem é por dinheiro, e caso qualificado sem
    preço apurado nas contas não pode ser ordenado. Sem a linha do rodapé o bloco
    esconderia casos por falha de dado.
  - **Segue o recorte** (Lei 0), como a Leitura e os dois Paretos. Recorte mais amplo
    não muda nada, porque os qualificados já são o degrau mais estrito; recorte de
    perfil reduz (em Ginecologia, "opera" leva de 228 para 48 casos).
  - **Não é aba.** As duas abas da página são duas LENTES do mesmo conjunto; este
    bloco é a conclusão tirada das duas. Como aba, ficaria atrás de um clique e no
    mesmo nível de duas perguntas que ele responde.
  - **Clicar na linha abre o painel do procedimento com o par APONTADO**; o nome e o
    chevron vão para o dossiê. Dois destinos, os dois já construídos, o mesmo par de
    gestos da tabela de Procedimentos. A linha carrega código e descrição, então o
    painel não depende de a tabela estar montada nem de o procedimento estar visível
    nela.
    - Apontado nos DOIS desenhos do painel: a linha na lista "Acima do critério" e o
      ponto no enxame da distribuição, com os demais recuando. Quem clica escolhe um
      PAR, e um painel que abrisse sem dizer qual dos 54 pontos é o dele obrigaria a
      procurar no gráfico o nome que se acabou de clicar. Se o cooperado estiver na
      cauda da lista, ela é aberta e rolada até ele.
    - A marca é a MESMA do fio de hover entre lista e gráfico: um segundo realce só
      para este caso ensinaria duas gramáticas para a mesma ideia. O que muda é a
      permanência — **o hover empresta o destaque e o devolve ao sair**, o apontado
      fica. Sem esse retorno, passar o cursor por um nome qualquer apagava o caso que
      o auditor veio investigar.
    - E o realce só TROCA quando há para onde trocar: o enxame tem todos os que
      solicitam o procedimento (54), a lista só os que passaram o critério (17).
      Apontar um ponto sem linha correspondente apagava a linha apontada sem acender
      nenhuma outra, e explorar o gráfico desfazia o estado do painel.
- **Distribuição** (dentro do container de gráficos, aba "Distribuição"): 1 ponto
por cooperado avaliável, haste do menor ao maior, faixa IQR do grupo que forma a
referência, régua de referência e de critério. Clicar num ponto destaca a linha na
tabela. Não renderiza nos estados sem referência plena. [v0]
  - **Escala de cor: variante E**, a mesma dos dois painéis de procedimento (ver
    abaixo), adotada em todo o app em set/2026. Dois estados: dentro do padrão da área
    em cinza, acima do critério da medida em cena em verde chapado, sem rampa e sem
    halo. O que saiu foi a tinta por excedente em R$ (cinza-âmbar-vermelho, por
    quantil): ela dizia dinheiro enquanto o eixo dizia frequência, e cobrava uma
    legenda de três valores para ser lida. Quem responde "quanto" é o Pareto ao lado, e
    a dica de cada ponto imprime o excedente por extenso.
  - **As duas réguas voltaram** em set/2026, pelo artboard "Medyx Area de Atuacao":
    referência de adequação (tracejada) e critério de revisão (contínua), as duas em
    `--g-900`, rotuladas com o valor. Elas tinham saído em ago/2026 porque o critério
    AGREGADO não governa a sinalização — o que continua verdade, está no título da
    linha e no rodapé do bloco, e é por isso que a régua aqui LOCALIZA em vez de
    julgar; quem julga é o gráfico por exame. O que mudou é o reconhecimento de que
    enxame sem marca nenhuma não responde pergunta: via-se espalhamento sem saber onde
    a área considera que o normal acaba. Ressalva que o desenho não pode apagar: 46 dos
    63 ficam do lado de cá da linha e carregam 34% do dinheiro — abaixo do critério
    agregado não é limpo.
  - **Convenção de linha** (artboard "Medyx Escala de Cor"): contínua = critério, o que
    julga; tracejada = referência, o que contextualiza. Vale nos três gráficos que
    desenham régua. Os tokens `--ch-ref-style-*` estavam invertidos e foram corrigidos
    em set/2026 — replicar no Design.
  - **Três medidas no eixo**, num segmentado no cabeçalho do cartão (2026-08-31):
    *Exames* (solicitações por consulta) · *Custo* (R$ solicitados por consulta,
    a mesma fonte da coluna "Custo por consulta" da tabela) · *Excesso* (variação
    excedente em R$ por consulta). Trocar de medida é LEITURA, não recorte: o
    conjunto em cena, a escolha de um ponto e o filtro de perfil atravessam a
    troca, e a medida não viaja na URL. Nas medidas de dinheiro, quem não tem
    preço nas contas ou par acima do critério fica FORA do gráfico e é contado
    no rodapé (ausência não é zero); a caixa some quando menos de
    `N_MINIMO_P75` formadores da referência têm a medida. Cada medida traz as suas
    duas réguas, tiradas da MESMA norma que desenha a caixa: no índice é a norma
    publicada da área, nas duas de dinheiro é a construída sobre o mesmo grupo.
  - **Altura igual nas três vistas** (set/2026): Concentração, Distribuição e
    Quantidade × custo mediam 516, 357 e 511px, e trocar de aba fazia a página saltar
    sob o cursor. Um `min-height` no painel iguala as três pela mais alta (o Pareto,
    medido — não arbitrado). Container que muda de altura ao trocar de vista faz o
    leitor perder o lugar, e a aba é leitura: não devia mover nada.
    - O CARTÃO PREENCHE o painel, em vez de flutuar no topo com o vão embaixo: a
      distribuição fechava em 357px e os 159 restantes eram branco, o que trocava o
      salto por um gráfico pequeno numa moldura grande. Cartão, faixa e plotagem
      crescem juntos, e a altura que sobra vira espaço de desenho.
    - O boxplot é AMPLIADO, não esticado: cada medida guarda a fração que tinha no
      gráfico de 110px, contada sobre a faixa entre o topo e a linha do eixo. A caixa
      continua sem encostar no eixo, com a mesma folga relativa; a haste continua no
      meio dela. Esticar até o eixo (como faz o artboard) daria outro desenho.
    - O enxame é reposto por `ResizeObserver`, e não só na montagem: a altura final só
      existe depois que o layout assenta, e ler antes punha os pontos 15px fora da
      caixa. O DOM não é refeito — muda só a altura de cada ponto, então escolha,
      recorte e foco sobrevivem.
  - Antes o eixo era só o índice, e quem pedia POUCO e CARO ficava no meio da
    nuvem: era a pergunta que o bloco não sabia responder.
- **Linha de contexto** sob o título: escopo da área, fixo, acima dos chips —
`64 na área · 63 comparáveis (ver os 6 fora da referência) · 63 com excedente em algum
procedimento · 18 também atípicos no índice agregado`. As duas medidas do excedente
(`132.526 solicitações · R$ 4,2 mi`) saíram dela em set/2026: a Leitura da área
imprime as duas logo abaixo — a de solicitações como linha do grupo, o R$ como
destaque, e as duas de novo na nota —, e a linha de contexto era a superfície em que
elas diziam menos, sem denominador ao lado e sem declarar que não se movem com o
recorte. O que a linha carrega é o ESCOPO, que nenhum outro bloco repete.
- **Os Paretos não trazem subtítulo de população** (set/2026). Ele dizia "excedente
somado sobre: comparáveis (63)" e era a terceira aparição do mesmo fato na mesma dobra:
o chip de Recorte, logo acima, imprime o recorte ativo com a contagem, e a Leitura da
área abre com o mesmo conjunto. Sobrou a leitura de concentração, que é o que só o
Pareto diz. A frase continua no rodapé da tabela de Procedimentos, onde não há chip nem
Leitura ao lado dela.
- **A faixa de abas dos gráficos sobrevive ao redesenho do Pareto.** Ela mora DENTRO do
cartão do gráfico em cena, e o Pareto se refaz com `replaceChildren` a cada troca de
ordem ou de recorte. A troca de recorte já a devolvia, por fora; a de ordem acontece
dentro do bloco e não tinha quem o fizesse, então ordenar apagava o caminho para
Distribuição e Quantidade × custo e o cartão encolhia a altura da faixa. `montarPareto`
passou a aceitar um retorno de redesenho, e a página devolve a faixa por ele.
- **Aba Cooperados** (default): identidade · magnitude · evidência · desfecho.
Colunas de evidência: procedimento que puxa (com razão), consistência por trimestre
com direção, leitura de concentração, fatores de contexto. [v0]
  - **Pareto, distribuição e tabela apontam o MESMO cooperado.** As três mostram o
    mesmo conjunto por eixos diferentes, e escolher num deles escolhe nos três. O fio
    corria só num sentido até set/2026 (a barra levava à linha, a linha não levava à
    barra): quem clicava na tabela procurava o cooperado à mão numa lista de 63 barras
    dentro de uma janela de 300px. A barra apontada recebe realce e régua à esquerda, e
    a lista rola até centrá-la — só quando ela está fora da vista, para que clicar numa
    barra visível não puxe a lista debaixo do cursor. A barra apontada muda só o FUNDO,
    no mesmo cinza da linha de tabela apontada: a régua vertical que ela teve por um dia
    resolvia um problema que a rolagem automática já não deixa acontecer, e cobrava por
    isso uma tinta forte dentro de um gráfico onde a cor é do dado.
- **Aba Procedimentos**: procedimento · prevalência entre os pares · solicitantes
elegíveis · referência · qualidade da referência · solicitações · acima do critério ·
excedente · % acumulado. Ordenável — por excedente é o Pareto; por prevalência é "o
que é rotina aqui"; por solicitações é "o que mais se pede". [v0]
  - **Solicitações** entrou em set/2026: prevalência diz quantos cooperados pedem, e
    nada dizia QUANTO se pede. Um exame que todos solicitam uma vez ao ano e outro que
    todos solicitam toda semana saíam com a mesma prevalência de 100%. Segue o recorte,
    como as demais colunas de achado.
  - **Filtro "Todos | Com excedente"** (segmentado no cabeçalho, com a contagem em
    cada opção): dois em cada três procedimentos da área não têm ninguém acima do
    critério — 232 de 671 em Ginecologia —, e eles ocupam a lista inteira abaixo da
    linha em que o excedente acaba. É LOCALIZAÇÃO, não recorte: esconde linhas e não
    toca em soma nenhuma (o % acumulado não muda, porque quem sai contribuía com
    zero). Viaja na URL (`pexc`) e é declarado no rodapé da tabela.
- **Painel do procedimento na área** — abre ao clicar numa linha da tabela ou numa
barra do Pareto de procedimentos, na mesma gaveta do painel do dossiê. Responde a
pergunta que nenhuma coluna separa: **este exame é norma da área ou hábito de alguns**.
Em Ginecologia, US Transvaginal (mediana 0,283 · P75 0,355) e US Estruturas
Superficiais (mediana 0,032 · P75 0,135) têm prevalência alta e excedente grande nas
duas linhas da tabela; o primeiro é discussão de protocolo e o segundo é auditoria.
Oito seções, na ordem de leitura: [v1]
  1. **Peso na área** — fatia das solicitações e do custo do recorte. Decide se vale
     ler o resto: um exame com 0,3% do custo não muda a conversa.
  2. **Distribuição na área** — o box plot do painel do dossiê com o enxame da tela de
     Área por cima, um ponto por cooperado. A POSIÇÃO é régua e não se move com o
     recorte; quem está fora do recorte recua. A leitura vem redigida do motor: a
     razão P75/referência separa a distribuição compacta da assimétrica.
     - **Escala de cor: variante E** do artboard "Medyx Escala de Cor" ("sem escala e
       sem brilho"), adotada em set/2026. Dois estados e só: dentro do padrão da área
       em cinza (`--g-500`, opacidade .6 no claro e .75 no escuro), acima do critério
       em verde chapado (`--acc`), 7px contra 8px, sem rampa e sem halo. Nenhum matiz
       novo entra — as duas tintas já são token nos dois temas.
     - O que a variante cobra, e onde o painel recupera: a tinta deixa de dizer
       QUANTO, e o realce passa a depender só de matiz. A lista logo abaixo ordena por
       excedente e acende o ponto no hover, que é o canal onde essa pergunta passou a
       viver. Sem esse fio a leitura ficaria incompleta: a lista ordena por excedente e
       o eixo é a taxa, e `excedente ≈ (taxa − referência) × consultas` — em US
       Estruturas Superficiais o primeiro da lista é o 11º ponto mais à direita, e o
       ponto mais à direita de todos não entra na lista.
  3. **Concentração entre cooperados** — quantos somam 80% do excedente deste exame,
     pelo mesmo `FRACAO_PARETO_MATERIAL` do degrau "material" da cascata.
  4. **Acima do critério** (recolhível, com a seta do resto do app) — o NÚCLEO dos 80% (o mesmo da seção anterior, entre
     `MIN_NOMES_PAINEL` e `MAX_NOMES_PAINEL`), com taxa, razão, excedente e R$, cada
     um com o chevron do dossiê. A cauda viaja no payload e é revelada sob demanda,
     nunca escondida. É a seção que fecha o painel em ação.
     - O corte era um número fixo, e acertava por acaso: nestes dados os oito
       primeiros somam de 79% a 97% do excedente. Mas em 40316378 quatro pessoas
       fazem 97% e listar oito enfileira quatro nomes irrelevantes; em 41301099 são
       nove e o corte em oito deixa um relevante de fora.
     - **Rodapé: "Ver os N na tabela de Cooperados"** — leva os nomes para a aba
       Cooperados como LOCALIZAÇÃO (`exame`/`exame_ids` na URL), irmã da busca e não
       do recorte: encontra dentro do que está em cena e não move card, Pareto nem
       régua. Declarada numa pílula desligável ao lado da busca e no rodapé da tabela.
       Existe porque a gaveta responde "quem pede este exame fora do padrão" e a
       pergunta seguinte — "e como esses estão no resto da prática deles?" — é a
       tabela, com ordenação e colunas agregadas que a lista não tem e não deve ter.
  5. **Solicitações por faixa etária** — a repartição do recorte contra a da área.
  6. **Repetição por beneficiário** — distingue "muitos pacientes uma vez" de "poucos
     pacientes muitas vezes". Sem a lista de quem concentra, que existe no painel do
     dossiê: no agregado da ÁREA ela seria sempre vazia.
  7. **Autorreferenciamento** — mesmo portão de cobertura do painel do dossiê, sobre o
     agregado. É onde a leitura vale mais: por par a cobertura mediana é de 11%.
  8. **Custo por trimestre** — sobre os cooperados ACIMA DO CRITÉRIO, para os quatro
     trimestres somarem o excedente que a seção 1 anuncia.
  Metade régua, metade achado, como a tabela de onde ele abre: a distribuição não se
  move com o recorte; peso, concentração, lista, faixas, repetição, autorreferência e
  trimestres seguem.
- Drill do procedimento para os cooperados · auditoria da referência por procedimento
(quem forma, quem foi excluído por sub-perfil). [v1 — F1/F2]



## 3. DOSSIÊ DO COOPERADO (a evidência) [sessão 2]

Pergunta: "por que este caso existe — e o que o defende?"

- Cabeçalho descritivo (consultas eletivas, pacientes distintos, especialidade,
sub-perfis, confiança, versão) — **todo número com o par da área ao lado**. [v0]
- Posição nas duas réguas · duas lentes por procedimento · trajetória contra a banda
da área por trimestre · consistência por procedimento · concentração por
beneficiário · fatores de contexto · piso de confiança ou "intervalo
não calculável". [v0]
- **Painel do procedimento** — abre ao clicar numa linha da tabela de procedimentos e
fica ao LADO dela, não sobre ela: o auditor troca de exame sem fechar nada e compara.
Não vira coluna — a tabela já carrega dez, e o que este painel mostra é evidência de
segundo nível, procurada depois que uma linha chama atenção. Quatro blocos: [v1]
  1. **Posição na área** — a distribuição daquele procedimento, um ponto por cooperado.
     Mesmo componente da distribuição da área, alimentado por `norma_por_procedimento`.
  2. **Repetição por paciente** — quantas vezes o mesmo exame foi solicitado para a
     mesma pessoa na janela, em OCASIÕES (consultas distintas), com o intervalo mediano
     entre elas. Nunca sem o par da área ao lado: repetição é o protocolo em pré-natal
     (cardiotocografia repete em 62% dos casos) e é achado em rastreio. O número
     sozinho não acusa.
  3. **Concentração entre pacientes** — lista ordenada dos que mais concentram, com a
     participação de cada um nas solicitações do exame e o intervalo entre repetições,
     mais o share do topo contra a referência dos pares.
  4. **Autorreferência do procedimento** — COM PORTÃO: só aparece acima de um mínimo de
     itens com conta localizada e de cobertura do cruzamento. A cobertura mediana por
     (cooperado, procedimento) é de 11% — abaixo do portão a célula declara "cobertura
     insuficiente" com o número real, nunca uma taxa apoiada em nada.
  Sem custo adicional, já calculados e hoje não exibidos: a série por trimestre do
  procedimento e o piso de confiança do par.

  **Identificação do beneficiário.** A lista usa o `ID_BENEFICIARIO` do mapa
  (`beneficiario_N`) — pseudônimo estável, nunca o hash de origem, que não sai do
  `dim_beneficiarios`. O id é estável de propósito: reconhecer que a mesma pessoa
  concentra dois exames diferentes é achado, e rótulo local ao painel esconderia isso.
  Nenhum dado clínico ou demográfico acompanha o id.
- Sem grupo de pares / referência insuficiente → dossiê intra-cooperado + posto. [v0]
- Ação "sinalizar classificação incorreta" → fila de revisão. [v1 — F4]
- Case-mix descritivo · exportar PDF. [v1]



## 4. PROCEDIMENTOS (a quarta dimensão) [set/2026]

A granulometria que faltava. As três telas anteriores olham QUEM: a especialidade,
o peer group, a pessoa. Esta olha O QUE SE PEDE, e responde a pergunta que nenhuma
das outras responde: **isto é hábito de alguns, ou é padrão da especialidade?**

### Por que esta lista tem número, e a de cooperados não

O índice de cooperados é uma porta sem número nenhum, por regra: ele atravessa os
peer groups, e coluna ordenável ali convida a ler a lista como ranking, que é a
comparação proibida.

Com procedimento a soma é legítima, e é essa diferença que torna a tela possível: o
excedente de cada par já foi medido contra a referência da ÁREA daquele cooperado.
Somar entre áreas junta dinheiro já comparado, nunca réguas. É a mesma soma que o
Pareto de procedimentos transversais do Panorama publica.

### 4.1 `/procedimentos` · o índice

Um procedimento por linha, somado entre as áreas com régua. Ordenável, busca por
nome ou código, ordem de entrada por variação excedente.

| Coluna | Motor |
| --- | --- |
| Procedimento (link) | `DS_PROCEDIMENTO` · `CD_PROCEDIMENTO` |
| Áreas | áreas COM EXCEDENTE, não onde ele aparece: presença sozinha não diz nada |
| Solicitantes · Custo total · Acima do critério | `posicao_proc_rs` |
| Variação excedente · % do custo | `excedente_reais` filtrado pelos três portões |

`blocos.indice_de_procedimentos` · `GET /api/procedimentos`.

Procedimento sem preço apurado nas contas aparece com volume e solicitantes, e o
custo sai como `SEM_MEDIDA`. São 254 dos 883 na janela de mai/25 a abr/26, e apenas
0,3% das solicitações: códigos genéricos ("Procedimento não identificado", pacotes)
e coisas pedidas por GO e pagas fora deste recorte (fonoaudiologia, TO, acupuntura).
Zero afirmaria ausência de custo onde há ausência de preço.

### 4.2 `/procedimento/{codigo}` · um procedimento

Três blocos:

1. **Leitura do procedimento** · volume, preço de referência (com o n de execuções
   que sustenta a mediana), alcance do excesso. Mesmo desenho da Leitura da área
   (`blocos/leitura-area.js`), com a unidade trocada.
2. **Onde ele é pedido, por área de atuação** · AS RÉGUAS LADO A LADO, a seção que
   só esta tela dá: prevalência, referência e critério de CADA área, com quantos
   passaram o critério e quanto isso vale. Não é ranking entre áreas, e a nota da
   seção diz isso na tela: a mesma frequência pode ser rotina em um grupo e sinal em
   outro. Sem ela, quem lê o excedente somado supõe uma régua única onde há várias.
3. **Quem pede acima da referência** · os pares acima do critério, cada um medido
   contra a régua da PRÓPRIA área, com a área declarada na linha e link ao dossiê.

`blocos.retrato_do_procedimento` · `GET /api/procedimento/{cd}`.

Nenhuma das duas tabelas ordena, e é decisão: a de áreas porque cabeçalho clicável
sobre peer groups convida a ranqueá-los; a de cooperados porque a ordem dela É o
achado.

### O seletor de área sai das duas telas

Um procedimento não pertence a uma área, ele atravessa todas. Controle que não
governa nada promete um papel que não cumpre. A faixa de critérios FICA: todo número
das duas telas é número comparado, e a faixa é o carimbo de sob qual régua.

### Pendente

Preço com dispersão (IQR do valor unitário) e a série trimestral do procedimento.

## 5. NOTA METODOLÓGICA [v0 — render do md]

METODOLOGIA renderizada + glossário do léxico + as defesas escritas: mediana e
robustez, percentis e não p-valor, critério ≠ referência, critério degradado por n,
fronteira GO/Ginecologia, regra do PS, quarentena do preço, premissa da
autorreferência.

## FORA DO MVP (decidido)

Estados de caso e trilha · IDs de caso · PDFs · fluxo de contestação da classificação ·
página de qualidade de dados · página LGPD/papéis · benchmark externo (norma injetável —
o motor já aceita `norma=` por argumento) · comparação entre especialidades.