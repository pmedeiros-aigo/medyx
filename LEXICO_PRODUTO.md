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
| itens | **solicitações** (ou **eventos**) |
| excedente | **variação excedente** (1ª menção: *variação de utilização acima da referência do grupo de pares*) |
| oportunidade bruta/qualificada | **oportunidade identificada / qualificada** (manter) |
| protocolo carimbado | **rotina na carteira** — sempre com o número ao lado: "74% da carteira vs 7% dos pares" |
| padrão difuso | **variação difusa multiprocedimento** |
| pede-e-executa / autorref | **autorreferenciamento** (termo do setor) |
| suspeito / suspeito persistente | **caso qualificado** / **variação persistente** |
| sinalizado | **em revisão** (estado) ou **acima do critério de revisão** |
| gatilho | **critério de revisão** (P90 do grupo de pares) |
| alvo | **referência de adequação** (mediana/P75/P90) |
| piso de consultas | **volume mínimo para avaliação** |
| norma | **referência do grupo de pares** |
| peer group | **grupo de pares** (área de atuação) |
| confundidor | **fator de contexto verificado** |
| o custo da inação | **impacto recorrente estimado** (por trimestre) |
| dossiê | **dossiê analítico** (manter — é profissional) |
| ÁREA DE TESTE — placeholder | **AMBIENTE DE HOMOLOGAÇÃO · classificação preliminar** |
| trilha de estados | **estados do caso**: *em análise → em tratativa → pertinência justificada → adequação em curso → mitigado* |
| concentração alta na margem intensiva | **case-mix a investigar** |
| poucos beneficiários recebem | **pouco volume** (com "menos de N beneficiários") |
| grupo pequeno demais para percentil | **grupo de pares insuficiente para análise comparativa** |
| zero formadores da norma | **sem referência: nenhum cooperado desta área forma a norma** |
| sem área classificada | **sem grupo de pares — classificação de área de atuação pendente** |
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
- ✗ "quem pede demais" → ✓ "variação de utilização acima da referência do grupo de pares"
- ✗ "o método descontando na sua frente" → ✓ "cada dedução é verificada e auditável"
- ✗ "números não reportáveis" → ✓ "resultados preliminares — não destinados a deliberação"