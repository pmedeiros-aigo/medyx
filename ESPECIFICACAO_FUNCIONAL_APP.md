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

1. **Peer group de sinalização = área do MVP da classificação v2.0** (`area_mvp` de
  `dim_classificacao_v2.csv`): Ginecologia Geral, Obstetrícia, Endoscopia Ginecológica,
   Mastologia, Ginecologia Endócrina, PTGI, Ultrassonografia, Patologia. A área vem
   da mistura de famílias de atendimento das consultas do cooperado, não de rótulo
   dado por médico (METODOLOGIA §4.1).
2. **Sub-perfil é exibição de identidade, nunca recorte nem base de comparação.**
  Ele aparece como etiqueta na linha do cooperado, com a explicação no hover; a
   régua continua sendo a da especialidade e nenhuma coluna vira travessão.
   O **filtro por sub-perfil** existiu até set/2026 e recortava a lista, com um
   **posto interno** ("3º de 12") numa coluna à parte. Saiu a pedido do médico que
   auditou a tela: os cinco perfis se declaram informativos, a identidade já está
   na linha, e o que só o filtro fazia era reagregar Leitura, Paretos e
   Oportunidades sobre 2 a 7 cooperados (METODOLOGIA §5.8).
3. **Norma construída só com** `elegivel_norma=True`**; todos são MEDIDOS contra ela.**
  Quem não forma aparece com o **motivo**, e o motivo distingue exclusão definitiva
   (perfil de execução) de provisória (cadastro agregado — confirmação pendente;
   confiança baixa; sem área).
4. **Base eletiva por padrão** (`incluir_ps=False`); carimbo BASE_ELETIVA visível.
5. **Critério degradado pelo n**: pleno → percentil padrão; intermediário → percentil
  inferior com o rótulo "critério ajustado ao tamanho do grupo"; abaixo do mínimo →
   **posto descritivo, sem percentil, sem sinalização**. A distribuição CONTINUA
   sendo desenhada, em modo **descritivo**: pontos e amplitude (menor ao maior
   observado), sem caixa interquartil, sem régua e sem ninguém marcado, com a
   leitura declarada no rodapé (set/2026). A regra dizia "sem gráfico de
   distribuição" e juntava duas coisas que não são a mesma: um P90 sobre 6
   observações é uma observação, mas os 6 valores existem — a tabela já os lista
   por posto e a dispersão já desenha os mesmos pontos na mesma tela. Suprimir o
   bloco não protegia ninguém; entregava um painel em branco.
   `gatilho_usado` sempre exibido (nulo no modo descritivo). No nível do
   procedimento, degrada pelo n **daquele procedimento**.
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
  proveniência com a versão da classificação (v2.0, não homologada).
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
do cartão de Ginecologia é, caractere a caractere, a linha "excedente" do grupo
"Custo" da Leitura da área.

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
- **Evolução mensal** (entre "Principais oportunidades" e as abas): a área no tempo,
em DUAS unidades. Motor: `blocos.evolucao_mensal_da_area`, sobre `pipeline.custo_mensal`
e sobre a mesma série trimestral do dossiê. [set/2026, vindo do artboard "Medyx Dossie
Cooperado"]
  - **Uma barra por MÊS**, altura = custo das solicitações do mês, valorado ao preço
    mediano da JANELA. Abaixo, a **faixa de fechamento por TRIMESTRE**, uma célula por
    trimestre com o excedente apurado ali, a fatia do custo que ele representa e a
    variação sobre o trimestre anterior.
  - **Por que duas unidades**: custo é soma e desce ao mês; excedente é apurado por
    trimestre (METODOLOGIA §5.4.2). Um excedente mensal seria uma medida que a
    metodologia não fez. É a única razão de o bloco ter duas camadas em vez de uma.
  - **O alinhamento é estrutural, não calculado**: o grupo de meses e a célula do
    fechamento recebem o MESMO peso (o número de meses, que vem do motor), e por isso
    a célula cai sob as barras que ela fecha em qualquer janela. Duas grades
    independentes com a mesma largura teórica acabam desencontradas em um pixel.
  - **As barras existem sem trimestre fechado.** Na janela de 3m não há fechamento, e o
    bloco aparece só com as barras, com a ausência da faixa declarada no rodapé. Antes
    de set/2026 o bloco inteiro sumia nessa janela.
  - **Mês parcial não vira barra**: entram só os meses completos dentro da janela, e os
    dias das pontas vão declarados. Barra de um dia lê-se como queda de custo.
  - **A identidade é verificada, nunca afirmada de véspera**: o bloco confere a soma
    par a par. Quando ela fecha, o rodapé NÃO diz nada (é o caso normal, e o rodapé é
    onde mora a ressalva); quando a janela não começa no dia 1, ele declara que o
    fechamento cobre um período deslocado. O aceite continua cobrado no smoke.
  - **O rodapé é legenda em cima, ressalva embaixo** (`.tbl-ft.tbl-ft-nota`), o mesmo
    arranjo do Pareto, da distribuição e da dispersão. A legenda saiu da direita do
    cabeçalho: acima do gráfico ela obriga a decorar as duas tintas antes de ver o
    desenho a que elas se referem.
  - **NÃO segue o recorte** (Lei 0), como a distribuição: a série é da área inteira, e
    trocar os chips não muda quem está sendo medido nela.
  - **O MESMO bloco serve a Área e o dossiê** (set/2026). As duas telas respondem a
    mesma pergunta em escalas diferentes (a área e um cooperado), e um desenho por
    escala obrigaria o leitor a reaprender o gráfico ao descer de uma para a outra.
    O bloco recebe a faixa trimestral PRONTA (de `evolucao_da_area` num caso, de
    `evolucao_trimestral` no outro): quem é o sujeito só muda quem monta a série de
    trimestres, e nada do desenho depende disso.
    A linha de apoio **pacientes** aparece só onde o dado existe — no dossiê ela
    separa "atendeu mais gente" de "pediu mais para a mesma gente"; na área não sobe,
    porque o mesmo beneficiário pode ter passado por dois cooperados e a soma das
    contagens não seria contagem de distintos. A célula não escreve a linha, em vez
    de imprimir um traço.
    Os **dois painéis de procedimento** continuam no `blocos/evolucao.js` trimestral:
    na coluna estreita de um painel o mês não cabe.
- **Distribuição** (dentro do container de gráficos, aba "Distribuição"): 1 ponto
por cooperado avaliável, haste do menor ao maior, faixa IQR do grupo que forma a
referência, régua de referência e de critério. Clicar num ponto destaca a linha na
tabela. Não renderiza nos estados sem referência plena. [v0]
  - **Título é a GRANDEZA, subtítulo é a LEITURA** (set/2026): `Solicitações por
    consulta` · `Custo por consulta` · `Excesso por consulta`, e abaixo
    "Distribuição dos cooperados pelo número de solicitações realizadas por
    consulta." (adaptado às outras duas medidas). Os dois abriam com
    "Distribuição", que gastava o começo de ambos sem distinguir um do outro. A
    ressalva "Sem critério de revisão nesta área." entra como SEGUNDA FRASE nas
    áreas que não sustentam percentil: é estado do dado, não descrição.
  - **A legenda não diz o que é um ponto.** Com o subtítulo abrindo em
    "Distribuição dos cooperados por…", a marca do ponto neutro repetia, duas
    linhas abaixo, o que a frase acima do gráfico acabou de dizer. Ela ficou com
    o que só ela explica: o ponto marcado, a caixa e as duas réguas. Vale nos
    dois estados (com e sem critério).
  - **A dica de cada ponto é FICHA** (set/2026): identidade no título e um
    `Rótulo: valor` por linha, com marcador. São a medida em cena, a posição no
    grupo (percentil COM a tradução ao lado, ajuste 2 do CLAUDE.md), o
    denominador de consultas (rigor §1) e o excedente na janela. O rótulo da
    segunda linha muda com a medida: *Posição na área* no índice, onde há
    percentil, e *Referência do grupo* nas duas de dinheiro, onde não há. As
    linhas vêm redigidas do motor. Forma e regra em `LEXICO_PRODUTO.md`.
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
    conjunto em cena e a escolha de um ponto atravessam a troca, e a medida não
    viaja na URL. Nas medidas de dinheiro, quem não tem
    preço nas contas ou par acima do critério fica FORA do gráfico e é contado
    no rodapé (ausência não é zero); a caixa some quando menos de
    `N_MINIMO_P75` formadores da referência têm a medida. Cada medida traz as suas
    duas réguas, tiradas da MESMA norma que desenha a caixa: no índice é a norma
    publicada da área, nas duas de dinheiro é a construída sobre o mesmo grupo.
  - **Modo descritivo em área sem critério** (set/2026): abaixo de `N_MINIMO_P75`
    formadores, a distribuição sai com os PONTOS e a HASTE (menor ao maior
    observado) e mais nada — sem caixa, sem as duas réguas, sem ninguém marcado.
    A dica de cada ponto troca o percentil pelo POSTO ("2º de 8"), que é o mesmo
    que a coluna de posição da tabela imprime, e o rodapé declara a leitura e o n.
    A **legenda acompanha**: ela nomeia só as marcas que estão no desenho, porque
    anunciar "referência da área" onde não há linha nenhuma faz o leitor procurar
    o que não existe e concluir que o gráfico falhou.
  - **Vista "Solicitações × custo"** (era "Quantidade × custo" até set/2026;
    "quantidade" era vago e não é termo do léxico). Um ponto por cooperado:
    solicitações por consulta no X, custo médio por consulta no Y, **valor total
    solicitado no tamanho**. TRÊS dimensões, e não quatro — a tinta do ponto era
    o excedente em R$, numa rampa, e **saiu em set/2026**: punha dois dinheiros
    diferentes no mesmo ponto (porte no tamanho, excesso na cor) sobre eixos que
    já falavam de um terceiro, e exigia uma legenda de três valores para ser
    decodificada. Mesma decisão que a distribuição tomou ao trocar a rampa por
    dois estados. O excedente segue na dica de cada ponto, por extenso, e é o
    Pareto ao lado que responde "quanto" com o eixo inteiro.
    Sem régua e sem cor de severidade, de propósito: o método não define critério
    para custo, e este gráfico descreve, não julga.
    O subtítulo diz o que é um PONTO; a legenda, de um item, diz o que é o
    TAMANHO. Cada fato numa superfície só.
  - **O rodapé é o mesmo nos três, e tem UMA LINHA** (set/2026): a faixa cinza
    (`.tbl-ft.tbl-ft-nota`) leva a legenda, e a ressalva entra como último item
    DELA, sem marca — o lugar onde o Pareto já punha "linha tracejada = corte de
    80%". A legenda da distribuição e a da dispersão ficavam soltas sobre o
    branco, e a nota abria uma segunda linha: a faixa da distribuição media 49px
    contra 39px do Pareto, em três gráficos que se alternam no MESMO cartão.
    Duas causas somadas, as duas corrigidas: a nota repetia o rótulo da marca da
    caixa ("Caixa P25–P75 de 44 que formam a referência" logo abaixo de "metade
    central do grupo"), e a marca `band` herdava `padding:12px 14px` do
    componente homônimo `.band` — por isso ela virou `mk-iqr`, e `.legend i`
    ganhou `padding:0` para nenhuma marca depender de não haver homônimo.
    A NOTA sobrou para a exceção: grupo sem caixa, e quem ficou fora do desenho
    (ausência não é zero). O **n da caixa** mudou de suporte e vive no hover da
    marca dela, como o denominador da leitura de concentração do Pareto.
  - **Onde não há mesmo o que desenhar** (sem área de atuação; sem nenhum
    formador da referência), o lugar do gráfico recebe a ressalva do estado numa
    `.caveat-box` centrada (`.tbl-vazio`), e não fica em branco. A aba continua
    na faixa de propósito: escondê-la faria sumir o sintoma e a explicação junto,
    e quem vem de uma área com três vistas para uma com duas não teria como saber
    o que aconteceu.
  - **Altura igual nas três vistas** (set/2026): Concentração, Distribuição e
    Quantidade × custo mediam 516, 357 e 511px, e trocar de aba fazia a página saltar
    sob o cursor. Um `min-height` no painel iguala as três pela mais alta (o Pareto,
    medido — não arbitrado). Container que muda de altura ao trocar de vista faz o
    leitor perder o lugar, e a aba é leitura: não devia mover nada.
    - O CARTÃO PREENCHE o painel, em vez de flutuar no topo com o vão embaixo: a
      distribuição fechava em 357px e os 159 restantes eram branco, o que trocava o
      salto por um gráfico pequeno numa moldura grande. Cartão, faixa e plotagem
      crescem juntos, e a altura que sobra vira espaço de desenho.
    - A LISTA DO PARETO entrou nessa conta em set/2026: a regra esticava só a
      plotagem, e o Pareto — que é justamente quem deu a medida da faixa — ficava
      30px aquém dela, com a legenda flutuando e branco embaixo. Quem estica nele
      é a lista, porque no Pareto a altura que sobra vira linha visível.
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
- **Seletor de recorte**: cada degrau da cascata traz a **definição escrita** sob o
rótulo, e não só no `title` (set/2026). Ela sempre veio do motor e sempre viajou com a
opção, mas ficava no hover: o leitor via `Sem explicação de contexto · 20` sem meio de
saber que aquilo retira quem tem urgência ou pronto-socorro que explique o volume.
Rótulo de recorte não se adivinha, e filtro que só se entende passando o cursor não é
filtro que alguém usa. O rótulo passa a quebrar em vez de truncar onde há definição
(`.pf-opt:has(.pf-desc) .nm`): cortar o nome e imprimir a explicação embaixo é a
hierarquia ao contrário. O filtro de áreas do Panorama usa a mesma opção, não manda
definição, e lá a linha única com reticências continua valendo.
- **Linha de contexto** sob o título: escopo da área, fixo, acima dos chips —
`64 cooperados na área · 63 comparáveis (ver os 6 fora da referência) · 63 com
excedente · 18 acima do critério`. Quatro partes CURTAS, e a qualificação de cada uma
no `titulo_longo`: a linha é ENQUADRAMENTO, e o comprimento de uma parte custa a
leitura das outras três. Ela chegou a imprimir as qualificações por extenso ("com
excedente em algum procedimento", "acima do critério em procedimentos por consulta") e
virou quatro orações; o que desceu para o hover foi só isso, nada se perdeu. A primeira
parte diz `cooperados` porque é a única que declara a UNIDADE que as outras contam.
Antes de set/2026 a última dizia "N também atípicos no índice agregado", que não
comunicava: "atípico" não é termo do produto e "índice agregado" é o nome interno da
razão. O valor do critério que ela invoca está desenhado como régua no gráfico de
distribuição, com o valor no rótulo. As duas medidas do excedente
(`132.526 solicitações · R$ 4,2 mi`) saíram dela em set/2026: a Leitura da área
imprime as duas logo abaixo, e a linha de contexto era a superfície em que elas
diziam menos, sem denominador ao lado e sem declarar que não se movem com o
recorte. O que a linha carrega é o ESCOPO, que nenhum outro bloco repete — e em
set/2026 a Leitura deixou de repetir a última parte dela ("N também atípicos no
índice agregado"), que ela imprimia numa segunda frase com um número que não
seguia o recorte.
- **Leitura da área**, abaixo dos chips: os números do recorte agrupados pela
GRANDEZA que medem, e cada grupo com o mesmo par de linhas — **total em cima,
excedente embaixo, com a fração ao lado**. São quatro: *Cooperados*, *Médias
por consulta*, *Solicitações* e *Custo*. O primeiro chamou-se *Escopo em cena* até
set/2026: o grupo nomeia a GRANDEZA que as suas linhas medem, como os outros três, e
"escopo" não é uma grandeza. As linhas dele não repetem o nome do grupo (*no recorte*,
*com volume para comparação*), pelo mesmo motivo que *Médias por consulta* tem
*procedimentos* e *custo*. A organização anterior (set/2026) tinha um
grupo "Solicitado no recorte" que juntava o custo TOTAL com as SOLICITAÇÕES
excedentes — duas grandezas em dois degraus diferentes, lado a lado como se fossem
comparáveis — e punha o custo excedente numa faixa de destaque ABAIXO da grade,
longe do total de que ele é a parte. Com o par junto, "quanto disso está acima da
referência" se lê na vertical, dentro do grupo, sem o olho atravessar o cartão.
  - A **frase** sob o título é a leitura de concentração do Pareto, e nomeia a
    grandeza: "21 de 49 cooperados concentram 81% **do custo excedente**". Ela dizia
    "do valor", e o mesmo bloco imprime dois R$ diferentes (custo total e custo
    excedente) a poucos centímetros. Sai com a **marca das afirmações**
    (`.res-itens`/`.res-item`, a bolinha de `--exc`), a mesma do "Leitura do caso" do
    dossiê: como `.sub` ela era indistinguível de um subtítulo que descreve o bloco, e
    ela não descreve o bloco — afirma um fato apurado.
  - **Sem apoio sob os números e sem notas no rodapé** (set/2026). Cada linha tinha
    uma terceira linha de 11px sob o valor (a fração, a base do preço), e o `.res-p`
    era criado mesmo vazio — então TODA linha carregava um vão sob o número,
    inclusive as que nunca tiveram apoio. E o bloco fechava com dois parágrafos de
    prosa cinza cujas afirmações já estavam na tela: `N dos N comparáveis têm
    excedente em algum procedimento` é a terceira parte da linha de contexto,
    `o excedente da área soma X e Y` é a própria grade sob o recorte default, e a
    régua é o que a faixa de critérios declara no alto e o que a distribuição
    desenha como linha, com o valor no rótulo.
    O único fato que não estava em outro lugar — **quanto do excedente da ÁREA este
    recorte cobre** — virou hover das duas linhas de excedente, e só aparece quando
    o recorte é menor que a área. A fração que o apoio imprimia se lê sozinha: total
    e excedente são as duas linhas do mesmo grupo, uma sob a outra, na mesma escala.
  - **O bloco não tem rodapé** (set/2026). Ele já tinha sido reduzido de dois
    parágrafos a uma linha (`Excedente medido procedimento a procedimento: cada um
    contra a referência da área naquele procedimento`), e a linha que restou era
    afirmação de **método**, não número do recorte: um resumo de números não fecha
    com uma frase sobre como eles nascem. O fato continua onde ele pertence, em três
    superfícies: a definição da coluna *Excesso em R$* da tabela, o painel de cada
    procedimento e a Nota Metodológica. O cartão é título, afirmação e grade.
    - **A RÉGUA AGREGADA DA ÁREA NUNCA ENTROU AQUI**, e as duas metades dela ficaram
      de fora por motivos diferentes (set/2026) que continuam valendo.
      A **referência** colidia com a grade: o grupo *Médias por consulta* imprime
      `procedimentos 5,26` e o rodapé imprimia `Referência da área: 5,23 procedimentos
      por consulta`. Mesma unidade, mesmo formato, dois centímetros de distância — e
      **estatísticas diferentes**: 5,26 é razão de totais sobre quem está em cena;
      5,23 é a **mediana das taxas individuais** dos que formam a referência. Próximas
      por acaso do dado, e indistinguíveis na tela. Duas médias parecidas lado a lado
      não informam: fazem procurar o erro.
      O **critério agregado** era pior — ele **não governa número nenhum da página**.
      `posicao_e_excedente` roda por PAR (cooperado × procedimento) contra
      `norma_por_procedimento`; `acima_gatilho`, que é o agregado, tem exatamente dois
      consumidores em todo o app (a contagem da linha de contexto e a canaleta de
      realce da linha da tabela) e **nenhum deles é número**. Imprimi-lo como a régua
      do bloco era apontar para a régua errada. Ele segue desenhado onde é POSIÇÃO e
      não número solto: a régua do gráfico de distribuição.
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