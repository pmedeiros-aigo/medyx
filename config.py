"""
config.py, FONTE ÚNICA DE TODOS OS VALORES da metodologia analítica (Medyx / Unimed).

Princípio: nenhum número da metodologia existe fora deste arquivo. O documento
METODOLOGIA_ANALITICA.md descreve o MÉTODO e referencia estas constantes POR NOME;
este arquivo guarda os VALORES. Os dois se apontam, nunca duplicam.

Convenção de status de cada constante:
  - MEDIÇÃO    -> nasce None; preenchida pela exploração/calibração. Nunca inventar.
  - DECISÃO    -> carrega o valor decidido pelo método; ajustável conscientemente.
  - PROVISÓRIO -> calibrado na amostra atual (área placeholder única, jul/2026);
                  recalibrar quando a classificação real por área chegar.

Toda constante traz: o que é, de onde vem (proveniência) e a seção do documento que a explica.
Constantes marcadas "parâmetro do analista" são DEFAULTS: a UI expõe o controle e o
pipeline recebe o valor escolhido POR ARGUMENTO, nunca lê daqui no meio do cálculo.

Proveniência geral dos PROVISÓRIOS: calibrações do unimed_natal/calculos_iniciais.ipynb
(amostra 2025-05 a 2026-04, 202 cooperados, área placeholder única).
"""

# ---------------------------------------------------------------------------
# CAMINHOS DOS DADOS  —  contrato de dados  —  fora do repo do app
# Raw e marts vivem em ../unimed_natal (irmão de medyx/). O fato dos marts JÁ
# carrega AREA_ATUACAO (classificação v2.0, coluna area_mvp) e elegivel_norma —
# gerado por preparar_marts.py a partir dos CSVs brutos e da dim v2.
# A dim v2 é gerada pelo notebook unimed_natal/classificacao_cooperados.ipynb
# (Parte 15) e documentada em unimed_natal/marts/LEIAME_classificacao_v2.md.
# ---------------------------------------------------------------------------
from pathlib import Path as _Path

DIR_UNIMED = _Path(__file__).resolve().parent.parent / "unimed_natal"
DIR_MARTS = DIR_UNIMED / "marts"
CAMINHO_FATO_SOLICITACOES = DIR_MARTS / "fato_solicitacoes.parquet"
CAMINHO_CONTAS = DIR_MARTS / "contas.parquet"
CAMINHO_DIM_EXECUTANTES = DIR_MARTS / "dim_executantes_cooperado.parquet"
CAMINHO_DIM_BENEFICIARIOS = DIR_MARTS / "dim_beneficiarios.parquet"
CAMINHO_DIM_CLASSIFICACAO = DIR_MARTS / "dim_classificacao_v2.csv"
DIR_RAW = DIR_UNIMED / "dados_iniciais"
CAMINHO_RAW_REQUISICOES = DIR_RAW / "base_requisicoes_gineco_obs_202504_202604.csv"
CAMINHO_RAW_CONTAS = DIR_RAW / "base_contas_gineco_obs_202504_202604.csv"


# ---------------------------------------------------------------------------
# PEER GROUP / GRANULARIDADE  —  classificação v2.0 (set/2026)
# O peer group de SINALIZAÇÃO é a área do MVP (coluna area_mvp da dim v2, que
# vira AREA_ATUACAO no fato). A v2 classifica cada consulta por família de
# atendimento a partir do pacote de procedimentos pedido; o médico é a MISTURA
# das suas consultas, e a área principal é a maior família específica com
# >= 15% das consultas ("Ginecologia Geral" quando nenhuma chega lá). A
# area_mvp agrupa as áreas finas em nomes de especialidade (decisão de produto,
# 2026-09-11). A mistura, as áreas secundárias e a execução são IDENTIDADE
# visível (badges), nunca subdivisão de régua (espec funcional, regra 2).
# INDEFINIDO é estado legítimo: sem área principal (volume insuficiente,
# prática pouco visível, só pronto-socorro), fora de comparação.
# ---------------------------------------------------------------------------
ESPECIALIDADES = [
    "Ginecologia Geral",
    "Obstetrícia",
    "Endoscopia Ginecológica",
    "Mastologia",
    "Ginecologia Endócrina",
    "PTGI",
    "Ultrassonografia",
    "Patologia",
]
AREA_INDEFINIDA = "INDEFINIDO"   # sem área principal na classificação
# A área fina da classificação -> a área do MVP. É o MESMO dicionário do
# notebook (AREA_MVP, Parte 12); aqui serve para saber se a área secundária de
# um cooperado cai na própria área do MVP (aí a etiqueta "também X" repete o
# rótulo e não entra).
AREA_MVP_DAS_FINAS = {
    "cirurgia / histeroscopia": "Endoscopia Ginecológica",
    "dor pélvica / endometriose": "Endoscopia Ginecológica",
    "generalista": "Ginecologia Geral",
    "climatério": "Ginecologia Endócrina",
    "infertilidade": "Ginecologia Endócrina",
    "pré-natal": "Obstetrícia",
    "ultrassonografia obstétrica": "Ultrassonografia",
    "ultrassonografia": "Ultrassonografia",
    "laudos de citopatologia": "Patologia",
    "mastologia": "Mastologia",
    "PTGI": "PTGI",
}

# ---------------------------------------------------------------------------
# RÓTULOS DE EXIBIÇÃO  —  o CSV fala a língua do pipeline; a tela, a do cliente.
# Camada de tradução, não renomeação na origem. Na v2 os nomes da area_mvp já
# são os de tela; só INDEFINIDO precisa de tradução. Área ausente do mapa
# aparece com o rótulo da classificação, sem tradução.
# ---------------------------------------------------------------------------
ROTULOS_AREA = {
    AREA_INDEFINIDA: "Sem área de atuação",
}

# Perfil de cada área numa linha, para o `title` da opção do seletor: o rótulo
# diz o nome, o perfil diz o que distingue a área das vizinhas.
#
# QUALITATIVO de propósito, sem número: percentual escrito aqui não recalcula
# quando o analista muda a janela — número na tela tem de sair do motor.
PERFIS_AREA = {
    "Ginecologia Geral": "Rotina ginecológica; nenhuma frente específica chega a "
                         "15% das consultas.",
    "Obstetrícia": "Acompanhamento de gestação é a maior frente da prática.",
    "Endoscopia Ginecológica": "Cirurgia ginecológica, histeroscopia, dor pélvica e "
                               "endometriose.",
    "Mastologia": "Mama: rastreio e investigação diagnóstica.",
    "Ginecologia Endócrina": "Climatério, osteoporose e infertilidade.",
    "PTGI": "Patologia do trato genital inferior: vulvoscopia, biópsia, "
            "cauterização.",
    "Ultrassonografia": "Perfil de execução: realiza ultrassonografia mais do que "
                        "solicita.",
    "Patologia": "Perfil de execução: lauda citopatologia mais do que solicita.",
    AREA_INDEFINIDA: "Sem área principal: volume insuficiente ou prática pouco "
                     "visível nas solicitações. Fora de comparação.",
}

# Versão/status da classificação injetada — carimbo em TODA saída do pipeline
# e em toda tela (léxico: governança visível). Homologação clínica PENDENTE.
# DECISÃO 2026-08-14: o status de homologação NÃO aparece para o usuário — o
# carimbo diz só a versão. O status vive na documentação (LEIAME da
# classificação e Nota Metodológica), não na tela.
CLASSIFICACAO_VERSAO = "v2.0"
CLASSIFICACAO_HOMOLOGADA = False

# O que a dim v2 traz por cooperado e o app usa (o resto é identidade):
#   situacao            classificável · classificável pela execução · volume
#                       insuficiente · prática pouco visível · só pronto-socorro
#   area_mvp            o peer group (ESPECIALIDADES acima); vazio -> INDEFINIDO
#   area_principal      a área fina; area_secundaria; area_execucao
#   confianca           alta · média · baixa · indicativa (não classificável)
#   cadastro_agregado   >= 25% de pacientes homens: cadastro que agrega mais de
#                       um profissional, não um perfil clínico
#   elegivel_norma      quem FORMA a referência: classificável, sem cadastro
#                       agregado, sem a execução como prática principal e sem
#                       confiança baixa. Todos os demais seguem MEDIDOS.
#   no_limiar           área principal entre 12% e 18% das consultas (perto do
#                       corte de 15%): o rótulo é frágil
#   perfil_instavel_no_ano  a mistura mudou >= 20 pontos entre os semestres
# As duas últimas são a fila de observação da classificação: a v1 mantinha
# listas de cooperados no config; a v2 traz o sinal por dado.


# ---------------------------------------------------------------------------
# PISO_CONSULTAS_ANO  —  MEDIÇÃO (PROVISÓRIO no _default)  —  doc §5.2
# Piso de consultas/ano para um cooperado ENTRAR na construção da norma.
# Proveniência: funil de estabilização (jul/2026, área placeholder): IQR das taxas
#   trava (~2,0) a partir de 100 consultas; retenção 66,8% (135/202). Faixas
#   intermediárias (30–100) têm n de um dígito — não sustentam piso menor.
# Escalado proporcionalmente à duração da janela em tempo de execução (não aqui).
# Parcimônia (doc §4): só diferenciar por área se a calibração MOSTRAR diferença;
#   áreas ficam None até a calibração com classificação real.
# ---------------------------------------------------------------------------
# Re-justificação com áreas reais (notebook §13.1, Mov 3): em Ginecologia e GO
# todos os formadores de norma têm >=100 consultas — o piso é NÃO-VINCULANTE
# nessas áreas (gate efetivo = elegivel_norma); sem dado sub-100 para re-derivar.
# Mantido 100, por especialidade só quando a calibração MOSTRAR diferença.
PISO_CONSULTAS_ANO = {
    "_default": 100,             # PROVISÓRIO, re-justificado com áreas reais (Mov 3)
    "Ginecologia Geral": None,
    "Obstetrícia": None,
    "Endoscopia Ginecológica": None,
    "Mastologia": None,
    "Ginecologia Endócrina": None,
    "PTGI": None,
    "Ultrassonografia": None,
    "Patologia": None,
}


# ---------------------------------------------------------------------------
# N_MINIMO_PEER_GROUP  —  MEDIÇÃO/DECISÃO (PROVISÓRIO)  —  doc §5.3
# Nº mínimo de cooperados VÁLIDOS por trás de uma norma para ela ser apresentada
# como sólida ('apresentavel'). Abaixo: valores brutos, rótulo "amostra pequena".
# Proveniência: retenção medida (jul/2026): n>=10 mantém 38% dos pares
#   (área, procedimento) apresentáveis. Recalibrar com áreas reais (grupos menores).
# ---------------------------------------------------------------------------
N_MINIMO_PEER_GROUP = 10         # PROVISÓRIO


# ---------------------------------------------------------------------------
# N MÍNIMO POR PERCENTIL-GATILHO  —  DECISÃO (PROVISÓRIO)  —  defensabilidade
# P90 de um grupo com n<20 é ~o 2º maior valor (sorteio, não régua); P75 com
# n<10 idem. O gatilho degrada automaticamente pelo n de elegíveis que o
# sustenta: p90 -> p75 (10 <= n < 20) -> nenhum (n < N_MINIMO_P75), com
# rastreabilidade na coluna gatilho_usado. Sem régua defensável, não se
# sinaliza ninguém — só posição descritiva.
# ---------------------------------------------------------------------------
N_MINIMO_P90 = 20                # PROVISÓRIO, recalibrar com áreas reais
N_MINIMO_P75 = 10                # PROVISÓRIO, coincide com N_MINIMO_PEER_GROUP por ora


# ---------------------------------------------------------------------------
# PISO_EXECUCOES_ANO  —  MEDIÇÃO (PROVISÓRIO)  —  lado da execução (notebook §8.3)
# Piso de execuções/ano para o perfil de execução (autorreferência, mix de regime)
# ser confiável. Mesmo espírito do piso de consultas; escalado pela janela em runtime.
# ---------------------------------------------------------------------------
PISO_EXECUCOES_ANO = 50          # PROVISÓRIO


# ---------------------------------------------------------------------------
# JANELA_MINIMA  —  DECISÃO  —  doc §5.1
# Menor janela temporal analisável. Abaixo dela a maioria cai sob o piso e a
# norma desestabiliza. Decisão de método: trimestral, com aviso de confiabilidade
# quando o n de consultas do cooperado na janela cai abaixo do piso escalado.
# ---------------------------------------------------------------------------
JANELA_MINIMA = "trimestral"
# A forma NUMÉRICA da decisão acima, para a validação da janela livre. Existe
# desde que a UI passou a aceitar intervalo escolhido (14/ago): com 3/6/12
# meses fixos o mínimo nunca era exercido; com início e fim livres, ele é a
# única coisa entre o analista e uma janela que não sustenta norma.
JANELA_MINIMA_MESES = 3


# ---------------------------------------------------------------------------
# GATILHO_DEFAULT  —  DECISÃO  —  doc §6, §7.1  —  parâmetro do analista
# Percentil que define outlier por padrão na UI (quem SINALIZAR). Separado do
# alvo — nunca o mesmo corte, sob pena de condenar o quartil superior por
# construção. Grafia minúscula: nome de coluna do pipeline ("p75"/"p90").
# ---------------------------------------------------------------------------
GATILHO_DEFAULT = "p90"


# ---------------------------------------------------------------------------
# ALVO_DEFAULT  —  DECISÃO  —  doc §7.1  —  parâmetro do analista
# Nível-alvo para o qual a redução é calculada (o "trazer para cá").
# Recomendação de método: a mediana da área — norma plausível que NÃO embute o
# próprio desvio que se quer eliminar.
# ---------------------------------------------------------------------------
ALVO_DEFAULT = "mediana"


# ---------------------------------------------------------------------------
# CONFUNDIDORES  —  DECISÃO (PROVISÓRIO)  —  doc §7.3  —  parâmetro do analista
# Q_CONFUNDIDOR: quantil dos pares elegíveis acima do qual o cooperado recebe
#   flag de confundidor (urgência, regime). 0.90 = marca os 10% mais altos.
#   Contexto para investigação — NÃO altera nenhum cálculo.
# STRING_URGENCIA: valor literal de CARATER_ATENDIMENTO que identifica urgência
#   na base de requisições (contrato de dados).
# ---------------------------------------------------------------------------
Q_CONFUNDIDOR = 0.90             # PROVISÓRIO
STRING_URGENCIA = "URGÊNCIA/EMERGÊNCIA"


# ---------------------------------------------------------------------------
# CONTEXTO DE PS (episódio de pronto-socorro)  —  DECISÃO  —  doc §5.6, notebook §12
# Regra por CONTEXTO (teste pré-comprometido, jul/2026): episódio-PS é identificável
#   no próprio dado — consulta com CARATER_ATENDIMENTO == STRING_URGENCIA em QUALQUER
#   item OU contendo CD_PACOTE_URGENCIA. A norma roda sobre consultas NÃO-PS de todo
#   mundo: a consulta-PS sai INTEIRA (numerador e denominador juntos); a flag de
#   plantonista da classificação vira informativa.
# Proveniência (calculos_iniciais.ipynb §12): coerência 100% entre os marcadores
#   (12.699/12.701), separação 366× (mediana share_ps plantão 0,70 vs 0,0019),
#   custo do filtro 7,2% das consultas / 1,9% dos itens; corte de volume do
#   critério B varrido de 100 a 1000 — 0 suspeitos em todos (inócuo). Consultas
#   mistas 1,7% com 0,1% de itens eletivos de carona — viés conservador declarado.
#   Validação clínica da lista top-15 PENDENTE (médico): regra ADOTADA, não "validada".
# CD_PACOTE_URGENCIA: código do "PACOTE ATENDIMENTO DE URGENCIA" (contrato de dados).
# INCLUIR_PS_DEFAULT: default do parâmetro incluir_ps dos motores — False = análise
#   sobre eletivas. A UI expõe a escolha; o motor recebe POR ARGUMENTO.
# ---------------------------------------------------------------------------
CD_PACOTE_URGENCIA = "85101036"
INCLUIR_PS_DEFAULT = False       # DECISÃO (teste §12)


# ---------------------------------------------------------------------------
# QUALIDADE DE DADO  —  DECISÃO (PROVISÓRIO)  —  ingestão (preparar_fato)
# QT_MAX_PLAUSIVEL: teto de quantidade plausível por item solicitado; acima disso
#   a quantidade é erro de digitação (código TUSS no campo de quantidade) e vale 1.
#   A linha NUNCA é deletada. Proveniência: 9 linhas de lixo na amostra (140 a
#   431.649); sensibilidade testada com tetos 20/127/1000 — top-15 de cooperados
#   estável 14–15/15 e top-15 de pares 15/15 (o ranking não depende do teto).
# LIMIAR_REGRESSAO_QT: mínimo de estabilidade (em 15) no teste de regressão da
#   regra a cada carga nova; abaixo disso o app alerta "recalibrar antes de reportar".
# ---------------------------------------------------------------------------
QT_MAX_PLAUSIVEL = 127           # PROVISÓRIO
LIMIAR_REGRESSAO_QT = 13         # de 15


# ---------------------------------------------------------------------------
# CONCENTRAÇÃO POR BENEFICIÁRIO  —  DECISÃO (PROVISÓRIO)  —  parâmetro do analista
# Q_ALTO_CONCENTRACAO: quantil dos pares que define margem (extensiva/intensiva)
#   "alta" na leitura de concentração.
# MIN_PACIENTES_CONCENTRACAO: mínimo de pacientes recebedores para a leitura não
#   ser "pouco volume".
# FRAC_TOP_CONCENTRACAO: fração de pacientes do share de concentração (top 10%).
# ---------------------------------------------------------------------------
Q_ALTO_CONCENTRACAO = 0.75       # PROVISÓRIO
MIN_PACIENTES_CONCENTRACAO = 10  # PROVISÓRIO
FRAC_TOP_CONCENTRACAO = 0.10     # PROVISÓRIO


# ---------------------------------------------------------------------------
# CONTROLADOR DE CONFIABILIDADE  —  doc §8  —  parâmetro do analista
# NIVEL_CONFIANCA_DEFAULT: confiança default do piso do excedente ("com X de
#   confiança, é PELO MENOS Y"). Incerteza ESTATÍSTICA — nunca misturar com o
#   desconto comercial de realização (premissa de diretoria, fora deste controle).
# N_BOOTSTRAP: nº de reamostras (cluster = paciente da carteira inteira).
# MIN_PACIENTES_BOOTSTRAP: portão — abaixo disso, "intervalo não calculável".
# SEED_BOOTSTRAP: semente obrigatória (mesmo dado + parâmetros => mesmo número).
# ---------------------------------------------------------------------------
NIVEL_CONFIANCA_DEFAULT = 0.90
N_BOOTSTRAP = 1000               # DECISÃO
MIN_PACIENTES_BOOTSTRAP = 20     # PROVISÓRIO
SEED_BOOTSTRAP = 42              # DECISÃO (reprodutibilidade)


# ---------------------------------------------------------------------------
# FRACAO_PARETO_MATERIAL  —  DECISÃO  —  degrau "material" da cascata
# Material é o caso que entra no topo do Pareto que concentra esta fração da
# variação excedente DA ÁREA.
# NATUREZA: critério operacional de TRIAGEM, não de VALIDADE. Não afeta a
#   defensabilidade de nenhum número — o caso abaixo do corte continua correto,
#   medido e exibido; muda apenas a POSIÇÃO NA FILA (o que se olha primeiro).
#   Por isso não entra na linha de justificativa nem no carimbo metodológico:
#   ele ordena trabalho, não sustenta alegação.
# Corte relativo, não absoluto: um limiar em nº de solicitações não sobreviveria
#   à troca de área nem de janela (áreas têm volumes de ordem diferente); o
#   Pareto se recalibra sozinho (rigor-estatistico §3: magnitude é onde se age).
# Proveniência: no notebook (célula 35) a materialidade era só ORDENAÇÃO — "o
#   desempate é a magnitude"; como FILTRO nasce aqui, decidida em jul/2026.
# ---------------------------------------------------------------------------
FRACAO_PARETO_MATERIAL = 0.80

# FRACAO_SEGUNDA_ORIGEM_RELEVANTE  —  DECISÃO (PROVISÓRIO)  —  coluna "Origem do
# excedente". Quando a parcela do 2º procedimento chega a esta fração da parcela
# do 1º, os dois são lidos JUNTOS ("juntos 15%"): dois procedimentos empatados no
# topo são uma leitura diferente de um dominante. Abaixo disso, só o primeiro.
# Não é limiar de método — não entra em cálculo nenhum, só decide o que a
# sub-linha escreve.
FRACAO_ORIGEM_CONCENTRADA = 0.30
# FRACAO_ORIGEM_CONCENTRADA  —  DECISÃO (PROVISÓRIO)  —  coluna "Origem do
# excedente". Parcela mínima do excedente no procedimento do topo para a leitura
# ser CONCENTRADA ("responde por X%"); abaixo dela é "variação difusa
# multiprocedimento" (termo do LEXICO_PRODUTO.md).
# Calibração jul/2026 em Ginecologia (63 comparáveis): mediana da parcela do topo
# = 28%; a 30% ficam 26 concentrados e 37 difusos. Escolhido ACIMA da mediana de
# propósito — na dúvida a tela diz "difusa", que é a leitura conservadora: afirmar
# que um procedimento puxa a variação quando ele responde por 28% dela é apontar
# o alvo errado numa conversa com o médico.
# Não entra em cálculo nenhum: decide qual frase a sub-linha escreve.

FRACAO_SEGUNDA_ORIGEM_RELEVANTE = 0.80

# FAIXA_ESTABILIDADE_SERIE  —  DECISÃO (PROVISÓRIO)  —  direção da mini-série
# Variação do índice entre o primeiro e o último trimestre medido, abaixo da qual
# a série é lida como ESTÁVEL em vez de alta/queda. Oscilação de poucos por cento
# numa taxa trimestral é ruído; sem esta faixa, toda série ganharia seta e a seta
# deixaria de significar alguma coisa. Não entra em cálculo — só decide qual
# palavra a célula escreve.
FAIXA_ESTABILIDADE_SERIE = 0.10


# ---------------------------------------------------------------------------
# PERSISTÊNCIA TEMPORAL  —  DECISÃO (PROVISÓRIO)  —  notebook §9
# MIN_JANELAS_AVALIAVEIS: mínimo de janelas em que o cooperado foi avaliável para
#   a persistência ser reportável (o 1/1 nunca desfila como 4/4).
# ---------------------------------------------------------------------------
MIN_JANELAS_AVALIAVEIS = 2       # PROVISÓRIO

# ─────────────────────────────────────────────────────────────────────────────
# VARIACAO_MINIMA_SETA  —  APRESENTAÇÃO  —  set/2026
#
# Variação relativa mínima, entre um trimestre e o anterior, para a tela desenhar
# a seta de direção. Existe como constante, e não solto no bloco, porque a seta
# é uma AFIRMAÇÃO: sem piso, uma oscilação de 0,4% ganharia o mesmo símbolo de
# uma queda de 30%, e a tela passaria a apontar ruído amostral como movimento.
# Abaixo do piso a variação não some — ela continua no hover, em número.
# PROVISÓRIO: 5% é ponto de partida, não calibração.
# ─────────────────────────────────────────────────────────────────────────────
VARIACAO_MINIMA_SETA = 0.05      # PROVISÓRIO


# ---------------------------------------------------------------------------
# TABELA DE PREÇO  —  MEDIÇÃO (externa)  —  doc §3.1, §9
# função_de_valor de custo = quantidade × preço_do_procedimento.
# A tabela OFICIAL ainda não chegou. O preço derivado de contas (mediana de
# VALORTOTAL/QUANTIDADEEXECUTADA) existe SÓ como prova de conceito em runtime,
# quarentenado — não é constante do método e nenhum R$ dele é reportável.
# STATUS: ausente — quando a tabela oficial chegar, é injetada no pipeline
# (parâmetro `preco`), não gravada aqui como número.
# ---------------------------------------------------------------------------
PRECO_POR_PROCEDIMENTO = None


# ---------------------------------------------------------------------------
# CONTRATO DE DADOS  —  confirmado na exploração  —  doc §5.1
# Eixo temporal = DATA DE SOLICITAÇÃO (o evento clínico que gera o custo).
# Confirmação (analise.ipynb / calculos_iniciais.ipynb): DT_REQUISICAO cobre
# exatamente a janela da amostra; DATA_EXECUCAO vaza de 2022 a 2026 (não serve
# de eixo). Toda análise filtra por esta coluna.
# ---------------------------------------------------------------------------
COLUNA_DATA_SOLICITACAO = "DT_REQUISICAO"


# ---------------------------------------------------------------------------
# JANELA_CONSULTA_MINUTOS  —  DECISÃO (PROVISÓRIO)  —  ago/2026
# A consulta inferida é o conjunto de solicitações do MESMO cooperado para o
# MESMO beneficiário cujos lançamentos consecutivos distam no máximo isto. O
# DIA continua sendo fronteira externa: sessão não atravessa a meia-noite,
# porque o eixo temporal de toda análise é a data de solicitação.
#
# Substitui a regra anterior ("mesmo dia", sem hora), que era aproximação
# forçada: `preparar_fato` descartava o horário com .dt.normalize(), e sem ele
# não havia como separar atendimentos.
#
# Calibração (base de abril/2025 a abril/2026, lado solicitante):
#   · 85,2% das consultas têm lançamento ÚNICO — não são afetadas pela regra;
#   · entre as com mais de um lançamento, o intervalo mediano é de 8 minutos e
#     72,4% cabem dentro de 1 hora;
#   · aplicada a todos: 188.605 -> 196.542 consultas (+4,21%), taxa mediana por
#     cooperado de 5,124 -> 4,925 itens/consulta;
#   · ranking preservado: Spearman 0,978, movimento mediano de 2 posições;
#   · 0,97% dos intervalos de pacientes identificados passam de 1h e são
#     divididos — erro conhecido, para o lado conservador.
#
# RESSALVA REGISTRADA (não resolvida): consultas de span longo têm assinatura
# clínica — citopatologia (lift 20x), vulvoscopia (7x) e captura híbrida (4x),
# começando por procedimento de consultório e terminando em imagem. Podem ser
# UM atendimento de investigação de colo, e não dois. Pendente de validação
# clínica com a Unimed; decisão de produto foi seguir com a regra única.
JANELA_CONSULTA_MINUTOS = 60


# ---------------------------------------------------------------------------
# BENEFICIÁRIO NÃO IDENTIFICADO  —  MEDIÇÃO (ago/2026)
# Registro que o sistema de origem grava quando o campo do beneficiário chega
# vazio. Não é uma pessoa: é o ÚNICO da base com SEXO='I' (contra 1.006.931
# linhas F ou M), idade constante 26 ao longo de 229 datas, 2.537 linhas
# distribuídas por 6 cooperados, com painel ocupacional (ácido hipúrico e
# metilhipúrico — marcadores de exposição a tolueno e xileno).
#
# NÃO é excluído: os pedidos são reais e o volume e o custo estão certos — o
# que está inválido é um campo. Ele recebe id próprio no mapa de beneficiários
# e a regra de sessão (JANELA_CONSULTA_MINUTOS) o trata como todos os outros.
#
# Concentração: 78,4% das linhas do cooperado_116 e 75,4% do cooperado_112.
# Pendente de confirmação da Unimed de que SEXO='I' + idade fixa é mesmo o
# registro de preenchimento deles.
HASH_BENEFICIARIO_NAO_IDENTIFICADO = (
    "178ADA1D734416F2057C250AFA7427D10AEB88DE88FF0D433FED91EE59D96ECC"
)
ID_BENEFICIARIO_NAO_IDENTIFICADO = "beneficiario_nao_identificado"


# ---------------------------------------------------------------------------
# CARTEIRA ATENDIDA  —  DECISÃO (PROVISÓRIO)  —  set/2026
# A composição etária dos beneficiários que o cooperado atendeu na janela,
# contra a mesma composição na área. NÃO entra em cálculo nenhum: é fator de
# contexto, a lente com que se lê a frequência dele antes de concluir qualquer
# coisa (METODOLOGIA §7.3, confundidor antes de conclusão). Carteira mais velha
# eleva a frequência ESPERADA de rastreio, e sem esse número na tela a leitura
# "ele pede demais" fica sem a pergunta seguinte.
#
# FAIXAS_ETARIAS: cortes de rotina em saúde suplementar (a última faixa é
# aberta). Poucas e largas de propósito: dez faixas dariam n pequeno em cada uma
# para um cooperado de carteira média, e faixa com n de 12 não sustenta
# comparação com a área.
FAIXAS_ETARIAS = (
    (0, 19, "até 19"), (20, 29, "20–29"), (30, 39, "30–39"),
    (40, 49, "40–49"), (50, 64, "50–64"), (65, 200, "65+"),
)

# COBERTURA_MINIMA_PERFIL — fração dos beneficiários do cooperado para os quais
# a idade é conhecida, abaixo da qual a composição NÃO é apresentada.
#
# Hoje a cobertura é TOTAL: a idade vem da própria requisição, gravada na
# dim_beneficiarios pelo preparar_fato, e alcança 100% dos beneficiários do fato
# (medido em set/2026: zero sem idade em 57.213). O portão fica como guarda —
# base nova, outra especialidade ou mudança na origem podem trazer buraco, e
# neste app composição sobre uma minoria da carteira não vai à tela sem dizer
# que é minoria. A cobertura apurada viaja junto do número quando não é plena.
#
# A primeira versão buscava a idade nas CONTAS e chegava a 82%, porque só tem
# conta quem teve execução na janela; o dado sempre esteve do lado da
# solicitação. Registrado para ninguém refazer o caminho errado.
COBERTURA_MINIMA_PERFIL = 0.70     # PROVISÓRIO

# MIN_BENEFICIARIOS_CARTEIRA — carteira mínima para a composição ser publicada.
# Com 20 beneficiários, uma faixa inteira se move 5 pontos por causa de uma
# pessoa, e a comparação com a área vira ruído.
MIN_BENEFICIARIOS_CARTEIRA = 30    # PROVISÓRIO


# MIN_SOLICITACOES_FAIXA EXISTIU E FOI REMOVIDO (set/2026). Ele escondia a
# repartição etária de exames com poucas solicitações, com o argumento de que
# "8% numa faixa" pode ser uma solicitação só.
#
# O argumento vale para a PORCENTAGEM, não para a contagem, e a contagem é o que
# a seção mostra: cada faixa imprime "20–29 · 2" ao lado de "13%". O n viaja
# junto da fatia, que é o que a lei analítica exige — e com o n na tela o piso
# só suprimia dado real, agregado sem nenhuma inferência.
#
# Registrado para a regra não voltar por parecer prudente. Ela não era: era
# esconder o que o usuário pediu para ver.


# ---------------------------------------------------------------------------
# PAINEL DO PROCEDIMENTO (espec §3)  —  DECISÃO (PROVISÓRIO)  —  ago/2026
# Portões do detalhe por (cooperado, procedimento). Nenhum deles altera cálculo:
# governam o que é APRESENTÁVEL, no mesmo espírito de N_MINIMO_PEER_GROUP.
#
# Repetição/concentração exigem um mínimo de pacientes para a distribuição não
# ser anedota — abaixo disso o painel declara "pouco volume" (mesmo vocabulário
# de concentracao_por_beneficiario).
MIN_PACIENTES_PAINEL = 5           # PROVISÓRIO

# QUANTOS NOMES a lista "Acima do critério" do painel do exame na área mostra
# antes de pedir para revelar o resto. Não é um número: é o núcleo que soma
# FRACAO_PARETO_MATERIAL do excedente daquele exame, a mesma regra do degrau
# "material" da cascata. Estes dois só o CONTÊM.
#
# O piso existe porque lista de um nome não é lista — sem ele, um exame cujo
# excedente vem quase todo de uma pessoa mostraria essa pessoa sozinha, e o
# leitor não teria com que compará-la.
# O teto existe porque acima dele a gaveta vira rolagem, e aí a resposta certa
# é revelar sob demanda em vez de empilhar.
#
# Medido em Ginecologia (671 procedimentos, 232 com alguém acima do critério):
#   acima do critério por exame: mediana 8 · p90 16 · máximo 19
#   núcleo dos 80%: varia de 4 a 9 nos exames de maior excedente
# ou seja, o teto raramente morde, e quando morde é exatamente o caso em que
# uma lista completa seria ilegível.
MIN_NOMES_PAINEL = 3               # PROVISÓRIO
MAX_NOMES_PAINEL = 10              # PROVISÓRIO


# ---------------------------------------------------------------------------
# PRINCIPAIS OPORTUNIDADES  —  DECISÃO DE PRODUTO  —  espec §Área
# Quantos pares (cooperado × procedimento) o bloco mostra antes de a cauda ser
# revelada sob demanda.
#
# CINCO, e não o núcleo dos 80% como no painel do exame: lá o corte responde
# "quem concentra este excedente", uma pergunta sobre o exame; aqui o bloco é
# uma fila de trabalho, e fila se dimensiona pelo que cabe numa sessão de
# trabalho, não pela forma da cauda. Em Ginecologia os pares qualificados são
# 38, e o núcleo dos 80% deles passaria de vinte: lista longa demais para o
# lugar que ela ocupa na página, logo abaixo da Leitura da área.
#
# A cauda inteira viaja no payload e é revelada por link (§10, disclosure
# progressivo). Nenhum par é escondido, só adiado.
# ---------------------------------------------------------------------------
N_OPORTUNIDADES_VISIVEIS = 5       # PROVISÓRIO

# LIMIAR_CONCENTRACAO_PACIENTE — participação de UM paciente nas solicitações de
# um exame a partir da qual ele é listado nominalmente no painel.
#
# Substitui um "top 5 fixo" (ago/2026) que era chute meu e, pior, convivia com o
# FRAC_TOP_CONCENTRACAO do método no mesmo card: a lista falava de 5 pessoas e o
# rodapé de 39, sem nada dizer que eram conjuntos diferentes. Um conceito de
# concentração por card, e ele sai do dado.
#
# Medido (10.981 pares com >=5 pacientes, janela anual, sem PS):
#   participação de um paciente: mediana 0,5% · p90 3,3% · p99 16,7%
# 10% é 20x a mediana e 3x o p90 — quem passa disso destoa de verdade. Efeito:
#   dispara em 40,7% dos pares; lista de 5 linhas na mediana, 8 no p90, 9 no máximo
# ou seja, quando há achado a lista é curta o bastante para caber no painel, e
# quando não há ela simplesmente não existe — que é a leitura correta.
LIMIAR_CONCENTRACAO_PACIENTE = 0.10   # PROVISÓRIO

# Autorreferência POR PROCEDIMENTO só é apresentável com base suficiente. O
# cruzamento solicitação x conta acha 31% dos itens no agregado, mas a mediana
# por (cooperado, procedimento) cai para 11% — e sobre 11% a taxa salta entre 0%
# e 100% (medido ago/2026: mediana 0,00 e p90 1,00 nos pares com volume). Abaixo
# do portão a UI diz "cobertura insuficiente" com o número real, nunca a taxa.
MIN_ITENS_AUTORREF_PROC = 20       # PROVISÓRIO, itens com conta localizada
MIN_COBERTURA_AUTORREF_PROC = 0.50 # PROVISÓRIO, fração de itens com conta


# ---------------------------------------------------------------------------
# EXCLUSÃO POR PAR (Mov 5)  —  DECISÃO  —  desligada na classificação v2.0
# Na v1 os portadores de sub-perfil (opera, alto risco) saíam da formação da
# norma nas cestas que o perfil explicava. Na v2 as áreas já separam essas
# práticas (Endoscopia Ginecológica, Obstetrícia), e a mistura por médico é
# identidade visível. O mecanismo continua no motor (montar_exclusao_por_par);
# a lista de regras está vazia. Formato de cada regra, se voltar a ser usada:
# (flag booleana da dim, área onde vale, regex da cesta sobre DS_PROCEDIMENTO).
# ---------------------------------------------------------------------------
EXCLUSOES_SUBPERFIL = ()
LIMIAR_DISTORCAO_EXCLUSAO = 0.15   # PROVISÓRIO, movimento de mediana que ativa exclusão

# ---------------------------------------------------------------------------
# O QUE CADA SUB-PERFIL MUDA NA COMPARAÇÃO  —  hover do badge na tabela
# Uma frase por sub-perfil. O badge é IDENTIDADE (espec funcional, regra 2) e
# nunca subdivide a régua. Na v2 nenhum badge altera cálculo: todos são
# informativos, e a frase diz isso para ninguém supor que muda.
# As chaves são as colunas booleanas que dados.carregar_classificacao deriva da
# dim v2 (ver blocos._BADGES).
# ---------------------------------------------------------------------------
AJUDA_SUBPERFIL = {
    "faz_cirurgia": (
        "Informativo. Cirurgia e histeroscopia respondem por uma fatia das "
        "consultas acima do corte natural do dado (7%). Não altera o cálculo "
        "da referência."
    ),
    "faz_mastologia": (
        "Informativo. Mama responde por uma fatia das consultas acima do corte "
        "natural do dado (38%). Não altera o cálculo da referência."
    ),
    "tem_secundaria": (
        "Informativo. Uma segunda frente de prática com pelo menos 15% das "
        "consultas. Não altera o cálculo da referência."
    ),
    "executa": (
        "Informativo. Também atua no lado da execução (ultrassonografia, "
        "colposcopia, citopatologia ou imagem mamária). Não altera o cálculo "
        "da referência; quando a execução é a prática principal, o cooperado "
        "não a forma."
    ),
    "carteira_jovem": (
        "Informativo. Carteira predominantemente jovem (pacientes de 20 a 39 "
        "anos). Não altera o cálculo da referência."
    ),
    "carteira_climaterio": (
        "Informativo. Carteira predominantemente de 50 anos ou mais. Não "
        "altera o cálculo da referência."
    ),
}

# MIN_PORTADORES_RECORTE_PERFIL  —  DECISÃO (2026-08-13)  —  recorte por perfil
# Mínimo de portadores para o sub-perfil ser SELECIONÁVEL no recorte.
# Era 3 (proteção contra "1º de 2" ler como posição); baixado para 1 por decisão
# do usuário: o recorte serve para VER quem carrega o perfil, não para leitura
# estatística interna — a régua não muda, e o posto sempre viaja com o
# denominador ("1º de 2"), que é a própria ressalva.
MIN_PORTADORES_RECORTE_PERFIL = 1

# LIMIAR_CONCENTRACAO_PARETO  —  DECISÃO (2026-08-13)  —  leitura do Pareto
# O NÚCLEO do Pareto: menor conjunto de cooperados cuja soma atinge este
# percentual do custo evitável potencial da área (leitura clássica 80/20).
# As barras do núcleo são destacadas e a frase de concentração usa o valor
# acumulado REAL do núcleo, não o limiar.
LIMIAR_CONCENTRACAO_PARETO = 0.80

# Nome da CESTA de cada sub-perfil com exclusão por par ativa (hover da etiqueta
# "perfil explica a origem"). Vazio na v2: nenhuma exclusão por par ativa.
CESTA_SUBPERFIL = {}


# ---------------------------------------------------------------------------
# UI — DEFAULTS E OPÇÕES DOS CONTROLES  —  parâmetros do analista
# A UI expõe o controle com estas opções/default; o motor recebe POR ARGUMENTO.
# ---------------------------------------------------------------------------
PIPELINE_VERSAO = "v1"
ESPECIALIDADE_MVP = "Ginecologia & Obstetrícia"   # rótulo fixo do seletor (MVP)
JANELAS_UI = {"3m": 3, "6m": 6, "12m": 12}        # rótulo -> meses (ancorados no fim da amostra)
JANELA_DEFAULT = "12m"
GATILHOS_UI = ("p75", "p90")                      # ver GATILHO_DEFAULT
ALVOS_UI = ("mediana", "p75", "p90")              # ver ALVO_DEFAULT; regra: alvo <= gatilho
NIVEIS_CONFIANCA_UI = (0.80, 0.90, 0.95)          # ver NIVEL_CONFIANCA_DEFAULT


# ---------------------------------------------------------------------------
# LIMITES DE ENTRADA DOS CONTROLES NUMÉRICOS  —  VALIDAÇÃO, não metodologia
# O front não conhece regra nenhuma: /api/meta manda estas restrições junto de
# `ativo`/`recomendado` e a tela só desenha o que recebe. Antes disso o mínimo
# vivia escrito no JavaScript, duplicando o `ge=` da assinatura da API — se um
# mudasse, o outro não ficava sabendo.
#   minimo : espelha o `ge=` de `obter_parametros`. Fonte única: daqui saem os
#            dois (a validação do FastAPI e o que a tela desenha).
#   maximo : None = SEM TETO declarado. Não invento um: a API não impõe `le=`, e
#            um teto arbitrário barraria uma base maior sem justificativa medida.
#   passo  : incremento dos botões − / +. O valor também é digitável, então o
#            passo serve a ajuste fino, não a percorrer a faixa.
# ---------------------------------------------------------------------------
LIMITES_CONTROLES = {
    "piso":     {"minimo": 1, "maximo": None, "passo": 1},
    "n_minimo": {"minimo": 1, "maximo": None, "passo": 1},
}

# Textos institucionais fixos (léxico do produto — LEXICO_PRODUTO.md)
BANNER_HOMOLOGACAO = (
    "AMBIENTE DE HOMOLOGAÇÃO: classificação preliminar; "
    "resultados não destinados a deliberação"
)
SELO_PRECO = "preço interno em quarentena"   # todo R$ derivado de contas

# Texto que ocupa o lugar de um número que NÃO PÔDE ser calculado — nunca um
# travessão. Travessão sozinho numa célula lê como zero, e a distinção que o
# ajuste 4 do CLAUDE.md protege é justamente "ausência de par ≠ zero medido".
# O motivo específico viaja sempre ao lado (traducao / motivo / title).
SEM_MEDIDA = "sem medida"

# Ocupa o lugar do NÚMERO nas estatísticas que dependem de régua, quando a área
# não tem referência plena. Diferente de SEM_MEDIDA: lá o par não pôde ser
# medido; aqui a medida existe, o que falta é contra quem compará-la. O motivo
# específico viaja na linha de apoio ao lado.
SEM_SINALIZACAO = "sem sinalização comparativa"


# ---------------------------------------------------------------------------
# ACEITES / SMOKE  —  MEDIÇÃO (output G do notebook, 27/07/2026)
# Valores esperados dos testes de aceitação do app (instrux sessão 1): o app
# deve reproduzir o notebook com a MESMA janela e os MESMOS argumentos.
# Não são metodologia — são o gabarito da migração. Regravar juntos a cada
# re-execução do notebook com dado novo.
# ---------------------------------------------------------------------------
SMOKE_JANELA = ("2025-05-01", "2026-04-30")        # 12m do teste de aceitação
# RE-BASELINE set/2026 (classificação v2.0): a área de referência do gabarito
# passou de "Ginecologia" (v1, 64 medidos / 58 na norma / mediana 5,11) para
# "Ginecologia Geral" (v2). A régua da consulta inferida (JANELA_CONSULTA_MINUTOS,
# ago/2026) não mudou. Valores v1 preservados para rastreabilidade:
#   SMOKE_MEDIANA 5.11 · N_NA_NORMA 58 · N_TOTAL 64 · cooperado_85: 76 ·
#   cooperado_71: 97 · zeros: cooperado_31, cooperado_116.
SMOKE_AREA_REFERENCIA = "Ginecologia Geral"
SMOKE_MEDIANA_AREA = 4.96
SMOKE_N_NA_NORMA_AREA = 44                         # elegíveis que formam a norma
SMOKE_N_TOTAL_AREA = 55
# Pares (cooperado, procedimento) que passam os TRÊS portões (avaliavel &
# apresentavel & sinalizado — pipeline.filtrar_sinalizados). Positivos trazem a
# contagem de procedimentos sinalizados; negativos exigem zero. cooperado_85 e
# cooperado_71 são de Endoscopia Ginecológica (critério p75, 18 formadores).
SMOKE_AREA_SINALIZADOS = "Endoscopia Ginecológica"   # área dos positivos e do topo por razão
SMOKE_SINALIZADOS_ESPERADOS = {"cooperado_85": 52, "cooperado_71": 73}
SMOKE_NAO_SINALIZADOS_ESPERADOS = ("cooperado_61", "cooperado_116")
# Referência agregada da MESMA janela: avaliáveis e o topo por razão — ancoram a
# migração no lado agregado, não só na norma. Os dois atravessaram a v2 intactos.
SMOKE_N_AVALIAVEIS = 132
SMOKE_TOPO_RAZAO = ("cooperado_71", "cooperado_85", "cooperado_19")
