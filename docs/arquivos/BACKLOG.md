# BACKLOG — inteligências mapeadas e ainda não construídas

Extraído de um documento exploratório de jul/2026, já descartado: tudo o que
sobreviveu está aqui.
As demais ideias daquele documento — persistência temporal, concentração por
beneficiário e controlador de confiabilidade — **já foram construídas** e vivem na
`METODOLOGIA_ANALITICA.md`. A seção "por que não é replicável internamente" já está
coberta pelo `CONTEXTO_NEGOCIO.md` §3 e §9.

Nenhum item aqui está no escopo do MVP. Ordem por valor comercial estimado.

---

## B1 · Variação excedente × negação — o argumento comercial mais forte
**O cruzamento:** quem tem excedente alto **e** taxa de negação baixa. Os campos de
estágio/status da requisição mostram o que a auditoria atual da Unimed já barra
(~3% negados). O caso valioso é o cooperado cujo padrão **passa ileso** pelo sistema
atual de regulação.

**Por que importa:** é a demonstração direta de valor incremental — "nós enxergamos o
que a sua auditoria já não pega". Não é uma métrica a mais; é a resposta à pergunta
que a diretoria fará ("nós já não controlamos isso?").

**Custo:** baixo. Os dois lados já estão no fato. Exige apenas definir a taxa de
negação por cooperado e cruzá-la com a fila qualificada.

## B2 · Assinatura de painel (co-ocorrência dentro da consulta)
**A medida:** com que frequência a mesma cesta de exames aparece junta na mesma
consulta inferida. Se uma fração alta das consultas do cooperado contém a mesma cesta,
é protocolo pessoal — e o auditor vê **qual** cesta.

**Por que importa:** é inteligência que só existe quando se olha a consulta como
unidade de análise; auditoria por item não enxerga. Complementa a leitura de
concentração (que responde "para quem?") com "o quê, junto".

**Custo:** médio. Exige contagem de co-ocorrência por consulta e uma regra de corte
para "cesta recorrente" — que, como todo corte, precisa de homologação clínica.

## B3 · Direcionamento de rede
**A medida:** concentração anormal de encaminhamentos de um cooperado para um
executante específico (clínica/laboratório), a partir do par solicitante→executante
nas contas.

**Por que importa:** é dimensão que nenhum relatório atual da cooperativa cruza, e
conversa com a autorreferência — mas cobre o caso em que o incentivo é indireto.

**Custo:** médio. Exige tratar a identidade do executante e um enquadramento cuidadoso
(indicador investigativo, jamais veredito) — vale a mesma disciplina do
autorreferenciamento: sempre com cobertura do join e fator de contexto ao lado.

---

## Pré-requisitos externos que destravariam outras análises
- **Tabela de preço contratual** — tira todo R$ da quarentena.
- **Guias de internação/cirúrgicas** — destravam a classificação das áreas cirúrgicas
  (hoje "indeterminada por cobertura de dado") e a visão de custo cirúrgico.
- **Período anterior de dados** — resolveria parte dos cooperados de baixo volume hoje
  em classificação pendente.
