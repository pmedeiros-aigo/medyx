**A regra que vale pra tudo abaixo:** todo cálculo de comparação é dentro de uma área de atuação. Nada cruza área. A área entra como um rótulo por cooperado, e tudo se reagrupa por ela.

**Nível 1 — por cooperado (ainda não envolve área).** Aqui você só prepara os ingredientes. Para cada cooperado: o denominador (consultas, que você já tem) e, para cada procedimento que ele solicita, a taxa = contagem do procedimento ÷ consultas do cooperado. Isso é uma tabela longa: cooperado × procedimento × taxa. Não precisa de área ainda — é a matéria-prima.

**Nível 2 — a norma, por área e por procedimento.** Agora a área entra. Você reagrupa os cooperados por área de atuação e, para cada par (área, procedimento), calcula a distribuição das taxas individuais dos cooperados daquela área. Dessa distribuição saem: a mediana (a referência da área para aquele procedimento), o IQR (P25–P75, a dispersão), e os percentis que você vai querer pro gatilho (P75, P90). Repare: a norma não é um número do cooperado, é um número do par área-procedimento. É isso que responde "o que é normal nesta área para este exame".

Antes de confiar nessa norma, dois filtros que a metodologia exige e que entram aqui: só entram na construção da norma os cooperados acima do piso de consultas (senão a taxa deles é ruído), e a norma só é apresentável se a área tiver cooperados suficientes (o n mínimo). Esses dois você ainda vai calibrar — mas o cálculo da norma já tem que respeitá-los desde o desenho.

**Nível 3 — posição de cada cooperado contra a norma da área dele.**  Com a norma pronta, para cada cooperado e cada procedimento você compara a taxa dele contra a distribuição da área: em que percentil ele cai, quão acima da mediana ele está. É aqui que "fora do padrão" ganha significado — e só aqui, porque só agora existe um padrão da área pra comparar.


**Antes de tudo isso, três calibrações que são pré-requisito** e que são o verdadeiro trabalho desta sessão (o resto é mecânico depois que esses três valores existem):

A primeira é o **funil de estabilização** — descobrir acima de quantas consultas a taxa de um cooperado para de oscilar. Esse é o piso. Calcula-se uma vez, por área (ou único, se as áreas não diferirem).

A segunda é a **forma das distribuições** — confirmar que são cauda-longa, o que valida usar mediana e não média. Se alguma for simétrica, a regra muda pra aquele caso.

A terceira é a **prevalência** — para cada área, quantos cooperados solicitam cada procedimento. Isso você só mede agora; serve pra decidir depois se um procedimento que quase ninguém pede entra ou não na norma. Não decida nada sobre isso ainda, só meça.

**A ordem de execução, sem ambiguidade**: mapa de áreas-teste → taxa por cooperado/procedimento (Nível 1) → funil/piso + forma + prevalência (as três calibrações) → norma por área/procedimento com piso e n mínimo aplicados (Nível 2) → posição de cada cooperado (Nível 3). Cada etapa usa a anterior; nenhuma pula.

**O que ainda NÃO entra nesta sessão**, pra não vazar escopo: nada de custo (continua só quantidade), nada de excedente ou oportunidade de redução (isso é o degrau seguinte, depois que a norma estiver de pé e validada), nada de decidir a regra dos zeros (só medir prevalência), e nada de escrever no config — os valores calibrados saem como proposta pra você revisar.