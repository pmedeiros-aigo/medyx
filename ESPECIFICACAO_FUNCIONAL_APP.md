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
- **Aba Cooperados** (default): identidade · magnitude · evidência · desfecho.
Colunas de evidência: procedimento que puxa (com razão), consistência por trimestre
com direção, leitura de concentração, fatores de contexto. [v0]
- **Aba Procedimentos**: procedimento · prevalência entre os pares · solicitantes
elegíveis · referência · qualidade da referência · acima do critério · excedente ·
% acumulado. Ordenável — por excedente é o Pareto; por prevalência é "o que é
rotina aqui". [v0]
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