# Contexto de Negócio — Inteligência de Atuação e Custos para Cooperados

**Cliente:** Unimed Natal · **Domínio inicial:** Ginecologia (202 cooperados) · **Status:** classificação v1.0 vigente (não homologada) · pipeline analítico completo e calibrado · MVP web em construção

---

## 1. Em uma frase

Transformar o faturamento bruto dos cooperados em **segmentação clínica confiável**, para permitir **comparações justas entre pares** e revelar onde existe **variação de custo não justificada** — de forma acionável e defensável perante o corpo clínico.

A classificação **não é o produto**. Ela é a fundação que torna o produto possível: inteligência de custo em que a Unimed pode confiar e agir.

---

## 2. O problema de negócio

A Unimed Natal tem 202 médicos nominalmente na mesma especialidade (ginecologia/obstetrícia), mas que na prática atuam em subáreas muito diferentes — obstetrícia geral, alto risco, reprodução, endoscopia, patologia do trato genital inferior. O custo da cooperativa é dirigido pelo que cada médico **solicita e executa**.

Sem segmentar por área real de atuação, qualquer análise de custo mistura perfis incomparáveis. Um reprodutivo *parece* caro ao lado de um ginecologista geral — mas é perfeitamente normal entre reprodutivos. O efeito é duplo e ruim: **outliers reais se escondem** no meio da mistura, e **falsos outliers geram ruído** que destrói a credibilidade da análise. Sem peer group correto, não há sinal de custo confiável.

---

## 3. Por que ir além do TI interno da Unimed

O TI interno sabe construir dashboard, rodar SQL e cuidar do dado. O que tipicamente **não** entregam é a camada clínico-analítica:

- encodar conhecimento médico — quais procedimentos *assinam* cada subárea;
- construir grupos de pares clinicamente válidos;
- separar variação **justificada** (case-mix, subfoco legítimo) de variação **não justificada** (desperdício/desvio de padrão).

Nosso diferencial não é infraestrutura — é **tornar o dado clinicamente significativo e pronto para decisão de custo**. Competir em "fazer dashboard" é perder para o time de casa. Competir em "fazer o dado virar decisão defensável" é o espaço onde temos vantagem e ninguém mais entrega.

---

## 4. O princípio central: comparação justa

Um médico só é outlier em relação aos **pares verdadeiros** dele. Toda a credibilidade do projeto repousa nisso, porque o médico avaliado vai contestar qualquer comparação injusta — e, no contexto de uma cooperativa (onde os médicos são os donos), essa contestação tem poder político real.

Por isso a classificação vem primeiro: ela existe para **viabilizar a justiça da comparação**. É o coração intelectual do projeto e o que lhe dá legitimidade perante o corpo clínico. Sem justiça percebida, não há adoção.

---

## 5. A escada de valor

```
1. CLASSIFICAÇÃO      segmentar por área real de atuação         [PRONTO — v1.0, não homologada]
        ↓
2. BENCHMARKING       comparar dentro de cada peer group         [PRONTO — normas reais calibradas]
        ↓
3. INTELIGÊNCIA       achar os desvios de custo que importam     [PRONTO no motor — em exposição no app]
   DE CUSTO
        ↓
4. AÇÃO               recomendar, acompanhar, re-medir           [PRÓXIMO — exige o app em uso]
```

Os três primeiros degraus estão construídos e validados. O caminho 1 → 3 deixou de ser
promessa: existe pipeline calibrado sobre a classificação real, com variação excedente
quantificada por área e por procedimento, filtrada por persistência, fatores de
contexto e piso de confiança. O que falta é o degrau 4 — e ele depende do app em uso,
não de mais método.

---

## 6. Objetivo principal: variação não justificada (onde está o dinheiro)

A economia vem de identificar **variação não justificada dentro do grupo de pares** — e não de punir quem é diferente.

Dentro de cada área de atuação, comparamos métricas como: utilização (exames/procedimentos por consulta), custo por paciente, taxa de procedimentos de alto custo, padrão de encaminhamento. Quem está consistentemente **muito acima da mediana dos pares, sem case-mix que explique**, é candidato a revisão.

Enquadramento crítico — e inegociável para a credibilidade:

- Nem toda variação é desperdício. Pacientes mais graves, subfoco legítimo e estilo de prática justificam parte dela.
- A ferramenta **sinaliza para investigação, não emite veredito**. Ela diz "olhe aqui", com a evidência, para que o médico explique ou corrija.
- A economia se realiza ao **trazer outliers em direção à norma** quando a variação não se justifica — ou ao entender por que ela existe quando se justifica.

Esse enquadramento ("variação não justificada", sempre com evidência) é o que diferencia uma ferramenta de gestão respeitada de uma ferramenta de vigilância rejeitada pelo corpo clínico.

---

## 7. Como os dados viram funcionalidades


| Dado que já temos                              | Vira esta funcionalidade                                                 | Que responde a                                |
| ---------------------------------------------- | ------------------------------------------------------------------------ | --------------------------------------------- |
| Classificação por área                         | Visão de segmentação — quem está em cada área, com confiança e evidência | "Quem é meu peer group?"                      |
| Atividade completa (SOL/SAD/HON) + peer groups | Benchmarking — distribuição de métricas de custo/uso dentro de cada área | "O que é normal nesta área?"                  |
| Métricas normalizadas por peer group           | Detecção de outliers — médicos sinalizados com magnitude do desvio       | "Quem está fora do padrão?"                   |
| Procedimentos por médico                       | Drill-down — a evidência por trás de cada flag                           | "Por que ele foi sinalizado? É justificável?" |
| Limiares do método                             | Parâmetros editáveis — o clínico ajusta e vê o efeito ao vivo            | "E se eu mudar o critério?"                   |


---

## 8. Como o Claude deve me ajudar a achar valor

Quando sentarmos com o dado, me orientar por estas perguntas, nesta prioridade:

1. **Onde está o custo?** Qual a concentração (Pareto) — quase sempre poucos médicos/procedimentos respondem por boa parte do custo evitável. Começar por aí.
2. **Normalizado por peer group, o que revela variação?** Nunca comparar áreas diferentes. Sempre dentro do grupo.
3. **É justificável?** Para cada desvio, buscar o que poderia explicá-lo (volume, perfil de paciente, subfoco) antes de chamá-lo de desperdício.
4. **Dá para agir e defender?** Priorizar achados que sejam, ao mesmo tempo: **grandes em R$**, **defensáveis com evidência rastreável** e **acionáveis**. Um achado lindo mas indefensável não vale nada num ambiente de cooperativa.

Resumo da postura: me puxar para **valor financeiro defensável**, não para sofisticação metodológica.

---

## 9. A leitura de founder

**Ginecologia é a cabeça de praia, não o mercado.** O método — classificar por área real de atuação para viabilizar comparação justa e inteligência de custo — generaliza para **qualquer especialidade** (cardiologia, ortopedia, oftalmologia...) e qualquer Unimed do país. O mercado real é enorme; ginecologia é só onde provamos.

A jogada, então:

- **Estreitar para provar.** Entregar ginecologia de forma **inegável**: classificação validada por médico (já feito) + um número concreto de economia identificada. Esse é o caso de referência.
- **Land and expand.** Um resultado real e clinicamente validado em uma especialidade é o que vende a próxima — e, depois, a expansão para outras cooperativas.
- **O ativo defensável** não é o código do app; é o **método clínico-analítico** e a confiança do corpo clínico. É isso que o TI interno não replica e que compõe a vantagem ao longo do tempo.
- **Métrica que importa no MVP:** não "o app funciona", e sim "conseguimos apontar R$ X de variação não justificada que a Unimed não enxergava antes, com evidência que sobrevive ao questionamento do médico". Esse é o gatilho de expansão.

---

## 10. Princípios / guardrails

- **Justiça:** só comparar pares verdadeiros.
- **Defensabilidade:** todo flag carrega evidência rastreável até o procedimento.
- **Não-punitivo:** sinaliza variação para investigação, nunca veredito automático.
- **Validação clínica:** o método é homologado por médico antes de virar decisão (já em prática).
- **Sensibilidade do dado:** produção médica é dado sensível; uso restrito ao fim acordado com a cooperativa.

---

## 11. Onde estamos / próximos passos

- **Pronto:** classificação v1.0 dos 202 cooperados (`classificacao_v1.csv`, com
  genealogia registrada) · pipeline analítico completo — norma por peer group,
  detecção com critério degradado por n, variação excedente nas duas lentes,
  persistência temporal, concentração por beneficiário, fatores de contexto e
  controlador de confiabilidade · calibração sobre a classificação real concluída,
  com as previsões de aceitação registradas antes do resultado · API validada.
- **Em curso:** MVP web (FastAPI + front vanilla) para revisão interativa pelo médico.
- **De terceiros:** homologação clínica dos limiares de sub-perfil e da lista
  de plantonistas · triagem dos cooperados sob alerta de perfil · tabela de preço
  contratual (todo R$ segue em quarentena até ela chegar) · guias de internação/
  cirúrgicas (destravam a classificação das áreas cirúrgicas).
- **Depois:** Dossiê e Panorama · acompanhamento de caso com baseline congelado
  (§5.4 da metodologia) — o degrau 4.

