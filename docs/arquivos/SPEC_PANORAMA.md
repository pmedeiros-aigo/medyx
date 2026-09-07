# PANORAMA DE OPORTUNIDADES — especificação da página (para o Claude Design)

## O que esta página é

A porta de entrada do app e o nível da **especialidade inteira** (hoje: Ginecologia &
Obstetrícia). Todas as áreas de atuação dentro dela, vistas de cima. Responde a
pergunta de quem abre o app de manhã: **"onde está o dinheiro, e o que eu olho hoje?"**

Hierarquia de navegação: **Panorama (especialidade) → Área de Atuação (grupo de pares)
→ Dossiê (pessoa)**. O Panorama é o único lugar que junta as áreas.

**Regras fixas (valem em toda a página):**

- A régua é sempre **da área de cada um**. O Panorama junta pessoas e valores, nunca
junta réguas — por isso não existe posição/percentil comparando médicos de áreas
diferentes; a unidade comum entre áreas é o **excesso** (solicitações e R$).
- Valores em R$ aparecem limpos. Em cada bloco com R$, uma nota de rodapé discreta:
"Valores calculados com tabela de preços provisória; serão atualizados com a tabela
contratual da cooperativa." (mesma frase no hover). Nada de "quarentena" na tela.
- Área sem régua (grupo pequeno, sem grupo de pares, classificação pendente)
**aparece** — só não sinaliza ninguém. Ninguém desaparece.
- Zero jargão interno (cascata, lente, norma, elegíveis, convergência).

---



## A página, de cima para baixo



### 1. CABEÇALHO — "de que especialidade estamos falando"

- Seletor de **Especialidade** (hoje uma só; vira lista quando entrarem outras) ·
**Período** · botão **Critérios** (o mesmo diálogo das outras telas).
- Título: nome da especialidade.
- Linha de contexto (texto, sem cards):
`202 cooperados · 118 comparáveis em 4 áreas com referência · 84 sem grupo de pares · 182.000 solicitações excedentes vindas de 116 cooperados · R$ 6,0 mi`



### 2. CARDS POR ÁREA DE ATUAÇÃO — "o que tem dentro" (fixos, não seguem recorte)

Um card por área, ordenados por excesso. Cada card:

- Nome da área
- **Comparáveis** (`63 de 64`)
- **Acima do critério** (`8`)
- **Excesso** (`87.816 solicitações · R$ 2,9 mi`)
- **Estado da régua** como etiqueta discreta: `referência plena` / `grupo pequeno — sem sinalização` / `sem grupo de pares` / `classificação pendente — em triagem`
- Mini-barra de proporção: quanto do excesso da especialidade esta área carrega.
- **Clique no card → página da Área** (com os mesmos critérios/período na URL).
Áreas sem régua ficam esmaecidas, com o estado no lugar dos números de sinalização
(ex.: Mastologia `4 cooperados · grupo pequeno — sem sinalização`; Classificação
pendente `72 cooperados · em triagem clínica`).



### 3. FILA DE CASOS — o coração da página (segue o recorte)

Chips de recorte, mesmo eixo aninhado da Área: `Qualificados` (default) ·
`Persistentes` · `Comparáveis`. Cards do recorte, abaixo dos chips:

- **Casos no recorte** (`44` · qualificados · de 118 comparáveis)
- **Excesso de solicitações** (`X` · acima do padrão de cada grupo)
- **Excesso em R$** (`R$ Y` · o custo dos X exames acima do padrão)

Tabela — médicos de **todas as áreas juntas**, ordenada por excesso em R$ (desc):


| coluna                                                                             | conteúdo                                                                         |
| ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **Cooperado**                                                                      | nome (link) + badges de perfil; hover: os 5 exames que mais puxam o excesso dele |
| **Área de atuação**                                                                | a área dele — a régua é a dela                                                   |
| **Consultas**                                                                      | volume no período                                                                |
| **Consistência**                                                                   | mini-série 4 trimestres + direção                                                |
| **Excesso**                                                                        | solicitações · R$ (sub-linha: piso)                                              |
| **›**                                                                              | abrir dossiê                                                                     |
| Sem coluna de posição/percentil (réguas diferentes por área). Rodapé: "44 de 118 · |                                                                                  |
| recorte: qualificados · ordenado por excesso em R$".                               |                                                                                  |




### 4. FUNIL DA ESPECIALIDADE — "de onde a fila veio" (segue o recorte)

Os degraus do método com o n de cada um, somando as áreas com referência:
`118 comparáveis → 116 com algum exame acima do padrão → 72 com padrão repetido nos trimestres → 47 com excesso relevante → 45 sem classificação em disputa → 44 sem explicação de contexto → 44 qualificados`
Desenho: barras horizontais decrescentes (ou degraus), cada uma clicável = aplica o
recorte correspondente na fila. Frase de rodapé: "cada etapa filtra o que sobrou da
anterior; a fila é o que sobrou, não uma escolha".

### 5. ONDE O EXCESSO SE CONCENTRA — dois Paretos lado a lado (fixos)

- **Por área**: qual área carrega quanto do excesso da especialidade (barras + %
acumulado).
- **Por procedimento** (especialidade inteira): os exames que concentram 80% do
excesso, com "em quantas áreas aparece". Top 8 + "ver todos".
Subtítulo de unidade nos dois: "excesso medido exame a exame".



### 6. RODAPÉ

Proveniência (pipeline · período · base eletiva · classificação v1.0 · critério ·
referência · confiança) + nota da tabela de preços provisória.

---



## Comportamento

- **Fixo** (descreve a especialidade): linha de contexto, cards por área, Paretos.
- **Segue o recorte**: cards do recorte, fila, funil.
- Trocar critério/período no diálogo recalcula tudo junto; tudo na URL.
- Clique no card de área → Área com os mesmos parâmetros; clique no nome → Dossiê;
clique no degrau do funil → aplica o recorte na fila.



## Estados

- Especialidade com uma área só ou sem áreas com referência: a fila mostra a ressalva
("nenhuma área com referência suficiente para sinalizar") e os cards por área ficam
todos esmaecidos.
- Sem casos qualificados no recorte: estado vazio com a frase "nenhum caso atravessa
todos os filtros neste período" e o funil mostrando onde a fila zerou.



## Fora desta página (não desenhar)

Comparação entre especialidades (só há uma), estados de caso/pareceres/prazos (v1),
economia realizada vs baseline (v1), deltas vs período anterior (aguarda 24 meses de
dados), qualquer número em R$ por trimestre aqui (vive no Dossiê e na tendência da Área).