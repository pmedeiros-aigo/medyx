# PENDÊNCIAS — Medyx

Coisas identificadas durante a construção, decididas como "não agora". Cada uma diz o que
falta, por que não foi feita e o que destrava. Nada aqui bloqueia o que já está no ar.

Quem fecha uma pendência: apaga a entrada e registra a decisão onde ela pertence
(`CLAUDE.md` se for regra, Claude Design se for contrato visual, `config.py` se for valor).

---

## Dados que a API ainda não expõe

### 1. Consistência por trimestre (série, não contagem)

**O que falta.** A coluna "Consistência" da tabela de cooperados mostra `4/4`. A intenção é
mostrar a série: uma barra por trimestre, marcando em quais o cooperado foi sinalizado.

**Por que não foi feita.** `blocos.py` calcula e expõe `janelas_sinalizado`,
`janelas_avaliaveis` e `total_fatias` — **contagens**. Não expõe *quais* trimestres. Sem a
série não há o que desenhar.

**O contrato já está pronto:** `.spark`, `.spark i`, `.spark i.hi`, `.spark i.crit`,
`.sparkwrap`, `.sparkq` existem no guia. É mudança de Python, não de Design.

**Destrava com:** `blocos.py` passar a devolver, por cooperado, a lista de trimestres com o
estado de cada um (sinalizado · avaliável e não sinalizado · não avaliável).

### 2. Leitura de concentração por cooperado

**O que falta.** A coluna de concentração (margem extensiva × intensiva: muitos pacientes
recebendo pouco, ou poucos recebendo muito) não existe na tela.

**Por que não foi feita.** Não existe no payload. Procurado em `/api/area/{id}`, em
`/api/area/{id}/procedimentos` e em `blocos.py`: zero ocorrência. O `config.py` tem
`Q_ALTO_CONCENTRACAO` e `MIN_PACIENTES_CONCENTRACAO`, então o método está decidido e o
motor sabe calcular — o resultado é que não sobe agregado por cooperado.

**Destrava com:** decidir se a leitura é por cooperado ou por par (cooperado, procedimento)
e expor no bloco `cooperados`. Antes disso, acionar a skill `rigor-estatistico`: é razão
com denominador pequeno, e denominador pequeno explode a taxa.

### 3. Impacto em R$ é um ponto, e foi pedido como faixa

**O que falta.** A linha de apoio da variação excedente deveria trazer um INTERVALO
(`R$ 218–827 mil`). Traz um valor único: `R$ 2.869.260 (em quarentena)`.

**Por que não foi feita.** O motor não calcula intervalo nenhum para o dinheiro.
`_cascata_area` soma `excedente_reais` e devolve um float; o preço é a mediana derivada
das contas, sem dispersão associada. Inventar as pontas da faixa seria fabricar número
justamente onde o produto declara quarentena, que é o oposto do que o selo existe para
proteger.

**Destrava com:** decidir de onde sai a faixa. Duas origens plausíveis, e a escolha é de
método, não de tela: (a) percentis do preço observado por procedimento, propagados até o
total; (b) bootstrap sobre as contas, como já se faz para o piso de confiança. Acionar a
skill `rigor-estatistico` antes: somar percentis por procedimento NÃO dá o percentil da
soma, e o erro é fácil de cometer.

**O contrato já está pronto:** `.stats .v.rng` (17px) existe justamente para valor que é
faixa, e não número único.

### 4. Descrição do procedimento chega cortada em 50 caracteres

**O que falta.** Na aba Procedimentos, 609 das 662 descrições têm exatamente 50 caracteres e
terminam no meio da palavra: *"Marcadores Tumorais (Ca 19.9, Ca 125, Ca 72-4, Ca "*.

**Por que não foi feita.** O corte vem da BASE DE ORIGEM, não do app: `blocos.py` só lê
`descricoes.get(codigo)`. Não há texto completo em lugar nenhum do pipeline para restaurar,
e inventar a continuação seria pior que o corte. A tela mostra o que veio e repete no
`title`, para o dia em que a origem mandar o texto inteiro.

**Destrava com:** conferir na extração se o campo de descrição do procedimento está
truncado na consulta ou já vem assim do sistema de origem.

### 5. A fragilidade do rótulo de área não tem superfície

**O que falta.** A classificação v2.0 mede por dado quando o rótulo de área é frágil
(`no_limiar`: a frente que define a área está entre 12% e 18% das consultas;
`perfil_instavel_no_ano`: a mistura mudou ≥ 20 pontos entre os semestres) — 25 cooperados em
set/2026. A etiqueta "classificação em observação" que expunha isso na linha e no dossiê saiu
em set/2026 (decisão do usuário: não parecia profissional). O sinal continua na dim; o app não
o mostra em lugar nenhum e o degrau "Com classificação de área resolvida" da cascata não retira
ninguém.

**Destrava com:** tela de governança da classificação (versão, vigência, quem forma a
referência e por quê, os rótulos frágeis, o cadastro agregado pendente de confirmação). Não
muda cálculo nenhum.

### 6. Busca na barra superior

**O que falta.** O guia põe um campo de busca no meio da barra superior ("Buscar cooperado,
procedimento"). Ele **não foi construído**.

**Por que não foi feita.** Não existe endpoint de busca. A API serve área, cooperados e
procedimentos por parâmetro, não por texto livre. Caixa de busca que não busca é promessa
falsa, e uma que só filtra a tabela em cena mente sobre o próprio alcance: quem digita um
cooperado de outra área espera encontrá-lo.

**O contrato já está pronto:** `.search` existe e está estilizada, com `flex:1 1 200px` e
`max-width:320px` reservados no meio da barra. É construção de Python + JS.

**Destrava com:** decidir o ESCOPO antes do endpoint. Buscar dentro da área em cena é uma
coisa; buscar na especialidade inteira e navegar para a área do achado é outra, e só a
segunda justifica ocupar a barra superior.

---

## Classificação v2.0 (set/2026)

### 6a. A régua ainda é por médico; a classificação já é por consulta

**O que falta.** A v2 classifica cada consulta por tipo de atendimento e sabe que o médico é
uma mistura, mas o app compara médico com médico dentro da `area_mvp` (etapa 1, MVP). O
cooperado com 41% de rotina e 23% de cirurgia é medido só entre os 20 de Endoscopia
Ginecológica. A comparação que a classificação sustenta é **por tipo de atendimento**: os
atendimentos de dor pélvica dele contra os de dor pélvica de todos que fazem dor pélvica.

**O que já existe.** `unimed_natal/marts/dim_consulta_familia.csv` (ID_CONSULTA → tipo de
atendimento, o mesmo id do fato) e `dim_familia_procedimento.csv`.

**Destrava com:** o motor agrupar pela família da consulta (volume do cooperado por família,
piso por família recalibrado), e as telas de Área/Panorama passarem a falar de tipo de
atendimento. Etapa 2 do plano de 2026-09-11.

### 6b. Três tipos de atendimento carregados por um exame de hábito

**O que falta.** Dor pélvica (43% das consultas definidas só por CA-125 + CEA), PTGI (71% só
por vulvoscopia) e mama diagnóstica (84% só por Rx ampliação) são inflados por exames que
qualquer cooperado pede. A correção proposta e ainda não aplicada: "dosagem não define, ato
define" (o grupo TUSS 4.03 nunca define a consulta; só atos definem) e mover vulvoscopia para
rotina e Rx ampliação para rastreio, com base na coesão medida (< 1 para os dois). Efeito
esperado: PTGI deixa de ser área principal; Endoscopia Ginecológica perde ~4 cooperados.

**Destrava com:** aplicar no `mapa_procedimentos.csv` e no notebook, reexecutar, regerar os
marts com `preparar_marts.py` e re-baselinear os `SMOKE_*`.

### 6c. Piso por área e validação clínica

**O que falta.** `PISO_CONSULTAS_ANO` continua 100 para todas as áreas (calibrado na v1); o
mapa de procedimentos teve revisão médica parcial (15 perguntas); RQE pendente. Os `SMOKE_*`
foram re-baselineados na v2 (área de referência: Ginecologia Geral).

### 6d. Página do cooperado: composição e comparação por tipo de atendimento

**O que falta.** A dim v2 traz a mistura (`pratica_*`), a estabilidade no ano e a comparação
por tipo de atendimento (`unimed_natal/dados/v2/comparacao_por_familia.csv`). Nada disso está
na tela. Proposta de 2026-09-11: composição do atendimento (barra empilhada, com a da área ao
lado), comparação por tipo de atendimento (solicitações por atendimento vs. quem faz o mesmo
tipo), observações de prática com a referência ao lado, estabilidade no período. Mostrar
resultados, nunca regras.

## Contrato visual

### 7. `.v.rng` está fazendo dois trabalhos

**Estado.** A faixa de estatísticas usa `.v.rng` para a RESSALVA ("sem sinalização
comparativa") quando a área não tem referência plena. O nome da classe diz *range*, e o
guia a documenta como a variante de valor em intervalo.

**Por que assim.** `.v` é 22px com `white-space:nowrap`; a ressalva estoura a coluna. A
variante de 17px é exatamente o tratamento necessário, e criar uma classe nova para o
mesmo resultado visual duplicaria a regra.

**Destrava com:** uma ida ao Design que ou renomeie `.v.rng` para algo que cubra os dois
casos (valor que não é um número grande), ou acrescente `.v-ressalva` como apelido da
mesma declaração. Enquanto isso, funciona e está registrado.

### 8. Realce de linha "acima do critério": a COR está em conflito

**Estado.** A classe `tr.acima` foi criada no Design e existe no contrato. A tabela chegou a
usá-la e **foi desligada** (jul/2026, decisão do usuário). O código está em `tabela.js`,
comentado, pronto para reativar numa linha.

**O conflito.** `tr.acima` pinta a canaleta com `--read-above`. É o **mesmo âmbar** que
`.cb-c` usa na barra de composição, um centímetro acima na mesma tela, para "fora da
construção da referência". Duas condições diferentes, mesma cor, mesmo campo de visão.

Pior: o `tokens.css` define esse token como *"leitura de dado = preenchido (acima da
referência, **abaixo** do critério)"* — o oposto do que `tr.acima` significa. E o resto do
sistema já usa `--crit` para acima do critério: na mesma linha, `.pctl-crit` pinta o `P98`
de vinho enquanto a canaleta ficava âmbar. Fura a seção 09 do guia: *"Um token, um
significado."*

**Três saídas, decisão de contrato:**
1. `tr.acima` passa a `--crit` — casa com o `.pctl-crit` que já está ao lado.
2. O token muda de significado e o comentário do `tokens.css` é reescrito — mas aí `.cb-c`,
   `.mk.warnmk`, `.pt-read` e as linhas de critério do gráfico mudam de sentido junto.
3. Fica âmbar de propósito (para não parecer acusação) e quem muda é o `.pctl-crit`.

**Enquanto isso:** o ajuste 4 do `CLAUDE.md` segue pedindo que o critério agregado governe o
realce da linha, e a tela não realça nada. É dívida declarada, não esquecimento.

---

## Fila da próxima ida ao Claude Design

Agrupadas de propósito: cada ida ao Design custa uma rodada de sincronização e releitura.

- **realce de linha acima do critério** (item 8 acima)
- **`.v.rng` com dois significados** (item 7 acima)
- **painel da cascata** — "como esta lista foi filtrada", com os 7 degraus, seus `n` e a
  natureza de cada um (escopo · validade · triagem · artefato · contexto). Exigido pelo
  ajuste 5 do `CLAUDE.md`; não existe nada equivalente no guia.
- **shell do guia com a barra lateral em vigor** — o cartão "Shell renderizada, arranjo em
  vigor" já demonstra a barra superior corretamente (crumbs + chip), mas a lateral dele
  ainda usa `.params-hd` / `.params-body` / `.plbl` / `.chipbtn`, o arranjo anterior. O app
  usa `.panel-in` / `.p-blk` / `.p-sec` / `.disc`. Quem comparar a shell do app contra o
  guia vai achar defasagem onde não há. Fazer **antes do Dossiê**, que reutiliza a shell.

## Passada dedicada, sem construção em curso

- **CSS morto:** 256 regras, ~29% do `components.css` — família `.fields`, `.sidemock` e 60
  ids de demonstração. Exige **revisão manual**: a detecção automática quase apagou a regra
  `#cf-80`, que é viva.
- **Higiene:** 116 classes declaradas e usadas em lugar nenhum; `.wf-banner` e `.wf-top` na
  marcação sem regra; `--shell-params-bg` sem uso desde que o painel virou branco;
  `.dlg-note` órfã desde que a linha de proveniência saiu do diálogo.
- **Órfãs do bloco Análise (30/jul/2026):** ao mover a régua para a faixa de critérios,
  ficaram sem uso `.p-sec` (53 regras), `.disc`/`.disc-body`, `.deviation`, `.calbtn`,
  `.summ`, `.sel-note` e `.step-err`. Decisão de contrato antes de apagar: o guia mantém
  arranjos recusados de propósito (`.parambar`, `.ctxbar`), e este foi SUBSTITUÍDO, não
  recusado. Se a regra é "arranjo substituído sai", são ~75 regras a remover de uma vez.
