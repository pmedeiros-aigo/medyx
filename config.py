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
# carrega AREA_ATUACAO real (classificação v1.0) e elegivel_norma — gerado pelo
# notebook calculos_iniciais.ipynb (célula do mart, 27/07/2026).
# ---------------------------------------------------------------------------
from pathlib import Path as _Path

DIR_UNIMED = _Path(__file__).resolve().parent.parent / "unimed_natal"
DIR_MARTS = DIR_UNIMED / "marts"
CAMINHO_FATO_SOLICITACOES = DIR_MARTS / "fato_solicitacoes.parquet"
CAMINHO_CONTAS = DIR_MARTS / "contas.parquet"
CAMINHO_DIM_EXECUTANTES = DIR_MARTS / "dim_executantes_cooperado.parquet"
CAMINHO_DIM_CLASSIFICACAO = DIR_MARTS / "dim_classificacao.csv"
CAMINHO_CLASSIFICACAO_V1 = DIR_UNIMED / "dados" / "classificacao_v1.csv"


# ---------------------------------------------------------------------------
# PEER GROUP / GRANULARIDADE  —  classificação v1.0 (jul/2026)
# O peer group de SINALIZAÇÃO é a ESPECIALIDADE da classificacao_v1.csv
# (coluna AREA_ATUACAO do fato). GO e Ginecologia SEPARADOS — decisão jul/2026,
# ratificada pelo Mov 4 (perfis por procedimento distintos: 27% dentro de
# [0.8, 1.25] << critério de fusão 70%). Sub-área/sub-perfil é IDENTIDADE
# visível (badges), nunca subdivisão de régua (espec funcional, regra 2).
# INDEFINIDO é estado legítimo: sem peer group, fora de comparação.
# ---------------------------------------------------------------------------
ESPECIALIDADES = [
    "Ginecologia",
    "GO",
    "Mastologia",
    "Obstetrícia",
    "Reprodução",
    "Ultrassonografista",
    "Geral",
]
AREA_INDEFINIDA = "INDEFINIDO"   # sem rótulo ou rótulo com "?" na classificação

# ---------------------------------------------------------------------------
# RÓTULOS DE EXIBIÇÃO  —  o CSV fala a língua do pipeline; a tela, a do cliente.
# Camada de tradução, não renomeação na origem: a classificação v1.0 continua
# carimbando "GO" em toda saída do motor, e o Mov 4 (que ratificou a separação
# GO × Ginecologia) segue válido sem revalidar nada.
#
# Por que "GO" não podia ficar: é a SIGLA DA PRÓPRIA ESPECIALIDADE, e o seletor
# logo acima dela lê "Ginecologia & Obstetrícia". Lidos em sequência, sugerem
# que a área é a especialidade inteira — quando o que "GO" significa é atuar nas
# duas frentes. Mesmo mecanismo que já traduzia INDEFINIDO para
# "Classificação pendente"; ele existia e não tinha sido aplicado aos demais.
#
# Área ausente do mapa aparece com o rótulo da classificação, sem tradução.
# ---------------------------------------------------------------------------
ROTULOS_AREA = {
    "GO": "Ginecologia e Obstetrícia",
    AREA_INDEFINIDA: "Classificação pendente",
}

# Perfil de cada área numa linha, para o `title` da opção do seletor: o rótulo
# diz o nome, o perfil diz o que distingue a área das vizinhas.
#
# QUALITATIVO de propósito, sem número. A caracterização vem da medição
# (jul/2026: ultrassonografia obstétrica em 98% dos comparáveis de GO contra 38%
# em Ginecologia; sub_alto_risco em 10 de GO contra 1 de Ginecologia) e do
# critério do Mov 4, mas percentual escrito aqui não recalcula quando o analista
# muda a janela — número na tela tem de sair do motor, sempre.
PERFIS_AREA = {
    "Ginecologia": "Predomínio ginecológico; parte também acompanha gestação.",
    "GO": "Atua nas duas frentes: ginecologia e obstetrícia, inclusive gestação "
          "de alto risco.",
    "Obstetrícia": "Predomínio obstétrico.",
    "Mastologia": "Mama.",
    "Reprodução": "Reprodução humana.",
    "Ultrassonografista": "Perfil de execução: lauda exames, não os solicita.",
    "Geral": "Perfil de solicitação fora do escopo da especialidade; "
             "em triagem clínica.",
    AREA_INDEFINIDA: "Sem área de atuação atribuída: fora de comparação.",
}

# Versão/status da classificação injetada — carimbo em TODA saída do pipeline
# e em toda tela (léxico: governança visível). Homologação clínica PENDENTE.
# DECISÃO 2026-08-14: o status de homologação NÃO aparece para o usuário — o
# carimbo diz só a versão. O status vive na documentação (LEIAME da
# classificação e Nota Metodológica), não na tela.
CLASSIFICACAO_VERSAO = "v1.0"
CLASSIFICACAO_HOMOLOGADA = False

# Divergências rótulo do médico × estatística, roteadas de volta ao médico
# (notebook §13.4): aparecem na UI esmaecidos, "classificação em revisão" —
# artefato de classificação, não achado.
COOPERADOS_CLASSIFICACAO_EM_REVISAO = ("cooperado_61", "cooperado_97", "cooperado_110")

# Perfil de solicitação FORA DO ESCOPO da especialidade classificada — mesma
# fila de triagem clínica das divergências acima, motivo diferente.
# cooperado_112 está classificado como "Geral" dentro de Ginecologia &
# Obstetrícia, mas o que ele solicita é clínica geral: patologia
# osteomioarticular, teste ergométrico, audiometria tonal, prova de função
# pulmonar. Nenhum procedimento ginecológico ou obstétrico na lista.
# Levantado em 31/jul/2026. Possível erro de classificação, não achado sobre o
# cooperado.
#
# ATENÇÃO ao alcance desta lista: ela REGISTRA o motivo, não exclui ninguém.
# Quem forma a referência é decidido por `elegivel_norma` no CSV da
# classificação, e cooperado_112 tem `elegivel_norma=True`. O motivo só aparece
# na tela quando o cooperado JÁ está fora da construção da referência — é o que
# acontece hoje com cooperado_110 e NÃO acontece com cooperado_61 nem
# cooperado_97, que estão na fila acima e não aparecem em lugar nenhum.
# Tornar a fila visível por si exige uma superfície que o app ainda não tem
# (ver PENDENCIAS.md).
COOPERADOS_PERFIL_FORA_DA_ESPECIALIDADE = ("cooperado_112",)

# ---------------------------------------------------------------------------
# ALERTA DE PERFIL MASCULINO  —  regra PROVISÓRIA da classificação v1.0
# O alerta marca cooperado com fração atípica de pacientes homens. Em
# especialidades cuja prática inclui o paciente masculino POR DESENHO, ele é
# FALSO POSITIVO PREVISÍVEL — assinatura da especialidade, não anomalia:
#   Reprodução -> espermograma (o paciente É o homem).
# Nessas áreas o cooperado continua fora da CONSTRUÇÃO da norma (a regra v1.0
# ainda vigora e não se burla regra em silêncio), mas a UI exibe o status de
# triagem clínica pendente — é esse status que alimenta o loop de correção da
# classificação. Lista revisada na homologação clínica.
# ---------------------------------------------------------------------------
ESPECIALIDADES_PACIENTE_MASCULINO_ESPERADO = ("Reprodução",)


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
    "Ginecologia": None,
    "GO": None,
    "Mastologia": None,
    "Obstetrícia": None,
    "Reprodução": None,
    "Ultrassonografista": None,
    "Geral": None,
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
# EXCLUSÃO POR PAR (Mov 5)  —  DECISÃO (PROVISÓRIO)  —  notebook §13.3
# Portadores de sub-perfil não FORMAM a norma dos pares (área, procedimento)
# onde o teste de distorção mostrou movimento >15% da mediana; seguem MEDIDOS.
# Ativado: sub_alto_risco em GO (cesta trombofilia/vitalidade fetal, mediana
# −25 a −40% sem portadores) e sub_opera em Ginecologia (os 2 pares que moveram
# >15%). As cestas são regex sobre DS_PROCEDIMENTO (resolvidas em códigos pelo
# construtor montar_exclusao_por_par em app/utils/pipeline.py).
# Limiares PROVISÓRIOS — o teste re-roda na homologação e confirma/ajusta.
# ---------------------------------------------------------------------------
RGX_CESTA_ALTO_RISCO = (
    r"Anticardiolipina|Anticoagulante Lúpico|Obstétrica Com Doppler"
    r"|Perfil Biofísico|Cardiotocografia Anteparto"
)
RGX_CESTA_OPERA = r"Procedimento Diagnóstico Em Peça|Tempo De Tromboplastina"
EXCLUSOES_SUBPERFIL = (
    ("sub_alto_risco", "GO", RGX_CESTA_ALTO_RISCO),
    ("sub_opera", "Ginecologia", RGX_CESTA_OPERA),
)
LIMIAR_DISTORCAO_EXCLUSAO = 0.15   # PROVISÓRIO, movimento de mediana que ativa exclusão

# ---------------------------------------------------------------------------
# O QUE CADA SUB-PERFIL MUDA NA COMPARAÇÃO  —  hover do badge na tabela
# Uma frase por sub-perfil. O badge é IDENTIDADE (espec funcional, regra 2) e
# nunca subdivide a régua; o que ele muda, quando muda, é a formação da norma em
# UMA cesta de procedimentos — e é exatamente isso que quem lê a tabela não tem
# como adivinhar de um rótulo de duas palavras.
#
# Dois tipos de frase, e a diferença importa:
#   · sub-perfil COM exclusão ativa (EXCLUSOES_SUBPERFIL acima): diz que ele
#     forma a referência, exceto na cesta, e que o limiar está em validação;
#   · sub-perfil INFORMATIVO: diz que não muda cálculo nenhum, para ninguém
#     supor que muda.
# ---------------------------------------------------------------------------
AJUDA_SUBPERFIL = {
    "sub_opera": (
        "Integra o cálculo da referência da área, exceto nos procedimentos "
        "próprios do perfil cirúrgico (peça cirúrgica, pré-operatório). "
        "Exclusão aplicada apenas onde há evidência de distorção; limiar em "
        "validação clínica."
    ),
    "sub_alto_risco": (
        "Integra o cálculo da referência da área, exceto nos procedimentos "
        "próprios do acompanhamento de alto risco (trombofilia, vitalidade "
        "fetal), em Ginecologia e Obstetrícia. Exclusão aplicada apenas onde "
        "há evidência de distorção; limiar em validação clínica."
    ),
    "sub_plantao_ps": (
        "Informativo. Os atendimentos de pronto socorro já são excluídos do "
        "cálculo para todos os cooperados."
    ),
    "sub_ptgi": (
        "Informativo. Identifica a prática e não altera o cálculo da "
        "referência."
    ),
    "sub_ultrassonografista": (
        "Atua no lado da execução, enquanto a referência mede solicitação. "
        "Por isso não integra o cálculo da referência da área."
    ),
}

# Nome da CESTA de cada sub-perfil, para o hover da etiqueta "perfil explica a
# origem". A composição da cesta é a regex em EXCLUSOES_SUBPERFIL; aqui fica só
# como ela se chama em português.
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

CESTA_SUBPERFIL = {
    "sub_opera": "peça cirúrgica e pré-operatório",
    "sub_alto_risco": "trombofilia e vitalidade fetal",
}


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
SMOKE_MEDIANA_GINECOLOGIA = 5.25
SMOKE_N_NA_NORMA_GINECOLOGIA = 58                  # elegíveis que formam a norma
SMOKE_N_TOTAL_GINECOLOGIA = 64
# As 4 previsões do notebook §13.4 rodam sobre posicao_proc COM OS TRÊS PORTÕES
# (avaliavel & apresentavel & sinalizado — pipeline.filtrar_sinalizados), NÃO sobre
# o agregado: são pares (cooperado, procedimento). Positivos trazem a contagem de
# procedimentos sinalizados; negativos exigem zero.
SMOKE_SINALIZADOS_ESPERADOS = {"cooperado_85": 75, "cooperado_71": 97}
SMOKE_NAO_SINALIZADOS_ESPERADOS = ("cooperado_31", "cooperado_116")
# Referência agregada da MESMA janela (notebook §9, bloco "ANO"): avaliáveis e o
# topo por razão — ancoram a migração no lado agregado, não só na norma.
SMOKE_N_AVALIAVEIS = 132
SMOKE_TOPO_RAZAO = ("cooperado_71", "cooperado_85", "cooperado_19")
