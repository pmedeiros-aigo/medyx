# LÉXICO DO PRODUTO — Medyx (padrão enterprise)

Vocabulário oficial de toda superfície visível (UI, relatórios, exports, e-mails).
Regra: a UI fala a língua institucional de operadora (ANS/auditoria assistencial),
em **linguagem de processo, nunca de pessoa**. Gíria interna de análise não vaza.

## Princípios

1. **Processo, não pessoa.** "Solicitações do período apresentam variação acima da
   referência do grupo" — nunca "ele pede demais". Estados descrevem o caso, não o médico.
2. **O vocabulário do cliente.** Utilização, pertinência, variação de prática,
   referência do grupo de pares, auditoria assistencial, regulação.
3. **Neutralidade acusatória zero.** Nada de "suspeito", "ofensor", "excesso" na UI.
   O sistema identifica variação e qualifica evidência; a conclusão é do comitê.
4. **Governança visível.** Todo número carrega versão, vigência e critério. Isso é
   texto na tela, não metadado escondido.
5. **Ausência não é atributo.** Só sub-perfis presentes viram etiqueta; a ausência é
   célula vazia, nunca "não opera".
6. **Todo número de indivíduo anda com a referência do grupo ao lado.** Número isolado
   de uma pessoa não é publicável — nem em tela, nem em export.

## Tabela de conversão (interno → UI)

| Interno (notebook/análise) | UI / relatório |
|---|---|
| Fila do auditor | **Central de Revisão** |
| As 5 conversas | **Frentes prioritárias de atuação** |
| O número para a diretoria | **Síntese executiva** |
| Régua da análise / do valor | **Parâmetros da análise** / **Critérios de valoração** |
| taxa de exames por consulta | **índice de solicitação por consulta** |
| exame (o objeto solicitado) | **procedimento** ·  ver a nota abaixo da tabela |
| itens | **solicitações** (ou **eventos**) |
| excedente | **variação excedente** (1ª menção: *variação de utilização acima da referência da área*) |
| oportunidade bruta/qualificada | **oportunidade identificada / qualificada** (manter) |
| protocolo carimbado | **rotina na carteira** — sempre com o número ao lado: "74% da carteira vs 7% dos pares" |
| padrão difuso | **variação difusa multiprocedimento** |
| pede-e-executa / autorref | **autorreferenciamento** (termo do setor) |
| suspeito / suspeito persistente | **caso qualificado** / **variação persistente** |
| sinalizado | **em revisão** (estado) ou **acima do critério de revisão** |
| gatilho | **critério de revisão** (P90 da área) |
| alvo | **referência de adequação** (mediana/P75/P90) |
| piso de consultas | **volume mínimo para avaliação** |
| norma | **referência da área** ·  ver a nota abaixo da tabela |
| peer group | **área de atuação** ·  "grupo de pares" foi aposentado |
| confundidor | **fator de contexto verificado** |

> ### "grupo de pares" saiu do produto (2026-09-06)
>
> O termo era o do léxico para *peer group*, mas na tela ele nomeava **duas coisas
> diferentes**, às vezes na mesma frase do painel do procedimento:
>
> - a **área de atuação** inteira (63 comparáveis em Ginecologia);
> - o subconjunto que **solicita aquele exame** e forma a referência dele (32).
>
> Além disso, o app já dizia "referência da área" em 24 lugares e "referência do
> grupo de pares" só no painel: dois nomes para a mesma coisa.
>
> **A regra agora é uma só:**
>
> | conceito | como se escreve |
> | --- | --- |
> | o peer group (a área de atuação) | **área** / **área de atuação** |
> | a norma calculada nele | **referência da área** |
> | quem forma a referência de UM exame | **os cooperados da área que solicitam este exame**, sempre com o denominador: *"Referência apurada entre 32 dos 63 cooperados da área, os que solicitam este exame."* |
>
> O denominador não é enfeite: é a regra §1 do rigor estatístico. Um "32" solto
> não diz se é a área inteira ou um punhado dela, e era assim que a frase
> aparecia.

> ### "exame" saiu do produto (2026-09-07)
>
> A UI dizia "exame" e "procedimento" para a MESMA coisa, às vezes na mesma tela:
> a coluna "Exames por consulta" na tabela de cooperados e a coluna
> "Procedimento" na tabela ao lado, o painel lateral falando "deste exame" sobre
> um objeto que o título dele chama de procedimento.
>
> **A palavra é uma só: procedimento.** É o termo do setor (TUSS, rol da ANS,
> autorização), é o que já estava em metade das superfícies, e "exame" exclui o
> que não é diagnóstico. As consequências:
>
> | onde | era | é |
> | --- | --- | --- |
> | coluna da tabela de cooperados | Exames por consulta | **Solicitações por consulta** |
> | medida do gráfico de distribuição | Exames | **Solicitações** |
> | degrau da cascata | Com algum exame acima do critério | **Com algum procedimento acima do critério** |
> | textos de apoio e hovers | "deste exame", "exame a exame" | **"deste procedimento", "procedimento a procedimento"** |
>
> Duas coisas NÃO mudam. As **chaves internas** (`exames` como chave da medida,
> `taxa_exames_por_consulta` como nome de coluna do motor) seguem: são
> identificadores, não vocabulário, e renomeá-las trocaria a URL e o gabarito do
> smoke sem ninguém ler nada diferente na tela. E a **descrição que vem do dado**
> ("Exame A Fresco Do Conteúdo Vaginal E Cervical") é o nome oficial do
> procedimento na tabela de origem, não uma frase nossa.
| o custo da inação | **impacto recorrente estimado** (por trimestre) |
| dossiê | **Cooperado** — a página do cooperado chama-se só "Cooperado" (set/2026); "dossiê" saiu da tela |
| ÁREA DE TESTE — placeholder | **AMBIENTE DE HOMOLOGAÇÃO · classificação preliminar** |
| trilha de estados | **estados do caso**: *em análise → em tratativa → pertinência justificada → adequação em curso → mitigado* |
| concentração alta na margem intensiva | **case-mix a investigar** |
| poucos beneficiários recebem | **pouco volume** (com "menos de N beneficiários") |
| grupo pequeno demais para percentil | **cooperados insuficientes na área para análise comparativa** |
| zero formadores da norma | **sem referência: nenhum cooperado desta área forma a norma** |
| sem área classificada | **sem área de atuação** (volume insuficiente ou prática pouco visível) |
| cadastro agregado (≥ 25% de pacientes homens) | **cadastro agregado (pacientes homens) · confirmação pendente** |
| família de atendimento (v2) | **tipo de atendimento** |
| gatilho degradado pelo n | **critério ajustado ao tamanho do grupo** |
| bootstrap abaixo do portão | **intervalo não calculável** |
| norma do procedimento com poucos solicitantes | **referência não conclusiva** |
| percentil | sempre acompanhado da tradução: **"P92 · acima de 9 em cada 10 colegas da área"** |
| valor padrão do parâmetro | **recomendado** ("P90 ✓ recomendado"; ao desviar, aviso discreto com ação de restaurar) |

## Tradução do percentil (jul/2026)

O percentil nunca aparece sozinho (ajuste 2 do `CLAUDE.md`). A tradução tem forma fixa:

> **`P98` → "acima de 98% dos pares da área"**

Duas decisões dentro dela, e as duas valem para qualquer texto do produto:

**Precisa, não aproximada.** Saem *"acima de praticamente todos"*, *"9 em cada 10"* e
*"abaixo da maior parte"*. A aproximação colapsava P92 e P98 na mesma frase, e é
exatamente entre esses dois que a conversa com o médico acontece. Um número que vai ser
contestado não pode chegar arredondado na leitura e exato na coluna ao lado.

**Pares, nunca "colegas".** O peer group é uma construção do método — quem entrou nele
passou por piso de volume, elegibilidade e n mínimo. "Colegas" sugere relação social e
apaga o critério que sustenta a comparação.

| Não usar | Usar |
|---|---|
| colegas da área | **pares da área** |
| acima de 9 em cada 10 colegas | **acima de 92% dos pares da área** |
| acima de praticamente todos | **acima de 98% dos pares da área** |
| abaixo da maior parte | **acima de 4% dos pares da área** |

Implementado em `apresentacao.traduzir_percentil`. A frase nasce no Python; a tela imprime.

## Elementos de governança que a UI exibe como texto

- **Identificação de caso** *(v1 — fora do MVP)*: cada oportunidade recebe ID
  (`MDX-2026-0038`) — auditável, citável em ata de comitê. Desenhado, não implementado.
- **Carimbo de proveniência** em todo número: `critério P90 · referência mediana ·
  confiança 90% · pipeline v0.9 · dados 2025-05→2026-04 · classificação v1.0
  (não homologada — validação clínica pendente)`.
- **Nota metodológica** como página do app (a METODOLOGIA_ANALITICA renderizada) +
  glossário com as definições formais — o "por quê" de cada número a um clique.
- **Trilha de auditoria** *(v1 — fora do MVP)*: quem alterou estado de caso, quando,
  com que justificativa. Desenhada, não implementada.
- **Ciclo de governança da classificação**: vigência, revisão periódica, fluxo de
  contestação pelo cooperado — descritos na própria UI.

## Tom dos textos fixos

Frases curtas, voz institucional, verbo no processo. Exemplos calibrados:
- ✗ "quem pede demais" → ✓ "variação de utilização acima da referência da área"
- ✗ "o método descontando na sua frente" → ✓ "cada dedução é verificada e auditável"

## PADRÃO DE REDAÇÃO DE TELA (set/2026) — vale para TODA string visível

Esta seção existe porque o defeito se repetiu: notas de rodapé, subtítulos e
ressalvas escritas em voz de quem construiu o bloco, não de quem o lê. Não é
questão de gosto, e por isso as regras abaixo são verificáveis, uma a uma.

**As dez regras.** Antes de qualquer string ir para a tela, ela passa por todas.

1. **Escreva sobre o DADO, nunca sobre o app.** Proibido "o gráfico mostra",
   "esta série", "este bloco", "as barras", "nesta tela". O leitor está vendo a
   tela; ela não precisa se descrever.
   ✗ "O gráfico mostra os trimestres completos da janela."
   ✓ "Período coberto: abr/25 a mar/26."
2. **Uma frase, um fato.** Duas afirmações não se emendam com "e", "então" ou
   dois-pontos. Frases separadas.
3. **Não explique mecânica interna.** O leitor precisa do fato e da consequência,
   não do algoritmo. "Não completa um trimestre" é consequência; "o fatiamento
   descarta o resto" é mecânica.
4. **Declarativa e impessoal.** Sem "nós", sem "você", sem imperativo, sem
   "note que", "vale lembrar", "é importante observar".
5. **Maiúscula inicial e ponto final** em toda frase. Rótulo de dado (micro,
   cabeçalho de coluna, chip, legenda) não é frase: sem ponto.
6. **Número anda com unidade e base.** "30 dias", não "30". "3% do custo
   excedente da área", não "3%".
7. **Só o vocabulário da tabela de conversão acima.** Nunca um sinônimo novo
   para um termo que já existe (referência, critério, comparáveis, excedente).
8. **Sem travessão** (`—`), regra do CLAUDE.md. Use `·`, `,`, `:` ou parênteses.
9. **Sem adjetivo de estado de projeto**: "provisório", "em quarentena",
   "estimativa", "ainda não homologado", "por enquanto". O estado do projeto não
   é característica do número.
10. **Sem hedge sobre número exato**: "aproximadamente", "cerca de", "talvez",
    quando o valor é calculado.

**O teste.** Leia a frase em voz alta imaginando um diretor da operadora do
outro lado da mesa. Se ela explicar como o software funciona, em vez de o que os
dados dizem, ela falhou.

**Onde isso é cobrado.** `smoke_api.py`, seção "TEXTO DE TELA", varre as strings
de frase dos payloads e reprova as regras **1, 8 e 9**, que são mecânicas.

As demais são de revisão humana, e isso é decisão, não preguiça: a regra 5
(maiúscula e ponto) foi automatizada e removida, porque o payload mistura, sob a
mesma chave, sentenças e fragmentos telegráficos que completam um rótulo. Três
de cada quatro apontamentos eram texto certo, e uma prova que reprova o certo
ensina a ignorá-la. Elas estão escritas aqui para não serem redescobertas a cada
frase, que é o que vinha acontecendo.
- ✗ "números não reportáveis" → ✓ "resultados preliminares — não destinados a deliberação"