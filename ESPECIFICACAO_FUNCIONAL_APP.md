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

## 1. PANORAMA DE OPORTUNIDADES (página inicial) [sessão 3]

Pergunta: "onde está o dinheiro, por grupo — e o que eu olho hoje?"

- Síntese executiva: faixa qualificada (referência mediana ↔ critério) + piso de
confiança ← pipeline 2× + controlador. Selo de quarentena. [v0]
- Cards por especialidade: n/elegíveis, mediana, acima do critério, consistentes,
excedente ← pipeline por área. Estado de referência visível no card. [v0]
- Cascata de qualificação (identificada → contexto → não persistente → referência
frágil → qualificada) ← fila final. v0 tabela · v1 waterfall.
- Ranking qualificado: caso, consistência n/n, faixa, piso, fatores de contexto,
leitura de concentração; excluídos esmaecidos com motivo. [v0]
- IDs de caso · estados com trilha · PDF executivo · economia vs baseline. [v1]



## 2. ÁREA DE ATUAÇÃO (o peer group visível) [sessão 1 — em construção]

Pergunta: "o que é normal aqui, e quem está fora?"

- Título + contexto → linha de justificativa → **barra de composição segmentada**
(formam · abaixo do volume · fora da construção, com nome e motivo ao expandir) →
**faixa de estatísticas sem moldura** (acima do critério · consistência · variação
excedente · impacto estimado · peso na especialidade). [v0]
- **Distribuição** (dentro do container de gráficos, aba "Distribuição"): 1 ponto
por cooperado avaliável, haste do menor ao maior, faixa IQR do grupo que forma a
referência, cor pelo excedente em R$. Clicar num ponto destaca a linha na tabela.
Não renderiza nos estados sem referência plena. [v0]
  - **Três medidas no eixo**, num segmentado no cabeçalho do cartão (2026-08-31):
    *Exames* (solicitações por consulta) · *Custo* (R$ solicitados por consulta,
    a mesma fonte da coluna "Custo por consulta" da tabela) · *Excesso* (variação
    excedente em R$ por consulta). Trocar de medida é LEITURA, não recorte: o
    conjunto em cena, a escolha de um ponto e o filtro de perfil atravessam a
    troca, e a medida não viaja na URL. Nas medidas de dinheiro, quem não tem
    preço nas contas ou par acima do critério fica FORA do gráfico e é contado
    no rodapé (ausência não é zero); a caixa some quando menos de
    `N_MINIMO_P75` formadores da referência têm a medida.
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



## 4. NOTA METODOLÓGICA [v0 — render do md]

METODOLOGIA renderizada + glossário do léxico + as defesas escritas: mediana e
robustez, percentis e não p-valor, critério ≠ referência, critério degradado por n,
fronteira GO/Ginecologia, regra do PS, quarentena do preço, premissa da
autorreferência.

## FORA DO MVP (decidido)

Estados de caso e trilha · IDs de caso · PDFs · fluxo de contestação da classificação ·
página de qualidade de dados · página LGPD/papéis · benchmark externo (norma injetável —
o motor já aceita `norma=` por argumento) · comparação entre especialidades.