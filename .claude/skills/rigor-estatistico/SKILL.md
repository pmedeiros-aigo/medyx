---
name: rigor-estatistico
description: >
  OBRIGATÓRIO antes de qualquer cálculo estatístico neste projeto: taxa, média, mediana,
  percentil, IQR, distribuição, ranking, benchmark, norma, outlier, excedente, comparação
  entre cooperados, agregação por área, piso, n mínimo, prevalência. Dispara SEMPRE que a
  tarefa envolver resumir números de cooperados, construir referência de peer group,
  ordenar médicos por qualquer métrica, ou escolher/aplicar cortes. Este projeto produz
  números que acusam médicos de atuar fora do padrão — número indefensável é pior que
  nenhum número. Rodar o checklist ANTES de calcular, não depois.
---

# Rigor Estatístico — Medyx / Unimed

Regras atemporais. Nenhum valor operacional vive aqui — piso, n mínimo, gatilhos e afins
são constantes nomeadas em `config.py`; o método completo está em `METODOLOGIA_ANALITICA.md`.
Os "casos reais" são episódios datados do próprio projeto — evidência de que a armadilha
morde de verdade, não regra corrente.

---

## 1. Denominador pequeno EXPLODE a taxa

Taxa = eventos/denominador. Denominador pequeno → taxa dominada por ruído amostral, não
por comportamento. Nunca rankear/comparar taxas sem aplicar o piso de volume (constante
nomeada, passada por argumento). Quem está abaixo do piso não entra na construção da
norma, mas permanece no dataset com flag de baixa confiança. O denominador aparece SEMPRE
ao lado da taxa em qualquer output.

*Caso real (calibração, jun/2026): o topo do ranking agregado era um cooperado com meia
dúzia de consultas; os super-solicitadores verdadeiros, com milhares de consultas, vinham
logo abaixo — invisíveis para quem olhasse só a taxa.*

## 2. Estatística de grupo minúsculo é anedota

Mediana, IQR ou percentil de um punhado de observações não sustenta conclusão. Toda
estatística de grupo reporta o **n** junto; grupo abaixo do mínimo (constante nomeada)
não é apresentado como sólido — valores brutos com rótulo "amostra pequena, não conclusivo".
Nunca inferir estabilização/tendência de faixas com n de um dígito.

*Caso real: ao refinar faixas do funil, IQRs de zero surgiram parecendo "estabilidade
perfeita" — eram faixas de um único cooperado. Quase cravaram o piso no lugar errado.*

## 3. Razão sozinha mente: favorece o raro, esconde o volume

Razão vs mediana mede intensidade; em procedimento raro (mediana minúscula), razões
enormes correspondem a pouquíssimos itens. Sinalização séria exige as DUAS lentes:
razão (intensidade) E excedente absoluto (magnitude = onde agir = Pareto). Suspeito
persistente é quem sobrevive às duas.

*Caso real: o top por razão era todo de exames raros; o top por excedente, outro mundo —
volume clínico. Quase nenhum nome liderava as duas listas… exceto os suspeitos reais.*

## 4. Outlier sem peer group certo é confundidor, não desvio

Excedente calculado em coorte misturada captura diferença de PERFIL de atuação, não
excesso. Comparação SÓ dentro da área de atuação. Antes de sinalizar, perguntar: "isso
pode ser subfoco/perfil legítimo?" (tipo de atendimento, volume, gravidade). Confundidor
nomeado e descartado ANTES de virar oportunidade — senão o primeiro caso levado ao
cliente é o que tem a melhor defesa clínica.

*Caso real: com área placeholder única, o top por excedente era uma lista de perfis —
plantonistas (pacote de urgência), PTGI (vulvoscopia/colposcopia), mastologia (imagem
mamária) — todos disfarçados de outliers.*

## 5. Média em cauda-longa mente; verificar a forma, não assumir

Custo/utilização em saúde tende a assimetria à direita; a média é puxada pela cauda.
Default: mediana + IQR. Média só com simetria verificada NAQUELA análise — a verificação
da forma é passo do pipeline, a cada janela, nunca herdada.

## 6. Ausência ≠ zero (a decisão dos zeros é explícita)

Na tabela esparsa, cooperado sem linha num procedimento tem taxa AUSENTE, não zero.
Regra do projeto: norma de procedimento é calculada ENTRE QUEM SOLICITA; "não pede" é
dimensão separada (prevalência), não taxa zero. A norma só é apresentável com
solicitantes elegíveis suficientes (constante nomeada). Ausência na base também não é
ausência na prática (pode faturar em outro lugar).

*Caso real: essa decisão quase nasceu implícita dentro de um groupby — foi caçada e
tornada explícita em docstring. Decisão silenciosa é a que ninguém defende depois.*

## 7. O outlier é o PRODUTO — nunca deletar

Estatística robusta (mediana/IQR) para a norma não ser dominada pelo extremo — mas o
extremo permanece no dataset: ele é o candidato a investigação, a razão do projeto
existir. Nenhum drop de outlier, em lugar nenhum.

## 8. Corte é argumento com evidência, nunca número cravado

Todo corte (piso, n mínimo, gatilho) entra por argumento, com valor vindo de constante
nomeada, com status (provisório/calibrado) e proveniência comentados. A escolha de
qualquer corte olha DOIS lados simultaneamente: estabilização (quando a medida vira
confiável) E retenção (quem sobrevive ao corte). Corte que estabiliza tudo mas retém
uma minoria não produz norma — produz elite de alto volume.

*Caso real: um piso apareceu solto no notebook, órfão do diagnóstico que o justificava —
virou número mágico até ser religado ao painel de evidência (funil + IQR + retenção).*

## 9. Numerador e denominador do MESMO conjunto

Numerador de um filtro com denominador de outro = taxa inconsistente e invisível. Ambos
derivam do mesmo dataframe, com os mesmos filtros. Antes de somar quantidades, auditar a
coluna (nulos, zeros, distribuição) e registrar a decisão de tratamento como comentário.

## 10. Razão de totais, não média de razões

Taxa agregada de um cooperado = total de itens / total de consultas. A média das taxas
por consulta daria peso igual a consultas de 1 e de 15 itens — distorce.

## 11. Solicitação ≠ execução; norma recalculada ≠ baseline congelado

Semânticas e denominadores diferentes — nunca misturar nem inferir uma da outra.
Detecção de outlier usa norma recalculada na janela corrente; medição de progresso usa
baseline congelado — trocá-los faz o número mentir (a régua desce junto com a melhora).

---

## Checklist antes de QUALQUER cálculo (responder de verdade, não pular)

1. Qual o peer group? A comparação cruza área de atuação? (se cruza → parar)
2. Qual o denominador de cada taxa? Alguém com denominador pequeno aparece no resultado?
   O piso foi aplicado por argumento, vindo de constante nomeada?
3. Que n sustenta cada estatística de grupo? O n está visível no output?
4. A forma da distribuição foi verificada NESTA análise? Mediana/IQR como default?
5. Se há ranking: as duas lentes (razão E excedente) estão presentes?
6. Se há excedente: o confundidor de perfil foi considerado antes de sinalizar?
7. Zeros/ausências: a regra explícita (norma entre solicitantes) está sendo respeitada?
8. Todo corte veio por argumento, de constante nomeada, com status comentado?