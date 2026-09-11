"""blocos, monta os BLOCOS DA TELA "Área de atuação" a partir da saída dos motores.

Esta camada não calcula nada (Lei 1): ela LÊ o resultado do pipeline canônico e
o reorganiza no formato que cada bloco do contrato visual consome. Cada função
daqui corresponde a um componente do guia visual (Claude Design, projeto
"Medyx - Style tile Enterprise", ver CLAUDE.md § Contrato visual):

    composicao_referencia  -> §08 "Barra de composição segmentada" (+ excluídos)
    contexto_da_area       -> linha de texto sob o título; ocupou o lugar da
                              §08 "Faixa de estatísticas" em 2026-08-19
    distribuicao           -> §05 "Distribuição do índice de solicitação",
                              em três medidas alternáveis na tela
    linhas_cooperados      -> §04 "Cooperados da área" (tabela + régua de posição)
    linhas_procedimentos   -> aba "Procedimentos"

Regra de formatação: todo número viaja em DOIS campos, o valor cru (para
ordenar/plotar) e o `_fmt` já em pt-BR (vírgula decimal, ponto de milhar).
O front imprime; não converte, não arredonda, não calcula.

Geometria: as posições da régua e do gráfico (`pos_pct`) são calculadas AQUI,
em Python, pela mesma razão, JavaScript não faz conta, nem de layout de dado.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

import config
from utils import apresentacao as apr
from utils import cascata
from utils import dados
from utils.pipeline import filtrar_sinalizados, norma_por_area

# Estados de uma área — governam o que a tela pode mostrar (espec funcional, regra 5).
# Cada um tem tratamento visual próprio no guia; nenhum é silencioso.
#
# Área SEM NENHUM formador de norma (Ultrassonografia, Patologia) NÃO é um
# quarto estado: o tratamento de tela é idêntico ao de grupo pequeno em tudo que
# importa — sem gráfico, sem percentil, sem sinalização, lista com posto. Um
# estado a mais obrigaria o usuário a aprender outra regra para algo que se
# comporta igual. A distinção vive na BARRA DE COMPOSIÇÃO (0 formam a referência)
# e no motivo por cooperado; só a frase de apoio muda (campo `variante`).
ESTADO_PLENA = "plena"                    # >= N_MINIMO_P90 formadores: P90 sustentado
ESTADO_AJUSTADA = "criterio_ajustado"     # 10–19: degrada a P75, com ressalva (§07 caveat-box)
ESTADO_INSUFICIENTE = "grupo_insuficiente"  # < N_MINIMO_P75 formadores (inclusive zero)
ESTADO_SEM_PEER_GROUP = "sem_peer_group"  # INDEFINIDO: fora de qualquer comparação

VARIANTE_GRUPO_PEQUENO = "grupo_pequeno"        # 1–9 formadores
VARIANTE_SEM_FORMADORES = "sem_formadores"      # zero formadores


# ─────────────────────────────────────────────────────────────────────────────
# Catálogo de motivos — por que um cooperado não forma a referência
# ─────────────────────────────────────────────────────────────────────────────
# O motivo é OBRIGATÓRIO e precisa distinguir naturezas opostas:
#   definitiva — exclusão por desenho da análise; não há o que corrigir;
#   provisoria — exclusão por regra da classificação v2.0 ainda em validação
#                clínica; a pendência aparece na tela e alimenta o loop de
#                correção da classificação (o app não esconde a pendência).
# Nenhum destes cooperados sai da análise: seguem MEDIDOS contra a referência.

MOTIVO_EXECUCAO = "perfil_execucao"
MOTIVO_ALERTA_MASCULINO = "alerta_perfil_masculino"
MOTIVO_CONFIANCA_BAIXA = "confianca_baixa"
MOTIVO_CLASSIFICACAO_PENDENTE = "classificacao_pendente"
MOTIVO_VOLUME = "volume_abaixo_do_minimo"

_CATALOGO_MOTIVOS = {
    MOTIVO_EXECUCAO: {
        "rotulo": "perfil de execução: realiza mais do que solicita",
        "natureza": "definitiva",
        "detalhe": ("A execução (ultrassonografia, citopatologia) é a prática "
                    "principal; a referência mede solicitação. Exclusão por "
                    "desenho da análise: não é achado sobre o cooperado, e não "
                    "há classificação a corrigir."),
    },
    MOTIVO_ALERTA_MASCULINO: {
        "rotulo": "cadastro agregado (pacientes homens)",
        "natureza": "provisoria",
        "detalhe": ("Um quarto ou mais das pacientes são homens: o cadastro "
                    "parece agregar mais de um profissional, e a solicitação "
                    "não descreve uma prática ginecológica. Confirmação "
                    "pendente com a operadora."),
    },
    MOTIVO_CONFIANCA_BAIXA: {
        "rotulo": "confiança baixa da classificação",
        "natureza": "provisoria",
        "detalhe": ("Menos de 100 consultas com pedido no período: a área foi "
                    "atribuída com confiança baixa e, até a validação, o "
                    "cooperado não define a referência."),
    },
    MOTIVO_CLASSIFICACAO_PENDENTE: {
        "rotulo": "sem área de atuação",
        "natureza": "provisoria",
        "detalhe": ("Sem área principal: volume insuficiente ou prática pouco "
                    "visível nas solicitações. Sem cooperados contra quem "
                    "comparar, fora de comparação."),
    },
    MOTIVO_VOLUME: {
        "rotulo": "volume abaixo do mínimo para avaliação",
        "natureza": "definitiva",
        "detalhe": ("Consultas insuficientes na janela para a taxa ser confiável. "
                    "Não é juízo sobre a prática: é o piso amostral."),
    },
}


def _motivo(codigo: str, detalhe_extra: str | None = None,
            revisao: dict | None = None) -> dict:
    base = dict(_CATALOGO_MOTIVOS[codigo])
    base["codigo"] = codigo
    if detalhe_extra:
        base["detalhe"] = detalhe_extra
    base["revisao"] = revisao
    return base


def motivos_por_cooperado(classificacao: pd.DataFrame) -> dict[str, list[dict]]:
    """ID_COOPERADO -> motivos estruturados de não formar a referência.

    Os motivos são os da regra de `elegivel_norma` da dim v2, na mesma ordem
    em que a regra os aplica; cada um carrega a natureza (definitiva por desenho,
    ou provisória e pendente de confirmação). O cadastro agregado viaja com o
    status de triagem pendente que alimenta o loop de correção da classificação.
    """
    saida: dict[str, list[dict]] = {}
    for _, linha in classificacao.iterrows():
        coop = linha["ID_COOPERADO"]
        motivos = []
        if linha.get("especialidade") == config.AREA_INDEFINIDA:
            motivos.append(_motivo(
                MOTIVO_CLASSIFICACAO_PENDENTE,
                detalhe_extra=(f"Situação na classificação: {linha['situacao']}. "
                               "Sem área principal, sem cooperados contra quem "
                               "comparar: fora de comparação."),
            ))
        if linha.get("execucao_principal"):
            motivos.append(_motivo(MOTIVO_EXECUCAO))
        if linha.get("alerta_perfil_masculino"):
            motivos.append(_motivo(MOTIVO_ALERTA_MASCULINO, revisao={
                "pendente": True,
                "rotulo": "confirmação pendente",
                "falso_positivo_previsivel": False,
                "acao": ("confirmar com a operadora se o cadastro agrega mais "
                         "de um profissional; alimenta o loop de correção da "
                         "classificação"),
            }))
        if linha.get("confianca") == "baixa":
            motivos.append(_motivo(MOTIVO_CONFIANCA_BAIXA))
        saida[coop] = motivos
    return saida


# ─────────────────────────────────────────────────────────────────────────────
# Formatação pt-BR (o front imprime a string pronta)
# ─────────────────────────────────────────────────────────────────────────────

def fmt(valor, casas: int = 2) -> str:
    """Número em pt-BR: vírgula decimal, ponto de milhar. None/NaN -> travessão
    (guia §07: "o campo mostra travessão, nunca zero")."""
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return config.SEM_MEDIDA
    s = f"{valor:,.{casas}f}"
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def fmt_taxa(valor) -> str:
    """Taxa de solicitação por consulta, legível também quando RARA.

    Com 2 casas decimais, toda taxa abaixo de 0,005 vira "0,00" na tela e lê
    como régua zero — e em Ginecologia isso era MAIS DA METADE da aba
    Procedimentos (129 referências sólidas). Abaixo de 0,01, a taxa é expressa
    POR MIL consultas ("1,3 por mil"), forma padrão de utilização rara.
    """
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return config.SEM_MEDIDA
    v = float(valor)
    if 0 < v < 0.01:
        return f"{fmt(v * 1000, 1)} por mil"
    return fmt(v)


def fmt_frequencia(valor) -> str:
    """Frequência de solicitação POR CONSULTA, com casas que sustentam a razão.

    Frequência e Referência ficam lado a lado com a Razão entre elas, e a razão
    é a divisão das duas. Com 2 casas fixas, 0,3864 e 0,0161 viram "0,39" e
    "0,02", cuja divisão dá 19,5 enquanto a coluna ao lado diz 24,1× — as três
    células se contradizem na mesma linha, e é a linha inteira que perde
    credibilidade.

    O número de casas ACOMPANHA A GRANDEZA, em vez de ser um degrau só em 0,1.
    Com três casas fixas abaixo de 0,1, uma referência de 0,0038 saía "0,004" e
    a divisão errava 6% — o bastante para a razão ao lado parecer outra conta.
    Cada faixa mantém três algarismos significativos, que é o que a divisão
    precisa para fechar em qualquer escala de raridade.
    """
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return config.SEM_MEDIDA
    v = float(valor)
    if 0 < v < 0.0001:
        return "< 0,0001"
    # TRÊS ALGARISMOS SIGNIFICATIVOS em toda a escala, inclusive acima de 0,1.
    # Com duas casas ali, 0,1755 saía "0,18" e a divisão pela referência errava
    # até 6% — "0,18 ÷ 0,012" lê 15,0 sob uma coluna que diz 14,1×. Era a mesma
    # falha que a faixa abaixo de 0,01 já tinha, um degrau acima.
    #
    # Efeito colateral bem-vindo: frequência e referência passam a ser impressas
    # com a MESMA precisão. Antes "0,18" ficava ao lado de "0,012" na mesma
    # linha, e duas precisões diferentes numa comparação sugerem que uma das
    # duas foi medida com mais cuidado.
    if v >= 1:
        return fmt(v, 2)
    if v >= 0.1:
        return fmt(v, 3)
    # QUATRO casas nesta faixa, e não três: 0,0117 com três saía "0,012", que
    # são DOIS algarismos significativos, e a divisão errava 3% — "0,130 ÷
    # 0,012" lê 10,8 sob uma coluna que diz 11,1×. É a mesma falha das outras
    # faixas, na única banda que ainda a tinha.
    if v >= 0.01:
        return fmt(v, 4)
    return fmt(v, 4) if v >= 0.001 else fmt(v, 5)


def fmt_por_mil(valor) -> str:
    """Taxa em solicitações POR MIL consultas, casas conforme a grandeza.

    Uma unidade só para a coluna inteira (decisão 2026-08-14, dossiê): misturar
    "0,39" e "1,3 por mil" na mesma coluna obrigava o leitor a trocar de unidade
    linha a linha. A unidade é declarada UMA vez, no cabeçalho da coluna.
    """
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return config.SEM_MEDIDA
    v = float(valor) * 1000
    return fmt(v, 1 if v < 10 else 0)


def _maior_resto(fracoes: list[float]) -> list[int]:
    """Frações 0–1 -> inteiros por cento que SOMAM exatamente 100.

    Arredondar cada fatia isolada não fecha a composição: seis fatias com parte
    fracionária alta viram 101%, e o leitor procura a sétima que não existe.
    Maior resto é o método padrão para isso (o mesmo de repartição de cadeiras):
    todos recebem a parte inteira, e as unidades que sobram vão para quem tem a
    maior parte fracionária.

    Só se aplica onde as fatias formam um TODO. Percentual solto (cobertura,
    participação de um procedimento no total do cooperado) continua em `fmt_pct`:
    ali não há soma para fechar, e forçar uma mudaria o número.
    """
    if not fracoes:
        return []
    total = sum(fracoes)
    if not total:
        return [0] * len(fracoes)
    exatos = [f / total * 100 for f in fracoes]
    base = [int(v) for v in exatos]
    sobra = 100 - sum(base)
    ordem = sorted(range(len(exatos)), key=lambda i: exatos[i] - base[i],
                   reverse=True)
    for i in ordem[:max(0, sobra)]:
        base[i] += 1
    return base


def fmt_pct(fracao, casas: int = 0) -> str:
    """Fração 0–1 -> percentual pt-BR ('0.586' -> '59%')."""
    if fracao is None or (isinstance(fracao, float) and np.isnan(fracao)):
        return config.SEM_MEDIDA
    return f"{fmt(fracao * 100, casas)}%"


def fmt_reais(valor) -> str:
    """Valor monetário na regra do guia (§ formatos): R$ ABREVIADO, 1 CASA.

        2.869.260 -> "R$ 2,9 mi"
          384.000 -> "R$ 384 mil"
              950 -> "R$ 950"

    O guia é explícito: "R$ abreviado, 1 casa · R$ 1,2 mi · Abaixo de 1 milhão:
    R$ 384 mil · valor exato só no dossiê". Sete dígitos numa linha de apoio de
    11px não se leem — o que a tela precisa dar é a ORDEM DE GRANDEZA, e o valor
    ao centavo pertence ao dossiê, onde se contesta caso a caso.
    """
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return config.SEM_MEDIDA
    v = float(valor)
    if abs(v) >= 1_000_000:
        return f"R$ {fmt(v / 1_000_000, 1)} mi"
    if abs(v) >= 1_000:
        return f"R$ {fmt(v / 1_000, 0)} mil"
    return f"R$ {fmt(v, 0)}"


def fmt_reais_exato(valor) -> str:
    """Valor monetário SEM abreviar: 11.440 -> "R$ 11.440".

    `fmt_reais` abrevia para dar ordem de grandeza, e é o certo numa faixa de
    KPI ou numa barra de Pareto, onde o que se compara é o porte. Ele NÃO serve
    quando dois números do mesmo bloco precisam ser distinguidos entre si.

    O caso que obrigou a separação (set/2026): cooperado_19 no exame 40316378
    pede 40 vezes a referência da área, então 97,7% do custo dele está acima
    dela. Custo do trimestre R$ 11.440, parcela acima da referência R$ 11.176 —
    dois números diferentes que `fmt_reais` imprimia como "R$ 11 mil" e
    "R$ 11 mil", um ao lado do outro na mesma grade, e numa frase que saía
    autocontraditória: "R$ 11 mil em custo, dos quais R$ 11 mil acima da
    referência". O leitor conclui que a régua está zerada; ela não está.

    O guia já previa isto ao definir a abreviação: "valor exato só no dossiê".
    O painel do procedimento é dossiê, e é aqui que o exato entra.

    Sem centavos: é total, não preço unitário (esse é `fmt_reais_unitario`).
    """
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return config.SEM_MEDIDA
    return f"R$ {fmt(float(valor), 0)}"


def fmt_reais_unitario(valor) -> str:
    """Valor monetário POR CONSULTA: R$ com centavos, sem abreviar.

    `fmt_reais` abrevia e arredonda ao real porque foi escrito para TOTAIS, onde
    sete dígitos numa linha de apoio de 11px não se leem e o que importa é a
    ordem de grandeza. Preço unitário é o caso oposto: vive entre zero e algumas
    centenas, e arredondar ao real inteiro apaga a parte BAIXA da distribuição,
    onde R$ 0,40 vira "R$ 0" e passa a ler como ausência de custo. É a mesma
    armadilha que `fmt_taxa` resolve para taxas raras, e a mesma distinção que o
    ajuste 4 do CLAUDE.md existe para proteger: ausência não é zero.
    """
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return config.SEM_MEDIDA
    return f"R$ {fmt(valor, 2)}"


def slug(area: str) -> str:
    """Nome da área -> id de URL, sem acento ('Obstetrícia' -> 'obstetricia')."""
    import unicodedata
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", area)
        if unicodedata.category(c) != "Mn"
    )
    return sem_acento.lower().replace(" ", "-")


# ─────────────────────────────────────────────────────────────────────────────
# Estado da área — decide o que a tela PODE mostrar
# ─────────────────────────────────────────────────────────────────────────────

def estado_area(area: str, n_formam_norma: int, gatilho_usado: str | None,
                gatilho_pedido: str) -> dict:
    """Classifica a área numa das camadas por n (espec funcional, regra 5).

    Devolve código, se é comparável, e os textos que o guia exige em cada
    estado, inclusive a ressalva metodológica (§07 caveat-box) quando o
    critério foi degradado pelo tamanho do grupo.
    """
    if area == config.AREA_INDEFINIDA:
        return {
            "codigo": ESTADO_SEM_PEER_GROUP, "variante": None, "comparavel": False,
            "tem_distribuicao": False, "tem_percentil": False,
            "titulo": "Sem área de atuação",
            "frase_apoio": "classificação de área de atuação pendente",
            "descricao": ("Classificação de área de atuação pendente. Análises "
                          "comparativas não são aplicáveis; a leitura abaixo é "
                          "descritiva, por cooperado."),
            "ressalva": None,
        }
    if gatilho_usado is None:
        # mesmo estado do guia (grupo insuficiente): sem gráfico, sem percentil,
        # sem sinalização, posto descritivo. Zero formadores só troca a frase —
        # a distinção real está na barra de composição e no motivo por cooperado.
        sem_formadores = n_formam_norma == 0
        return {
            "codigo": ESTADO_INSUFICIENTE,
            "variante": VARIANTE_SEM_FORMADORES if sem_formadores
                        else VARIANTE_GRUPO_PEQUENO,
            "comparavel": False,
            "tem_distribuicao": False, "tem_percentil": False,
            "titulo": "Cooperados insuficientes na área para análise comparativa",
            "frase_apoio": (
                "sem referência: nenhum cooperado desta área forma a norma, "
                "motivos abaixo" if sem_formadores else
                "cooperados insuficientes na área para análise comparativa"),
            "descricao": (
                ("Nenhum cooperado desta área forma a referência nesta janela, "
                 "não há norma contra a qual medir. A barra de composição mostra "
                 "por que, cooperado a cooperado. A leitura abaixo é descritiva: "
                 "posição como posto, sem percentil e sem sinalização.")
                if sem_formadores else
                (f"A referência foi construída com {n_formam_norma} "
                 f"cooperado(s) elegível(is), abaixo de {config.N_MINIMO_P75}. "
                 "Percentil e critério de revisão não são exibidos: a posição "
                 "aparece como posto descritivo, e ninguém é sinalizado.")),
            "ressalva": {
                "titulo": ("nenhum solicitante elegível na área"
                           if sem_formadores else
                           f"n<{config.N_MINIMO_P75} solicitantes na área"),
                "detalhe": ("Sem formadores, não existe percentil nem critério de "
                            "revisão para esta área, só leitura descritiva."
                            if sem_formadores else
                            f"Estatística de {n_formam_norma} observações não "
                            "sustenta encaminhamento a comitê, serve a triagem "
                            "interna."),
                "tags": [f"n={n_formam_norma}", "sem critério de revisão"],
            },
        }
    if gatilho_usado != gatilho_pedido:
        return {
            "codigo": ESTADO_AJUSTADA, "variante": None, "comparavel": True,
            "frase_apoio": "critério ajustado ao tamanho do grupo",
            "tem_distribuicao": True, "tem_percentil": True,
            "titulo": "Critério ajustado ao tamanho do grupo",
            "descricao": (f"O grupo tem {n_formam_norma} elegíveis, abaixo de "
                          f"{config.N_MINIMO_P90}, que é o mínimo para sustentar "
                          f"{gatilho_pedido.upper()}. O critério vigente é "
                          f"{gatilho_usado.upper()}."),
            "ressalva": {
                "titulo": f"n<{config.N_MINIMO_P90} solicitantes na área",
                "detalhe": (f"Os percentis são exibidos com ressalva: com "
                            f"{n_formam_norma} elegíveis, {gatilho_pedido.upper()} "
                            "seria sorteio, não régua."),
                "tags": [f"n={n_formam_norma}",
                         f"critério ajustado {gatilho_usado.upper()}"],
            },
        }
    return {
        "codigo": ESTADO_PLENA, "variante": None, "comparavel": True,
        "tem_distribuicao": True, "tem_percentil": True,
        "titulo": None, "frase_apoio": None, "descricao": None, "ressalva": None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# §08 — Barra de composição segmentada (+ excluídos com nome e motivo)
# ─────────────────────────────────────────────────────────────────────────────

def composicao_referencia(posicao_area: pd.DataFrame, classificacao: pd.DataFrame,
                          piso_aplicado: int) -> dict:
    """Quem forma a referência, quem não forma e POR QUÊ.

    Três segmentos disjuntos que somam o total da área (guia §08):
      formam a norma          = avaliável E elegivel_norma
      abaixo do volume mínimo = ~avaliável (consultas < piso da janela)
      fora da construção      = avaliável E ~elegivel_norma

    'Fora da construção' NÃO é exclusão da análise: esses cooperados seguem
    MEDIDOS contra a referência, apenas não a definem (CLAUDE.md, lei da norma).
    """
    p = posicao_area
    eleg = p["elegivel_norma"].astype(bool)
    m_formam = p["avaliavel"] & eleg
    m_abaixo = ~p["avaliavel"]
    m_fora = p["avaliavel"] & ~eleg

    catalogo = motivos_por_cooperado(classificacao)
    excluidos = []
    for idx, linha in p[m_abaixo | m_fora].sort_values(
            "consultas_totais", ascending=False).iterrows():
        coop = linha["ID_COOPERADO"]
        if m_abaixo.loc[idx]:
            grupo = "abaixo_volume_minimo"
            motivos = [_motivo(MOTIVO_VOLUME, detalhe_extra=(
                f"{int(linha['consultas_totais'])} consultas na janela, abaixo "
                f"do mínimo de {piso_aplicado} para a taxa ser confiável."))]
        else:
            grupo = "fora_da_construcao"
            motivos = catalogo.get(coop) or [
                {"codigo": "nao_elegivel", "rotulo": "não elegível para formar a "
                 "referência", "natureza": "provisoria", "detalhe": None,
                 "revisao": None}]
        revisao_pendente = any(m["revisao"] for m in motivos)
        excluidos.append({
            "id": coop, "grupo": grupo,
            "motivos": motivos,
            "motivo": " · ".join(m["rotulo"] for m in motivos),   # linha da tabela
            "natureza": ("definitiva"
                         if all(m["natureza"] == "definitiva" for m in motivos)
                         else "provisoria"),
            # o código é para máquina; a tela imprime o rótulo (léxico)
            "natureza_rotulo": ("definitiva · por desenho da análise"
                                if all(m["natureza"] == "definitiva" for m in motivos)
                                else "provisória · regra em validação"),
            "revisao_pendente": revisao_pendente,
            "em_revisao": revisao_pendente,   # compat: esmaecimento na UI
            "consultas": int(linha["consultas_totais"]),
            "consultas_fmt": fmt(linha["consultas_totais"], 0),
            "medido_contra_a_referencia": grupo == "fora_da_construcao",
        })

    n_formam, n_abaixo, n_fora = int(m_formam.sum()), int(m_abaixo.sum()), int(m_fora.sum())
    return {
        "total": len(p),
        "segmentos": [
            {"chave": "formam_norma", "n": n_formam, "classe": "cb-a",
             "rotulo": f"{n_formam} formam a referência"},
            {"chave": "abaixo_volume_minimo", "n": n_abaixo, "classe": "cb-b",
             "rotulo": f"{n_abaixo} abaixo do volume mínimo"},
            {"chave": "fora_da_construcao", "n": n_fora, "classe": "cb-c",
             "rotulo": f"{n_fora} fora da construção da referência"},
        ],
        "excluidos": excluidos,
        "revisao_pendente": sum(1 for e in excluidos if e["revisao_pendente"]),
        "nota": ("Quem não forma a referência segue medido contra ela, "
                 "apenas não a define."),
    }


# ─────────────────────────────────────────────────────────────────────────────
# §08 — Faixa de estatísticas (sem moldura, divisores de 1px)
# ─────────────────────────────────────────────────────────────────────────────

# Como cada alvo se chama na tela. O motor fala "mediana"/"p75"/"p90"; a faixa
# de estatísticas precisa da palavra que o leitor reconhece ao lado do R$.
ROTULO_ALVO = {"mediana": "mediana", "p75": "P75", "p90": "P90"}


# ─────────────────────────────────────────────────────────────────────────────
# RECORTE — quem está em cena
# ─────────────────────────────────────────────────────────────────────────────
#
# A REGRA (canônica, CLAUDE.md): o recorte muda QUEM ESTÁ EM CENA, nunca CONTRA
# QUEM SE MEDE. Régua parada, achado segue o filtro.
#
# Espelho de `RECORTES` em app/static/blocos/recorte.js: a mesma chave que viaja
# na URL, o mesmo predicado, sobre os MESMOS campos que a linha do cooperado já
# carrega (`avaliavel`, `grupos`, `sub_perfis`). Existir dos dois lados não é
# duplicação de regra: o front esconde LINHAS que já tem em mãos (ir ao servidor
# para ocultar uma linha seria absurdo), e o motor refaz o mesmo corte quando
# precisa REAGREGAR — somar excedente é cálculo, e cálculo não mora no
# JavaScript. Os dois concordam porque leem o mesmo campo, não porque repetem a
# mesma conta.
#
# O rótulo é SUBSTANTIVO no plural porque as frases que o usam pedem isso:
# "se os 39 persistentes convergissem", "excedente somado sobre: persistentes".
def _no_degrau(chave: str):
    """Predicado de um degrau da cascata: a linha do cooperado carrega em
    `grupos` todos os degraus que ele alcançou."""
    return lambda l: chave in (l.get("grupos") or ())


# A escada inteira, e não só dois degraus dela. Até 2026-08-19 a tela oferecia
# quatro recortes — Todos, Comparáveis, Persistentes, Qualificados — e os dois
# últimos eram o 3º e o 7º degrau de uma cascata de sete. O leitor via a lista
# cair de 39 para 21 sem nada que dissesse onde os 18 saíram.
#
# As CHAVES são de URL e falam a língua da tela; os degraus do motor
# (`confianca_calculavel`) ficam do lado de dentro — `?recorte=` viaja em link
# que se manda por e-mail.
#
# Os dois primeiros NÃO são degraus: são população (quem existe, quem tem
# volume). Ficam num grupo à parte no seletor, e é isso que impede a leitura de
# que "63 comparáveis" e o degrau de 63 são a mesma coisa — coincidem nesta
# janela, por acaso do dado.
_RECORTES: dict[str, tuple] = {
    "todos": (lambda l: True, "cooperados"),
    "comparaveis": (lambda l: bool(l.get("avaliavel")), "comparáveis"),
    "acima-do-criterio": (_no_degrau("acima_do_criterio"),
                          "com procedimento acima do critério"),
    "persistente": (_no_degrau("persistente"), "persistentes"),
    "material": (_no_degrau("material"), "materiais"),
    "classificacao-firme": (_no_degrau("classificacao_firme"),
                            "com classificação firme"),
    "sem-fator-de-contexto": (_no_degrau("sem_fator_de_contexto"),
                              "sem fator de contexto"),
    "qualificados": (_no_degrau("confianca_calculavel"), "qualificados"),
}

# Recorte desconhecido cai no mais amplo, como no front: chave inválida numa URL
# compartilhada deve mostrar tudo, nunca esvaziar a tela.
_RECORTE_PADRAO = "todos"


def ids_em_cena(linhas_coop: list[dict], recorte: str | None = None,
                perfis_flags: list[str] | None = None) -> list[str]:
    """Os ids dos cooperados EM CENA, pelo mesmo predicado que o front aplica.

    `perfis_flags` são as COLUNAS de classificação (o `flag` de
    `perfis_da_area`), não as chaves de URL — a tradução é de quem chama, que é
    quem tem a lista de perfis da área em mãos.

    Perfil é UNIÃO sobre o recorte, nunca interseção entre perfis: identidades
    se acumulam, e ninguém procura "quem opera E é de alto risco". Idêntico ao
    `emCena()` de area.js.
    """
    predicado = _RECORTES.get(recorte or _RECORTE_PADRAO,
                              _RECORTES[_RECORTE_PADRAO])[0]
    alvo = set(perfis_flags or ())
    saida = []
    for l in linhas_coop:
        if not predicado(l):
            continue
        if alvo and not any(sp.get("chave") in alvo
                            for sp in (l.get("sub_perfis") or ())):
            continue
        saida.append(l["id"])
    return saida


def rotulo_recorte(recorte: str | None,
                   perfis_rotulos: list[str] | None = None) -> str:
    """Como o recorte se chama nas frases da bancada. Os perfis entram depois do
    substantivo porque recortam POR CIMA dele: "qualificados · opera"."""
    base = _RECORTES.get(recorte or _RECORTE_PADRAO,
                         _RECORTES[_RECORTE_PADRAO])[1]
    return f"{base} · {', '.join(perfis_rotulos)}" if perfis_rotulos else base


def subtitulo_recorte(rotulo: str, n: int) -> str:
    """A declaração de população de um bloco de achado: sem ela, dois blocos da
    mesma tela somam conjuntos diferentes sem dizer qual é qual.

    Sobrou UM chamador, o rodapé da tabela de Procedimentos, e sobrou uma cópia:
    a função estava escrita duas vezes, palavra por palavra, e os dois Paretos
    da área deixaram de usá-la em set/2026. Lá a frase era a terceira aparição
    do mesmo fato na mesma dobra — o chip de Recorte imprime o recorte ativo com
    a contagem, e a Leitura da área abre com o mesmo conjunto —, e era ela que
    empurrava o gráfico para baixo.
    """
    return f"excedente somado sobre: {rotulo} ({fmt(n, 0)})"


def leitura_da_area(cards: list[dict], ids: list[str], n_comparaveis: int,
                    concentracao: str | None, n_nucleo: int | None,
                    n_sinalizados: int, n_com_excedente: int | None,
                    excedente_itens_area: float, excedente_reais_area: float | None,
                    itens_em_cena: float, reais_em_cena: float | None,
                    custo_total: float | None, n_procs_com_preco: int | None,
                    n_procs: int | None, referencia: float | None,
                    criterio: float | None, gatilho: str | None,
                    n_formam: int) -> dict:
    """A LEITURA DA ÁREA: o que a tela inteira produziu, num bloco.

    Substitui, na função de resumo, a faixa de cinco cards de KPI, que dava aos
    cinco números o mesmo peso: "cooperados no recorte" e "custo excedente"
    lado a lado, do mesmo tamanho, sem nada dizendo qual deles é o produto da
    tela. Aqui os mesmos números vêm agrupados pela pergunta que respondem, o
    excedente ganha o destaque que ele é, e duas linhas de prosa fecham com o
    que o número não diz sozinho.

    Nenhum número nasce aqui: `cards` já vem montado e este bloco o AGRUPA;
    concentração, excedente e régua vêm dos blocos que já os produzem.

    ── as duas linhas de prosa, e por que elas existem ────────────────────────
    A primeira ancora o recorte no todo: sem ela, "R$ 2,9 mi" com um recorte
    ativo lê como o dinheiro da área inteira.
    A segunda declara a RÉGUA e que ela não se move com o recorte. É a Lei 0 do
    projeto escrita na tela, no lugar exato onde alguém pode achar que filtrar
    mudou a comparação.
    """
    por_chave = {c["chave"]: c for c in (cards or [])}

    def _linha(chave, rotulo, valor_fmt=None, apoio=None, titulo=None):
        base = por_chave.get(chave) or {}
        return {"chave": chave, "rotulo": rotulo,
                "valor_fmt": valor_fmt or base.get("valor_fmt") or config.SEM_MEDIDA,
                "apoio": apoio,
                "titulo_longo": titulo or base.get("titulo_longo")}

    grupos = [
        {"rotulo": "Escopo em cena", "linhas": [
            _linha("cooperados", "cooperados no recorte"),
            _linha("_comparaveis", "com volume para comparação",
                   fmt(n_comparaveis, 0),
                   titulo=("Cooperados da área que atingem o volume mínimo de "
                           "consultas no período. É contra eles que a "
                           "comparação acontece.")),
        ]},
        {"rotulo": "Médias por consulta", "linhas": [
            _linha("sadt_por_consulta", "SADT"),
            _linha("custo_por_consulta", "custo"),
        ]},
        {"rotulo": "Solicitado no recorte", "linhas": [
            _linha("_custo_total", "custo total",
                   config.SEM_MEDIDA if custo_total is None else fmt_reais(custo_total),
                   apoio=(None if not n_procs_com_preco or not n_procs else
                          f"em {fmt(n_procs_com_preco, 0)} de {fmt(n_procs, 0)} "
                          f"procedimentos"),
                   titulo=("Valor de tudo que os cooperados em cena "
                           "solicitaram no período, a preços de referência "
                           "internos derivados das contas. Só entra "
                           "procedimento com preço apurado.")),
            _linha("_itens", "solicitações excedentes", fmt(itens_em_cena, 0),
                   titulo=("Solicitações a mais que a referência da área, "
                           "somadas procedimento a procedimento entre os pares "
                           "acima do "
                           "critério de cada um.")),
        ]},
    ]

    # O DESTAQUE: o número que a tela existe para produzir, e a fatia que ele
    # representa do que foi solicitado. Os dois têm a MESMA base (só pares com
    # preço), então a fração é legítima.
    fatia = ((reais_em_cena / custo_total)
             if reais_em_cena and custo_total else None)
    destaque = {
        "valor_fmt": (config.SEM_MEDIDA if reais_em_cena is None
                      else fmt_reais(reais_em_cena)),
        "apoio": ("de custo excedente no recorte"
                  + ("" if fatia is None else
                     f" · {fmt_pct(fatia)} do custo solicitado")),
    }

    notas = []
    if n_com_excedente is not None and excedente_reais_area:
        # DUAS frações, não uma: o recorte carrega uma fatia das SOLICITAÇÕES
        # excedentes e outra do VALOR excedente, e elas não coincidem — quem
        # está em cena não solicita ao preço médio da área. Uma porcentagem só,
        # pendurada nos dois números, afirmava do volume o que só valia para o
        # dinheiro. Quando as duas arredondam ao mesmo inteiro, uma frase basta.
        p_reais = (reais_em_cena / excedente_reais_area) if reais_em_cena else 0.0
        p_itens = ((itens_em_cena / excedente_itens_area)
                   if excedente_itens_area else None)
        if p_itens is not None and fmt_pct(p_itens) != fmt_pct(p_reais):
            fatia_txt = (f"Este recorte responde por {fmt_pct(p_itens)} das "
                         f"solicitações e {fmt_pct(p_reais)} do valor.")
        else:
            fatia_txt = f"Este recorte responde por {fmt_pct(p_reais)} do total."
        # "O excedente da área soma", e não "no total da área são": a área tem
        # 389 mil solicitações no período, e a frase anterior deixava o leitor
        # tomar as 133 mil excedentes por esse total.
        notas.append(
            f"{fmt(n_com_excedente, 0)} dos {fmt(n_comparaveis, 0)} comparáveis "
            f"da área têm excedente em algum procedimento. O excedente da área "
            f"soma {fmt(excedente_itens_area, 0)} solicitações e "
            f"{fmt_reais(excedente_reais_area)}. {fatia_txt}")
    if referencia is not None and criterio is not None and gatilho:
        notas.append(
            f"Referência de {fmt(referencia)} SADT por consulta e critério "
            f"{gatilho.upper()} em {fmt(criterio)}, formados pelos "
            f"{fmt(n_formam, 0)} cooperados que constroem a referência. "
            f"A régua não se move com o recorte.")

    return {"titulo": "Leitura da área",
            "frase": _frase_da_area(concentracao, n_nucleo, n_sinalizados),
            "grupos": grupos, "destaque": destaque, "notas": notas}


def _frase_da_area(concentracao: str | None, n_nucleo: int | None,
                   n_sinalizados: int) -> str | None:
    """O caso da ÁREA numa frase: onde está o dinheiro, e quantos destoam também
    no agregado. Duas afirmações, duas frases (padrão de redação, regra 2)."""
    partes = []
    if concentracao:
        partes.append(f"{concentracao[0].upper()}{concentracao[1:]}.")
    if n_sinalizados:
        partes.append(f"{fmt(n_sinalizados, 0)} estão acima do critério "
                      f"também no índice agregado.")
    return " ".join(partes) if partes else None


def cards_do_recorte(reais_por_coop: dict[str, float],
                     itens_por_coop: dict[str, float],
                     ids: list[str], rotulo: str,
                     n_comparaveis: int,
                     base_por_coop: dict[str, dict] | None = None) -> list[dict]:
    """Os cards abaixo dos chips: quem está em cena, o que ele pede e o excesso.

    Seguem o recorte (CLAUDE.md, lei 0: acima dos chips é a área, abaixo é a
    bancada). Um número por card.

    Os dois do meio são MAGNITUDE (o que uma consulta do recorte pede e custa);
    os dois últimos são DESVIO (quanto disso está acima da referência). Mesma
    ordem da tabela, para a página falar uma língua só.

    As médias são RAZÃO DE TOTAIS (soma dos itens ÷ soma das consultas), não
    média das razões individuais: a média das taxas daria o mesmo peso a quem
    fez 100 consultas e a quem fez 6.000.
    """
    em_cena = set(ids)
    itens = float(sum(v for c, v in itens_por_coop.items() if c in em_cena))
    reais = float(sum(v for c, v in reais_por_coop.items() if c in em_cena))
    base = [v for c, v in (base_por_coop or {}).items() if c in em_cena]
    consultas = float(sum(v.get("consultas") or 0 for v in base))
    sadt = float(sum(v.get("solicitacoes") or 0 for v in base))
    valor = float(sum(v.get("valor_total") or 0 for v in base))
    # sem consultas em cena não há denominador; card sai com SEM_MEDIDA em vez
    # de zero, que leria como "não pede nada"
    sadt_cons = sadt / consultas if consultas else None
    custo_cons = valor / consultas if consultas else None
    return [
        {"chave": "cooperados", "rotulo": "Cooperados no recorte",
         "valor": len(ids), "valor_fmt": fmt(len(ids), 0),
         # "comparáveis · de 63 comparáveis" seria a palavra duas vezes
         "apoio": (rotulo if rotulo == "comparáveis" else
                   f"{rotulo} · de {fmt(n_comparaveis, 0)} comparáveis"),
         "titulo_longo": None},
        {"chave": "sadt_por_consulta", "rotulo": "SADT por consulta",
         "valor": None if sadt_cons is None else round(sadt_cons, 2),
         "valor_fmt": config.SEM_MEDIDA if sadt_cons is None else fmt(sadt_cons),
         "apoio": "média do recorte",
         "titulo_longo": ("Solicitações divididas por consultas atendidas, "
                          "somando todos os cooperados em cena.")},
        {"chave": "custo_por_consulta", "rotulo": "Custo por consulta",
         "valor": None if custo_cons is None else round(custo_cons, 2),
         "valor_fmt": (config.SEM_MEDIDA if custo_cons is None
                       else fmt_reais(custo_cons)),
         "apoio": "média do recorte",
         "titulo_longo": ("Valor de tudo que se solicitou dividido pelas consultas "
                          "atendidas, a preços de referência internos derivados "
                          "das contas do período.")},
        {"chave": "itens", "rotulo": "Excesso de solicitações",
         "valor": itens, "valor_fmt": fmt(itens, 0),
         "apoio": "acima do padrão do grupo",
         "titulo_longo": None},
        {"chave": "reais", "rotulo": "Excesso em R$",
         "valor": round(reais, 2), "valor_fmt": fmt_reais(reais),
         # o apoio cabe em UMA linha: o pontilhado de hover sublinha o texto
         # inteiro, e em duas linhas ele risca o KPI de ponta a ponta. O custo
         # dos N exames é o que o card ao lado já diz; aqui fica a ressalva.
         "apoio": "acima da referência",
         "titulo_longo": (f"Custo das {fmt(itens, 0)} solicitações acima do padrão, "
                          "apurado procedimento a procedimento contra a "
                          "referência de cada "
                          "um.")},
    ]


# ─────────────────────────────────────────────────────────────────────────────
# §08 — Barra de composição segmentada (+ excluídos com nome e motivo)
# ─────────────────────────────────────────────────────────────────────────────

def composicao_referencia(posicao_area: pd.DataFrame, classificacao: pd.DataFrame,
                          piso_aplicado: int) -> dict:
    """Quem forma a referência, quem não forma e POR QUÊ.

    Três segmentos disjuntos que somam o total da área (guia §08):
      formam a norma          = avaliável E elegivel_norma
      abaixo do volume mínimo = ~avaliável (consultas < piso da janela)
      fora da construção      = avaliável E ~elegivel_norma

    'Fora da construção' NÃO é exclusão da análise: esses cooperados seguem
    MEDIDOS contra a referência, apenas não a definem (CLAUDE.md, lei da norma).
    """
    p = posicao_area
    eleg = p["elegivel_norma"].astype(bool)
    m_formam = p["avaliavel"] & eleg
    m_abaixo = ~p["avaliavel"]
    m_fora = p["avaliavel"] & ~eleg

    catalogo = motivos_por_cooperado(classificacao)
    excluidos = []
    for idx, linha in p[m_abaixo | m_fora].sort_values(
            "consultas_totais", ascending=False).iterrows():
        coop = linha["ID_COOPERADO"]
        if m_abaixo.loc[idx]:
            grupo = "abaixo_volume_minimo"
            motivos = [_motivo(MOTIVO_VOLUME, detalhe_extra=(
                f"{int(linha['consultas_totais'])} consultas na janela, abaixo "
                f"do mínimo de {piso_aplicado} para a taxa ser confiável."))]
        else:
            grupo = "fora_da_construcao"
            motivos = catalogo.get(coop) or [
                {"codigo": "nao_elegivel", "rotulo": "não elegível para formar a "
                 "referência", "natureza": "provisoria", "detalhe": None,
                 "revisao": None}]
        revisao_pendente = any(m["revisao"] for m in motivos)
        excluidos.append({
            "id": coop, "grupo": grupo,
            "motivos": motivos,
            "motivo": " · ".join(m["rotulo"] for m in motivos),   # linha da tabela
            "natureza": ("definitiva"
                         if all(m["natureza"] == "definitiva" for m in motivos)
                         else "provisoria"),
            # o código é para máquina; a tela imprime o rótulo (léxico)
            "natureza_rotulo": ("definitiva · por desenho da análise"
                                if all(m["natureza"] == "definitiva" for m in motivos)
                                else "provisória · regra em validação"),
            "revisao_pendente": revisao_pendente,
            "em_revisao": revisao_pendente,   # compat: esmaecimento na UI
            "consultas": int(linha["consultas_totais"]),
            "consultas_fmt": fmt(linha["consultas_totais"], 0),
            "medido_contra_a_referencia": grupo == "fora_da_construcao",
        })

    n_formam, n_abaixo, n_fora = int(m_formam.sum()), int(m_abaixo.sum()), int(m_fora.sum())
    return {
        "total": len(p),
        "segmentos": [
            {"chave": "formam_norma", "n": n_formam, "classe": "cb-a",
             "rotulo": f"{n_formam} formam a referência"},
            {"chave": "abaixo_volume_minimo", "n": n_abaixo, "classe": "cb-b",
             "rotulo": f"{n_abaixo} abaixo do volume mínimo"},
            {"chave": "fora_da_construcao", "n": n_fora, "classe": "cb-c",
             "rotulo": f"{n_fora} fora da construção da referência"},
        ],
        "excluidos": excluidos,
        "revisao_pendente": sum(1 for e in excluidos if e["revisao_pendente"]),
        "nota": ("Quem não forma a referência segue medido contra ela, "
                 "apenas não a define."),
    }


# ─────────────────────────────────────────────────────────────────────────────
# §08 — Faixa de estatísticas (sem moldura, divisores de 1px)
# ─────────────────────────────────────────────────────────────────────────────

# Como cada alvo se chama na tela. O motor fala "mediana"/"p75"/"p90"; a faixa
# de estatísticas precisa da palavra que o leitor reconhece ao lado do R$.
ROTULO_ALVO = {"mediana": "mediana", "p75": "P75", "p90": "P90"}


# ─────────────────────────────────────────────────────────────────────────────
# RECORTE — quem está em cena
# ─────────────────────────────────────────────────────────────────────────────
#
# A REGRA (canônica, CLAUDE.md): o recorte muda QUEM ESTÁ EM CENA, nunca CONTRA
# QUEM SE MEDE. Régua parada, achado segue o filtro.
#
# Espelho de `RECORTES` em app/static/blocos/recorte.js: a mesma chave que viaja
# na URL, o mesmo predicado, sobre os MESMOS campos que a linha do cooperado já
# carrega (`avaliavel`, `grupos`, `sub_perfis`). Existir dos dois lados não é
# duplicação de regra: o front esconde LINHAS que já tem em mãos (ir ao servidor
# para ocultar uma linha seria absurdo), e o motor refaz o mesmo corte quando
# precisa REAGREGAR — somar excedente é cálculo, e cálculo não mora no
# JavaScript. Os dois concordam porque leem o mesmo campo, não porque repetem a
# mesma conta.
#
# O rótulo é SUBSTANTIVO no plural porque as frases que o usam pedem isso:
# "se os 39 persistentes convergissem", "excedente somado sobre: persistentes".
def _no_degrau(chave: str):
    """Predicado de um degrau da cascata: a linha do cooperado carrega em
    `grupos` todos os degraus que ele alcançou."""
    return lambda l: chave in (l.get("grupos") or ())


# A escada inteira, e não só dois degraus dela. Até 2026-08-19 a tela oferecia
# quatro recortes — Todos, Comparáveis, Persistentes, Qualificados — e os dois
# últimos eram o 3º e o 7º degrau de uma cascata de sete. O leitor via a lista
# cair de 39 para 21 sem nada que dissesse onde os 18 saíram.
#
# As CHAVES são de URL e falam a língua da tela; os degraus do motor
# (`confianca_calculavel`) ficam do lado de dentro — `?recorte=` viaja em link
# que se manda por e-mail.
#
# Os dois primeiros NÃO são degraus: são população (quem existe, quem tem
# volume). Ficam num grupo à parte no seletor, e é isso que impede a leitura de
# que "63 comparáveis" e o degrau de 63 são a mesma coisa — coincidem nesta
# janela, por acaso do dado.
_RECORTES: dict[str, tuple] = {
    "todos": (lambda l: True, "cooperados"),
    "comparaveis": (lambda l: bool(l.get("avaliavel")), "comparáveis"),
    "acima-do-criterio": (_no_degrau("acima_do_criterio"),
                          "com procedimento acima do critério"),
    "persistente": (_no_degrau("persistente"), "persistentes"),
    "material": (_no_degrau("material"), "materiais"),
    "classificacao-firme": (_no_degrau("classificacao_firme"),
                            "com classificação firme"),
    "sem-fator-de-contexto": (_no_degrau("sem_fator_de_contexto"),
                              "sem fator de contexto"),
    "qualificados": (_no_degrau("confianca_calculavel"), "qualificados"),
}

# Recorte desconhecido cai no mais amplo, como no front: chave inválida numa URL
# compartilhada deve mostrar tudo, nunca esvaziar a tela.
_RECORTE_PADRAO = "todos"


def ids_em_cena(linhas_coop: list[dict], recorte: str | None = None,
                perfis_flags: list[str] | None = None) -> list[str]:
    """Os ids dos cooperados EM CENA, pelo mesmo predicado que o front aplica.

    `perfis_flags` são as COLUNAS de classificação (o `flag` de
    `perfis_da_area`), não as chaves de URL — a tradução é de quem chama, que é
    quem tem a lista de perfis da área em mãos.

    Perfil é UNIÃO sobre o recorte, nunca interseção entre perfis: identidades
    se acumulam, e ninguém procura "quem opera E é de alto risco". Idêntico ao
    `emCena()` de area.js.
    """
    predicado = _RECORTES.get(recorte or _RECORTE_PADRAO,
                              _RECORTES[_RECORTE_PADRAO])[0]
    alvo = set(perfis_flags or ())
    saida = []
    for l in linhas_coop:
        if not predicado(l):
            continue
        if alvo and not any(sp.get("chave") in alvo
                            for sp in (l.get("sub_perfis") or ())):
            continue
        saida.append(l["id"])
    return saida


def rotulo_recorte(recorte: str | None,
                   perfis_rotulos: list[str] | None = None) -> str:
    """Como o recorte se chama nas frases da bancada. Os perfis entram depois do
    substantivo porque recortam POR CIMA dele: "qualificados · opera"."""
    base = _RECORTES.get(recorte or _RECORTE_PADRAO,
                         _RECORTES[_RECORTE_PADRAO])[1]
    return f"{base} · {', '.join(perfis_rotulos)}" if perfis_rotulos else base


def contexto_da_area(gatilho_usado: str | None, criterio_pedido: str,
                     n_sinalizados: int, n_comparaveis: int,
                     n_total: int, n_excluidos: int,
                     estado_codigo: str, n_formam: int | None = None,
                     n_com_excedente: int | None = None) -> dict:
    """O CONTEXTO FIXO DA ÁREA, em uma linha de texto sob o título:

        64 na área · 63 comparáveis (ver os 6 fora da referência) ·
        63 com excedente em algum procedimento · 18 também atípicos no
        índice agregado

    Foi a faixa de três números-herói do guia §08 até 2026-08-19. Perdeu o
    tamanho, não o conteúdo: é ENQUADRAMENTO, não achado. Números de 22px
    ocupavam a dobra inteira e competiam por atenção com o gráfico e a tabela,
    que são onde o trabalho acontece — e o leitor precisa dos três uma vez, no
    início, para saber contra o que está lendo o resto da página.

    NÃO SE MEXE COM O RECORTE, e é essa a metade fixa da regra canônica
    (CLAUDE.md, lei 0): acima dos chips, a área; abaixo, a bancada. Se esta
    linha seguisse o filtro, nunca mais se citaria o número da área sem antes
    dizer que recorte estava ligado — e é justamente ela que se cita.

    Cada parte carrega o próprio `titulo_longo`: a linha é curta de propósito, e
    o que a faixa dizia nas linhas de apoio (quantos formam a referência, contra
    que índice se mede, de onde vem o R$) migrou para o hover em vez de sumir.

    O que fica de fora, e por quê:

    · mediana, IQR e P90 saíram quando o gráfico de distribuição entrou: lá eles
      têm contexto visual (a posição de cada cooperado dentro da faixa), e como
      número solto só duplicariam informação.
    · consultas na janela é INVENTÁRIO. Diz o tamanho da operação, não o que a
      página existe para responder.
    · peso na especialidade pertence ao Panorama: é comparação ENTRE áreas, e
      esta tela é sobre o que acontece DENTRO de uma.
    · o excesso EM CENA vive nos três cards abaixo dos chips (2026-08-19):
      segue o recorte, e aqui é o andar dos totais fixos da área.

    COMPARÁVEIS é `n_avaliaveis`, o mesmo conjunto do chip de recorte — quem tem
    volume para sustentar comparação. NÃO é quem forma a referência: os dois
    diferem (63 e 58 em Ginecologia). Os EXCLUÍDOS do link são da formação da
    referência, não dos comparáveis; sem o "N definem o padrão" no hover o leitor
    faz "64 − 63 = 1 ≠ 6" e o link parece erro.

    Sem régua na área (gatilho degradado a nenhum), as partes que dependem de
    sinalização dão lugar a UMA ressalva. Nunca zero, e nunca travessão: zero
    afirmaria que ninguém está fora, e é isso que não se pode afirmar sem
    referência. As duas primeiras partes continuam, porque contar quem sobrou
    dos cortes não exige régua nenhuma.
    """
    sem_regua = gatilho_usado is None
    # o motor degrada P90 -> P75 quando o grupo tem 10–19 formadores; o critério
    # EFETIVO é o que a tela deve nomear, e a diferença precisa aparecer
    ajustado = not sem_regua and gatilho_usado != criterio_pedido
    # Dois jeitos diferentes de não ter régua, e o léxico os separa: um grupo
    # pequeno demais para sustentar percentil não é a mesma coisa que um
    # cooperado sem área classificada. Confundi-los faria a tela sugerir que a
    # classificação pendente é um problema de tamanho.
    motivo = ("sem área de atuação · classificação pendente"
              if estado_codigo == ESTADO_SEM_PEER_GROUP else
              "grupo insuficiente para formar referência")

    # Nomear o índice não é redundância com "acima do critério": a parte diz que
    # está acima, o hover diz acima do quê. O mesmo cooperado pode estar dentro
    # no agregado e acima em procedimentos específicos.
    hover_revisao = "Cooperados acima do critério de revisão no índice agregado."
    if ajustado:
        hover_revisao += (f" Critério {gatilho_usado.upper()}, ajustado ao "
                          "tamanho do grupo.")

    # `valor` cru ao lado do texto em toda parte, como manda a regra de
    # formatação do módulo: o front imprime `texto`, e quem cruza número com
    # número (as provas, uma exportação futura) lê `valor` sem reparsear frase.
    partes = [
        {"chave": "na_area", "valor": n_total,
         "texto": f"{fmt(n_total, 0)} na área",
         "acao": None,
         "titulo_longo": "Cooperados da área com atividade no período."},
        {"chave": "comparaveis", "valor": n_comparaveis,
         "texto": f"{fmt(n_comparaveis, 0)} comparáveis",
         # o link mora DENTRO da parte, entre parênteses, porque é o complemento
         # deste número e de nenhum outro: quem não entrou na formação da régua
         "acao": (None if not n_excluidos else
                  {"chave": "excluidos",
                   "rotulo": f"ver {'o' if n_excluidos == 1 else 'os'} "
                             f"{fmt(n_excluidos, 0)} fora da referência"}),
         "titulo_longo": (
             "Volume suficiente para comparação; é o mesmo conjunto do "
             "recorte Comparáveis."
             + ("" if n_formam is None else
                f" A referência é formada por {fmt(n_formam, 0)} deles, e "
                "define o padrão contra o qual todos são medidos, inclusive "
                "quem não entra nela."))},
    ]

    if sem_regua:
        # UMA ressalva no lugar das partes que dependem de sinalização. `valor`
        # None é o que diz "não há número aqui" — e é diferente de zero, que
        # afirmaria que ninguém está fora.
        partes.append({"chave": "sem_regua", "valor": None,
                       "texto": config.SEM_SINALIZACAO,
                       "acao": None, "titulo_longo": motivo})
        return {"partes": partes, "separador": " · "}

    # ── OS DOIS NÍVEIS, nomeados ────────────────────────────────────────────
    # O achado é o par (cooperado, procedimento): 63 cooperados têm excedente em
    # algum exame. "Acima do critério" é outra leitura, sobre o índice AGREGADO,
    # e são 8. Os dois convivem na página, e até 2026-08-19 só o segundo estava
    # escrito — colado em "87.816 solicitações excedentes", ele fazia o leitor
    # ligar um no outro e concluir que 8 médicos geraram o total. O número que
    # desfaz isso é o dos 63, e ele não existia em lugar nenhum da tela.
    # Ordem deliberada: o achado primeiro, a leitura adicional depois.
    if n_com_excedente is not None:
        partes.append(
            {"chave": "com_excedente", "valor": n_com_excedente,
             "texto": f"{fmt(n_com_excedente, 0)} com excedente em algum "
                      "procedimento",
             "acao": None,
             "titulo_longo": ("Cooperados com ao menos um procedimento acima "
                              "do critério daquele procedimento. É a população que "
                              "gera o excedente e o valor em R$ da página.")})
    partes.append(
        {"chave": "em_revisao", "valor": n_sinalizados,
         # "também" amarra esta leitura à anterior em vez de abrir uma
         # contagem paralela; "no índice agregado" diz de que eixo ela fala
         "texto": f"{fmt(n_sinalizados, 0)} também atípicos no índice agregado",
         "acao": None, "titulo_longo": hover_revisao})
    # AS DUAS MEDIDAS DO EXCEDENTE saíram desta linha em 2026-09-07
    # (`excedente` e `excedente_reais`). Elas viviam aqui desde antes da
    # "Leitura da área", que hoje imprime as duas logo abaixo — as solicitações
    # excedentes como linha do grupo "Solicitado no recorte", o R$ como o
    # destaque do bloco, e as duas de novo na nota ("O excedente da área soma
    # 132.526 solicitações e R$ 4,2 mi"). Eram os mesmos dois números três
    # vezes na mesma dobra da tela, e a linha de contexto era a superfície onde
    # eles diziam menos: sem o denominador ao lado e sem dizer que não se movem
    # com o recorte.
    #
    # O que a linha continua carregando é o ESCOPO — quantos na área, quantos
    # comparáveis, quantos com excedente, quantos atípicos no agregado —, que é
    # a leitura que ela existe para dar e que nenhum outro bloco repete.
    return {"partes": partes, "separador": " · "}


# ─────────────────────────────────────────────────────────────────────────────
# Geometria da régua e do gráfico (§04 régua · §05 gráfico)
# ─────────────────────────────────────────────────────────────────────────────

def _escala(valores: list[float]) -> dict:
    """Domínio do eixo com 4% de folga nas pontas, o mesmo para a régua da
    tabela e para o gráfico, que é o que faz a marca do cooperado cair no mesmo
    lugar nos dois ('componente-assinatura', guia §04)."""
    validos = [float(v) for v in valores if v is not None and not np.isnan(v)]
    lo, hi = min(validos), max(validos)
    folga = (hi - lo) * 0.04 or 1.0
    return {"min": lo - folga, "max": hi + folga}


def _pos(valor, escala: dict) -> float | None:
    """Valor -> posição percentual no eixo (0–100), arredondada a 2 casas."""
    if valor is None or np.isnan(valor):
        return None
    amplitude = escala["max"] - escala["min"]
    return round((float(valor) - escala["min"]) / amplitude * 100, 2)


def _classe_ponto(taxa: float, p75: float | None, valor_crit: float | None) -> str:
    """Cor do ponto = significado declarado (guia §09, um token um significado):
    acima do critério de revisão · acima da faixa interquartil (leitura de dado)
    · dentro da referência. Nunca "alto = vermelho"."""
    if valor_crit is not None and taxa > valor_crit:
        return "crit"
    if p75 is not None and taxa > p75:
        return "read"
    return "neutro"


# ─────────────────────────────────────────────────────────────────────────────
# §05 — Gráfico de distribuição
# ─────────────────────────────────────────────────────────────────────────────

# ── as TRÊS leituras da mesma caixa (2026-08-31) ─────────────────────────────
#
# O gráfico respondia uma pergunta só: quem pede mais exames por consulta. Quem
# pede POUCO e CARO ficava no meio da nuvem, indistinguível de quem pede pouco e
# barato. As três medidas são o MESMO desenho, sobre o MESMO grupo, trocando só
# a grandeza do eixo:
#
#   exames    quantidade   solicitações por consulta       (o índice de sempre)
#   custo     dinheiro     R$ solicitados por consulta     (a coluna da tabela)
#   excesso   dinheiro     variação excedente em R$ por consulta
#
# Trocar de medida NÃO troca quem está em cena: é leitura, não recorte (lei 0).
# O recorte e o perfil continuam governando quem aparece, nas três.
#
# Duas regras governam as duas medidas de dinheiro:
#
#   · AUSÊNCIA NÃO É ZERO (ajuste 4). Quem não tem preço nas contas, ou nenhum
#     procedimento acima do critério, fica FORA do gráfico e é contado no
#     rodapé. Um ponto sobre o zero leria como "não custa nada" quando o que há
#     é "não medido". Mesma decisão que a dispersão já tomava.
#   · A CAIXA continua sendo a do grupo que FORMA A REFERÊNCIA da área, medida
#     pela mesma função do pipeline que constrói a norma (`norma_por_area`),
#     com o mesmo piso, recebido por argumento. Nenhum quantil nasce aqui
#     (Lei 1). Em "excesso" a caixa é necessariamente CONDICIONAL: resume quem
#     tem excedente valorado, e o rodapé declara isso, com o n.
#
# (chave, rótulo do controle, título do cartão, grandeza do subtítulo, motivo de
#  quem fica de fora)
# O RÓTULO do controle é telegráfico ("Custo", não "Custo médio por consulta"):
# o segmentado é o interruptor, e quem diz a grandeza por extenso é o título do
# cartão, que troca junto e fica a dois centímetros dele. Rótulo longo aqui
# quebrava em duas linhas e engolia a metade direita do cabeçalho.
_MEDIDAS = (
    # A CHAVE continua "exames" (interna, e é o que o `_FORMATO_MEDIDA` e o
    # smoke leem); o RÓTULO, que é o que aparece no controle, diz
    # "Solicitações" — "exame" saiu de toda superfície visível em set/2026.
    ("exames", "Solicitações",
     "Distribuição do índice de solicitação",
     "solicitações por consulta na janela",
     "sem índice medido"),
    ("custo", "Custo",
     "Distribuição do custo por consulta",
     "R$ solicitados por consulta na janela, a preço interno provisório",
     "sem preço nas contas"),
    ("excesso", "Excesso",
     "Distribuição do excesso por consulta",
     "variação excedente em R$ por consulta na janela",
     "sem variação excedente valorada"),
)

# formatador de cada medida: quantidade em número, dinheiro em R$ com
# centavos (é preço unitário, não total: ver `fmt_reais_unitario`)
_FORMATO_MEDIDA = {"exames": fmt, "custo": fmt_reais_unitario,
                   "excesso": fmt_reais_unitario}


def _valores_da_medida(av: pd.DataFrame, chave: str,
                       custo_por_coop: dict[str, dict] | None,
                       excedente_por_coop: dict[str, float] | None) -> pd.Series:
    """A coluna de valores de uma medida, com AUSÊNCIA em NaN, nunca em zero.

    `custo` sai do MESMO `custo_coop` do motor de execução que alimenta a coluna
    "Custo por consulta" da tabela: derivar aqui um segundo custo por consulta
    faria o gráfico e a lista logo abaixo discordarem sobre o mesmo cooperado.

    `excesso` é razão de dois TOTAIS do motor (excedente em R$ da janela ÷
    consultas da janela), nunca média de razões por consulta (rigor §10).
    """
    if chave == "exames":
        return av["taxa_exames_por_consulta"].astype(float)
    if chave == "custo":
        bruto = av["ID_COOPERADO"].map(
            lambda c: (custo_por_coop or {}).get(c, {}).get("custo_por_consulta"))
    else:
        bruto = (av["ID_COOPERADO"].map(excedente_por_coop or {})
                 / av["consultas_totais"].astype(float))
    valores = pd.to_numeric(bruto, errors="coerce")
    # zero aqui é ausência de preço ou de par acima do critério, não dinheiro
    # medido: sai da medida em vez de virar um ponto empilhado no eixo
    return valores.where(valores > 0)


def _norma_da_medida(av: pd.DataFrame, valores: pd.Series, piso: int):
    """Mediana, P25 e P75 da medida pela MESMA função que constrói a norma da área.

    Roda sobre `av` com a coluna da medida no lugar da taxa: piso e
    elegibilidade (`elegivel_norma`) continuam sendo os do pipeline, passados
    por argumento (Lei 3), e quem não tem a medida (NaN) não entra na conta em
    vez de entrar como zero. Devolve None quando ninguém que forma a referência
    tem a medida, e aí a medida vai para a tela SEM caixa, o que é honesto:
    sem grupo não há quartil.
    """
    quadro = av.assign(_medida=valores)
    n = norma_por_area(quadro, piso, col_taxa="_medida")
    if n.empty or int(n.iloc[0]["n_na_norma"]) == 0:
        return None
    return n.iloc[0]


def _bloco_da_medida(chave: str, rotulo: str, titulo: str, grandeza: str,
                     motivo_fora: str, av: pd.DataFrame, valores: pd.Series,
                     norma, rotulos_posicao: pd.Series,
                     exc: dict[str, float], gatilho: str | None = None,
                     alvo: str = "mediana") -> dict | None:
    """Uma medida pronta para desenhar: escala, haste, caixa, eixo e pontos.

    Geometria em `pos_pct`, como o resto do bloco: o JavaScript posiciona, não
    calcula. Cada ponto carrega o próprio DENOMINADOR (`consultas_fmt`), que é o
    mesmo nas três medidas e é o que sustenta qualquer uma delas (rigor §1).
    """
    presentes = valores.dropna().sort_values()
    if presentes.empty:
        return None
    formatar = _FORMATO_MEDIDA[chave]

    def _num(campo):
        if norma is None or pd.isna(norma[campo]):
            return None
        return float(norma[campo])

    p25, p75, mediana = _num("p25"), _num("p75"), _num("mediana")
    # AS DUAS RÉGUAS da medida em cena: a referência de adequação (o alvo ativo)
    # e o critério de revisão (o gatilho ativo). Saem da MESMA norma que produz
    # a caixa — no índice é a norma publicada da área, nas duas de dinheiro é a
    # construída sobre o mesmo grupo —, então a linha e a caixa nunca podem
    # discordar sobre qual população estão descrevendo.
    valor_ref = _num(alvo)
    valor_crit = _num(gatilho) if gatilho else None
    n_caixa = 0 if norma is None else int(norma["n_na_norma"])

    # Estatística de grupo minúsculo é ANEDOTA (rigor §2). Abaixo do n que
    # sustenta percentil, a medida vai para a tela SEM caixa e SEM referência do
    # grupo, com o motivo no rodapé: uma caixa desenhada sobre três observações
    # afirma um espalhamento que não existe. Acontece só nas medidas de dinheiro,
    # e só quando quase ninguém da área tem preço nas contas ou par acima do
    # critério; os PONTOS ficam todos, porque o outlier é o produto (rigor §7).
    if n_caixa < config.N_MINIMO_P75:
        p25 = p75 = mediana = valor_ref = valor_crit = None

    observados = [float(v) for v in presentes]
    escala = _escala(observados
                     + [v for v in (p25, p75, valor_ref, valor_crit)
                        if v is not None])

    # todo número de indivíduo anda com a referência do grupo ao lado
    # (LEXICO_PRODUTO, princípio 6). No índice essa referência é o percentil
    # traduzido, que o motor já produz; nas duas de dinheiro, a mediana do grupo.
    if chave == "exames":
        leitura_padrao = "dentro da referência da área"
    elif mediana is None:
        leitura_padrao = "sem referência do grupo para esta medida"
    else:
        leitura_padrao = f"referência do grupo: {formatar(mediana)} por consulta"

    pontos = []
    for indice, valor in presentes.items():
        linha = av.loc[indice]
        coop = linha["ID_COOPERADO"]
        rotulo_pos = (rotulos_posicao.get(indice, config.SEM_MEDIDA)
                      if chave == "exames" else None)
        # ajuste 2 do CLAUDE.md: percentil nunca viaja sem tradução
        traducao = apr.traduzir_percentil(rotulo_pos) if rotulo_pos else None
        pontos.append({
            "id": coop,
            "valor": round(float(valor), 4), "valor_fmt": formatar(valor),
            "pos_pct": _pos(valor, escala),
            "excedente_reais": round(exc.get(coop, 0.0), 2),
            "excedente_reais_fmt": fmt_reais(exc[coop]) if coop in exc else None,
            "consultas": int(linha["consultas_totais"]),
            "consultas_fmt": fmt(linha["consultas_totais"], 0),
            "percentil": rotulo_pos,
            "leitura": traducao or leitura_padrao,
            # ACIMA DO CRITÉRIO da medida em cena, e não do índice agregado: é o
            # que a linha desenhada logo acima diz, e ponto verde à esquerda de
            # uma linha tracejada seria o desenho contradizendo a si mesmo.
            "acima": bool(valor_crit is not None and float(valor) > valor_crit),
        })

    menor, maior = observados[0], observados[-1]
    n_fora = int(len(av) - len(presentes))

    # o rodapé do cartão: sobre quantos a caixa se apoia, quem ficou de fora e
    # por quê, e a ressalva de preço quando a medida é dinheiro. Estatística de
    # grupo sem n visível é anedota (rigor §2), e ausência sem motivo declarado
    # vira zero na cabeça de quem lê.
    nota = []
    if p25 is not None:
        nota.append(f"Caixa P25–P75 de {n_caixa} que formam a referência")
    elif n_caixa:
        nota.append(f"sem caixa: só {n_caixa} de quem forma a referência tem esta "
                    f"medida, abaixo dos {config.N_MINIMO_P75} que sustentam quartis")
    else:
        nota.append("sem caixa: nenhum formador da referência tem esta medida")
    if n_fora:
        nota.append(f"{n_fora} {motivo_fora}, fora do gráfico")

    return {
        "chave": chave, "rotulo": rotulo, "titulo": titulo,
        "subtitulo": f"Cada ponto é um cooperado avaliável · {grandeza}",
        "escala": {"min": round(escala["min"], 4), "max": round(escala["max"], 4)},
        # HASTE do menor ao maior valor observado: é o alcance total da
        # distribuição, que a caixa sozinha não mostra
        "haste": {"de": round(menor, 4), "ate": round(maior, 4),
                  "de_fmt": formatar(menor), "ate_fmt": formatar(maior),
                  "pos_pct": _pos(menor, escala),
                  "largura_pct": round(_pos(maior, escala) - _pos(menor, escala), 2)},
        "faixa_iqr": None if p25 is None or p75 is None else {
            "rotulo": "IQR", "de": round(p25, 4), "ate": round(p75, 4),
            "pos_pct": _pos(p25, escala),
            "largura_pct": round(_pos(p75, escala) - _pos(p25, escala), 2)},
        # AS DUAS LINHAS voltaram em 2026-09-07, pelo artboard "Medyx Area de
        # Atuacao". Elas tinham saído em 2026-08-20 com o argumento de que o
        # critério agregado não governa a sinalização — o que continua verdade,
        # e por isso o rodapé do bloco diz de que grupo elas falam. O que mudou
        # é o reconhecimento de que um enxame sem nenhuma marca não responde
        # pergunta nenhuma: sem a régua, o leitor vê espalhamento e não sabe
        # onde a área considera que o normal acaba.
        "referencias": [r for r in (
            (None if valor_ref is None else
             {"classe": "median", "valor": round(valor_ref, 4),
              "valor_fmt": formatar(valor_ref), "pos_pct": _pos(valor_ref, escala),
              "rotulo": f"referência {formatar(valor_ref)}",
              "titulo": ("Referência de adequação da área nesta medida "
                         f"({_ROTULO_NIVEL.get(alvo, alvo)}). É dela que se mede "
                         "o excedente.")}),
            (None if valor_crit is None or not gatilho else
             {"classe": "criterion", "valor": round(valor_crit, 4),
              "valor_fmt": formatar(valor_crit), "pos_pct": _pos(valor_crit, escala),
              "rotulo": f"{gatilho.upper()} {formatar(valor_crit)}",
              "titulo": ("Critério de revisão da área nesta medida. Acima dele o "
                         "caso entra na lista; a sinalização do método continua "
                         "sendo por procedimento, não por este índice.")}),
        ) if r],
        # extremos observados e as bordas da caixa: a única marca de grupo que
        # sobrou, e ela é descritiva
        "eixo": [{"valor": round(v, 4), "valor_fmt": formatar(v),
                  "pos_pct": _pos(v, escala)}
                 for v in dict.fromkeys(
                     [menor] + [x for x in (p25, p75) if x is not None] + [maior])],
        "pontos": pontos,
        "n_pontos": len(pontos),
        "n_fora": n_fora,
        "n_na_caixa": n_caixa,
        "nota": " · ".join(nota),
    }


def distribuicao(posicao_area: pd.DataFrame, norma_linha, gatilho_usado: str | None,
                 rotulos_posicao: pd.Series, referencia: str = "mediana",
                 excedente_por_coop: dict[str, float] | None = None, *,
                 piso: int, custo_por_coop: dict[str, dict] | None = None) -> dict | None:
    """Um ponto por cooperado avaliável, em TRÊS medidas alternáveis na tela.

    Devolve None quando a área não sustenta distribuição (grupo insuficiente,
    sem referência, sem peer group): o guia proíbe gráfico sem critério visível.

    ── as três medidas (2026-08-31) ────────────────────────────────────────
    Ver o comentário de `_MEDIDAS`, logo acima: mesmo desenho, mesmo grupo, três
    grandezas no eixo. Todas viajam prontas no MESMO payload, porque trocar de
    medida é leitura e não recorte, e uma ida ao servidor para mudar de eixo
    faria parecer que o conjunto medido mudou junto.

    ── DOIS ESTADOS, e não uma rampa (2026-09-07) ──────────────────────────
    Cada ponto tem duas aparências: cinza, ou marcado por estar acima do critério
    da medida em cena. É a variante E do artboard "Medyx Escala de Cor", "sem
    escala e sem brilho", e ela desfaz um arranjo anterior em que a cor era o
    EXCEDENTE EM R$, por quantil, do neutro ao vermelho.

    A rampa dizia dinheiro enquanto o eixo dizia frequência, e cobrava do leitor
    uma legenda de três valores para ser decodificada. Pior: cor contínua sugere
    ordenação contínua, e o cooperado que ficava um degrau mais escuro que o
    vizinho não estava, por isso, mais fora do padrão que ele — o que decide isso
    é a posição, não a tinta. O que a cor deixou de dizer, o Pareto e a lista ao
    lado dizem melhor, e a dica de cada ponto imprime o excedente por extenso.

    Sobrou UMA distinção, e ela é a que o desenho precisa carregar: de que lado
    da régua o ponto está. Com dois estados, cor e posição afirmam a mesma coisa,
    e nunca podem se contradizer.

    ── as DUAS RÉGUAS, e a ressalva que anda com elas (2026-09-07) ──────────
    Referência de adequação e critério de revisão voltaram a ser desenhadas, pelo
    artboard "Medyx Area de Atuacao". Elas tinham saído em ago/2026, e o
    argumento de então continua de pé: o critério AGREGADO não governa nada. Não
    filtra a cascata, não entra em nenhum R$, não decide quem vai a comitê — a
    sinalização do método é por PAR (cooperado × procedimento). Por isso o título
    da linha e o rodapé do bloco dizem isso com todas as letras.

    O que mudou é o reconhecimento de que um enxame sem marca nenhuma não
    responde pergunta: o leitor vê espalhamento e não sabe onde a área considera
    que o normal acaba. A régua aqui LOCALIZA; quem julga é o gráfico por exame,
    onde ela de fato rege.

    Vale repetir o que o desenho não deve deixar concluir: 46 dos 63 cooperados
    ficam do lado de cá da linha, e esses 46 carregam 34% do dinheiro da área.
    Estar abaixo do critério agregado não é estar limpo, e é para isso que o
    Pareto ao lado existe.

    Parâmetros além dos evidentes:
        piso: volume mínimo de consultas, por argumento (Lei 3), o mesmo do
            pipeline. Governa quem forma a caixa de cada medida.
        custo_por_coop: `custo_coop` do motor de execução, indexado por
            cooperado. É a fonte da coluna "Custo por consulta" da tabela.
        excedente_por_coop: excedente em R$ por cooperado, a mesma fonte que
            tinge os pontos, alimenta o Pareto e os cards.
    """
    if norma_linha is None or gatilho_usado is None:
        return None
    av = posicao_area[posicao_area["avaliavel"]]
    if av.empty:
        return None

    # o excedente em R$ não tinge mais nada (ver "as duas cores", acima); ele
    # continua viajando porque a dica de cada ponto o imprime por extenso.
    exc = {c: float(v) for c, v in (excedente_por_coop or {}).items() if v > 0}

    medidas = []
    for chave, rotulo, titulo, grandeza, motivo_fora in _MEDIDAS:
        valores = _valores_da_medida(av, chave, custo_por_coop, excedente_por_coop)
        # o índice usa a norma JÁ PUBLICADA da área, a mesma que o rodapé da
        # tabela imprime; as duas de dinheiro não têm norma publicada e a
        # constroem com a mesma função, sobre o mesmo grupo
        norma = (norma_linha if chave == "exames"
                 else _norma_da_medida(av, valores, piso))
        bloco = _bloco_da_medida(chave, rotulo, titulo, grandeza, motivo_fora,
                                 av, valores, norma, rotulos_posicao,
                                 exc, gatilho_usado, referencia)
        if bloco is not None:
            medidas.append(bloco)
    if not medidas:
        return None

    return {
        "medida_padrao": medidas[0]["chave"],
        "medidas": medidas,
        # ── A RAMPA SAIU (2026-09-07) ───────────────────────────────────────
        # A tinta era o excedente em R$, por ordem, numa escala de cinza-âmbar-
        # vermelho. Ela dizia uma coisa (dinheiro) enquanto o eixo dizia outra
        # (frequência), e exigia uma legenda de três valores para ser decodifi-
        # cada. O artboard "Medyx Escala de Cor" resolveu isso escolhendo a
        # variante E, "sem escala e sem brilho": dois estados, e só. O que a
        # cor deixa de dizer, a lista e o Pareto ao lado dizem melhor.
        "rampa": None,
        # A LEGENDA do artboard "Medyx Area de Atuacao", na ordem em que o olho
        # precisa dela: o que é um ponto, o que é um ponto marcado, e as três
        # marcas de grupo.
        "legenda": [
            {"classe": "pt-mk-fundo", "rotulo": "um cooperado comparável"},
            {"classe": "pt-mk-acima", "rotulo": "acima do critério"},
            {"classe": "band", "rotulo": "metade central do grupo"},
            {"classe": "mk-ref", "rotulo": "referência da área"},
            {"classe": "mk-crit", "rotulo": "critério de revisão"},
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Dispersão: quantidade × custo (bloco experimental, 2026-08-19)
# ─────────────────────────────────────────────────────────────────────────────

def dispersao(posicao_area: pd.DataFrame, valor_por_coop: dict[str, float],
              rotulos_posicao: pd.Series,
              excedente_por_coop: dict[str, float] | None = None) -> dict | None:
    """Um ponto por cooperado avaliável: quantidade no X, custo no Y, porte no
    tamanho.

        X  exames solicitados por consulta   (o mesmo índice da distribuição)
        Y  custo médio por consulta          (R$ solicitado ÷ consultas)
        r  valor total solicitado            (o peso dele na operação)
        cor  excedente em R$                 (o dinheiro em jogo)

    TAMANHO e COR são dois dinheiros diferentes, e é essa a leitura do bloco:
    bola grande e clara é operação grande e dentro do padrão; bola pequena e
    escura é operação modesta com muito excedente. Confundir os dois era o que
    a tela fazia quando só existia porte.

    É o primeiro gráfico do app que põe DINHEIRO num eixo. A distribuição
    responde "quem pede muito"; esta responde "quem custa muito", e as duas
    perguntas não têm a mesma resposta — quem pede pouco e caro é invisível lá.

    Sem linha de referência e sem cor de severidade, de propósito: o método não
    define critério para custo, e desenhar régua onde não há uma foi o defeito
    que a distribuição carregava. Aqui o gráfico descreve, não julga.

    X e Y são colineares por construção (custo/consulta = exames/consulta ×
    preço médio da cesta), então a nuvem puxa para uma diagonal; o desvio
    vertical é o MIX de exames de cada um. Está assim de propósito, para a
    diagonal ser vista antes de se decidir o eixo definitivo.

    `valor_por_coop` é o R$ solicitado somado por cooperado, valorado a preço
    interno — parcial por construção: só entra procedimento com preço nas
    contas de execução. `None` quando não há nenhum valor a distribuir.
    """
    av = posicao_area[posicao_area["avaliavel"]]
    if av.empty or not valor_por_coop:
        return None

    pontos_crus = []
    for _, linha in av.iterrows():
        coop = linha["ID_COOPERADO"]
        valor = float(valor_por_coop.get(coop, 0.0))
        consultas = float(linha["consultas_totais"])
        if valor <= 0 or consultas <= 0:
            continue          # sem preço nas contas: ausência, não zero
        pontos_crus.append((coop, float(linha["taxa_exames_por_consulta"]),
                            valor / consultas, valor, int(consultas)))
    if not pontos_crus:
        return None

    esc_x = _escala([p[1] for p in pontos_crus])
    esc_y = _escala([p[2] for p in pontos_crus])
    maior = max(p[3] for p in pontos_crus)
    # mesma rampa da distribuição: tinta por ORDEM do excedente, não por valor
    exc = {c: float(v) for c, v in (excedente_por_coop or {}).items() if v > 0}
    ordem = sorted(exc.values())

    pontos = []
    for coop, x, y, valor, consultas in sorted(pontos_crus, key=lambda p: -p[3]):
        rotulo_pos = rotulos_posicao.get(coop, config.SEM_MEDIDA)
        pontos.append({
            "id": coop,
            "x": round(x, 4), "x_fmt": fmt(x),
            "y": round(y, 2), "y_fmt": fmt_reais(y),
            "valor": round(valor, 2), "valor_fmt": fmt_reais(valor),
            "consultas": consultas, "consultas_fmt": fmt(consultas, 0),
            "x_pct": _pos(x, esc_x), "y_pct": _pos(y, esc_y),
            # área proporcional ao valor (raiz do valor), não diâmetro: com
            # diâmetro proporcional, o maior ocuparia área ~30× a do segundo e
            # o olho leria a diferença errada
            "tamanho": round((valor / maior) ** 0.5, 4),
            "intensidade": (0.0 if coop not in exc or len(ordem) < 2 else
                            round(ordem.index(exc[coop]) / (len(ordem) - 1), 4)),
            "excedente_reais_fmt": (fmt_reais(exc[coop]) if coop in exc else None),
            "leitura": (f"{fmt_reais(y)} por consulta · {fmt(x)} solicitações por "
                        f"consulta · {fmt(consultas, 0)} consultas na janela"),
            "percentil": rotulo_pos,
        })

    def _eixo(escala, valores, formatar):
        """Extremos observados e o meio da escala: três marcas, sem grade."""
        marcas = [min(valores), (min(valores) + max(valores)) / 2, max(valores)]
        return [{"valor": round(v, 4), "valor_fmt": formatar(v),
                 "pos_pct": _pos(v, escala)} for v in marcas]

    return {
        "titulo": "Quantidade × custo por consulta",
        "subtitulo": ("Cada ponto é um cooperado avaliável · o tamanho é o "
                      "valor total solicitado por ele na janela"),
        "eixo_x": {"rotulo": "solicitações por consulta",
                   "marcas": _eixo(esc_x, [p[1] for p in pontos_crus], fmt)},
        "eixo_y": {"rotulo": "custo médio por consulta",
                   "marcas": _eixo(esc_y, [p[2] for p in pontos_crus], fmt_reais)},
        "pontos": pontos,
        "n_sem_preco": int(len(av) - len(pontos_crus)),
        "rampa": None if len(ordem) < 2 else {
            "rotulo": "excedente em R$",
            "metodo": "tinta por ordem de excedente, não por valor",
            "marcas": [
                {"intensidade": 0.0, "valor_fmt": fmt_reais(ordem[0])},
                {"intensidade": 0.5, "valor_fmt": fmt_reais(ordem[len(ordem) // 2])},
                {"intensidade": 1.0, "valor_fmt": fmt_reais(ordem[-1])},
            ],
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# §04 — Tabela "Cooperados da área"
# ─────────────────────────────────────────────────────────────────────────────

# Colunas booleanas derivadas da dim v2 em dados.carregar_classificacao, na
# ordem em que os badges aparecem. O rótulo de "tem_secundaria" e "executa"
# é completado com a área (ver _rotulo_do_badge): "também obstetrícia" diz mais
# do que "área secundária".
_BADGES = (
    ("faz_cirurgia", "cirurgia"),
    ("faz_mastologia", "mastologia"),
    ("tem_secundaria", "área secundária"),
    ("executa", "executa"),
    ("carteira_jovem", "carteira jovem"),
    ("carteira_climaterio", "carteira climatério"),
)


def _rotulo_do_badge(coluna: str, rotulo: str, flags_coop) -> str:
    if coluna == "tem_secundaria":
        return f"também {flags_coop.get('area_secundaria')}"
    if coluna == "executa":
        return f"executa {flags_coop.get('area_execucao')}"
    return rotulo


def _sub_perfis(flags_coop) -> list[dict]:
    """Badges de identidade (espec funcional, regra 2). Ajuste 1 do handoff:
    ausência de atributo NÃO vira etiqueta, a célula fica vazia.

    Cada badge viaja com a frase que diz o que ele MUDA na comparação
    (config.AJUDA_SUBPERFIL) — na v2, nada; e é preciso dizer isso, porque um
    rótulo de duas palavras não informa se o cooperado entra ou não na referência.
    """
    if flags_coop is None:
        return []
    return [{"chave": coluna, "rotulo": _rotulo_do_badge(coluna, rotulo, flags_coop),
             "ajuda": config.AJUDA_SUBPERFIL.get(coluna)}
            for coluna, rotulo in _BADGES if bool(flags_coop.get(coluna))]


def perfis_da_area(posicao_area: pd.DataFrame,
                   classificacao: pd.DataFrame) -> list[dict]:
    """Sub-perfis PRESENTES na área, com quantos portadores comparáveis cada um.

    Recorte de QUEM APARECE, nunca de contra quem se compara: a régua continua
    sendo a da área inteira, e é por isso que este bloco não devolve mediana,
    critério nem percentil por perfil — eles não existem por perfil.

    Contagem entre os COMPARÁVEIS, não entre todos: o recorte serve para olhar
    dentro do grupo que sustenta comparação, e contar quem está abaixo do volume
    mínimo prometeria uma leitura que a lista não entrega.
    """
    comparaveis = posicao_area.loc[posicao_area["avaliavel"], "ID_COOPERADO"]
    flags = classificacao.set_index("ID_COOPERADO")
    presentes = flags.reindex(comparaveis).fillna(False)
    saida = []
    for coluna, rotulo in _BADGES:
        if coluna not in presentes.columns:
            continue
        n = int(presentes[coluna].astype(bool).sum())
        if not n:
            continue
        ok = n >= config.MIN_PORTADORES_RECORTE_PERFIL
        saida.append({
            "chave": rotulo.replace(" ", "-"),   # o que vai na URL, na língua da tela
            "flag": coluna,
            "rotulo": rotulo,
            "n": n,
            "selecionavel": ok,
            "motivo": (None if ok else
                       "sem leitura interna: poucos portadores"),
            "ajuda": config.AJUDA_SUBPERFIL.get(coluna),
        })
    return sorted(saida, key=lambda x: -x["n"])


def sem_sub_perfil(posicao_area: pd.DataFrame,
                   classificacao: pd.DataFrame) -> int:
    """Comparáveis sem NENHUM sub-perfil: fecha a conta da composição da área.

    O bloco "Perfis na área" lista os portadores de cada perfil; sem este
    número, a soma não bate com os comparáveis e a leitura fica incompleta.
    Contado entre os COMPARÁVEIS, a mesma população de perfis_da_area().
    """
    comparaveis = posicao_area.loc[posicao_area["avaliavel"], "ID_COOPERADO"]
    flags = classificacao.set_index("ID_COOPERADO")
    presentes = flags.reindex(comparaveis).fillna(False)
    cols = [c for c, _ in _BADGES if c in presentes.columns]
    if not cols:
        return int(len(presentes))
    return int((~presentes[cols].astype(bool).any(axis=1)).sum())


def postos_por_perfil(posicao_area: pd.DataFrame,
                      classificacao: pd.DataFrame) -> dict[str, dict[str, dict]]:
    """Posto de cada cooperado DENTRO de cada sub-perfil que ele carrega.

    Ordenado pelo índice, decrescente, entre os portadores COMPARÁVEIS — a mesma
    ordem que a coluna "Índice / consulta" produz quando o recorte está ativo.

    O total do grupo é obrigatório ("3º de 9"): posto isolado não é publicável
    (léxico), e com denominador pequeno ele identifica a pessoa.

    Isto NÃO é uma segunda régua. É a posição dele na lista que está em cena; a
    comparação segue sendo com a área, e o percentil da coluna ao lado é que a
    carrega.
    """
    comparaveis = posicao_area.loc[posicao_area["avaliavel"]]
    flags = classificacao.set_index("ID_COOPERADO")
    saida: dict[str, dict[str, dict]] = {}
    for coluna, _ in _BADGES:
        if coluna not in flags.columns:
            continue
        ids = [c for c in comparaveis["ID_COOPERADO"]
               if bool(flags[coluna].get(c, False))]
        if not ids:
            continue
        d = (comparaveis[comparaveis["ID_COOPERADO"].isin(ids)]
             .sort_values("taxa_exames_por_consulta", ascending=False))
        total = len(d)
        saida[coluna] = {
            r.ID_COOPERADO: {"posto": i, "total": total,
                             "rotulo": f"{i}º de {total}"}
            for i, r in enumerate(d.itertuples(), start=1)
        }
    return saida


def _perfil_explica(coop: str, area: str, flags_coop, codigo_origem: str | None,
                    cesta_excluida: frozenset) -> dict | None:
    """A origem do excedente dele cai na cesta do próprio sub-perfil?

    Quando cai, a variação tem uma explicação de prática à mão e a linha diz
    isso. Quando não cai, NADA: operar não explica estradiol, e uma etiqueta
    genérica de "tem sub-perfil" transformaria identidade em desculpa.

    A relação cesta↔perfil não é decidida aqui. `cesta_excluida` é o conjunto
    (cooperado, área, procedimento) que `montar_exclusao_por_par` resolve a partir
    das regras do config — pertencer a ele já significa "este procedimento é da
    cesta do sub-perfil deste cooperado, nesta área".
    """
    if codigo_origem is None or flags_coop is None:
        return None
    if (coop, area, codigo_origem) not in cesta_excluida:
        return None
    for flag, area_regra, _ in config.EXCLUSOES_SUBPERFIL:
        if area_regra == area and bool(flags_coop.get(flag)):
            return {
                "rotulo": "perfil explica a origem",
                "perfil": dict(_BADGES).get(flag, flag),
                "cesta": config.CESTA_SUBPERFIL.get(flag),
                "detalhe": (
                    f"O procedimento que puxa a variação está na cesta "
                    f"{config.CESTA_SUBPERFIL.get(flag, 'do perfil')}, explicada "
                    f"pelo perfil \"{dict(_BADGES).get(flag, flag)}\". Ele não "
                    f"forma a referência NESSES pares e segue medido contra ela."
                ),
            }
    return None



# ─────────────────────────────────────────────────────────────────────────────
# Evidência por cooperado — agregações do que os motores já produziram
# ─────────────────────────────────────────────────────────────────────────────

def origem_do_excedente(sinal_area: pd.DataFrame, n_topo: int = 5) -> dict[str, dict]:
    """De ONDE vem a variação excedente de cada cooperado.

    Interno: "procedimento que puxa". Agregação pura de
    `posicao_vs_norma_procedimento` — o excedente por par já foi calculado pelo
    motor; aqui ele só é ordenado e somado por cooperado. Nada de novo é medido.

    Para cada cooperado:
      · o procedimento com a MAIOR parcela do excedente dele, com a razão vs
        referência e a fração do excedente total que essa parcela responde;
      · os `n_topo` maiores, para o hover;
      · a fração acumulada dos dois primeiros, quando o segundo é comparável ao
        primeiro (config.FRACAO_SEGUNDA_ORIGEM_RELEVANTE) — dois procedimentos
        empatados no topo são uma leitura diferente de um dominante.

    A razão acompanha a parcela de propósito: parcela alta com razão baixa é
    volume (ele pede muito de algo que todos pedem); parcela alta com razão alta
    é desvio de prática. Sem as duas juntas, a coluna não distingue as duas.
    """
    saida: dict[str, dict] = {}
    if not len(sinal_area):
        return saida
    cols = ["ID_COOPERADO", "CD_PROCEDIMENTO", "DS_PROCEDIMENTO",
            "excedente_itens", "razao_vs_alvo"]
    d = sinal_area[cols].copy()
    d["excedente_itens"] = d["excedente_itens"].fillna(0.0)
    for coop, g in d.groupby("ID_COOPERADO", sort=False):
        total = float(g["excedente_itens"].sum())
        if total <= 0:
            continue
        g = g.sort_values("excedente_itens", ascending=False)
        linhas = [{
            "codigo": r.CD_PROCEDIMENTO,
            "descricao": r.DS_PROCEDIMENTO,
            "excedente_itens": round(float(r.excedente_itens), 2),
            "pct": round(float(r.excedente_itens) / total, 4),
            "pct_fmt": fmt_pct(float(r.excedente_itens) / total),
            # contra a REFERÊNCIA ATIVA, porque é isso que a frase ao lado diz
            # ("12,2× a referência da área"). Ver razao_vs_alvo no pipeline.
            "razao": (None if pd.isna(r.razao_vs_alvo)
                      else round(float(r.razao_vs_alvo), 2)),
            "razao_fmt": (config.SEM_MEDIDA if pd.isna(r.razao_vs_alvo)
                          else f"{fmt(r.razao_vs_alvo, 1)}×"),
        } for r in g.head(n_topo).itertuples()]

        juntos = None
        if len(linhas) >= 2:
            primeiro, segundo = linhas[0]["pct"], linhas[1]["pct"]
            if primeiro and segundo / primeiro >= config.FRACAO_SEGUNDA_ORIGEM_RELEVANTE:
                juntos = round(primeiro + segundo, 4)
        # CONCENTRADA ou DIFUSA. A coluna absorveu "Procedimentos acima do
        # critério", então a contagem que aquela coluna dava continua aqui — é
        # justamente ela que sustenta a leitura difusa.
        concentrado = linhas[0]["pct"] >= config.FRACAO_ORIGEM_CONCENTRADA
        saida[coop] = {
            "concentrado": concentrado,
            # "do excedente" era ambíguo: esta leitura ordena por SOLICITAÇÕES
            # excedentes, e na mesma tela o Pareto ordena por R$. Sem dizer qual
            # das duas, o card e o gráfico pareciam se contradizer ao apontar
            # procedimentos diferentes. São duas lentes de propósito (prática e
            # dinheiro); o que faltava era nomear cada uma.
            "leitura": (f"concentra {fmt_pct(linhas[0]['pct'])} das solicitações "
                        f"excedentes" if concentrado else
                        f"solicitações excedentes distribuídas em {len(g)} "
                        f"procedimentos"),
            "topo": linhas[0],
            "top": linhas,
            "n_procedimentos": int(len(g)),
            "excedente_total": round(total, 2),
            "juntos_pct": juntos,
            "juntos_fmt": None if juntos is None else fmt_pct(juntos),
        }
    return saida


# leitura do motor -> léxico do produto (LEXICO_PRODUTO.md). A UI não traduz.
_LEITURA_CONCENTRACAO = {
    "protocolo carimbado": "rotina na carteira",
    "case-mix a investigar": "case-mix a investigar",
    "material (extensiva+intensiva)": "rotina na carteira e case-mix",
    "pouco volume": "pouco volume",
    "referência insuficiente": "referência insuficiente",
    "sem padrão distinto": "sem padrão distinto",
}


def leitura_concentracao(conc: pd.DataFrame,
                         origem: dict[str, dict]) -> dict[str, dict]:
    """Como os itens se distribuem entre os pacientes do cooperado.

    A concentração é medida POR PROCEDIMENTO, e a tabela tem uma linha por
    cooperado — então é preciso escolher qual procedimento a linha lê. A escolha:
    o MESMO que aparece em "Origem do excedente". Qualquer outro critério faria a
    célula da esquerda falar de um procedimento e a da direita de outro, na mesma
    linha, sem dizer que mudou de assunto.

    Consequência declarada: quem não tem origem (sem excedente medido) não tem
    leitura de concentração. Não é falha de cálculo, é ausência de objeto.

    Os números que sustentam a leitura viajam junto (regra do léxico: "rotina na
    carteira" nunca aparece sem "74% da carteira vs 7% dos pares"), e os dois
    denominadores obrigatórios também — percentual de carteira sem o tamanho da
    carteira não é leitura.
    """
    saida: dict[str, dict] = {}
    if conc is None or not len(conc):
        return saida
    idx = conc.set_index(["ID_COOPERADO", "CD_PROCEDIMENTO"])
    for coop, o in origem.items():
        chave = (coop, o["topo"]["codigo"])
        if chave not in idx.index:
            continue
        r = idx.loc[chave]
        if isinstance(r, pd.DataFrame):
            r = r.iloc[0]
        bruta = str(r["leitura_concentracao"])
        saida[coop] = {
            "rotulo": _LEITURA_CONCENTRACAO.get(bruta, bruta),
            "leitura_motor": bruta,
            "procedimento": o["topo"]["descricao"],
            "pct_carteira": round(float(r["pct_carteira"]), 4),
            "pct_carteira_fmt": fmt_pct(float(r["pct_carteira"])),
            "pct_carteira_pares_fmt": fmt_pct(float(r["pct_carteira_mediana_pares"])),
            "n_pacientes_proc": int(r["n_pacientes_proc"]),
            "n_pacientes_carteira": int(r["n_pacientes_carteira"]),
            "itens_por_paciente_fmt": fmt(float(r["itens_por_paciente_mediana"]), 1),
            "itens_por_paciente_pares_fmt": fmt(float(r["intensidade_mediana_pares"]), 1),
            "referencia_solida": bool(r["referencia_solida"]),
            # a frase inteira, para o hover — montada aqui, a tela imprime
            "detalhe": (
                f"{o['topo']['descricao']}: solicitado para "
                f"{fmt_pct(float(r['pct_carteira']))} dos beneficiários "
                f"atendidos ({int(r['n_pacientes_proc'])} de "
                f"{int(r['n_pacientes_carteira'])}), contra "
                f"{fmt_pct(float(r['pct_carteira_mediana_pares']))} na "
                f"referência da área. Intensidade de "
                f"{fmt(float(r['itens_por_paciente_mediana']), 1)} itens por "
                f"beneficiário, contra "
                f"{fmt(float(r['intensidade_mediana_pares']), 1)} na referência."
            ),
        }
    return saida


# Os três estados de um trimestre na mini-série. Correspondem exatamente ao que
# o `.spark` do guia desenha: barra neutra, barra alta, barra de critério.
TRIMESTRE_NAO_AVALIAVEL = "nao_avaliavel"
TRIMESTRE_AVALIAVEL = "avaliavel"
TRIMESTRE_SINALIZADO = "sinalizado"


def serie_por_trimestre(persistencia: dict | None,
                        n_fatias: int) -> dict[str, list[dict]]:
    """A SÉRIE de trimestres por cooperado, não a soma.

    `persistencia_temporal` produz a grade (cooperado, procedimento, janela,
    sinalizado) e a reduz a contagens. Aqui a grade volta a ser série: por
    trimestre, o cooperado foi sinalizado em ALGUM procedimento?

    "3/4" não distingue 1º-2º-3º de 1º-2º-4º, e a diferença é a conversa: um
    padrão que persiste e um que intermite pedem perguntas diferentes.

    TRÊS estados, não dois. A grade só tem linha para (cooperado, janela) em que
    o sinal era POSSÍVEL — cooperado avaliável na janela E norma do procedimento
    apresentável. Janela sem linha nenhuma não é "não sinalizado": é "não dava
    para sinalizar", e colapsar as duas em `False` pintaria de limpo um trimestre
    em que ninguém olhou. Por isso a série é montada sobre o intervalo COMPLETO
    de janelas (`n_fatias`), não sobre o que a grade traz.
    """
    if not persistencia or "por_janela" not in persistencia or n_fatias < 1:
        return {}
    pj = persistencia["por_janela"]
    if not len(pj):
        return {}
    g = (pj.groupby(["ID_COOPERADO", "janela"])
         .agg(sinalizado=("sinalizado", "any"),
              n_pares=("CD_PROCEDIMENTO", "nunique"))
         .reset_index())

    # índice por (cooperado, janela): a MAGNITUDE de cada barra e a direção da
    # série. A altura da barra é dado, como no componente do guia — barra de
    # altura fixa diria só "sim/não" e a série não teria o que ler.
    pjc = persistencia.get("por_janela_cooperado")
    indice = {}
    escala = {}
    if pjc is not None and len(pjc):
        for r in pjc.itertuples():
            if bool(r.avaliavel) and pd.notna(r.taxa):
                indice[(r.ID_COOPERADO, int(r.janela))] = float(r.taxa)
        for (coop_, _), v in indice.items():
            escala[coop_] = max(escala.get(coop_, 0.0), v)

    saida: dict[str, list[dict]] = {}
    for coop, d in g.groupby("ID_COOPERADO", sort=False):
        por_janela = {int(r.janela): (bool(r.sinalizado), int(r.n_pares))
                      for r in d.itertuples()}
        teto = escala.get(coop) or 0.0
        serie = []
        for j in range(1, n_fatias + 1):
            v = indice.get((coop, j))
            # altura RELATIVA ao próprio cooperado: a série lê a trajetória
            # DELE, não o tamanho dele contra os outros — isso é o gráfico de
            # distribuição. Piso de 12% para a barra existir mesmo perto de zero.
            altura = None if v is None or not teto else round(max(0.12, v / teto), 3)
            if j not in por_janela:
                serie.append({"janela": j, "estado": TRIMESTRE_NAO_AVALIAVEL,
                              "sinalizado": False, "n_pares_avaliaveis": 0,
                              "indice": v, "indice_fmt": config.SEM_MEDIDA,
                              "altura_rel": altura,
                              "motivo": "sem par avaliável neste trimestre"})
                continue
            sinalizado, n_pares = por_janela[j]
            serie.append({
                "janela": j,
                "estado": TRIMESTRE_SINALIZADO if sinalizado else TRIMESTRE_AVALIAVEL,
                "sinalizado": sinalizado,
                "n_pares_avaliaveis": n_pares,
                "indice": None if v is None else round(v, 4),
                "indice_fmt": config.SEM_MEDIDA if v is None else fmt(v),
                "altura_rel": altura,
                "motivo": None,
            })
        saida[coop] = serie
    return saida


def direcao_da_serie(serie: list[dict] | None) -> dict | None:
    """Para onde a série aponta: primeiro trimestre medido contra o último.

    Leitura, não medição nova — compara dois números que o motor já produziu.
    Menos de dois trimestres medidos não têm direção; "estável" quando a
    variação fica dentro de config.FAIXA_ESTABILIDADE_SERIE, porque oscilação de
    poucos por cento numa taxa trimestral é ruído, não tendência.
    """
    if not serie:
        return None
    medidos = [t for t in serie if t.get("indice") is not None]
    if len(medidos) < 2:
        return None
    ini, fim = medidos[0]["indice"], medidos[-1]["indice"]
    if not ini:
        return None
    variacao = (fim - ini) / ini
    if abs(variacao) <= config.FAIXA_ESTABILIDADE_SERIE:
        classe, rotulo, seta = "dir-flat", "estável", "→"
    elif variacao > 0:
        classe, rotulo, seta = "dir-up", "em alta", "↑"
    else:
        classe, rotulo, seta = "dir-down", "em queda", "↓"
    n_sin = sum(1 for t in serie if t["sinalizado"])
    return {
        "classe": classe, "rotulo": rotulo, "seta": seta,
        "variacao": round(variacao, 4),
        # "com algum procedimento acima": a contagem da série é POR TRIMESTRE
        # (algum procedimento sinalizado nele), diferente do n/n da coluna, que
        # é o procedimento mais persistente. Sem o rótulo, as duas contagens na
        # mesma célula leem como contradição.
        #
        # A SETA SAIU DAQUI (set/2026). Ela era colada no fim desta frase, que
        # fala de CONTAGEM de trimestres, enquanto ela descreve a TENDÊNCIA de
        # outra medida (exames por consulta). "4 de 4 trimestres acima do
        # critério → estável" não diz estável o quê, e na tela a seta ainda
        # aparecia duas vezes: como glifo ao lado dos quadrados e dentro do
        # texto. Agora a contagem é uma frase e a tendência é outra, com sujeito.
        "texto": (f"{n_sin} de {len(serie)} trimestres com ao menos um "
                  f"procedimento acima do critério"),
        "tendencia": f"Solicitações por consulta {rotulo} no período.",
        "detalhe": (f"Solicitações por consulta {rotulo} no período: {fmt(ini)} no "
                    f"primeiro trimestre medido, {fmt(fim)} no último "
                    f"({fmt_pct(variacao)})."),
    }


# Tipos de atendimento com pelo menos esta fração das consultas entram na linha
# do cabeçalho; abaixo disso é cauda, e cauda numa linha só vira ruído.
FRACAO_MIN_TIPO_ATENDIMENTO = 0.10


def tipos_de_atendimento(flags_coop) -> dict | None:
    """A composição do atendimento do cooperado, numa linha: os tipos com
    >= FRACAO_MIN_TIPO_ATENDIMENTO das consultas, do maior ao menor.

    Vem das colunas `pratica_*` da dim v2 (fração das consultas de cada família
    de atendimento). Deliberadamente SEM comparação com a área e sem estabilidade:
    é o retrato do que ele atende, não um juízo. O período é o da classificação
    (a dim não segue a janela da barra), e a nota diz isso.
    """
    if flags_coop is None:
        return None
    tipos = []
    for coluna, valor in flags_coop.items():
        if not str(coluna).startswith("pratica_") or pd.isna(valor):
            continue
        if float(valor) >= FRACAO_MIN_TIPO_ATENDIMENTO:
            nome = str(coluna).removeprefix("pratica_").split(" (")[0]
            tipos.append({"tipo": nome, "fracao": round(float(valor), 3),
                          "fracao_fmt": f"{float(valor):.0%}"})
    if not tipos:
        return None
    tipos.sort(key=lambda t: -t["fracao"])
    return {
        "tipos": tipos,
        "linha": " · ".join(f"{t['tipo']} {t['fracao_fmt']}" for t in tipos),
        "nota": ("Tipos de atendimento inferidos do conjunto de procedimentos de "
                 "cada consulta, no período da classificação "
                 f"{config.CLASSIFICACAO_VERSAO}."),
    }


def _em_revisao(flags_coop) -> dict | None:
    """Etiqueta de classificação na linha. Vazia na v2 (set/2026, decisão do
    usuário): a v1 marcava 3 cooperados com rótulo em revisão pelo médico; a
    v2 mede a fragilidade do rótulo (`no_limiar`, `perfil_instavel_no_ano` na
    dim), mas isso não vira etiqueta na tela. O campo fica no payload, sempre
    None, para o front não mudar de contrato."""
    return None


def _consistencia_do_cooperado(serie, n_fatias: int) -> dict:
    """A coluna "Trimestres acima do critério" da tabela da área.

    UMA medida só (27/ago). Até aqui a célula misturava duas: os quadrados
    contavam trimestres em que ALGUM procedimento passou o critério, e o texto
    ao lado vinha do procedimento MAIS PERSISTENTE do cooperado, com denominador
    próprio (os trimestres em que aquele procedimento teve volume para ser
    avaliado). Daí "▪▪▪▪ 2 de 2 trimestres", que lê como erro de cálculo e não
    era: eram duas perguntas na mesma célula, sem dizer qual era qual.
    Acontecia em 17 das 64 linhas de Ginecologia.

    O texto agora conta EXATAMENTE o que os quadrados mostram. A persistência
    por procedimento não se perde: é a coluna Consistência do dossiê, onde se
    investiga um caso e cada procedimento tem a própria linha.
    """
    if not serie:
        return {"rotulo": config.SEM_MEDIDA,
                "janelas_sinalizado": None, "janelas_avaliaveis": None,
                "trimestres": None, "direcao": None, "total_fatias": n_fatias,
                "motivo": ("janela única, consistência não reportável"
                           if n_fatias < config.MIN_JANELAS_AVALIAVEIS
                           else "sem par avaliável em janelas suficientes")}
    # avaliáveis = trimestres em que houve o que medir; sinalizados = os que
    # ficaram acima. É o mesmo par que pinta os quadrados.
    n_av = sum(1 for t in serie if t["estado"] != TRIMESTRE_NAO_AVALIAVEL)
    n_sin = sum(1 for t in serie if t["estado"] == TRIMESTRE_SINALIZADO)
    return {
        "rotulo": config.SEM_MEDIDA if not n_av else f"{n_sin}/{n_av}",
        "janelas_sinalizado": n_sin if n_av else None,
        "janelas_avaliaveis": n_av or None,
        # a SÉRIE, não só a soma: 1º-2º-3º e 1º-2º-4º dão o mesmo "3/4"
        # e pedem perguntas diferentes
        "trimestres": serie,
        "direcao": direcao_da_serie(serie),
        "total_fatias": n_fatias,
        "motivo": None if n_av else "sem trimestre avaliável no período",
    }


def _campos_custo(c: dict | None) -> dict:
    """Os campos de R$ POR COOPERADO da tabela: custo por consulta e valor total.

    Sem par no motor de execução, os quatro campos saem None e a célula fica
    vazia: valor total é SOMA, e um zero ali leria como "não custa nada" em vez
    de "não medido" (mesma distinção do ajuste 4 do CLAUDE.md).

    `cobertura_preco` viaja junto porque a soma se apoia nela: 99,8% da base tem
    preço, mas quem lê um total precisa saber sobre que fração ele se apoia.
    """
    if not c:
        return {"custo_por_consulta": None, "custo_por_consulta_fmt": None,
                "valor_total": None, "valor_total_fmt": None,
                "cobertura_preco": None}
    cpc, vt = c.get("custo_por_consulta"), c.get("valor_total_solicitado")
    return {
        "custo_por_consulta": None if cpc is None else round(float(cpc), 2),
        "custo_por_consulta_fmt": None if cpc is None else fmt_reais(cpc),
        "valor_total": None if vt is None else round(float(vt), 2),
        "valor_total_fmt": None if vt is None else fmt_reais(vt),
        "cobertura_preco": (None if c.get("cobertura_preco") is None
                            else round(float(c["cobertura_preco"]), 4)),
    }


def linhas_cooperados(posicao_area: pd.DataFrame, norma_linha,
                      gatilho_usado: str | None, classificacao: pd.DataFrame,
                      sinal_area: pd.DataFrame, persistencia: dict | None,
                      n_fatias: int, rotulos_posicao: pd.Series,
                      degraus_por_cooperado: dict[str, list[str]] | None = None,
                      origem: dict[str, dict] | None = None,
                      concentracao: dict[str, dict] | None = None,
                      serie: dict[str, list[dict]] | None = None,
                      cesta_excluida: frozenset = frozenset(),
                      postos_perfil: dict[str, dict[str, dict]] | None = None,
                      reais_coop: dict[str, float] | None = None,
                      custo_coop: dict[str, dict] | None = None,
                      ) -> list[dict]:
    """Uma linha por cooperado da área, com todas as colunas da tabela do guia:
    cooperado · perfil · consultas · índice/consulta · posição (percentil OU
    posto + régua) · consistência · variação excedente.

    Não avaliáveis permanecem na lista, esmaecidos, com o motivo, nada some
    da tela (guia §04, última linha do exemplo).

    VARIAÇÃO EXCEDENTE, substitui a premissa do guia (ver CLAUDE.md, ajuste 4):
        O exemplo do style_guide mostra travessão na variação excedente de quem
        não está acima do critério AGREGADO. Aquilo assumia que as duas lentes
        coincidem, e elas não coincidem: o excedente é medido POR PROCEDIMENTO,
        e um cooperado dentro da referência no agregado pode ter procedimentos
        específicos acima do critério daquele procedimento. Esses pares já
        passaram os três portões (avaliável & apresentável & sinalizado); é a
        lente forte do método (rigor-estatistico §3: magnitude é onde se age).
        Portanto o valor REAL é sempre servido. O critério agregado governa o
        REALCE da linha (`acima_do_criterio`/`estado_linha`), nunca a medição.
        Travessão fica só para quem não tem nenhum procedimento sinalizado ,
        ausência de par que passe os portões, não um zero medido.
    """
    flags = classificacao.set_index("ID_COOPERADO")
    exc = (sinal_area.groupby("ID_COOPERADO")
           .agg(excedente_itens=("excedente_itens", "sum"),
                n_procs=("CD_PROCEDIMENTO", "nunique"))
           if len(sinal_area) else
           pd.DataFrame(columns=["excedente_itens", "n_procs"]))

    # A persistência do MELHOR par do cooperado saiu daqui (27/ago): ela vinha
    # para a coluna Consistência e contradizia os quadrados ao lado, que contam
    # outra coisa. Quem quer a leitura por procedimento tem a tabela do dossiê.

    tem_norma = norma_linha is not None and gatilho_usado is not None
    p25 = float(norma_linha["p25"]) if norma_linha is not None else None
    p75 = float(norma_linha["p75"]) if norma_linha is not None else None
    mediana = float(norma_linha["mediana"]) if norma_linha is not None else None
    valor_crit = float(norma_linha[gatilho_usado]) if tem_norma else None

    escala = None
    if tem_norma:
        taxas = posicao_area.loc[posicao_area["avaliavel"],
                                 "taxa_exames_por_consulta"].astype(float).tolist()
        if taxas:
            escala = _escala(taxas + [p25, p75, mediana, valor_crit])

    linhas = []
    for idx, linha in posicao_area.iterrows():
        coop = linha["ID_COOPERADO"]
        taxa = float(linha["taxa_exames_por_consulta"])
        avaliavel = bool(linha["avaliavel"])
        rotulo_pos = rotulos_posicao.get(idx, config.SEM_MEDIDA)
        traducao = apr.traduzir_percentil(rotulo_pos)
        sinalizado = bool(linha["acima_gatilho"]) and avaliavel

        posicao = {
            "rotulo": rotulo_pos if avaliavel else config.SEM_MEDIDA,
            "tipo": ("percentil" if traducao else
                     "posto" if avaliavel and rotulo_pos != config.SEM_MEDIDA else "indisponivel"),
            "traducao": traducao,
            "classe": ("pctl-crit" if sinalizado else
                       "pctl-warn" if avaliavel and p75 is not None and taxa > p75
                       else "pctl"),
            "indisponivel_motivo": (None if avaliavel
                                    else "não avaliável · volume abaixo do mínimo"),
            "regua": None,
        }
        if escala is not None and avaliavel:
            posicao["regua"] = {
                "iqr_pos_pct": _pos(p25, escala),
                "iqr_largura_pct": round(_pos(p75, escala) - _pos(p25, escala), 2),
                "mediana_pos_pct": _pos(mediana, escala),
                "criterio_pos_pct": _pos(valor_crit, escala),
                "marca_pos_pct": _pos(taxa, escala),
                "marca_classe": {"crit": "critmk", "read": "warnmk", "neutro": ""}[
                    _classe_ponto(taxa, p75, valor_crit)],
            }

        n_procs = int(exc["n_procs"].get(coop, 0)) if len(exc) else 0
        # medição independe do realce: o valor real vai sempre, mesmo para quem
        # está dentro da referência no agregado (ajuste 4)
        exc_itens = float(exc["excedente_itens"].get(coop, 0.0)) if n_procs else None

        linhas.append({
            "id": coop,
            "sub_perfis": _sub_perfis(flags.loc[coop] if coop in flags.index else None),
            # posto DENTRO de cada perfil que ele carrega; a tela mostra o do
            # perfil em cena. Não é régua nova: a comparação segue sendo a da área.
            "postos_perfil": {f: p[coop] for f, p in (postos_perfil or {}).items()
                              if coop in p},
            # só quando a origem CAI na cesta do próprio perfil; nunca genérico
            "perfil_explica": _perfil_explica(
                coop, str(linha["AREA_ATUACAO"]),
                flags.loc[coop] if coop in flags.index else None,
                ((origem or {}).get(coop) or {}).get("topo", {}).get("codigo"),
                cesta_excluida),
            "consultas": int(linha["consultas_totais"]),
            "consultas_fmt": fmt(linha["consultas_totais"], 0),
            "solicitacoes": int(linha["total_itens"]),
            "solicitacoes_fmt": fmt(linha["total_itens"], 0),
            "indice": round(taxa, 4), "indice_fmt": fmt(taxa),
            # CUSTO POR CONSULTA e VALOR TOTAL: magnitude em R$, não desvio.
            # Vêm de custo_coop (pipeline_execucao), valorados a preço mediano
            # interno — MESMA quarentena do excedente em R$, e por isso o mesmo
            # aviso viaja no title da célula. Ausente quando o motor de execução
            # não rodou; nunca zero, que leria como "não custa nada".
            **_campos_custo((custo_coop or {}).get(coop)),
            "razao_vs_mediana": (None if pd.isna(linha["razao_vs_mediana"])
                                 else round(float(linha["razao_vs_mediana"]), 3)),
            "posicao": posicao,
            # ORIGEM DO EXCEDENTE e LEITURA DE CONCENTRAÇÃO leem o MESMO
            # procedimento (o que puxa o excedente); ver leitura_concentracao().
            # Sem excedente medido, não há origem — e sem origem, não há leitura.
            # FILA DE TRIAGEM CLÍNICA. Antes o motivo só era impresso pelo
            # painel de excluídos, e lá só entra quem já está fora da construção
            # da referência — 3 dos 4 casos da fila nunca apareciam. A etiqueta
            # na linha não muda número nenhum: declara que a CLASSIFICAÇÃO
            # daquele cooperado está sob revisão, não o número dele.
            "em_revisao": _em_revisao(flags.loc[coop] if coop in flags.index else None),
            "origem_excedente": (origem or {}).get(coop),
            "concentracao": (concentracao or {}).get(coop),
            "consistencia": _consistencia_do_cooperado(
                (serie or {}).get(coop), n_fatias),
            "excedente_itens": None if exc_itens is None else round(exc_itens, 2),
            "excedente_fmt": config.SEM_MEDIDA if exc_itens is None else fmt(exc_itens, 0),
            "excedente_motivo": (None if exc_itens is not None else
                                 "nenhum procedimento acima do critério "
                                 "(nada a medir, não é zero medido)"),
            # ESTIMATIVA (preço interno provisório): soma dos pares sinalizados
            # COM preço; pode faltar mesmo com excedente medido (par sem preço
            # nas contas), e aí não viaja número nenhum
            "excedente_reais": ((reais_coop or {}).get(coop) and
                                round(float(reais_coop[coop]), 2)),
            "excedente_reais_fmt": (None if not (reais_coop or {}).get(coop) else
                                    fmt_reais(reais_coop[coop])),
            "procedimentos_em_revisao": n_procs,
            "avaliavel": avaliavel,
            "forma_referencia": avaliavel and bool(linha["elegivel_norma"]),
            "acima_do_criterio": sinalizado,
            # o realce da linha vem do critério AGREGADO; a medição, do
            # procedimento. Os grupos são os DEGRAUS DA CASCATA alcançados — o
            # front filtra por pertencimento, não recalcula regra (ajuste 4).
            "grupos": (degraus_por_cooperado or {}).get(coop, ["medidos"]),
            "estado_linha": ("acima_do_criterio" if sinalizado else
                             "nao_avaliavel" if not avaliavel else "normal"),
            "gatilho_usado": (None if pd.isna(linha["gatilho_usado"])
                              else linha["gatilho_usado"]),
        })
    return linhas


# ─────────────────────────────────────────────────────────────────────────────
# Aba "Procedimentos"
# ─────────────────────────────────────────────────────────────────────────────

def _pareto_montar(valores: list[tuple[str, float]], unidade: str,
                   custos: dict[str, float] | None = None,
                   excedentes: dict[str, float] | None = None) -> tuple | None:
    """Núcleo comum dos Paretos: ordena, acumula, marca o núcleo do limiar e
    redige a leitura de concentração. `valores` = [(id, reais)]; `unidade` é a
    palavra da frase ("cooperados", "procedimentos"). Devolve (linhas, total,
    leitura, n_nucleo) ou None sem valor a distribuir.

    ── barra aninhada (`custos` + `excedentes`) ─────────────────────────────
    Com os dois, a barra deixa de ter uma grandeza só: o COMPRIMENTO passa a ser
    o custo total e o trecho preenchido, o excedente dentro dele. `valores`
    continua sendo o que ORDENA e o que ACUMULA, e é por isso que os três
    viajam separados: ordenar por excedente desenhando custo é legítimo (o
    excedente é o produto, o custo é o contexto), e as barras então não descem
    em ordem — quem lê vê logo que comprimento e posição respondem a perguntas
    diferentes. Sem `custos`, nada muda: barra de uma grandeza só."""
    total = float(sum(v for _, v in valores))
    if not valores or total <= 0:
        return None
    linhas, acum = [], 0.0
    duplo = bool(custos)
    # a escala do desenho é a grandeza da BARRA, que com `custos` não é mais a
    # mesma coisa que a grandeza que ordena
    maior = (max((float(custos.get(k) or 0.0) for k, _ in valores), default=0.0)
             if duplo else max(v for _, v in valores))
    if duplo and maior <= 0:
        duplo = False
        maior = max(v for _, v in valores)
    for chave, v in sorted(valores, key=lambda kv: -kv[1]):
        # a barra pertence ao NÚCLEO se o acumulado ANTES dela ainda não
        # atingiu o limiar: é o menor conjunto que chega lá
        no_nucleo = (acum / total) < config.LIMIAR_CONCENTRACAO_PARETO
        acum += float(v)
        linhas.append({
            "id": chave,
            "reais": round(float(v), 2),
            "reais_fmt": fmt_reais(v),
            "pct_do_total": round(float(v) / total, 4),
            "pct_do_total_fmt": fmt_pct(float(v) / total),
            # largura da barra: proporção do MAIOR, não do total. É escala de
            # desenho, não leitura — a leitura é o valor ao lado. Contra o
            # total, a maior barra ocuparia 26% da pista e todas as outras
            # virariam risquinhos.
            "largura_pct": round(float(v) / maior * 100, 2),
            "pct_acumulado": round(acum / total, 4),
            "pct_acumulado_fmt": fmt_pct(acum / total),
            # o acumulado também em R$: "56%" responde que fração, e não quanto.
            # Numa reunião a pergunta é sempre "quanto vale parar nos três
            # primeiros" — e essa é a coluna que responde sem fazer conta.
            "reais_acumulado": round(acum, 2),
            "reais_acumulado_fmt": fmt_reais(acum),
            "no_nucleo": no_nucleo,
        })
        if duplo:
            c = float((custos or {}).get(chave) or 0.0)
            e = min(float((excedentes or {}).get(chave) or 0.0), c)
            linhas[-1].update({
                "custo": round(c, 2), "custo_fmt": fmt_reais(c),
                "excedente_rs": round(e, 2), "excedente_rs_fmt": fmt_reais(e),
                # comprimento = custo contra o MAIOR custo da lista
                "largura_pct": round(c / maior * 100, 2),
                # e o trecho preenchido é uma fração DA BARRA, não da pista:
                # assim ele continua sendo a parcela de dentro do próprio custo
                # em qualquer largura de tela
                "largura_exc_pct": round(e / c * 100, 2) if c > 0 else 0.0,
            })
    nucleo = [l for l in linhas if l["no_nucleo"]]
    pct_nucleo = fmt_pct(nucleo[-1]["pct_acumulado"] if nucleo else 0)
    leitura = (f"{len(nucleo)} de {len(linhas)} {unidade} concentram "
               f"{pct_nucleo} do valor")
    # ── o denominador se NOMEIA, no hover ────────────────────────────────────
    # Este N não é o dos comparáveis do cabeçalho: aqui só entra quem tem
    # variação excedente valorada, e quem não tem nenhum procedimento acima do
    # critério fica de fora. Em 12 meses os dois números coincidem em
    # Ginecologia (63) por acaso do dado; em mai–out/25 são 62 e 61. Dois
    # denominadores diferentes com a mesma cara na mesma tela é erro de
    # leitura esperando acontecer — a frase curta cabe no cabeçalho, e de quem
    # é o denominador fica à mão de quem passa o cursor.
    leitura_hover = (f"Os {len(linhas)} {unidade} do denominador são os que têm "
                     f"variação excedente valorada, não os comparáveis da área. "
                     f"Os {len(nucleo)} do núcleo, {fmt_pct(len(nucleo) / len(linhas))} "
                     f"deles, somam {pct_nucleo} do total.")
    return linhas, total, leitura, len(nucleo), leitura_hover


# A RESSALVA DE MÉTODO DO PARETO SAIU (set/2026), por decisão do produto. Ela
# dizia "Estimativa de teto: valora a preços de referência internos todas as
# solicitações, e nem toda solicitação é executada. Não representa economia
# realizada." O vocabulário de quarentena e de teto saiu junto, do app inteiro.
#
# O que a base de preço é continua dito onde ele é lido: na definição das
# colunas de R$ ("a preços de referência internos derivados das contas do
# período") e no hover do valor no dossiê. Registrado aqui para a remoção não
# ser confundida com esquecimento.


# ─────────────────────────────────────────────────────────────────────────────
# Dossiê do cooperado (espec §3): "por que este caso existe, e o que o defende?"
# ─────────────────────────────────────────────────────────────────────────────

# Como a REFERÊNCIA é construída, em uma frase, para o rodapé de cada KPI.
# Uma constante e não texto repetido: a definição é a mesma nos sete, e sete
# cópias de uma frase é como elas passam a divergir.
_TITULO_REFERENCIA = (
    "Mediana apurada entre os cooperados da mesma área de atuação que atingem "
    "o volume mínimo de consultas no período."
)


def _par_da_area(rotulo: str, valor_fmt: str, mediana_area, titulo: str,
                 chave: str | None = None) -> dict:
    """Um número do cooperado com a REFERÊNCIA DA ÁREA ao lado (espec §3: todo
    número do cabeçalho viaja acompanhado).

    O rótulo diz "referência" e não "mediana dos comparáveis" (27/ago):
    "comparáveis" é vocabulário do método, e a tela não deve exigir que o leitor
    o conheça para ler um número. Como a referência é construída fica no hover
    da própria linha.
    """
    return {"rotulo": rotulo, "valor_fmt": valor_fmt,
            # a CHAVE existe para o resumo do caso agrupar estes mesmos números
            # em Volume / Médias / Custo sem casar o rótulo por string: rótulo é
            # texto de tela e muda; chave é contrato.
            "chave": chave or slug(rotulo),
            "par_fmt": (config.SEM_MEDIDA if mediana_area is None
                        else f"referência: {mediana_area}"),
            "par_bruto": (None if mediana_area is None else str(mediana_area)),
            "titulo_longo": titulo,
            "par_titulo": (None if mediana_area is None else _TITULO_REFERENCIA)}


def _mediana_das_linhas(linhas_area: list[dict] | None, campo: str,
                        casas: int = 0):
    """Mediana de um campo entre os COMPARÁVEIS, lida das linhas já montadas.

    Os três primeiros KPIs tiram o par de `posicao_area` porque nascem lá. Os de
    R$ não existem no motor de posição: são montados por `linhas_cooperados` a
    partir do motor de execução. Ler as linhas prontas mantém o par do dossiê
    idêntico ao número que a tabela da área mostra, em vez de recalcular a mesma
    mediana por outro caminho e arriscar divergir.
    """
    if not linhas_area:
        return None
    vals = [l[campo] for l in linhas_area
            if l.get("avaliavel") and l.get(campo) is not None]
    if not vals:
        return None
    vals.sort()
    meio = len(vals) // 2
    m = vals[meio] if len(vals) % 2 else (vals[meio - 1] + vals[meio]) / 2
    return fmt_reais(m) if casas < 0 else fmt(m, casas)


def cabecalho_dossie(linha: dict, posicao_area: pd.DataFrame,
                     pacientes: pd.Series,
                     linhas_area: list[dict] | None = None) -> list[dict]:
    """A faixa de KPIs do dossiê, cada número com a mediana dos comparáveis.

    Ordem: MAGNITUDE (o tamanho da prática), depois INTENSIDADE (por consulta),
    depois DINHEIRO, e o excesso por último. É a mesma leitura da faixa da tela
    de Área, para as duas telas se lerem do mesmo jeito.
    """
    coop = linha["id"]
    comp = posicao_area[posicao_area["avaliavel"]]
    pac_coop = pacientes.get(coop)
    pac_comp = pacientes.reindex(comp["ID_COOPERADO"]).dropna()
    return [
        _par_da_area("Consultas", linha["consultas_fmt"],
                     fmt(comp["consultas_totais"].median(), 0) if len(comp) else None,
                     "Atendimentos distintos no período, agrupados por paciente. "
                     "Contagem agregada, sem identificação individual.", "consultas"),
        _par_da_area("Pacientes distintos",
                     config.SEM_MEDIDA if pac_coop is None else fmt(pac_coop, 0),
                     fmt(pac_comp.median(), 0) if len(pac_comp) else None,
                     "Beneficiários distintos atendidos no período. Contagem agregada, sem "
                     "identificação individual.", "pacientes"),
        _par_da_area("Solicitações", linha["solicitacoes_fmt"],
                     fmt(comp["total_itens"].median(), 0) if len(comp) else None,
                     "Total de procedimentos solicitados no período.", "solicitacoes"),
        _par_da_area("SADT por consulta", linha["indice_fmt"],
                     fmt(comp["taxa_exames_por_consulta"].median()) if len(comp) else None,
                     "Solicitações por consulta atendida no período.", "sadt_por_consulta"),
        # ── R$ (mesma quarentena do excedente em R$: preço interno derivado) ──
        _par_da_area("Custo por consulta",
                     linha.get("custo_por_consulta_fmt") or config.SEM_MEDIDA,
                     _mediana_das_linhas(linhas_area, "custo_por_consulta", -1),
                     "Valor do que foi solicitado no período, dividido pelas consultas "
                     "atendidas. Preços internos provisórios, ainda não "
                     "homologados contra a tabela contratual.", "custo_por_consulta"),
        _par_da_area("Custo total",
                     linha.get("valor_total_fmt") or config.SEM_MEDIDA,
                     _mediana_das_linhas(linhas_area, "valor_total", -1),
                     "Valor total do que foi solicitado no período. Mede o porte da "
                     "atividade, não o desvio. Preços internos provisórios.", "custo_total"),
        _par_da_area("Custo do excesso",
                     linha.get("excedente_reais_fmt") or config.SEM_MEDIDA,
                     _mediana_das_linhas(linhas_area, "excedente_reais", -1),
                     "Valor das solicitações acima da referência da área. Indica "
                     "oportunidade de revisão, não economia já realizada.", "custo_excesso"),
    ]


_GRUPOS_RESUMO = (
    ("Volume no período", ("consultas", "solicitacoes")),
    ("Médias por consulta", ("sadt_por_consulta", "custo_por_consulta")),
    ("Custo no período", ("custo_total", "custo_excesso")),
)


def carteira_atendida(minha: dict | None, da_area: dict | None) -> dict | None:
    """A carteira do cooperado por faixa de idade, contra a da área.

    ── por que isto existe numa tela que mede frequência ──────────────────────
    Porque a primeira defesa de quem é sinalizado é "a minha carteira é
    diferente", e ela às vezes está certa. cooperado_19 tem 57% da carteira
    acima de 50 anos contra 32% da área, e ele é o caso com um painel de
    marcadores tumorais 40 vezes acima da referência. Sem este bloco, a tela
    afirma a frequência e esconde a pergunta que a explica ou não.

    NÃO ENTRA EM CÁLCULO. É contexto declarado (METODOLOGIA §7.3): nenhuma taxa,
    norma ou excedente lê esta saída, e o excedente NÃO é rateado por faixa —
    para isso seria preciso a idade na data de cada solicitação, e distribuir
    pela composição da carteira produziria número inventado sobre um médico.

    ── os dois portões ───────────────────────────────────────────────────────
    Carteira pequena (config.MIN_BENEFICIARIOS_CARTEIRA) não sustenta composição:
    uma pessoa move uma faixa inteira. E cobertura baixa
    (config.COBERTURA_MINIMA_PERFIL) descreveria uma minoria como se fosse o
    todo. Fechado qualquer um dos dois, o bloco declara o motivo em vez de
    desenhar.

    Hoje a cobertura é PLENA (a idade vem da requisição, não das contas), e por
    isso a base só é escrita quando falta alguém: uma linha dizendo "idade
    conhecida em 100% dos beneficiários" é ruído que ensina o leitor a ignorar
    ressalva. Faltando um, ela volta com o número exato.
    """
    if not minha:
        return None
    n, cob = minha["n_beneficiarios"], minha["cobertura"]
    if n < config.MIN_BENEFICIARIOS_CARTEIRA:
        return {"n_fmt": fmt(n, 0), "faixas": [], "motivo": (
            f"Carteira de {fmt(n, 0)} beneficiários no período, abaixo do mínimo "
            f"de {config.MIN_BENEFICIARIOS_CARTEIRA} para descrever a composição.")}
    if cob < config.COBERTURA_MINIMA_PERFIL:
        return {"n_fmt": fmt(n, 0), "faixas": [], "motivo": (
            f"Idade conhecida em {fmt_pct(cob)} dos beneficiários do período, "
            f"abaixo do mínimo para descrever a composição.")}

    por_area = {f["rotulo"]: f["fracao"] for f in (da_area or {}).get("faixas", [])}
    n_com = minha["n_com_idade"]
    parcial = n_com < minha["n_beneficiarios"]

    # AS SEIS FATIAS SOMAM 100% NA TELA. Arredondar cada uma isolada dava 101%
    # em 3 de cada 25 cooperados (2 + 9 + 11 + 22 + 36 + 20 fecha; 5 + 20 + 30 +
    # 26 + 15 + 5 não), e composição que não fecha faz o leitor procurar a
    # sétima faixa que não existe. Maior resto: a sobra vai para as fatias com a
    # maior parte fracionária, que é a mesma técnica das barras trimestrais.
    _pcts = _maior_resto([f["fracao"] or 0.0 for f in minha["faixas"]])
    _area_pcts = _maior_resto([por_area.get(f["rotulo"]) or 0.0
                               for f in minha["faixas"]]) if por_area else None
    faixas = []
    for i, f in enumerate(minha["faixas"]):
        pa = por_area.get(f["rotulo"])
        faixas.append({
            "rotulo": f["rotulo"],
            "n": f["n"], "n_fmt": fmt(f["n"], 0),
            "fracao_fmt": f"{_pcts[i]}%",
            # A PISTA É A ESCALA 0–100%, e a barra é o próprio percentual.
            #
            # Antes a largura era relativa à maior faixa das duas distribuições,
            # e o resultado era uma barra CHEIA rotulada "36%". Barra cheia que
            # não vale 100% obriga o leitor a descobrir o teto do eixo para ler
            # o comprimento, e é o tipo de escala que a §12 das DIRETRIZES chama
            # de enganosa. Em 0–100% as seis barras são curtas, mas cada
            # comprimento É o número escrito ao lado, e o traço da referência
            # cai onde o percentual dela manda.
            "largura_pct": round((f["fracao"] or 0.0) * 100, 2),
            # "referência", nunca "área": é a MESMA palavra que os números de
            # cima usam para a mediana dos comparáveis, e duas palavras para a
            # mesma coisa no mesmo cartão fazem procurar a diferença.
            "area_fmt": (config.SEM_MEDIDA if pa is None or _area_pcts is None
                         else f"referência: {_area_pcts[i]}%"),
            "area_pct": (None if pa is None else round(pa * 100, 2)),
            # o hover conta QUANTAS pessoas há na faixa, e o denominador é o da
            # fração. "com idade conhecida" só entra quando ela de fato falta de
            # alguém: com cobertura plena a frase sugeria um subconjunto que não
            # existe, e fazia perguntar de quem é a idade que falta.
            "titulo": (f"{fmt(f['n'], 0)} de {fmt(n_com, 0)} beneficiários"
                       + (" com idade conhecida" if parcial
                          else " atendidos no período")),
        })
    return {
        "n": n, "n_fmt": fmt(n, 0),
        "por_beneficiario_fmt": None,
        "idade_mediana_fmt": (None if minha["idade_mediana"] is None
                              else fmt(minha["idade_mediana"], 0)),
        "idade_mediana_area_fmt": (None if not da_area or da_area["idade_mediana"] is None
                                   else fmt(da_area["idade_mediana"], 0)),
        "cobertura_fmt": fmt_pct(cob),
        "base": (None if minha["n_com_idade"] >= n else
                 f"Idade conhecida em {fmt(minha['n_com_idade'], 0)} dos "
                 f"{fmt(n, 0)} beneficiários do período ({fmt_pct(cob)}). "
                 f"As fatias são sobre esses."),
        "faixas": faixas,
        "motivo": None,
    }


def faixas_do_exame(bruto: dict | None,
                    com_referencia: bool = True) -> dict | None:
    """A repartição etária das solicitações de um exame, pronta para desenhar.

    Mesma forma de `carteira_atendida` de propósito: a tela reusa a barra com o
    traço da referência, e o leitor aprende o desenho uma vez. O que muda é o
    que a barra mede — lá é composição de gente, aqui é composição de pedido.

    A CONTAGEM é o número que o analista pediu; a FATIA é o que compara, porque
    contagem de indivíduo não tem contrapartida no grupo.

    ── A REFERÊNCIA SÓ EXISTE NO NÍVEL DO COOPERADO (set/2026) ─────────────
    `com_referencia=False` no painel da ÁREA, e não é preferência: ali o sujeito
    da barra É a área, e a linha de referência cairia em cima da própria barra.
    Traço que marca o mesmo lugar da barra não compara nada, e ainda sugere que
    há um segundo conjunto ali — o leitor procura a diferença entre dois números
    idênticos. Comparar contra a área só diz alguma coisa quando o sujeito é
    outro, que é o caso do painel do dossiê.

    SEM PISO DE VOLUME, e é decisão. Houve um (MIN_SOLICITACOES_FAIXA), com o
    argumento de que "8% numa faixa" pode ser uma solicitação só. O argumento
    vale para a porcentagem, não para a contagem — e a contagem está impressa ao
    lado de cada fatia, que é o que a lei analítica pede. Com o n na tela, o piso
    escondia dado real, agregado sem inferência nenhuma.
    """
    if not bruto or not bruto.get("total"):
        return None
    total = bruto["total"]

    pcts = _maior_resto([f["fracao"] or 0.0 for f in bruto["faixas"]])
    pcts_area = (_maior_resto([f["fracao_area"] or 0.0 for f in bruto["faixas"]])
                 if com_referencia else None)
    faixas = []
    for i, f in enumerate(bruto["faixas"]):
        faixas.append({
            "rotulo": f["rotulo"],
            "n": f["n"], "n_fmt": fmt(f["n"], 0),
            "fracao_fmt": f"{pcts[i]}%",
            "largura_pct": round((f["fracao"] or 0.0) * 100, 2),
            "area_fmt": (f"referência: {pcts_area[i]}%" if pcts_area else None),
            "area_pct": (round((f["fracao_area"] or 0.0) * 100, 2)
                         if com_referencia else None),
            "titulo": (f"{fmt(f['n'], 0)} de {fmt(total, 0)} solicitações "
                       f"deste procedimento no período"),
        })
    return {"total": total, "total_fmt": fmt(total, 0), "faixas": faixas,
            "motivo": None}


def resumo_do_caso(cabecalho: list[dict], frase: str | None,
                   partes: list[str] | None, barra: dict | None,
                   carteira: dict | None, consultas_por_benef: float | None) -> dict:
    """O caso em um bloco: a frase, os números com o par da área, o lugar dele
    no dinheiro da área, e a carteira que ele atende.

    Substitui a faixa de sete cartões de KPI no topo do dossiê. A faixa dava aos
    sete números o MESMO peso e nenhuma relação entre eles: sete caixas de 26px
    em linha, e o leitor montava sozinho a leitura "ele atende muito, pede na
    média, e o dinheiro está no excesso". Aqui os mesmos números vêm agrupados
    pela pergunta que respondem (quanto ele faz · com que intensidade · quanto
    custa), a frase do caso abre o bloco e a carteira fecha com o contexto.

    Nenhum número novo nasce aqui: `cabecalho` já vem montado com o par da área,
    e este bloco só o AGRUPA por chave.
    """
    por_chave = {e["chave"]: e for e in (cabecalho or [])}
    grupos = []
    for rotulo, chaves in _GRUPOS_RESUMO:
        linhas = [por_chave[c] for c in chaves if c in por_chave]
        if linhas:
            grupos.append({"rotulo": rotulo, "linhas": linhas})

    # UMA nota, e ela é sobre DINHEIRO. A segunda que existia aqui repetia
    # inteira o subtítulo ("excedente distribuído em 49 procedimentos",
    # "padrão sustentado nos 4 trimestres"): o mesmo fato em dois lugares do
    # mesmo cartão, a 20px um do outro (DIRETRIZES §8, informação redundante).
    #
    # Esta sobrevive porque diz o que o subtítulo não diz: o subtítulo posiciona
    # o cooperado no ÍNDICE ("acima de 97% da área"), e esta o posiciona no
    # CUSTO. São duas ordens diferentes, e a frase nomeia qual é a dela — sem
    # isso as duas liam como a mesma coisa dita de dois jeitos.
    notas = []
    if barra:
        notas.append(f"{barra['posto']}º maior custo excedente entre os "
                     f"{barra['total']} comparáveis, {barra['pct_do_total_fmt']} "
                     f"do total da área")

    if carteira and consultas_por_benef:
        carteira["por_beneficiario_fmt"] = fmt(consultas_por_benef, 2)
    # ITENS, e não uma frase e uma nota soltas: cada afirmação sobre o caso é uma
    # linha com marca própria, na mesma gramática dos fatores de contexto. Duas
    # linhas de texto corrido sob o título liam como parágrafo perdido.
    return {"frase": frase, "grupos": grupos,
            "itens": (partes or []) + notas,
            "carteira": carteira,
            "pacientes": por_chave.get("pacientes")}


def _confianca_do_par(row_conf) -> dict:
    """Faixa de incerteza do excedente de UM par (bootstrap por paciente).

    Na tela só aparece o piso QUANDO EXISTE (sub-linha da variação excedente);
    os estados sem piso ficam no payload, sem vocabulário interno na página.
    """
    if row_conf is None:
        return {"estado": "nao_avaliado", "rotulo": None, "detalhe": None}
    if not bool(row_conf["calculavel"]):
        return {"estado": "nao_calculavel", "rotulo": None, "detalhe": None}
    piso = fmt(row_conf["excedente_piso"], 0)
    central = fmt(row_conf["excedente_central"], 0)
    # O texto responde à objeção que o cooperado vai levantar — "esse número vem
    # de uns poucos casos atípicos" —, e não descreve o método. "Limite inferior
    # do intervalo de confiança" era exato e ilegível: quem lê a tela é auditor
    # assistencial, não estatístico. O método vai no hover, para quem quiser.
    return {"estado": "calculavel",
            "piso_itens": round(float(row_conf["excedente_piso"]), 2),
            "rotulo": f"{piso} de {central} se sustentam",
            "detalhe": (f"Das {central} solicitações acima da referência, {piso} "
                        f"se mantêm mesmo sem o peso dos beneficiários que mais "
                        f"receberam. Verificado sorteando a carteira do cooperado "
                        f"mil vezes: em 9 de cada 10 sorteios a variação excedente "
                        f"ficou acima de {piso}.")}


def _serie_do_procedimento(janelas_proc: pd.DataFrame | None, cd: str,
                           n_fatias: int) -> list[dict] | None:
    """A série de trimestres DE UM PROCEDIMENTO, na mesma forma que a coluna
    Consistência da tabela da área consome (`serie_por_trimestre`).

    Mesma forma de propósito: o front reusa o MESMO desenhador de quadrados nas
    duas tabelas, em vez de cada tela ter o seu.
    """
    if janelas_proc is None or not len(janelas_proc) or not n_fatias:
        return None
    sub = janelas_proc[janelas_proc["CD_PROCEDIMENTO"] == cd]
    if not len(sub):
        return None
    por_janela = dict(zip(sub["janela"], sub["sinalizado"]))
    serie = []
    for j in range(1, n_fatias + 1):
        if j not in por_janela:
            serie.append({"janela": j, "estado": TRIMESTRE_NAO_AVALIAVEL,
                          "sinalizado": False,
                          "motivo": "sem par avaliável neste trimestre"})
        else:
            sin = bool(por_janela[j])
            serie.append({"janela": j,
                          "estado": TRIMESTRE_SINALIZADO if sin else TRIMESTRE_AVALIAVEL,
                          "sinalizado": sin, "motivo": None})
    return serie


def procedimentos_do_cooperado(posproc_coop: pd.DataFrame,
                               persist_coop: pd.DataFrame | None,
                               pares_coop: pd.DataFrame | None,
                               conf_coop: pd.DataFrame | None,
                               reais_por_proc: dict[str, float],
                               n_fatias: int,
                               preco_por_proc: dict[str, float] | None = None,
                               janelas_coop: pd.DataFrame | None = None,
                               total_itens: float | None = None) -> dict:
    """A tabela central do dossiê: as duas lentes POR PROCEDIMENTO (magnitude =
    excedente; intensidade = razão), com persistência, degrau da cascata e
    confiança. Só pares em que o cooperado é MEDIDO (norma apresentável).

    Chips (espec regra 7): 'em revisão' (sinalizado, default) · 'todos'.
    """
    if persist_coop is not None and len(persist_coop):
        persist_ix = persist_coop.set_index("CD_PROCEDIMENTO")
    else:
        persist_ix = None
    conf_ix = (conf_coop.set_index("CD_PROCEDIMENTO")
               if conf_coop is not None and len(conf_coop) else None)
    pares_ix = (pares_coop.set_index("CD_PROCEDIMENTO")
                if pares_coop is not None and len(pares_coop) else None)

    linhas = []
    # TODOS os procedimentos que ele solicitou, e não só os que a área sabe
    # comparar (27/ago). Antes a tabela filtrava por `apresentavel` e sumia com
    # 72 dos 269 do cooperado_85 — 2,9% das solicitações, mas 11,8% do R$, e
    # entre eles o segundo maior gasto dele. Some da tela, e o leitor conclui
    # que não existe.
    #
    # O que falta referência não é inocentado, é NÃO MEDIDO: as colunas de
    # comparação (referência, razão, consistência, excedente) vêm vazias com o
    # motivo ao lado, e as que não dependem de par (solicitações, frequência,
    # proporção, custo unitário e total) vêm cheias. É a mesma regra que a
    # tabela da área já segue: "não avaliáveis permanecem na lista, esmaecidos,
    # com o motivo, nada some da tela".
    #
    # `apresentavel` vem NaN onde a área não tem norma (sem peer group):
    # NaN = não medido, nunca uma máscara que estoura.
    for _, r in posproc_coop.iterrows():
        cd = r["CD_PROCEDIMENTO"]
        medido = bool(pd.notna(r.get("apresentavel")) and r["apresentavel"])
        # os TRÊS portões, como em filtrar_sinalizados: abaixo do piso a taxa
        # não sustenta comparação e nenhum par dele entra "em revisão"
        avaliavel_par = bool(r.get("avaliavel", True))
        sinalizado = bool(r["sinalizado"]) and avaliavel_par and medido
        exc = float(r["excedente_itens"]) if sinalizado else None
        pers = None
        if persist_ix is not None and cd in persist_ix.index:
            pr = persist_ix.loc[cd]
            pers = {"rotulo": f"{int(pr['n_janelas_sinalizado'])}/{int(pr['n_janelas_avaliaveis'])}",
                    # as contagens SOLTAS, para a célula escrever o denominador
                    # por extenso ("3 de 4 trimestres"): "3/4" e "3/8" se leem
                    # como a mesma coisa, e o denominador muda com o período
                    "n_sinalizado": int(pr["n_janelas_sinalizado"]),
                    "n_avaliaveis": int(pr["n_janelas_avaliaveis"]),
                    "reportavel": bool(pr["reportavel"])}
        confianca = None
        if sinalizado:
            row_conf = (conf_ix.loc[cd] if conf_ix is not None
                        and cd in conf_ix.index else None)
            confianca = _confianca_do_par(row_conf)
        # o último degrau da cascata que este par alcançou: é a DEFESA do caso
        # ("qualificado" sustenta conversa; "sem persistência" pede cautela)
        degrau = None
        if pares_ix is not None and cd in pares_ix.index:
            pr_q = pares_ix.loc[cd]
            alcancados = [rot for chave, rot, *_ in cascata.DEGRAUS
                          if bool(pr_q.get(chave))]
            degrau = alcancados[-1] if alcancados else None
        reais = reais_por_proc.get(cd)
        preco = (preco_por_proc or {}).get(cd)
        preco = None if preco is None or pd.isna(preco) else float(preco)
        custo_total = None if preco is None else preco * float(r["n_solicitacoes"])
        linhas.append({
            "codigo": cd,
            "descricao": str(r.get("DS_PROCEDIMENTO", config.SEM_MEDIDA)).strip(),
            # SOLICITAÇÕES: o total absoluto, que é o que a frequência divide
            "solicitacoes": int(r["n_solicitacoes"]),
            "solicitacoes_fmt": fmt(r["n_solicitacoes"], 0),
            # FREQUÊNCIA e REFERÊNCIA na MESMA unidade (por consulta), senão a
            # razão ao lado não fecha com a divisão das duas colunas. Rara vira
            # "por mil" via fmt_taxa, para não virar 0,00 e ler como régua zero.
            "taxa": round(float(r["taxa"]), 4), "taxa_fmt": fmt_frequencia(r["taxa"]),
            "referencia_fmt": (fmt_frequencia(r[r["alvo_usado"]])
                               if medido and pd.notna(r.get(r["alvo_usado"]))
                               else config.SEM_MEDIDA),
            # PROPORÇÃO sobre TODAS as solicitações dele (o mesmo total do KPI
            # "Solicitações"), e não sobre o que a tabela mostra: a tabela só
            # traz procedimentos com referência conclusiva, e um denominador que
            # muda com o recorte não é proporção, é outro número a cada clique.
            # Consequência declarada: a coluna não soma 100%.
            "proporcao": (None if not total_itens
                          else round(float(r["n_solicitacoes"]) / total_itens, 4)),
            "proporcao_fmt": (config.SEM_MEDIDA if not total_itens else
                              f"{fmt(100 * float(r['n_solicitacoes']) / total_itens, 1)}%"),
            # RAZÃO = Frequência ÷ Referência, as duas colunas ao lado. Tem de
            # ser a referência ATIVA: com `referencia=p75` a razão contra a
            # mediana punha "0,061 · 0,011 · 12,2×" na mesma linha, e a conta
            # não fecha para quem confere.
            "razao": (None if not medido or pd.isna(r["razao_vs_alvo"])
                      else round(float(r["razao_vs_alvo"]), 2)),
            "razao_fmt": (config.SEM_MEDIDA
                          if not medido or pd.isna(r["razao_vs_alvo"])
                          else f"{fmt(r['razao_vs_alvo'], 1)}×"),
            # a MARCA de que este par não sustenta comparação, e o porquê. A
            # linha inteira é esmaecida por ela no front.
            "medido": medido,
            "motivo_nao_medido": (None if medido else
                                  "Menos de "
                                  f"{config.N_MINIMO_PEER_GROUP} cooperados da área "
                                  "solicitam este procedimento. Abaixo desse "
                                  "mínimo a referência não é estatisticamente "
                                  "sustentável."),
            "sinalizado": sinalizado,
            "excedente_itens": None if exc is None else round(exc, 2),
            "excedente_fmt": fmt(exc, 0) if exc else config.SEM_MEDIDA,
            "excedente_motivo": (None if sinalizado else
                                 "A área de atuação não tem referência apurável "
                                 "para este procedimento."
                                 if not medido else
                                 "Volume de consultas abaixo do mínimo exigido "
                                 "para comparação."
                                 if not avaliavel_par else
                                 "Frequência dentro do critério da área para "
                                 "este procedimento."),
            # O R$ sai FORMATADO e CRU. Só o formatado existia, e a coluna
            # "Custo excedente" da tabela acabava ordenando por
            # `excedente_itens` (a contagem), porque era o único número da
            # linha: o procedimento de R$ 57 mil caía abaixo de um de R$ 40 mil
            # que tinha o dobro de solicitações. Coluna que mostra R$ ordena por
            # R$; para isso, o R$ precisa existir como número.
            "excedente_reais": None if not reais else round(float(reais), 2),
            "excedente_reais_fmt": None if not reais else fmt_reais(reais),
            # ── R$ (mesma quarentena do excedente: preço interno derivado) ────
            "custo_unitario": None if preco is None else round(float(preco), 2),
            "custo_unitario_fmt": (config.SEM_MEDIDA if preco is None
                                   else fmt_reais(preco)),
            "custo_total": None if custo_total is None else round(custo_total, 2),
            "custo_total_fmt": (config.SEM_MEDIDA if custo_total is None
                                else fmt_reais(custo_total)),
            "persistencia": pers,
            # a SÉRIE, para a coluna Consistência desenhar os mesmos quadrados
            # da tabela da área (um por trimestre) em vez de só "4/4"
            "trimestres": (_serie_do_procedimento(janelas_coop, cd, n_fatias)
                           if medido else None),
            "total_fatias": n_fatias,
            "confianca": confianca,
            "degrau": degrau,
            "gatilho_usado": (None if pd.isna(r["gatilho_usado"])
                              else str(r["gatilho_usado"]).upper()),
        })
    # ORDEM PADRÃO PELO R$, e não pela contagem de solicitações excedentes.
    # A tabela fica logo abaixo de um Pareto ordenado por R$ e termina numa
    # coluna "Custo excedente" em R$: abrir por itens punha um procedimento no
    # topo da tabela e outro no topo do gráfico, com o mesmo rótulo de
    # "excedente". Itens continua como desempate, e a razão depois dele.
    linhas.sort(key=lambda l: (-(l.get("excedente_reais") or 0),
                               -(l["excedente_itens"] or 0),
                               -(l["razao"] or 0)))
    n_sin = sum(1 for l in linhas if l["sinalizado"])
    # ── por que NÃO existe mais um piso agregado (set/2026) ──────────────────
    # Ele era a soma dos pisos dos pares CALCULÁVEIS, e ia para a tela ao lado
    # do excedente total. As duas somas não compartilham base: a reamostragem
    # por paciente só roda em par que chegou ao degrau anterior da cascata e tem
    # ao menos config.MIN_PACIENTES_BOOTSTRAP pacientes. No cooperado_19 isso
    # dava 15 dos 38 pares sinalizados, e a linha "5.908 solicitações · piso:
    # 3.067" convidava à conta 3.067/5.908 = 52%, quando o que foi testado
    # sustenta 3.067/3.327 = 92%. Os outros 23 pares não foram reprovados: não
    # foram medidos.
    #
    # O piso continua no produto POR PAR, na coluna de custo excedente da tabela
    # ("574 de 617 se sustentam"), onde ele tem denominador próprio e serve à
    # conversa, que é sempre sobre um exame.
    n_medidos = sum(1 for l in linhas if l["medido"])
    return {
        # o sentinel de ausência, para o front não repetir a constante do
        # config em JavaScript (uma frase, dois lugares, é como elas divergem)
        "sem_medida": config.SEM_MEDIDA,
        "total_medidos": len(linhas),
        "com_referencia": n_medidos,
        "sem_referencia": len(linhas) - n_medidos,
        "em_revisao": n_sin,
        "ordenado_por": "custo excedente",
        "linhas": linhas,
    }


def frase_do_caso(linha: dict) -> str | None:
    """O caso numa FRASE, para o subtítulo da Leitura do caso: posição, origem
    e consistência na língua do leitor — o que este médico é, nunca a regra do
    método (a regra mora na Nota Metodológica e nos hovers).

    ── o que cada pedaço precisou ganhar (set/2026) ───────────────────────────
    A versão anterior dizia "acima de 97% dos cooperados da área, excedente
    distribuído em 38 procedimentos, padrão sustentado nos 4 trimestres". Três
    frases curtas que o leitor completava errado:

      · POSIÇÃO sem a medida. "Acima de 97%" em quê? No índice agregado, e não
        no custo, em que ele é o 8º de 63. A medida agora abre a frase.
      · ORIGEM sem o achado. "Distribuído" era o resultado de um limiar
        (config.FRACAO_ORIGEM_CONCENTRADA: o topo responde por menos de 30% do
        excedente), mas lia como palavra de ligação. Agora diz "sem um
        dominante", e o caso concentrado diz a parcela e o nome do exame.
      · CONSISTÊNCIA sem o sujeito. "Padrão sustentado" não dizia qual padrão,
        e sugeria o MESMO procedimento nos quatro trimestres — que é outra
        medida (a coluna Consistência, por par). O padrão é "ter ao menos um
        procedimento acima do critério", e agora está escrito.

    Os pedaços passam a ter vírgula dentro, então o separador vira " · ".

    A CONSISTÊNCIA saiu da frase (set/2026): ela já é uma seção própria do
    cartão antigo, com os quadrados que a explicam, e no subtítulo era a terceira
    afirmação de uma linha que o leitor já lia como parágrafo.
    """
    partes = partes_do_caso(linha)
    return " · ".join(partes) if partes else None


def partes_do_caso(linha: dict) -> list[str]:
    """As afirmações do caso, uma por item, cada uma começando em maiúscula.

    LISTA e não frase: no cartão elas viram itens com marca própria, e um item
    por afirmação é o que as separa de um parágrafo corrido. `frase_do_caso`
    continua juntando, para o cartão que ainda lê uma linha só.
    """
    partes = []
    pos = linha.get("posicao") or {}
    if pos.get("traducao"):
        partes.append(f"em solicitações por consulta, {pos['traducao']}")
    elif pos.get("indisponivel_motivo"):
        partes.append(pos["indisponivel_motivo"])
    origem = linha.get("origem_excedente") or {}
    topo = origem.get("topo") or {}
    n_procs = linha.get("procedimentos_em_revisao") or 0
    if origem.get("concentrado") and topo.get("descricao"):
        partes.append(f"{topo['pct_fmt']} do excedente em "
                      f"{topo['descricao'].strip()}")
    elif n_procs == 1:
        partes.append("excedente em um único procedimento")
    elif n_procs:
        partes.append(f"excedente espalhado por {n_procs} procedimentos, "
                      f"sem um dominante")
    return [t[0].upper() + t[1:] if t else t for t in partes]


def contexto_do_cooperado(resumo_row, perfil_row) -> list[dict]:
    """Fatores de contexto do dossiê: dizem "investigue com esta lente", nunca
    mudam número. Autorreferência NUNCA sem a cobertura ao lado (premissa
    declarada no motor)."""
    itens = []
    if resumo_row is not None:
        pct_urg = resumo_row.get("pct_urgencia")
        if pct_urg is not None and pd.notna(pct_urg):
            itens.append({
                "rotulo": "consultas de urgência",
                "valor_fmt": fmt_pct(float(pct_urg)),
                "alerta": bool(resumo_row.get("confundidor_urgencia")),
                "ajuda": ("Parcela das consultas registradas como urgência ou "
                          "emergência. Percentual elevado indica atuação em "
                          "pronto atendimento, o que altera o perfil de "
                          "solicitação esperado.")})
        taxa_auto = resumo_row.get("taxa_autorref_solic")
        cob = resumo_row.get("cobertura_join")
        if taxa_auto is not None and pd.notna(taxa_auto):
            itens.append({
                "rotulo": "autorreferência na solicitação",
                "valor_fmt": (f"{fmt_pct(float(taxa_auto))} "
                              f"(cobertura {fmt_pct(float(cob))})" if pd.notna(cob)
                              else fmt_pct(float(taxa_auto))),
                "alerta": False,
                "ajuda": ("Parcela dos itens solicitados que foram executados "
                          "pelo próprio solicitante, apurada sobre os itens com "
                          "conta localizada. Indicador para investigação, não "
                          "conclusão.")})
    if perfil_row is not None:
        pct_ps = perfil_row.get("pct_pronto_socorro")
        if pct_ps is not None and pd.notna(pct_ps):
            itens.append({
                "rotulo": "execuções em pronto-socorro",
                "valor_fmt": fmt_pct(float(pct_ps)),
                "alerta": bool(perfil_row.get("confundidor_regime")),
                "ajuda": ("Parcela das execuções em regime de pronto socorro, "
                          "apurada sobre a base completa do período.")})
        pct_int = perfil_row.get("pct_internacao")
        if pct_int is not None and pd.notna(pct_int):
            itens.append({
                "rotulo": "execuções em internação",
                "valor_fmt": fmt_pct(float(pct_int)),
                "alerta": False,
                "ajuda": "Parcela das execuções em regime de internação."})
    return itens


def _intervalo_fmt(dias) -> str | None:
    """Intervalo médio entre repetições, na unidade que o número comporta."""
    if dias is None or pd.isna(dias):
        return None
    d = float(dias)
    if d < 1:
        return "mesmo dia"
    if d < 2:
        return "1 dia"
    return f"{fmt(d, 0)} dias"


_ROTULO_NIVEL = {"mediana": "mediana", "p75": "P75", "p90": "P90"}


def regua_do_procedimento(linha_par, p25: float | None, taxa: float,
                          criterio_pedido: str, taxas_pares=None,
                          n_area: int | None = None) -> dict | None:
    """A posição do cooperado na distribuição DESTE procedimento, em um box plot.

    Por que box plot e não o enxame de pontos da tela de Área: aqui a pergunta é
    "onde ELE está", não "qual a forma da distribuição" — essa é a pergunta da
    tela de Área, que segue com o gráfico completo a um clique. Sessenta pontos
    numa coluna de 380px viram ruído, e o painel deixa de caber sem rolagem
    justo quando o gesto seguinte é clicar na próxima linha da tabela.

    O que o box plot dá e a curva de densidade que morava aqui não dava: números
    LEGÍVEIS. A curva mostrava a forma e escondia os quartis; a caixa é o resumo
    de cinco números que qualquer analista lê sem legenda, e sobra desenho para
    um ponto só ter destaque. Ele também é o MESMO componente da distribuição da
    área (`.plot`, com `.haste`/`.tampa`/`.iqrband`/`.refline`/`.pt`), o que
    fecha a identidade das duas telas em vez de manter dois desenhos para a
    mesma leitura.

    Geometria pela MESMA função (`_escala`/`_pos`) da régua da tabela: é o que
    faz a marca cair no mesmo lugar nas duas telas (componente-assinatura,
    guia §04).

    ── referência e critério são PARÂMETROS, e a régua obedece ────────────────

    As duas linhas seguem o que está ativo na barra de critérios, não valores
    fixos: a referência é o ALVO em vigor (`alvo_usado` — mediana, P75 ou P90) e
    o critério é o GATILHO EFETIVO (`gatilho_usado`), que pode ter degradado por
    n. Os rótulos nomeiam qual é qual, porque uma linha sem nome numa régua que
    muda de posição conforme o parâmetro é pior que nenhuma linha.

    Quando não há gatilho (grupo pequeno demais para sustentar percentil), a
    linha de critério NÃO é desenhada e o motivo viaja: régua desenhada que não
    mede é o defeito que o gráfico da área carregava.
    """
    if linha_par is None or p25 is None or pd.isna(p25):
        return None
    alvo = str(linha_par["alvo_usado"]) if pd.notna(linha_par.get("alvo_usado")) else "mediana"
    if pd.isna(linha_par.get(alvo)):
        return None
    referencia = float(linha_par[alvo])
    p75 = float(linha_par["p75"]) if pd.notna(linha_par.get("p75")) else None

    gatilho = (str(linha_par["gatilho_usado"])
               if pd.notna(linha_par.get("gatilho_usado")) else None)
    valor_crit = (float(linha_par[gatilho])
                  if gatilho and pd.notna(linha_par.get(gatilho)) else None)

    # AS PONTAS DA HASTE: menor e maior taxa observada entre os que formam a
    # referência deste exame. É o alcance total da distribuição, que a caixa
    # sozinha não mostra, e é o que impede a leitura "ele está muito longe do
    # grupo" quando na verdade metade da área está espalhada por ali.
    pares = np.asarray([float(v) for v in (taxas_pares if taxas_pares is not None else [])
                        if v is not None and not np.isnan(float(v))], dtype=float)
    minimo = float(pares.min()) if len(pares) else None
    maximo = float(pares.max()) if len(pares) else None

    # a escala cobre tudo que vai ser desenhado: sem incluir a marca, um
    # cooperado muito acima do grupo sai do eixo e o desenho mente por omissão
    escala = _escala([v for v in (minimo, maximo, p25, p75, referencia,
                                  valor_crit, taxa, 0.0) if v is not None])

    razao = (taxa / referencia) if referencia else None
    return {
        # HASTE do menor ao maior observado, com a caixa dos quartis dentro: o
        # box plot de sempre, o mesmo da distribuição da área.
        "haste": (None if minimo is None or maximo is None else
                  {"pos_pct": _pos(minimo, escala),
                   "largura_pct": round(_pos(maximo, escala) - _pos(minimo, escala), 2),
                   "min_fmt": fmt_frequencia(minimo),
                   "max_fmt": fmt_frequencia(maximo),
                   "rotulo": "menor e maior da área"}),
        # QUEM forma a referência DESTE exame: os cooperados da área que o
        # solicitam e são elegíveis. Não é a área inteira, e o painel precisa
        # dizer isso com o denominador ao lado — "grupo de pares" nomeava as
        # duas coisas e era a origem da confusão (set/2026).
        "n_pares": int(len(taxas_pares)) if taxas_pares is not None else 0,
        "n_area": n_area,
        "iqr": {"pos_pct": _pos(p25, escala),
                "largura_pct": (round(_pos(p75, escala) - _pos(p25, escala), 2)
                                if p75 is not None else 0.0),
                "rotulo": "metade central da área"},
        # Léxico: alvo -> "referência de adequação"; gatilho -> "critério de
        # revisão". O nível ativo vem junto porque é ele que muda de lugar
        # quando o parâmetro muda.
        "referencia": {"valor_fmt": fmt_frequencia(referencia),
                       "pos_pct": _pos(referencia, escala),
                       "rotulo": f"Referência de adequação ({_ROTULO_NIVEL.get(alvo, alvo)})"},
        "criterio": (None if valor_crit is None else
                     {"valor_fmt": fmt_frequencia(valor_crit),
                      "pos_pct": _pos(valor_crit, escala),
                      "rotulo": f"Critério de revisão ({gatilho.upper()})",
                      "ajustado": gatilho != criterio_pedido}),
        # o PONTO do cooperado. Sem classe de severidade: num box plot de UM
        # caso, a posição já diz onde ele está contra as duas linhas, e pintar o
        # ponto de vermelho repetia em tinta o que o desenho mostra em lugar.
        # A régua da tabela (`marca_classe`) segue com a paleta, porque lá são
        # 63 marcas e a cor é o que separa uma da outra à distância.
        "marca": {"valor_fmt": fmt_frequencia(taxa),
                  "pos_pct": _pos(taxa, escala)},
        "razao_fmt": None if razao is None else f"{fmt(razao, 1)}×",
        "sem_criterio_motivo": (None if valor_crit is not None else
                                "Cooperados insuficientes na área para sustentar "
                                "percentil. Posição descritiva, sem critério."),
    }


def painel_do_procedimento(cd: str, descricao: str, conc_row, pacientes: dict | None,
                           autorref_row, regua: dict | None,
                           serie: list[dict] | None, confianca: dict | None,
                           linha_par=None, conc_bruta=None, preco=None,
                           total_coop=None) -> dict:
    """O painel lateral do procedimento (espec §3): a evidência de segundo nível.

    Nada nasce aqui — é a saída dos motores vestida para a tela. Três regras que
    a montagem faz cumprir, e que são o motivo do painel existir:

    1. **Nenhum número de repetição sem o par ao lado.** Repetir é o protocolo em
       pré-natal (cardiotocografia repete em 62% dos casos) e é achado em
       rastreio. "2,4 por paciente" isolado não diz nada; contra "pares: 1,3" diz.
    2. **Ausência declarada, nunca zero.** Par sem referência, procedimento com
       poucos pacientes e autorreferência sem cobertura têm cada um o seu motivo
       escrito — célula vazia lê como medição, e não é.
    3. **O paciente é `beneficiario_N`**, o pseudônimo do mapa, sem nada clínico
       ou demográfico ao lado. O hash de origem não sai do dim_beneficiarios.
    """
    def num(row, campo, casas=1):
        if row is None or campo not in row or pd.isna(row[campo]):
            return None
        return fmt(float(row[campo]), casas)

    # ── repetição ───────────────────────────────────────────────────────────
    #
    # Só a FRAÇÃO QUE REPETE e o INTERVALO. Havia uma terceira medida — mediana
    # de solicitações por beneficiário — que saiu: ela vale 1,0 em 99,4% dos
    # 4.347 pares medidos, ou seja, não distingue ninguém de ninguém e ocupava a
    # primeira posição do bloco dizendo sempre a mesma coisa.
    #
    # As duas que ficaram andam com a referência da área ao lado, como
    # manda o léxico: repetir é rotina em pré-natal e é achado em rastreio, e o
    # mesmo percentual lê ao contrário nos dois.
    n_pac = None if conc_row is None else int(conc_row["n_pacientes_proc"])
    pouco = n_pac is not None and n_pac < config.MIN_PACIENTES_PAINEL
    sem_ref = conc_row is None or not bool(conc_row.get("referencia_solida", False))

    def _val(campo, casas=1, pct=False):
        if conc_row is None or campo not in conc_row or pd.isna(conc_row[campo]):
            return None
        v = float(conc_row[campo])
        return fmt_pct(v, casas) if pct else fmt(v, casas)

    repeticao = {
        "n_pacientes": n_pac,
        "pct_repetem_fmt": _val("pct_pacientes_repetem", 0, pct=True),
        "pct_repetem_pares_fmt": _val("pct_repetem_mediana_pares", 0, pct=True),
        "intervalo_fmt": _val("intervalo_mediano_dias", 0),
        "intervalo_pares_fmt": _val("intervalo_mediano_pares", 0),
        "motivo": (f"Pouco volume. Menos de {config.MIN_PACIENTES_PAINEL} "
                   "beneficiários com este procedimento no período."
                   if pouco else
                   "Cooperados insuficientes na área para análise comparativa."
                   if sem_ref else None),
    }


    # ── concentração ────────────────────────────────────────────────────────
    # ── concentração ────────────────────────────────────────────────────────
    #
    # O card RESPONDE, não despeja números. A pergunta é "de onde vem esse
    # volume", e ela tem duas respostas possíveis — "de ninguém em particular"
    # e "destas pessoas" —, cada uma com a sua forma:
    #
    #   sem ninguém acima do limiar -> uma frase e acabou. Sem lista, porque
    #     lista de cinco linhas de 1% sugere achado onde não há;
    #   com alguém acima -> a frase afirma o quanto, e a lista é a evidência.
    #
    # A comparação com os pares entra em PALAVRAS ("mais espalhado que o normal
    # da área"), com os percentuais como apoio: "top 10% concentram 20,9% contra
    # 25,0%" exige que o leitor saiba o que é um share do decil superior.
    concentracao = None
    if pacientes and not pouco:
        destacados = pacientes["linhas"]
        share = None if conc_row is None or pd.isna(conc_row.get("share_top")) \
            else float(conc_row["share_top"])
        share_pares = (None if conc_row is None
                       or pd.isna(conc_row.get("share_top_mediana_pares"))
                       else float(conc_row["share_top_mediana_pares"]))
        if share is not None and share_pares is not None:
            # A comparação com NÚMERO na tela, não só o adjetivo: "mais
            # espalhado que a área" é conclusão sem prova, e o leitor
            # não tem como saber se a diferença é de 1 ponto ou de 20.
            n_top = (math.ceil(config.FRAC_TOP_CONCENTRACAO * pacientes["n_pacientes"])
                     if pacientes["n_pacientes"] else 0)
            comparacao = (f"Os {n_top} beneficiários de maior volume concentram "
                          f"{fmt_pct(share, 1)} das solicitações; na área, "
                          f"{fmt_pct(share_pares, 1)}.")
            apoio = None
        else:
            comparacao = apoio = None

        if destacados:
            titulo = (f"{len(destacados)} "
                      f"{'beneficiário concentra' if len(destacados) == 1 else 'beneficiários concentram'} "
                      f"{fmt_pct(pacientes['pct_destacados'], 1)} das solicitações "
                      f"deste procedimento.")
        else:
            titulo = (f"Nenhum beneficiário concentra mais de "
                      f"{fmt_pct(pacientes['limiar'])} das solicitações. "
                      f"O maior concentra {fmt_pct(pacientes['maior_pct'], 1)}.")
        concentracao = {
            "titulo": titulo,
            "n_pacientes": pacientes["n_pacientes"],
            "comparacao": comparacao,
            "apoio": apoio,
            "linhas": [{
                "id": l["ID_BENEFICIARIO"],
                "ocasioes": int(l["ocasioes"]),
                "itens_fmt": fmt(float(l["itens"]), 0),
                "pct_fmt": fmt_pct(float(l["pct_do_procedimento"]), 1),
                "pct": round(float(l["pct_do_procedimento"]), 4),
                # "0 dias" lê como ausência de intervalo; o caso é repetição no
                # MESMO dia, que desde a regra de sessão significa dois
                # atendimentos separados por mais de uma hora
                "intervalo_fmt": _intervalo_fmt(l["intervalo_dias"]),
            } for l in destacados],
        }

    # ── autorreferência (com portão) ────────────────────────────────────────
    if autorref_row is None:
        autorreferencia = {"apresentavel": False, "motivo": "Sem solicitações no período",
                           "taxa_fmt": None, "cobertura_fmt": None}
    else:
        # "conta localizada" é vocabulário de quem fez o cruzamento das bases,
        # não de quem lê a tela. O que o auditor precisa saber é se dá para
        # apurar e sobre quanto: quem executou o pedido só é conhecido quando a
        # solicitação encontra a conta correspondente.
        ok = bool(autorref_row["apresentavel"])
        autorreferencia = {
            "apresentavel": ok,
            "taxa_fmt": (fmt_pct(float(autorref_row["taxa_autorref"]))
                         if ok and pd.notna(autorref_row["taxa_autorref"]) else None),
            "cobertura_fmt": fmt_pct(float(autorref_row["cobertura"])),
            "itens_com_conta": int(autorref_row["itens_com_conta"]),
            "itens": int(autorref_row["itens"]),
            "motivo": None if ok else "Não apurável",
        }

    # ── alcance na carteira ─────────────────────────────────────────────────
    #
    # A margem EXTENSIVA: que fatia dos beneficiários do cooperado recebe este
    # procedimento. É a leitura que a frequência por consulta não dá — 45% da
    # carteira contra 2,3% dos pares diz "isto virou rotina aqui", e nenhum
    # número de intensidade diz isso.
    alcance = None
    if conc_row is not None and pd.notna(conc_row.get("pct_carteira")):
        alcance = {
            "pct_fmt": fmt_pct(float(conc_row["pct_carteira"])),
            "pares_fmt": (None if pd.isna(conc_row.get("pct_carteira_mediana_pares"))
                          else fmt_pct(float(conc_row["pct_carteira_mediana_pares"]))),
            "n_beneficiarios": int(conc_row["n_pacientes_proc"]),
            "n_carteira": int(conc_row["n_pacientes_carteira"]),
        }

    # ── peso na prática ─────────────────────────────────────────────────────
    peso = None
    if linha_par is not None and total_coop:
        n_sol = float(linha_par["n_solicitacoes"])
        exc = linha_par.get("excedente_itens")
        # O excedente vai como FRAÇÃO do custo, não como um segundo R$ ao lado:
        # com razão de 23,8x, 96% do que foi pedido fica acima da referência, e
        # "R$ 41 mil no período · R$ 40 mil acima" lê como erro de cópia mesmo
        # estando certo. A fração diz a mesma coisa e não parece defeito.
        pct_exc = (float(exc) * preco / (n_sol * preco)
                   if preco and exc is not None and pd.notna(exc) and float(exc) > 0
                   and n_sol else None)
        peso = {
            "excedente_pct_fmt": None if pct_exc is None else fmt_pct(pct_exc),
            "solicitacoes_fmt": fmt(n_sol, 0),
            "proporcao_fmt": fmt_pct(n_sol / total_coop, 1),
            "custo_total_fmt": None if preco is None else fmt_reais(n_sol * preco),
            "custo_excedente_fmt": (None if preco is None or exc is None or pd.isna(exc)
                                    or float(exc) <= 0 else fmt_reais(float(exc) * preco)),
            "custo_unitario_fmt": None if preco is None else fmt_reais(preco),
        }

    return {
        "codigo": cd,
        "descricao": descricao,
        "regua": regua,
        "alcance": alcance,
        "peso": peso,
        "repeticao": repeticao,
        "concentracao": concentracao,
        "autorreferencia": autorreferencia,
        "trimestres": serie,
        "confianca": confianca,
        "sem_medida": config.SEM_MEDIDA,
    }


def _tooltip_trimestre(meses: str | None, consultas: float,
                       custo: float | None, exc: float | None,
                       volume_baixo: bool = False, piso=None) -> str:
    """A frase do hover de uma barra da evolução trimestral.

    Redigida aqui, e não na tela, pela mesma razão que a ressalva de método:
    texto que carrega número é parte do número. Segue o tom das definições de
    coluna da tabela de procedimentos, que é o padrão do app: frase inteira,
    vocabulário do léxico, sem rótulo em minúscula seguido de dois-pontos.
    """
    # "Trimestre" abre a frase porque o rótulo de meses é minúsculo por
    # formato de data ("ago/25–out/25"), e frase de tela começa em maiúscula
    abre = f"Trimestre {meses}. " if meses else ""
    # A ressalva de volume FECHA a frase e é curta: ela qualifica, não explica.
    # A versão anterior emendava "as taxas do período apoiam-se em pouco dado",
    # que é raciocínio do analista, não informação do trimestre.
    # sem repetir a contagem: ela já abre a frase
    fim = " Volume baixo neste trimestre." if volume_baixo else ""
    if custo is None:
        return f"{abre}{fmt(consultas, 0)} consultas, sem custo apurado.{fim}"
    if exc and exc > 0:
        return (f"{abre}{fmt(consultas, 0)} consultas, {fmt_reais(custo)} em "
                f"custo, dos quais {fmt_reais(exc)} acima da referência da "
                f"área.{fim}")
    if exc and exc < 0:
        return (f"{abre}{fmt(consultas, 0)} consultas, {fmt_reais(custo)} em "
                f"custo, {fmt_reais(abs(exc))} abaixo da referência da "
                f"área.{fim}")
    return (f"{abre}{fmt(consultas, 0)} consultas, {fmt_reais(custo)} em custo, "
            f"dentro da referência da área.{fim}")


def evolucao_do_procedimento(n_por_janela: dict, por_janela: pd.DataFrame | None,
                             cooperado: str | list[str], preco: float | None,
                             alvo_taxa: float | None, mede_excedente: bool,
                             rotulos: list[str] | None = None,
                             resto_dias: int | None = None) -> dict | None:
    """A série trimestral de UM exame: custo do período e a parcela excedente.

    Mesma construção do bloco do dossiê (`evolucao_trimestral`) e a MESMA régua
    congelada (METODOLOGIA §5.4.1): preço e alvo são anuais, o trimestre entra
    só com as solicitações dele e com as consultas do cooperado. A identidade
    vale por par: os quatro trimestres somam o custo e o excedente anuais deste
    exame.

    `mede_excedente` diz se há excedente apurado para este exame no período.
    Não havendo, as barras mostram só o custo e o bloco declara isso em uma
    linha: barra de excedente zerada afirmaria que ele não excede, quando o que
    houve foi não haver medida.

    O payload sai no MESMO formato de `evolucao_trimestral`, de propósito: a
    tela desenha os dois com o mesmo bloco.
    """
    if not n_por_janela or por_janela is None or not len(por_janela) or not preco:
        return None
    # UM cooperado ou um GRUPO deles. O painel do dossiê passa um id; o painel
    # do procedimento na área passa os que estão em cena, e aí as consultas do
    # trimestre são a soma delas — o denominador do excedente é o mesmo conjunto
    # cujo volume está no numerador, senão a barra mede duas populações.
    alvo = [cooperado] if isinstance(cooperado, str) else list(cooperado)
    pj = por_janela[por_janela["ID_COOPERADO"].isin(alvo)]
    if not len(pj):
        return None
    cons = {int(j): float(v) for j, v in
            pj.groupby("janela")["consultas_totais"].sum().items()}
    if not cons:
        return None

    tem_exc = bool(mede_excedente and alvo_taxa is not None)
    linhas = []
    for j in sorted(cons):
        vol = n_por_janela.get(j) or {}
        n = float(vol.get("solicitacoes") or 0.0)
        pac = vol.get("pacientes")
        custo = n * float(preco)
        exc = (custo - cons[j] * float(alvo_taxa) * float(preco)) if tem_exc else None
        rot = (rotulos[j - 1] if rotulos and len(rotulos) >= j else None)
        linhas.append({
            "janela": j, "rotulo": f"T{j}", "meses": rot,
            "avaliavel": True, "volume_baixo": False, "motivo": None,
            "consultas": cons[j], "consultas_fmt": fmt(cons[j], 0),
            "solicitacoes": n, "solicitacoes_fmt": fmt(n, 0),
            "pacientes": pac, "pacientes_fmt": None if pac is None else fmt(pac, 0),
            # repetição do trimestre: quantas vezes o mesmo beneficiário voltou.
            # É a única das três que é leitura nova; as outras duas são o
            # denominador dela, e por isso aparecem sempre ao lado.
            "por_paciente_fmt": (None if not pac else fmt(n / pac, 1)),
            "indice": None, "indice_fmt": None,
            "itens": n,
            # EXATO, não abreviado: aqui os dois números convivem na mesma
            # grade e precisam ser distinguíveis um do outro. Abreviados, um
            # exame 40 vezes acima da referência imprimia "R$ 11 mil" nas duas
            # linhas (ver fmt_reais_exato).
            "custo": round(custo, 2), "custo_fmt": fmt_reais_exato(custo),
            "excedente_reais": None if exc is None else round(exc, 2),
            "excedente_reais_fmt": None if exc is None else fmt_reais_exato(exc),
            "custo_por_consulta_fmt": None,
            "_exc_bruto": exc,
            "tooltip": _tooltip_exame(rot, n, custo, exc),
        })

    # sobra de arredondamento na maior barra, pelo mesmo motivo do bloco do
    # dossiê: quatro arredondamentos não podem afastar a soma do número do ano
    if tem_exc:
        _tot = round(sum(l["_exc_bruto"] or 0.0 for l in linhas), 2)
        _ar = [round(l["_exc_bruto"], 2) for l in linhas]
        _sobra = round(_tot - sum(_ar), 2)
        if _sobra:
            _i = max(range(len(_ar)), key=lambda i: abs(_ar[i]))
            _ar[_i] = round(_ar[_i] + _sobra, 2)
        for l, v in zip(linhas, _ar):
            l["excedente_reais"] = v
            l["excedente_reais_fmt"] = fmt_reais_exato(v)
    for l in linhas:
        l.pop("_exc_bruto", None)

    valores = [l["custo"] for l in linhas]
    negativos = [(l["excedente_reais"] or 0.0) for l in linhas]
    teto, piso, marcas = _escala_grade(max(valores) or 1.0,
                                       min(negativos) if negativos else 0.0)
    amplitude = (teto - piso) or 1.0
    zero_pct = round(-piso / amplitude * 100, 2)
    for l in linhas:
        exc = l["excedente_reais"] or 0.0
        l["altura_pct"] = round(l["custo"] / amplitude * 100, 2)
        l["exc_negativo"] = bool(tem_exc and exc < 0)
        l["altura_exc_pct"] = round(abs(exc) / amplitude * 100, 2) if tem_exc else 0.0
        l["topo_fmt"] = l["custo_fmt"]
        l["exc_fmt_dentro"] = (l["excedente_reais_fmt"]
                               if (tem_exc and not l["exc_negativo"]
                                   and l["altura_exc_pct"] >= 10) else None)
    grade = [{"valor": v, "rotulo": ("0" if v == 0 else fmt_reais(v).replace("R$ ", "")),
              "pct": round((v - piso) / amplitude * 100, 2)}
             for v in marcas]
    return {
        "titulo": "Custo deste procedimento por trimestre",
        "subtitulo": None,
        "leitura": None,
        "grandeza": "custo",
        "tem_reais": True,
        "grade": grade,
        "zero_pct": zero_pct,
        "tem_negativo": any(l["exc_negativo"] for l in linhas),
        "nota": " ".join(x for x in (
            _ressalva_do_resto(resto_dias, rotulos),
            (None if tem_exc else
             "Sem variação excedente apurada para este procedimento no período; "
             "as barras mostram o custo total."),
            # O TRIMESTRE ABAIXO DO ZERO precisa dizer o que é, senão a barra
            # que desce lê como erro. E a frase precisa dizer o que ele faz com
            # o número do ano, que é a pergunta seguinte de quem soma as barras.
            ("Trimestre abaixo da referência reduz o excedente do ano. Os "
             "quatro somam o total do resumo."
             if any(l["exc_negativo"] for l in linhas) else None),
        ) if x) or None,
        "linhas": linhas,
    }


def _tooltip_exame(meses: str | None, n: float, custo: float,
                   exc: float | None) -> str:
    """A frase do hover de uma barra da série do exame.

    As SOLICITAÇÕES entram sempre, e é regra, não estilo: sem o denominador ao
    lado, quatro barras de dois itens se leem como trajetória (rigor §1).
    """
    # "Trimestre" abre a frase porque o rótulo de meses é minúsculo por
    # formato de data ("ago/25–out/25"), e frase de tela começa em maiúscula
    abre = f"Trimestre {meses}. " if meses else ""
    # EXATO: a frase põe os dois valores lado a lado, e abreviados ela saía
    # autocontraditória quando o excedente é quase todo o custo ("R$ 11 mil em
    # custo, dos quais R$ 11 mil acima da referência").
    base = f"{fmt(n, 0)} solicitações, {fmt_reais_exato(custo)} em custo"
    if exc is None:
        return f"{abre}{base}."
    if exc > 0:
        return f"{abre}{base}, dos quais {fmt_reais_exato(exc)} acima da referência da área."
    if exc < 0:
        return f"{abre}{base}, {fmt_reais_exato(abs(exc))} abaixo da referência da área."
    return f"{abre}{base}, dentro da referência da área."


def _escala_grade(maior: float, menor: float = 0.0) -> tuple[float, float, list[float]]:
    """Teto, piso e marcas de uma régua vertical que pode cruzar o zero.

    Régua tem de pousar em número redondo: uma linha em "R$ 107.360" não é
    referência, é o próprio dado repetido. O passo sai da família 1 / 2 / 2,5 / 5
    vezes uma potência de dez, que é a que produz marcas mentalmente divisíveis,
    e teto e piso são os primeiros múltiplos do passo fora dos extremos.

    Quatro intervalos acima do zero: menos que isso não dá leitura de altura,
    mais transforma o fundo do gráfico numa pauta. Abaixo do zero entram só as
    marcas necessárias para alcançar o menor valor, porque a parte negativa é a
    exceção e não deve ganhar o mesmo peso visual da positiva.
    """
    menor = min(0.0, float(menor))
    if maior <= 0 and menor == 0:
        return 1.0, 0.0, [0.0, 1.0]
    alvo = max(maior, 1e-9) / 4
    exp = math.floor(math.log10(alvo))
    base = 10 ** exp
    for mult in (1, 2, 2.5, 5, 10):
        passo = mult * base
        if passo >= alvo:
            break
    teto = math.ceil(maior / passo) * passo if maior > 0 else 0.0
    # O PISO NÃO É ARREDONDADO ao passo, e o de cima é. Assimetria de propósito:
    # arredondar para baixo gastaria uma faixa inteira da régua com um valor
    # muitas vezes menor que o passo (um excedente de −R$ 300 abria −R$ 20 mil de
    # pista, 20% do gráfico para 0,5% do dado). Abaixo do zero entra só o espaço
    # necessário, com uma folga curta, e nenhuma marca: a parte negativa é a
    # exceção e não deve ganhar o peso visual da positiva.
    piso = menor * 1.12 if menor < 0 else 0.0
    n_cima = int(round(teto / passo)) if passo else 0
    marcas = [round(passo * i, 2) for i in range(n_cima + 1)]
    return teto, piso, marcas


def _ressalva_do_resto(resto_dias: int | None, rotulos: list[str] | None) -> str | None:
    """A frase que declara o pedaço da janela que os trimestres não cobrem.

    `fatiar_trimestres` só devolve trimestres COMPLETOS: um resto de fim de
    janela mais curto que três meses é descartado, porque uma fatia de poucos
    dias no denominador da persistência produz um "4 de 4" sustentado por
    quase nada. A decisão é certa e está documentada lá.

    O que faltava era DIZER isso onde as barras aparecem. Numa janela de 12
    meses o resto é zero e ninguém percebe; numa de 13 (abr/25 a abr/26) o
    último mês fica fora, os quatro trimestres somam R$ 27.280 e o card ao lado
    mostra R$ 29.040. Pior: a nota afirmava que "a soma dos trimestres
    corresponde ao total exibido", o que era falso justamente nesse caso.
    """
    if not resto_dias or resto_dias <= 0:
        return None
    # PADRÃO DE REDAÇÃO DE TELA (LEXICO_PRODUTO.md): fala do DADO, não do app.
    # Duas versões falharam antes desta. A primeira descrevia o desenho ("O
    # gráfico mostra… então as barras somam menos"); a segunda descrevia o nosso
    # artefato ("Série limitada aos trimestres completos… ficam fora dela") e
    # emendava dois fatos com dois-pontos. Esta diz o período coberto e o motivo
    # do que sobra, em duas frases, sem citar gráfico, série nem fatiamento.
    dias = f"{fmt(resto_dias, 0)} {'dia' if resto_dias == 1 else 'dias'}"
    if not rotulos:
        return f"Os {dias} finais do período não completam um trimestre."
    return (f"Período coberto: {rotulos[0].split('–')[0]} a "
            f"{rotulos[-1].split('–')[-1]}. Os {dias} finais do período não "
            f"completam um trimestre.")


# o cooperado sintético da série da ÁREA: `evolucao_trimestral` recorta por
# ID_COOPERADO, e a área entra como um "cooperado" que é a soma dos dela
_ID_AREA = "__area__"


def evolucao_da_area(por_janela: pd.DataFrame | None,
                     custo_por_janela: pd.DataFrame | None,
                     rotulos: list[str] | None = None,
                     resto_dias: int | None = None) -> dict | None:
    """A MESMA série trimestral do dossiê, com a área no lugar do cooperado.

    Custo e excedente são somas: agregá-los pela área é somar as linhas que já
    existem por cooperado, e a identidade continua valendo — os quatro
    trimestres somam o excedente do período que a Leitura da área anuncia,
    porque a cesta anual é a mesma dos dois lados.

    PACIENTES não sobe: o mesmo beneficiário pode ter passado por dois
    cooperados da área, e a soma das contagens deles seria uma contagem de
    distintos que não é distinta. Sem a coluna, o cartão do trimestre não
    escreve a linha — que é o certo, e não um traço no lugar de um número.

    Delega o desenho inteiro a `evolucao_trimestral`: dois blocos com o mesmo
    gráfico não podem ter duas escalas, dois arredondamentos e duas leituras.
    """
    if por_janela is None or not len(por_janela):
        return None
    pj = (por_janela.groupby("janela")
          .agg(consultas_totais=("consultas_totais", "sum"),
               total_itens=("total_itens", "sum"))
          .reset_index())
    if not len(pj):
        return None
    pj["taxa"] = (pj["total_itens"] / pj["consultas_totais"]
                  ).where(pj["consultas_totais"] > 0)
    pj["ID_COOPERADO"] = _ID_AREA
    # a área é sempre medida: o piso de volume decide sobre a TAXA de um
    # cooperado, e aqui o denominador é a área inteira
    pj["avaliavel"] = True

    cj = None
    if custo_por_janela is not None and len(custo_por_janela):
        cj = (custo_por_janela.groupby("janela")
              .agg(custo=("custo", "sum"),
                   excedente_reais=("excedente_reais", "sum"))
              .reset_index())
        cj["ID_COOPERADO"] = _ID_AREA

    return evolucao_trimestral(pj, cj, _ID_AREA, rotulos, resto_dias)


def evolucao_trimestral(por_janela: pd.DataFrame | None,
                        custo_por_janela: pd.DataFrame | None,
                        cooperado: str,
                        rotulos: list[str] | None = None,
                        resto_dias: int | None = None) -> dict | None:
    """A série do cooperado trimestre a trimestre: volume, índice e R$.

    Uma barra por trimestre. A barra INTEIRA é o custo efetivo do período,
    valorado a preços de referência internos; o trecho preenchido é o excedente
    dentro dele. É a mesma gramática do Pareto, no eixo do tempo — e é de
    propósito: duas leituras do mesmo dinheiro não podem ter desenhos
    diferentes, senão o leitor precisa reaprender a barra em cada bloco.

    A pergunta que ela responde e nenhum outro bloco responde: o caso é ESTÁVEL
    ou está PIORANDO. A coluna de consistência da tabela diz em quantos
    trimestres ele passou do critério; ela não diz se o excedente cresce.

    O PREÇO é constante entre os trimestres (ver `persistencia_temporal`): a
    variação da barra é volume, nunca reajuste de tabela.

    `por_janela` = `por_janela_cooperado` da persistência (índice e volume);
    `custo_por_janela` = a agregação valorada da mesma função. Sem preço, o
    bloco existe sem R$: os cartões perdem o custo por consulta e as barras
    passam a ser de SOLICITAÇÕES, porque uma barra sem grandeza declarada é
    pior que bloco nenhum. Devolve `None` quando não há trimestre medido.
    """
    if por_janela is None or not len(por_janela):
        return None
    pj = por_janela[por_janela["ID_COOPERADO"] == cooperado]
    if not len(pj):
        return None
    # O PISO DE VOLUME NÃO SE APLICA AQUI (set/2026). Ele existe para decidir se
    # uma TAXA é comparável, e este bloco não compara nada: o custo é uma soma, e
    # o excedente do trimestre é a decomposição de uma medição já feita no ano.
    # Antes, o trimestre abaixo do piso vinha sem barra e com "trimestre não
    # medido", escondendo um custo que é conhecido e ainda por cima quebrando a
    # identidade que faz os quatro somarem o excedente do período.
    # O que o piso ainda diz fica como RESSALVA: as taxas daquele trimestre
    # (SADT e custo por consulta) apoiam-se num denominador pequeno.

    cj = None
    if custo_por_janela is not None and len(custo_por_janela):
        cj = custo_por_janela[custo_por_janela["ID_COOPERADO"] == cooperado]
        cj = cj.set_index("janela") if len(cj) else None

    linhas = []
    for _, r in pj.sort_values("janela").iterrows():
        j = int(r["janela"])
        # `avaliavel` vira RESSALVA de volume, não portão de exibição
        volume_baixo = not (bool(r["avaliavel"]) if "avaliavel" in pj else True)
        consultas = float(r.get("consultas_totais") or 0)
        itens = float(r.get("total_itens") or 0)
        custo = exc = None
        if cj is not None and j in cj.index:
            custo = float(cj.loc[j, "custo"])
            exc = float(cj.loc[j, "excedente_reais"])
        rot = (rotulos[j - 1] if rotulos and len(rotulos) >= j else None)
        piso = r.get("piso")
        linhas.append({
            "janela": j,
            "rotulo": f"T{j}",
            "meses": rot,
            # o trimestre só deixa de ter barra quando não há CUSTO apurado;
            # volume baixo não esconde nada, só ressalva as taxas
            "avaliavel": custo is not None,
            "volume_baixo": volume_baixo,
            "motivo": (
                ("sem preço apurado para as solicitações deste trimestre"
                 if custo is None else
                 (f"volume baixo: {fmt(consultas, 0)} consultas, abaixo do "
                  f"mínimo de {fmt(float(piso), 0)} do trimestre"
                  if volume_baixo and piso is not None and not pd.isna(piso)
                  else ("volume baixo neste trimestre" if volume_baixo else None)))),
            "consultas": consultas,
            "consultas_fmt": fmt(consultas, 0),
            "pacientes": (None if pd.isna(r.get("pacientes"))
                          else int(r.get("pacientes"))),
            "pacientes_fmt": (None if pd.isna(r.get("pacientes"))
                              else fmt(float(r.get("pacientes")), 0)),
            "itens": itens,
            "indice": round(float(r["taxa"]), 2) if pd.notna(r["taxa"]) else None,
            "indice_fmt": (fmt(float(r["taxa"]), 2)
                           if pd.notna(r["taxa"]) else None),
            "custo": None if custo is None else round(custo, 2),
            "custo_fmt": None if custo is None else fmt_reais(custo),
            "excedente_reais": None if exc is None else round(exc, 2),
            "excedente_reais_fmt": None if exc is None else fmt_reais(exc),
            # o valor sem arredondar, para o ajuste de sobra logo abaixo
            "_exc_bruto": exc,
            "custo_por_consulta_fmt": (
                None if (custo is None or consultas <= 0)
                else fmt_reais(custo / consultas)),
            # O HOVER É FRASE, não uma pilha de rótulo e valor. O bloco de dica
            # do app (`lib/dica.js`) renderiza um parágrafo: quebra de linha ali
            # vira espaço, e "custo total: X · excedente: Y" saía corrido.
            # Só o que a barra NÃO diz sozinha: os meses do trimestre e a
            # decomposição do total. Consultas e custo por consulta já estão no
            # cartão logo abaixo, e repeti-los aqui é ruído.
            "tooltip": _tooltip_trimestre(rot, consultas, custo, exc,
                                          volume_baixo, piso),
        })
    if not linhas:
        return None

    # a escala e a leitura olham só os trimestres MEDIDOS; os outros ocupam a
    # posição deles no eixo do tempo e não entram em conta nenhuma
    med = [l for l in linhas if l["avaliavel"]]
    tem_rs = bool(med) and all(l["custo"] is not None for l in med)
    # a barra é o custo quando há preço; sem preço, é o volume de solicitações,
    # e o bloco diz isso no rótulo em vez de desenhar uma grandeza silenciosa
    grandeza = "custo" if tem_rs else "itens"
    valores = [((l["custo"] if tem_rs else l["itens"]) if l["avaliavel"] else 0.0)
               for l in linhas]
    # ── O ARREDONDAMENTO NÃO PODE QUEBRAR A IDENTIDADE ──────────────────────
    # Cada barra é publicada com 2 casas; quatro arredondamentos independentes
    # podem somar até dois centavos a mais ou a menos que o número do ano, e o
    # aceite do bloco é justamente que os dois batam na casa do centavo.
    # Sobra de arredondamento vai para a MAIOR barra, onde ela é imperceptível,
    # em vez de ficar distribuída e visível na conta de quem soma.
    _brutos = [l["_exc_bruto"] for l in linhas]
    if any(v is not None for v in _brutos):
        _tot = round(sum(v or 0.0 for v in _brutos), 2)
        _arred = [None if v is None else round(v, 2) for v in _brutos]
        _sobra = round(_tot - sum(v or 0.0 for v in _arred), 2)
        if _sobra:
            _i = max((i for i, v in enumerate(_arred) if v is not None),
                     key=lambda i: abs(_arred[i]))
            _arred[_i] = round(_arred[_i] + _sobra, 2)
        for l, v in zip(linhas, _arred):
            l["excedente_reais"] = v
            l["excedente_reais_fmt"] = None if v is None else fmt_reais(v)
        for l in linhas:
            l.pop("_exc_bruto", None)

    # A ESCALA CRUZA O ZERO quando algum trimestre tem excedente negativo. Isso
    # acontece de verdade: o excedente do trimestre é medido contra a referência
    # do ANO, e num trimestre em que ele pediu menos do que ela previa a conta dá
    # abaixo de zero. Sem clip (é o que faz os quatro somarem o número do ano),
    # então a régua precisa de espaço para baixo.
    negativos = [(l["excedente_reais"] or 0.0) for l in linhas if l["avaliavel"]]
    teto, piso, marcas = _escala_grade(max(valores) or 1.0,
                                       min(negativos) if negativos else 0.0)
    amplitude = (teto - piso) or 1.0
    # onde a linha do zero cai, medida do fundo da pista
    zero_pct = round(-piso / amplitude * 100, 2)
    for l, v in zip(linhas, valores):
        # tudo é medido contra a AMPLITUDE da régua, não contra a maior barra:
        # com a grade desenhada, uma barra que encostasse no topo contradiria a
        # última linha da régua
        l["altura_pct"] = round(v / amplitude * 100, 2)
        exc = (l["excedente_reais"] or 0.0) if l["avaliavel"] else 0.0
        l["exc_negativo"] = bool(tem_rs and exc < 0)
        l["altura_exc_pct"] = round(abs(exc) / amplitude * 100, 2) if tem_rs else 0.0
        l["topo_fmt"] = (None if not l["avaliavel"]
                         else (l["custo_fmt"] if tem_rs else fmt(l["itens"], 0)))
        # O VALOR DO EXCEDENTE dentro da própria barra, e só quando cabe: 10% da
        # pista são ~17px, o mínimo para uma linha de 11px respirar. Não cabendo,
        # o número continua no cartão do trimestre e no hover — nunca é escrito
        # por cima de um trecho que não o comporta.
        l["exc_fmt_dentro"] = (l["excedente_reais_fmt"]
                               if (tem_rs and not l["exc_negativo"]
                                   and l["altura_exc_pct"] >= 10) else None)

    # A GRADE vem do motor, não do desenho: ela é escala, e escala é número.
    # O rótulo sai sem "R$" porque a unidade já está escrita em cima de cada
    # barra; repeti-la cinco vezes na régua rouba largura do gráfico.
    grade = [{"valor": v,
              "rotulo": ("0" if v == 0 else
                         (fmt_reais(v).replace("R$ ", "") if tem_rs else fmt(v, 0))),
              "pct": round((v - piso) / amplitude * 100, 2)}
             for v in marcas]

    # ── DIREÇÃO contra o trimestre anterior ─────────────────────────────────
    # A seta é AFIRMAÇÃO, e por isso tem piso (config.VARIACAO_MINIMA_SETA): sem
    # ele, uma oscilação de meio por cento ganharia o mesmo símbolo de uma queda
    # de trinta, e a tela passaria a apontar ruído como movimento. Abaixo do
    # piso a variação não some, ela vira só texto no hover.
    _METRICAS = ("consultas", "pacientes", "indice", "custo_por_consulta")
    for l in linhas:
        if l["custo"] and l["consultas"]:
            l["custo_por_consulta"] = l["custo"] / l["consultas"]
        else:
            l["custo_por_consulta"] = None
    for anterior, atual in zip(linhas, linhas[1:]):
        var = {}
        for m in _METRICAS:
            a, b = anterior.get(m), atual.get(m)
            if a in (None, 0) or b is None:
                continue
            delta = (b - a) / a
            var[m] = {
                "pct": round(delta, 4),
                "pct_fmt": fmt_pct(abs(delta)),
                "dir": ("sobe" if delta > 0 else "cai") if abs(delta) >= config.VARIACAO_MINIMA_SETA else "estavel",
            }
        atual["variacao"] = var
    linhas[0]["variacao"] = {}

    # ── a leitura: o que a série diz, em uma frase ──────────────────────────
    # Primeiro contra último, e só. "Subiu 16%" é a única conclusão que uma
    # série de quatro pontos sustenta sem modelo; tendência com quatro
    # observações é afirmação que o dado não paga (rigor-estatistico).
    tem_negativo = any(l["exc_negativo"] for l in linhas)
    resto = _ressalva_do_resto(resto_dias, rotulos)
    nota = None
    if tem_rs:
        # a identidade "os quatro somam o total" só é AFIRMADA quando os
        # trimestres cobrem a janela inteira; fora disso o que se afirma é o
        # contrário, e com o motivo
        nota = ("Cada trimestre é medido contra a referência do período, a mesma "
                "do resumo acima."
                + ("" if resto else
                   " A soma dos trimestres corresponde ao total exibido."))
        if tem_negativo:
            nota += (" Valores abaixo de zero indicam utilização inferior a essa "
                     "referência.")
    if resto:
        nota = f"{resto} {nota}" if nota else resto

    ini, fim = med[0], med[-1]
    leitura = None
    if tem_rs and ini["custo_por_consulta_fmt"] and ini["consultas"] > 0 and fim["consultas"] > 0:
        a = ini["custo"] / ini["consultas"]
        b = fim["custo"] / fim["consultas"]
        if a > 0:
            var = (b - a) / a
            direcao = "sobe" if var > 0 else ("cai" if var < 0 else "fica estável")
            leitura = (f"O custo por consulta {direcao} {fmt_pct(abs(var))} "
                       f"de {ini['rotulo']} a {fim['rotulo']}.")
    return {
        "titulo": "Evolução trimestral",
        # O subtítulo diz O QUE ESTÁ MEDIDO e sobre que base. A descrição do
        # desenho ("a barra inteira é…") saiu: a legenda já nomeia as duas
        # tintas, e gastar a única linha de contexto explicando o gráfico
        # deixava o leitor sem saber sobre o que ele é.
        "subtitulo": ("Custo das solicitações e a parcela acima da referência "
                      "da área, trimestre a trimestre, com todos os "
                      "procedimentos do período somados."
                      if tem_rs else
                      "Solicitações por trimestre, com todos os procedimentos "
                      "do período somados. Não há preço apurado para valorar "
                      "este período."),
        "leitura": leitura,
        "nao_medidos": len(linhas) - len(med),
        "grandeza": grandeza,
        "tem_reais": tem_rs,
        "grade": grade,
        "zero_pct": zero_pct,
        "tem_negativo": tem_negativo,
        # A NOTA declara a base de comparação, e para aí. A versão anterior
        # explicava o método em três frases ("por isso os quatro somam", "sob a
        # régua do próprio período", uma remissão à coluna Consistência): isso é
        # raciocínio de quem construiu o bloco, não informação de quem o lê.
        # A frase do valor negativo só aparece quando existe algum: ressalva
        # sobre um caso que não está na tela é ruído.
        "nota": nota,
        "linhas": linhas,
    }


def pareto_custo_do_cooperado(rs_coop: pd.DataFrame) -> dict | None:
    """Onde está o dinheiro deste cooperado, por procedimento.

    MESMA construção do Pareto da tela de Área (`pareto_cooperados`), no outro
    eixo: a barra inteira é o custo do procedimento no período, o trecho
    preenchido é a parcela acima da referência da área, e a ordem
    escolhida vem pronta em `dados`. Um só desenho para o mesmo dinheiro: eram
    dois Paretos alternáveis de tinta única, e o leitor tinha de reaprender a
    barra ao descer da área para o dossiê.

    ── por que a ordem é um bloco inteiro, e não uma ordenação ─────────────────
    Num Pareto a barra, a ordem e o acumulado são a mesma grandeza. Ordenar por
    um eixo desenhando o outro deixaria a coluna de acumulado somando uma coisa
    numa ordem ditada por outra: número certo, leitura falsa. Por isso cada
    ordem é calculada por completo aqui, e a tela só troca qual mostra.

    `rs_coop` = posicao_proc_rs do cooperado. Sem preço não há barra: linha sem
    valor apurado não entra, e o total do bloco declara o que cobre.
    """
    if rs_coop is None or not len(rs_coop):
        return None
    d = rs_coop[rs_coop["preco_mediano"].notna()].copy()
    if not len(d):
        return None
    d["custo"] = d["n_solicitacoes"] * d["preco_mediano"]
    # só o excedente SINALIZADO é oportunidade: excedente medido em par que não
    # passou os portões não se apresenta como dinheiro a recuperar
    exc = d["excedente_itens"].fillna(0).clip(lower=0)
    d["excedente"] = np.where(d["sinalizado"].astype(bool),
                              exc * d["preco_mediano"], 0.0)

    agg = (d.groupby("CD_PROCEDIMENTO")
           .agg(custo=("custo", "sum"), excedente=("excedente", "sum"),
                n_solicitacoes=("n_solicitacoes", "sum"),
                preco_mediano=("preco_mediano", "first"))
           .reset_index())
    agg = agg[agg["custo"] > 0]
    if not len(agg):
        return None
    descricoes = (d.drop_duplicates("CD_PROCEDIMENTO")
                  .set_index("CD_PROCEDIMENTO")["DS_PROCEDIMENTO"])
    custos = dict(zip(agg["CD_PROCEDIMENTO"], agg["custo"].astype(float)))
    excs = dict(zip(agg["CD_PROCEDIMENTO"], agg["excedente"].astype(float)))
    por_cd = agg.set_index("CD_PROCEDIMENTO")

    def _bloco(medida: str) -> dict | None:
        fonte = excs if medida == "excedente" else custos
        valores = [(cd, v) for cd, v in fonte.items() if v > 0]
        base = _pareto_montar(valores, "procedimentos", custos, excs)
        if base is None:
            return None
        linhas, total, leitura, n_nucleo, leitura_hover = base
        for linha in linhas:
            cd = linha["id"]
            r = por_cd.loc[cd]
            desc = str(descricoes.get(cd, config.SEM_MEDIDA)).strip()
            linha["rotulo_linha"] = desc
            linha["rotulo_tooltip"] = desc
            linha["detalhes"] = [
                f"Código TUSS: {cd}",
                f"{fmt(r['n_solicitacoes'], 0)} solicitações · "
                f"{fmt_reais(r['preco_mediano'])} cada",
                f"Custo total no período: {linha['custo_fmt']}",
                (f"Acima da referência da área: {linha['excedente_rs_fmt']}"
                 if float(r["excedente"]) > 0
                 else "Dentro da referência da área"),
            ]
        # "Concentração do custo", e não "Custo excedente por procedimento": o
        # nome diz o que o gráfico RESPONDE (em quantos poucos está a maior
        # parte do dinheiro), não o que ele lista. Quem lista é a coluna, que já
        # se chama "Procedimento". Vale nas três montagens e nas duas telas.
        titulo = ("Concentração do custo excedente" if medida == "excedente"
                  else "Concentração do custo total")
        return {
            "titulo": f"{titulo} · {fmt_reais(total)}",
            "subtitulo": None,
            "colunas": {"rotulo": "Procedimento", "custo": "Custo total",
                        "valor": "Custo excedente",
                        "acumulado_reais": ("Acum. excedente (R$)" if medida == "excedente"
                                            else "Acum. custo (R$)"),
                        "acumulado": "% acum."},
            "total": round(total, 2), "total_fmt": fmt_reais(total),
            "linhas": linhas,
            "leitura_concentracao": leitura,
            "leitura_titulo": leitura_hover,
            "n_nucleo": n_nucleo,
            "limiar_concentracao": config.LIMIAR_CONCENTRACAO_PARETO,
            "grandeza": ("do excesso" if medida == "excedente" else "do custo"),
            "duplo": True,
            # SEM a ressalva de teto no rodapé (set/2026, pedido do usuário).
            # O subtítulo do bloco já declara que o preço é interno e provisório,
            # e no dossiê o Pareto responde "onde está o dinheiro DELE", não
            # "quanto se recupera": o parágrafo sobre economia realizada estava
            # respondendo uma pergunta que este bloco não faz. Na tela de Área
            # ele fica, porque lá o número é apresentado como oportunidade.
        }

    ordens = {"custo": _bloco("custo"), "excedente": _bloco("excedente")}
    if ordens["custo"] is None:
        return None
    # o DEFAULT é o custo: no dossiê a primeira pergunta é onde está o dinheiro
    # deste cooperado, e o excedente é a leitura seguinte. Na tela de Área é o
    # contrário, porque lá a lista já é a fila de quem está fora do padrão.
    return {
        "ordem_default": "custo",
        "ordens": [{"chave": "custo", "rotulo": "Custo total"},
                   {"chave": "excedente", "rotulo": "Custo excedente"}],
        "dados": {k: v for k, v in ordens.items() if v is not None},
    }


def _pareto_vazio(titulo: str, colunas: dict, subtitulo: str | None,
                  n_em_cena: int) -> dict:
    """O Pareto que existe e não tem o que distribuir. Só acontece sob recorte:
    o bloco continua na tela, dizendo que o conjunto escolhido não tem excedente
    valorado — que é informação, e diferente de "o bloco sumiu"."""
    return {
        "titulo": f"{titulo} · {fmt_reais(0)}",
        "subtitulo": subtitulo,
        "colunas": colunas,
        "total": 0.0, "total_fmt": fmt_reais(0),
        "n_nucleo": 0,
        "limiar_concentracao": config.LIMIAR_CONCENTRACAO_PARETO,
        "leitura_concentracao": None,
        "leitura_titulo": None,
        # dois vazios diferentes, e a diferença importa: "ninguém em cena" é
        # recorte que não alcança cooperado nenhum; "ninguém com excedente" é
        # recorte cheio de gente que não tem o que convergir
        "vazio": ("nenhum cooperado em cena neste recorte" if not n_em_cena else
                  f"nenhum excedente valorado entre os {fmt(n_em_cena, 0)} "
                  "em cena"),
        "linhas": [],
    }


def pareto_cooperados(reais_coop: dict[str, float],
                      linhas_coop: list[dict],
                      ids: list[str] | None = None,
                      subtitulo: str | None = None,
                      custos_coop: dict[str, float] | None = None) -> dict | None:
    """Pareto de custo por cooperado, com o EXCEDENTE aninhado dentro do custo.

    A barra inteira é o custo do período valorado a preços de referência
    internos; o trecho preenchido é a parcela acima da referência do grupo, ou
    seja, a soma dos procedimentos em que o cooperado passou o critério.

    ── duas ordens, um bloco ────────────────────────────────────────────────
    Num Pareto a ordem e o acumulado são a MESMA grandeza, e aqui há duas
    concorrendo. Em vez de escolher uma, o bloco entrega as duas prontas e a
    tela troca: `dados["excedente"]` e `dados["custo"]`, cada uma com sua
    ordem, seu acumulado e seu total. O que NÃO se faz é ordenar por uma e
    acumular a outra, que dá número certo e leitura falsa.
    O default é o excedente: ele é o produto desta tela; o custo é contexto.

    `ids` é QUEM ESTÁ EM CENA. Sendo `None`, é a área inteira. Total, ordem,
    % acumulado e o número do título são todos do conjunto recortado — este é
    um bloco de ACHADO, e achado segue o filtro (CLAUDE.md).

    A RÉGUA não entra aqui: nenhum número deste bloco é referência, mediana ou
    critério — são somas já medidas contra a régua da área, que permanece a
    mesma sob qualquer recorte.

    `None` quando não há excedente valorado em cena (sem referência plena, sem
    sinalizados, ou recorte que não alcança ninguém com R$).
    """
    em_cena = None if ids is None else set(ids)
    exc = {c: float(v) for c, v in reais_coop.items()
           if em_cena is None or c in em_cena}
    custos = {c: float(v) for c, v in (custos_coop or {}).items()
              if c in exc and (v or 0) > 0}
    # sem custo apurado a barra aninhada não existe: o bloco volta a ser o
    # Pareto de uma grandeza só, em vez de desenhar um todo que não foi medido
    duplo = len(custos) == len(exc) and bool(custos)

    colunas = {"rotulo": "Cooperado", "valor": "Excesso (R$)",
               "acumulado_reais": "Acumulado (R$)", "acumulado": "% acum."}
    if not exc or sum(exc.values()) <= 0:
        return None if em_cena is None else _pareto_vazio(
            "Excesso em R$ por cooperado", colunas, subtitulo, len(em_cena))

    por_id = {l["id"]: l for l in linhas_coop}
    de_quem = "do total da área" if em_cena is None else "do total em cena"

    def _bloco(medida: str) -> dict | None:
        valores = list((exc if medida == "excedente" else custos).items())
        base = _pareto_montar(valores, "cooperados",
                              custos if duplo else None,
                              exc if duplo else None)
        if base is None:
            return None
        linhas, total, leitura, n_nuc, leitura_hover = base
        for linha in linhas:
            l = por_id.get(linha["id"], {})
            origem = l.get("origem_excedente") or {}
            topo = origem.get("topo") or {}
            pos = (l.get("posicao") or {}).get("rotulo")
            linha["rotulo_linha"] = linha["id"]
            linha["rotulo_tooltip"] = (f"{linha['id']} · posição {pos} na área"
                                       if pos else linha["id"])
            linha["detalhes"] = [
                (f"Custo total: {linha['custo_fmt']}" if duplo else None),
                f"Variação excedente: "
                f"{linha.get('excedente_rs_fmt', linha['reais_fmt'])}",
                (f"Solicitações excedentes: {l.get('excedente_fmt', config.SEM_MEDIDA)}"
                 f" · {linha['pct_do_total_fmt']} {de_quem}"),
            ]
            linha["detalhes"] = [d for d in linha["detalhes"] if d]
            if topo.get("descricao"):
                linha["detalhes"].append(
                    f"Maior volume excedente: {topo['descricao'].strip()} "
                    f"({topo['razao_fmt']} a referência da área)")
            elif origem.get("leitura"):
                linha["detalhes"].append(f"Origem: {origem['leitura']}")
        titulo = ("Concentração do custo excedente" if medida == "excedente"
                  else "Concentração do custo total")
        cols = dict(colunas)
        if duplo:
            # os dois valores ficam SEMPRE na mesma ordem de colunas; o que a
            # ordem escolhida muda é só o que a coluna de acumulado soma, e ela
            # diz isso no próprio rótulo
            cols = {"rotulo": "Cooperado", "custo": "Custo total",
                    "valor": "Custo excedente",
                    "acumulado_reais": ("Acum. excedente (R$)" if medida == "excedente"
                                        else "Acum. custo (R$)"),
                    "acumulado": "% acum."}
        return {
            "titulo": f"{titulo} · {fmt_reais(total)}",
            "subtitulo": subtitulo,
            "colunas": cols,
            "total": round(total, 2), "total_fmt": fmt_reais(total),
            "n_nucleo": n_nuc,
            "limiar_concentracao": config.LIMIAR_CONCENTRACAO_PARETO,
            "leitura_concentracao": leitura,
            "leitura_titulo": leitura_hover,
            "grandeza": ("do excesso" if medida == "excedente" else "do custo"),
            "duplo": duplo,
                "linhas": linhas,
        }

    ordens = {"excedente": _bloco("excedente")}
    if duplo:
        ordens["custo"] = _bloco("custo")
    if ordens["excedente"] is None:
        return None if em_cena is None else _pareto_vazio(
            "Excesso em R$ por cooperado", colunas, subtitulo, len(em_cena))
    if not duplo:
        return ordens["excedente"]
    return {
        "ordem_default": "excedente",
        "ordens": [{"chave": "custo", "rotulo": "Custo total"},
                   {"chave": "excedente", "rotulo": "Custo excedente"}],
        "dados": {k: v for k, v in ordens.items() if v is not None},
    }


def pareto_procedimentos(rs_area: pd.DataFrame,
                         ids: list[str] | None = None,
                         subtitulo: str | None = None,
                         custo_pares: pd.DataFrame | None = None) -> dict | None:
    """Pareto de custo por procedimento, com o EXCEDENTE aninhado dentro dele.

    Mesma construção do Pareto de cooperados, agregada pelo outro eixo — os
    totais de excedente são, por construção, idênticos, e seguem idênticos sob
    recorte porque o corte é o MESMO conjunto de cooperados aplicado antes das
    duas agregações.

    `rs_area` = pares sinalizados com preço da área (posicao_proc_rs filtrado);
    é de onde sai o EXCEDENTE. O custo total vem de `custo_pares`, que são os
    pares SEM o filtro de sinalização: o denominador do custo é tudo que foi
    solicitado, não só o que passou os portões. Sem ele não há barra aninhada.

    `ids` = quem está em cena; `None` é a área inteira.
    """
    colunas = {"rotulo": "Procedimento", "valor": "Excesso (R$)",
               "acumulado_reais": "Acumulado (R$)",
               "acumulado": "% acum."}
    vazio = (None if ids is None else
             lambda: _pareto_vazio("Excesso em R$ por procedimento",
                                   colunas, subtitulo, len(ids)))
    if rs_area is None or not len(rs_area):
        return None if vazio is None else vazio()
    if ids is not None:
        rs_area = rs_area[rs_area["ID_COOPERADO"].isin(list(ids))]
        if not len(rs_area):
            return vazio()
    agg = (rs_area.groupby("CD_PROCEDIMENTO")
           .agg(reais=("excedente_reais", "sum"),
                itens=("excedente_itens", "sum"),
                n_coop=("ID_COOPERADO", "nunique")))
    descricoes = (rs_area.drop_duplicates("CD_PROCEDIMENTO")
                  .set_index("CD_PROCEDIMENTO")["DS_PROCEDIMENTO"])
    exc = {cd: float(v) for cd, v in agg["reais"].items()}

    custos: dict[str, float] = {}
    if custo_pares is not None and len(custo_pares):
        cp = custo_pares
        if ids is not None:
            cp = cp[cp["ID_COOPERADO"].isin(list(ids))]
        if len(cp):
            custos = {cd: float(v) for cd, v
                      in cp.groupby("CD_PROCEDIMENTO")["custo"].sum().items()
                      if cd in exc and (v or 0) > 0}
    duplo = len(custos) == len(exc) and bool(custos)

    if not exc or sum(exc.values()) <= 0:
        return None if vazio is None else vazio()

    def _bloco(medida: str) -> dict | None:
        valores = list((exc if medida == "excedente" else custos).items())
        base = _pareto_montar(valores, "procedimentos",
                              custos if duplo else None,
                              exc if duplo else None)
        if base is None:
            return None
        linhas, total, leitura, n_nuc, leitura_hover = base
        for linha in linhas:
            cd = linha["id"]
            desc = str(descricoes.get(cd, config.SEM_MEDIDA)).strip()
            # na linha vai a descrição (o que se lê); o código TUSS no tooltip
            linha["rotulo_linha"] = desc
            linha["rotulo_tooltip"] = desc
            linha["detalhes"] = [
                f"Código TUSS: {cd}",
                (f"Custo total: {linha['custo_fmt']}" if duplo else None),
                f"Variação excedente: "
                f"{linha.get('excedente_rs_fmt', linha['reais_fmt'])}",
                (f"Solicitações excedentes: {fmt(agg['itens'][cd], 0)}"
                 f" · {linha['pct_do_total_fmt']} "
                 f"{'do total da área' if ids is None else 'do total em cena'}"),
                f"Cooperados acima do critério neste procedimento: "
                f"{int(agg['n_coop'][cd])}",
            ]
            linha["detalhes"] = [d for d in linha["detalhes"] if d]
        # "Concentração do custo", e não "Custo excedente por procedimento": o
        # nome diz o que o gráfico RESPONDE (em quantos poucos está a maior
        # parte do dinheiro), não o que ele lista. Quem lista é a coluna, que já
        # se chama "Procedimento". Vale nas três montagens e nas duas telas.
        titulo = ("Concentração do custo excedente" if medida == "excedente"
                  else "Concentração do custo total")
        cols = dict(colunas)
        if duplo:
            cols = {"rotulo": "Procedimento", "custo": "Custo total",
                    "valor": "Custo excedente",
                    "acumulado_reais": ("Acum. excedente (R$)" if medida == "excedente"
                                        else "Acum. custo (R$)"),
                    "acumulado": "% acum."}
        return {
            "titulo": f"{titulo} · {fmt_reais(total)}",
            "subtitulo": subtitulo,
            "colunas": cols,
            "total": round(total, 2), "total_fmt": fmt_reais(total),
            "n_nucleo": n_nuc,
            "limiar_concentracao": config.LIMIAR_CONCENTRACAO_PARETO,
            "leitura_concentracao": leitura,
            "leitura_titulo": leitura_hover,
            "grandeza": ("do excesso" if medida == "excedente" else "do custo"),
            "duplo": duplo,
                "linhas": linhas,
        }

    ordens = {"excedente": _bloco("excedente")}
    if duplo:
        ordens["custo"] = _bloco("custo")
    if ordens["excedente"] is None:
        return None if vazio is None else vazio()
    if not duplo:
        return ordens["excedente"]
    return {
        "ordem_default": "excedente",
        "ordens": [{"chave": "custo", "rotulo": "Custo total"},
                   {"chave": "excedente", "rotulo": "Custo excedente"}],
        "dados": {k: v for k, v in ordens.items() if v is not None},
    }


def linhas_procedimentos(norma_proc_area: pd.DataFrame, posproc_area: pd.DataFrame,
                         gatilho_pedido: str, alvo: str,
                         reais_proc: dict[str, float] | None = None,
                         ids: list[str] | None = None) -> list[dict]:
    """Uma linha por procedimento da área: prevalência, solicitantes elegíveis,
    referência (mediana/P75/P90), qualidade da referência, solicitações,
    quantos estão acima do critério, variação excedente e % acumulado.

    Ordenado por variação excedente (magnitude = onde agir). A razão viaja junto
    como segunda lente: razão sozinha favorece o raro (rigor-estatistico §3).
    O % acumulado é do Pareto DESTA lista, declarado no campo, não implícito.

    ── o recorte entra por METADE da tabela ─────────────────────────────────
    `ids` são os cooperados em cena. Ele filtra SÓ o achado — solicitações,
    quantos estão acima do critério, variação excedente, R$, razão e %
    acumulado. As colunas de RÉGUA (prevalência, solicitantes elegíveis,
    referência, qualidade) ficam imóveis, vindas de `norma_proc_area` intacto.

    SOLICITAÇÕES é o volume bruto do exame entre quem está em cena, e responde
    a pergunta que nenhuma outra coluna respondia: o que a área mais pede.
    Prevalência diz quantos cooperados pedem, não quanto se pede — um exame que
    todos solicitam uma vez por ano e outro que todos solicitam toda semana
    saíam com a mesma prevalência. Ele segue o recorte, e não a régua, porque
    é magnitude do que está em cena: com o denominador da área ao lado de um
    excedente recortado, a divisão que o olho faz entre as duas colunas
    misturaria populações.

    Não é preciosismo: prevalência é `solicitantes / elegíveis da área`.
    Filtrar o numerador pelo recorte e deixar o denominador da área daria uma
    porcentagem que não é de conjunto nenhum (rigor-estatistico §9), e filtrar
    os dois reconstruiria a norma sobre 21 pessoas — comparar os recortados
    entre si é justamente o que a regra proíbe.

    A LISTA NÃO ENCOLHE. Procedimento cujo excedente vinha inteiro de alguém
    fora do recorte fica, com 0: é zero MEDIDO ("nenhum excedente vem destes"),
    não ausência de cálculo — o travessão é reservado ao que não foi calculado.
    Ordenada por excedente, a linha afunda sozinha para o fim.
    """
    em_cena = (posproc_area if ids is None else
               posproc_area[posproc_area["ID_COOPERADO"].isin(list(ids))])
    # VOLUME sai de `em_cena`, não de `sinal`: são todas as solicitações do
    # exame entre quem está em cena, e não só as de quem passou o critério
    # nele. Contado sobre os sinalizados, o número viraria outra leitura do
    # excedente em vez do total que ele existe para dar.
    solicitacoes = (em_cena.groupby("CD_PROCEDIMENTO")["n_solicitacoes"].sum()
                    if len(em_cena) else {})

    sinal = filtrar_sinalizados(em_cena)
    agg = (sinal.groupby("CD_PROCEDIMENTO")
           .agg(excedente_itens=("excedente_itens", "sum"),
                n_acima=("ID_COOPERADO", "nunique"),
                razao_mediana=("razao_vs_mediana", "median"))
           if len(sinal) else
           pd.DataFrame(columns=["excedente_itens", "n_acima", "razao_mediana"]))

    df = norma_proc_area.copy()
    df["excedente_itens"] = df["CD_PROCEDIMENTO"].map(
        agg["excedente_itens"] if len(agg) else {}).fillna(0.0)
    df["n_acima"] = df["CD_PROCEDIMENTO"].map(
        agg["n_acima"] if len(agg) else {}).fillna(0).astype(int)
    df["razao_mediana"] = df["CD_PROCEDIMENTO"].map(
        agg["razao_mediana"] if len(agg) else {})
    df["n_solicitacoes"] = df["CD_PROCEDIMENTO"].map(
        solicitacoes).fillna(0).astype(int)

    descricoes = (posproc_area.drop_duplicates("CD_PROCEDIMENTO")
                  .set_index("CD_PROCEDIMENTO")["DS_PROCEDIMENTO"])
    df = df.sort_values(["excedente_itens", "n_solicitantes_elegiveis"],
                        ascending=False)
    total_exc = float(df["excedente_itens"].sum())
    acumulado = 0.0

    linhas = []
    for _, r in df.iterrows():
        exc = float(r["excedente_itens"])
        acumulado += exc
        pct_acum = (acumulado / total_exc) if total_exc > 0 else None
        gat = r.get("gatilho_usado")
        gat = None if (gat is None or (isinstance(gat, float) and np.isnan(gat))) else gat
        linhas.append({
            "codigo": r["CD_PROCEDIMENTO"],
            "descricao": descricoes.get(r["CD_PROCEDIMENTO"], config.SEM_MEDIDA),
            "prevalencia": round(float(r["prevalencia"]), 4),
            "prevalencia_fmt": fmt_pct(float(r["prevalencia"])),
            "n_solicitantes_elegiveis": int(r["n_solicitantes_elegiveis"]),
            "n_elegiveis_area": int(r["n_elegiveis_area"]),
            "referencia": {
                "mediana": None if pd.isna(r["mediana"]) else round(float(r["mediana"]), 4),
                "mediana_fmt": fmt_taxa(r["mediana"]),
                "p75": None if pd.isna(r["p75"]) else round(float(r["p75"]), 4),
                "p75_fmt": fmt_taxa(r["p75"]),
                "p90": None if pd.isna(r["p90"]) else round(float(r["p90"]), 4),
                "p90_fmt": fmt_taxa(r["p90"]),
                "alvo_usado": alvo,
            },
            "qualidade": {
                "apresentavel": bool(r["apresentavel"]),
                "gatilho_usado": gat,
                "criterio_ajustado": bool(gat is not None and gat != gatilho_pedido),
                # rótulos do LEXICO_PRODUTO.md — a UI não inventa a própria frase.
                # O caso APRESENTÁVEL também recebe rótulo: a coluna de qualidade
                # da aba Procedimentos precisa dizer os dois estados, e "célula
                # vazia" ali leria como ausência de informação, não como "está boa".
                "rotulo": ("sólida" if r["apresentavel"] else "referência não conclusiva"),
                "rotulo_criterio": ("critério ajustado ao tamanho do grupo"
                                    if gat is not None and gat != gatilho_pedido else None),
                "motivo": (None if r["apresentavel"] else
                           f"referência construída com "
                           f"{int(r['n_solicitantes_elegiveis'])} solicitantes, "
                           f"abaixo do mínimo"),
            },
            # zero aqui é zero MEDIDO — ninguém em cena pediu este exame —,
            # e por isso sai como "0" e não como travessão.
            "n_solicitacoes": int(r["n_solicitacoes"]),
            "n_solicitacoes_fmt": fmt(int(r["n_solicitacoes"]), 0),
            "n_acima_do_criterio": int(r["n_acima"]),
            "razao_mediana": (None if pd.isna(r["razao_mediana"])
                              else round(float(r["razao_mediana"]), 3)),
            "razao_mediana_fmt": (config.SEM_MEDIDA if pd.isna(r["razao_mediana"])
                                  else f"{fmt(r['razao_mediana'], 1)}×"),
            "excedente_itens": round(exc, 2),
            "excedente_fmt": fmt(exc, 0) if exc else config.SEM_MEDIDA,
            # ESTIMATIVA (preço interno provisório); ausente quando o par não
            # tem preço nas contas, mesmo com excedente medido
            "excedente_reais": ((reais_proc or {}).get(r["CD_PROCEDIMENTO"]) and
                                round(float(reais_proc[r["CD_PROCEDIMENTO"]]), 2)),
            "excedente_reais_fmt": (
                None if not (reais_proc or {}).get(r["CD_PROCEDIMENTO"]) else
                fmt_reais(reais_proc[r["CD_PROCEDIMENTO"]])),
            "pct_acumulado": None if pct_acum is None else round(pct_acum, 4),
            "pct_acumulado_fmt": fmt_pct(pct_acum),
        })
    return linhas


# ─────────────────────────────────────────────────────────────────────────────
# PAINEL DO PROCEDIMENTO NA ÁREA
#
# O irmão de `painel_do_procedimento` com a unidade de análise trocada. Lá a
# pergunta é "de onde vem o volume DESTE médico"; aqui é **este exame é norma da
# área ou hábito de alguns**, e a diferença não é de grau: a tabela de
# procedimentos não distingue os dois casos, e eles pedem ações opostas.
#
# O caso que motivou o bloco, em Ginecologia (abr/25–abr/26, P75/mediana):
#
#   US Transvaginal            mediana 0,283 · P75 0,355   difuso, 15 acima
#   US Estruturas Superficiais mediana 0,032 · P75 0,135   subgrupo, 13 acima
#
# Nas colunas as duas linhas se parecem (prevalência alta, excedente grande). Na
# distribuição, não: no segundo o P75 é QUATRO vezes a mediana — "normal" é
# quase zero e um subgrupo transformou o exame em rotina. O primeiro é discussão
# de protocolo, o segundo é auditoria.
#
# Nada nasce aqui. Cada seção é a saída de um motor que a tela de área já roda,
# lida por procedimento em vez de por cooperado.
# ─────────────────────────────────────────────────────────────────────────────


def distribuicao_do_procedimento(taxas_por_coop: dict[str, float],
                                 linha_norma, gatilho: str | None,
                                 criterio_pedido: str, alvo: str,
                                 consultas_por_coop: dict[str, float] | None = None,
                                 n_area: int | None = None,
                                 excedente_por_coop: dict[str, float] | None = None,
                                 reais_por_coop: dict[str, float] | None = None,
                                 ids_em_cena: set[str] | None = None
                                 ) -> dict | None:
    """A distribuição da ÁREA neste exame: box plot com um ponto por cooperado.

    É o box plot do painel do cooperado (`regua_do_procedimento`) com o enxame
    da tela de Área por cima — mesma geometria (`_escala`/`_pos`), mesmas
    classes, mesma leitura. A diferença é que aqui não há um ponto para achar:
    há a FORMA, e a forma é a resposta.

    A LEITURA vem redigida daqui, e é o que o desenho sozinho não afirma: a
    razão entre o P75 e a mediana separa o exame que a área inteira pede muito
    do exame que quase ninguém pede e um punhado transformou em rotina. Dois
    excedentes idênticos, duas conversas diferentes.

    Cor pela mesma rampa `--i` da distribuição da área (o CSS já a converte em
    tinta): quem está acima do critério satura, quem está dentro recua. Nenhuma
    classe nova, nenhum segundo vocabulário visual para a mesma leitura.
    """
    taxas = {c: float(v) for c, v in (taxas_por_coop or {}).items()
             if v is not None and not np.isnan(float(v))}
    if not taxas or linha_norma is None:
        return None
    if pd.isna(linha_norma.get(alvo)):
        return None

    referencia = float(linha_norma[alvo])
    p25 = float(np.quantile(list(taxas.values()), 0.25))
    p75 = float(linha_norma["p75"]) if pd.notna(linha_norma.get("p75")) else None
    valor_crit = (float(linha_norma[gatilho])
                  if gatilho and pd.notna(linha_norma.get(gatilho)) else None)
    minimo, maximo = min(taxas.values()), max(taxas.values())

    escala = _escala([v for v in (minimo, maximo, p25, p75, referencia,
                                  valor_crit, 0.0) if v is not None])

    # ── a rampa de cor: posição do cooperado na ORDEM dos EXCEDENTES ─────────
    #
    # A MESMA regra da distribuição da tela de Área, e por um motivo que só
    # apareceu com o painel na tela: a lista "Acima do critério" ordena por
    # EXCEDENTE e o eixo do gráfico é a TAXA, que são grandezas diferentes
    # (excedente ≈ (taxa − referência) × consultas). Em US Estruturas
    # Superficiais o primeiro da lista é o 11º ponto mais à direita, e o ponto
    # mais à direita de todos não entra na lista: taxa alta, volume pequeno.
    #
    # Pintando por distância à referência — como esta função fazia — o gráfico
    # dizia "estes treze são iguais" enquanto a lista dizia que um vale 907 e
    # outro vale 30. Pintando pelo excedente, o ponto mais escuro é o primeiro
    # da lista, e as duas leituras param de se contradizer sem que nenhuma das
    # duas ordens mude: a lista responde onde está o dinheiro, o eixo responde
    # quem pede fora do padrão.
    exc = {c: float(v) for c, v in (excedente_por_coop or {}).items()
           if v and float(v) > 0}
    ordem_exc = sorted(exc.values())

    def _i(coop):
        v = exc.get(coop)
        if v is None or len(ordem_exc) < 2:
            return 0.0
        return round(ordem_exc.index(v) / (len(ordem_exc) - 1), 4)

    pontos = []
    for coop, taxa in sorted(taxas.items(), key=lambda kv: kv[1]):
        acima = valor_crit is not None and taxa > valor_crit
        cons = (consultas_por_coop or {}).get(coop)
        e = exc.get(coop)
        pontos.append({
            "id": coop,
            "pos_pct": _pos(taxa, escala),
            "valor_fmt": fmt_frequencia(taxa),
            "intensidade": _i(coop),
            "acima": acima,
            # POSIÇÃO é régua e não se move; TINTA e presença seguem o recorte.
            # Quem está fora dele recua (a mesma `.pt-no-recorte` da
            # distribuição da tela de Área), porque o excedente que pinta o
            # ponto é o do conjunto em cena — deixá-lo aceso com tinta de outra
            # população seria a contradição que o recorte veio corrigir.
            "em_cena": ids_em_cena is None or coop in ids_em_cena,
            "consultas_fmt": None if not cons else fmt(cons, 0),
            "excedente_fmt": None if not e else fmt(e, 0),
            "reais_fmt": (fmt_reais((reais_por_coop or {})[coop])
                          if (reais_por_coop or {}).get(coop) else None),
            "leitura": (f"{fmt(taxa / referencia, 1)}× a referência da área"
                        if referencia else config.SEM_MEDIDA),
        })

    # ── a leitura, em uma frase ─────────────────────────────────────────────
    # O que separa "a área inteira pede muito" de "um subgrupo pede sempre" é a
    # ASSIMETRIA da distribuição, não o tamanho do excedente. A razão P75/mediana
    # é a forma mais curta de dizê-la, e o corte é declarado no texto para o
    # leitor poder discordar dele.
    leitura = None
    if p75 is not None and referencia:
        razao = p75 / referencia
        n_acima = sum(1 for p in pontos if p["acima"])
        if razao >= 2:
            leitura = (f"Distribuição assimétrica: o P75 da área é "
                       f"{fmt(razao, 1)}× a referência. O procedimento é pouco "
                       f"frequente para a maioria e rotina para um subgrupo.")
        elif razao >= 1.4:
            leitura = (f"Distribuição alongada à direita: o P75 da área é "
                       f"{fmt(razao, 1)}× a referência. O excedente vem de uma "
                       f"cauda, não do conjunto.")
        else:
            leitura = (f"Distribuição compacta: o P75 da área é "
                       f"{fmt(razao, 1)}× a referência. O volume é próximo "
                       f"entre os cooperados e o excedente é difuso.")
        if n_acima:
            leitura += (f" {fmt(n_acima, 0)} de {fmt(len(pontos), 0)} "
                        f"{'está' if n_acima == 1 else 'estão'} acima do "
                        f"critério.")

    return {
        "haste": {"pos_pct": _pos(minimo, escala),
                  "largura_pct": round(_pos(maximo, escala) - _pos(minimo, escala), 2),
                  "min_fmt": fmt_frequencia(minimo),
                  "max_fmt": fmt_frequencia(maximo),
                  "rotulo": "menor e maior da área"},
        "iqr": {"pos_pct": _pos(p25, escala),
                "largura_pct": (round(_pos(p75, escala) - _pos(p25, escala), 2)
                                if p75 is not None else 0.0),
                "rotulo": "metade central da área"},
        "referencia": {"valor_fmt": fmt_frequencia(referencia),
                       "pos_pct": _pos(referencia, escala),
                       "rotulo": f"Referência de adequação ({_ROTULO_NIVEL.get(alvo, alvo)})"},
        "criterio": (None if valor_crit is None else
                     {"valor_fmt": fmt_frequencia(valor_crit),
                      "pos_pct": _pos(valor_crit, escala),
                      "rotulo": f"Critério de revisão ({gatilho.upper()})",
                      "ajustado": gatilho != criterio_pedido}),
        "pontos": pontos,
        "n_fora_do_recorte": sum(1 for x in pontos if not x["em_cena"]),
        "n_pares": len(pontos),
        "n_area": n_area,
        "leitura": leitura,
        "sem_criterio_motivo": (None if valor_crit is not None else
                                "Cooperados insuficientes na área para sustentar "
                                "percentil. Distribuição descritiva, sem critério."),
    }


def concentracao_entre_cooperados(excedente_por_coop: dict[str, float],
                                  reais_por_coop: dict[str, float] | None = None,
                                  fracao: float = config.FRACAO_PARETO_MATERIAL
                                  ) -> dict | None:
    """Quantos cooperados concentram 80% do excedente DESTE exame.

    A pergunta prática que fecha a distribuição: quantas conversas resolvem o
    caso. Mesmo cálculo do Pareto da página (`FRACAO_PARETO_MATERIAL`), aplicado
    a uma linha em vez de à área inteira.
    """
    itens = sorted(((c, float(v)) for c, v in (excedente_por_coop or {}).items()
                    if v and float(v) > 0), key=lambda kv: -kv[1])
    if not itens:
        return None
    total = sum(v for _, v in itens)
    acumulado, n_nucleo = 0.0, 0
    for _, v in itens:
        acumulado += v
        n_nucleo += 1
        if acumulado / total >= fracao:
            break
    reais = sum(float((reais_por_coop or {}).get(c) or 0.0)
                for c, _ in itens[:n_nucleo]) or None
    return {
        "n_nucleo": n_nucleo,
        "n_com_excedente": len(itens),
        "fracao_fmt": fmt_pct(fracao),
        "reais_fmt": None if reais is None else fmt_reais(reais),
        "frase": (f"{fmt(n_nucleo, 0)} de {fmt(len(itens), 0)} "
                  f"{'cooperado concentra' if n_nucleo == 1 else 'cooperados concentram'} "
                  f"{fmt_pct(fracao)} do excedente deste procedimento."),
    }


def cooperados_acima_do_criterio(linhas_par: list[dict], n_nucleo: int | None = None,
                                 minimo: int = config.MIN_NOMES_PAINEL,
                                 maximo: int = config.MAX_NOMES_PAINEL) -> dict:
    """Quem está acima do critério neste exame, do maior excedente ao menor.

    É a seção que fecha o painel em AÇÃO: o passo seguinte do auditor é sempre
    uma pessoa, e sem esta lista a resposta exigia fechar o painel, trocar de
    aba e procurar o exame na tabela de cada cooperado.

    ── quantos nomes, e por quê ──────────────────────────────────────────────
    O corte é a REGRA DE CONCENTRAÇÃO que a seção logo acima já anuncia: entram
    os cooperados que somam `FRACAO_PARETO_MATERIAL` do excedente do exame.

    Era um número fixo (oito), e ele acertava por acaso — nestes dados os oito
    primeiros somam de 79% a 97% do excedente, porque a cauda é curta. Mas em
    40316378 QUATRO pessoas fazem 97%, e listar oito ali enfileira quatro nomes
    irrelevantes; em 41301099 são nove, e o corte em oito deixa um relevante de
    fora. A regra se ajusta ao caso, e transforma a frase da seção anterior na
    legenda desta: "8 de 13 concentram 80%" passa a nomear exatamente estes 8.

    O piso existe porque lista de um nome não é lista; o teto, porque acima
    dele a gaveta vira rolagem — e aí a resposta certa é abrir o resto sob
    demanda, não empilhar. `linhas` traz TODOS, e `n_visiveis` diz onde cortar:
    a tela mostra o núcleo e revela a cauda quando pedida (§10, disclosure
    progressivo).
    """
    ordenadas = sorted(linhas_par, key=lambda l: -(l.get("excedente_itens") or 0))
    corte = min(max(n_nucleo or minimo, minimo), maximo, len(ordenadas))
    return {
        "n": len(ordenadas),
        "n_visiveis": corte,
        "linhas": ordenadas,
        "resto": max(0, len(ordenadas) - corte),
        # a fração viaja formatada para a tela não escrever "80%" à mão: o
        # número é do config, e um literal aqui é o dia em que ele muda lá e a
        # frase da gaveta continua dizendo o valor antigo
        "fracao_fmt": fmt_pct(config.FRACAO_PARETO_MATERIAL),
        "criterio_do_corte": (f"Os que somam {fmt_pct(config.FRACAO_PARETO_MATERIAL)} "
                              f"do excedente deste procedimento."),
    }


def painel_do_procedimento_na_area(cd: str, descricao: str, distribuicao: dict | None,
                                   nucleo: dict | None, acima: dict,
                                   peso: dict | None, repeticao: dict | None,
                                   autorreferencia: dict, qualidade: dict | None
                                   ) -> dict:
    """O painel lateral de UM procedimento da ÁREA (espec §3, outra unidade).

    Ordem de leitura, do fato mais forte ao contexto: quanto pesa na área ->
    como se distribui entre os cooperados -> quantos concentram o excedente ->
    quem são -> para quem se pede -> quantas vezes nos mesmos -> quem executou
    -> como se comportou no tempo.

    É a mesma sequência do painel do dossiê com o sujeito trocado, e de
    propósito: quem aprendeu a ler um lê o outro. O que muda é o meio da
    cadeia — lá "concentra em quais pacientes", aqui "concentra em quais
    cooperados" —, porque é aí que a pergunta da tela é outra.
    """
    return {
        "codigo": cd,
        "descricao": descricao,
        "qualidade": qualidade,
        "distribuicao": distribuicao,
        "nucleo": nucleo,
        "acima": acima,
        "peso": peso,
        "repeticao": repeticao,
        "autorreferencia": autorreferencia,
        "sem_medida": config.SEM_MEDIDA,
    }


def peso_do_exame_na_area(n_solicitacoes: float, total_area: float,
                          custo: float | None, custo_area: float | None,
                          excedente_reais: float | None,
                          preco: float | None) -> dict | None:
    """Quanto este exame pesa no que a área solicitou no período.

    O denominador é o RECORTE em cena, o mesmo das outras seções: a fração de um
    exame sobre o total da área ao lado de um excedente recortado seria a
    divisão de duas populações.
    """
    if not total_area:
        return None
    return {
        "proporcao_fmt": fmt_pct(n_solicitacoes / total_area, 1),
        "solicitacoes_fmt": fmt(n_solicitacoes, 0),
        "custo_total_fmt": None if custo is None else fmt_reais(custo),
        "custo_unitario_fmt": None if preco is None else fmt_reais(preco),
        "proporcao_custo_fmt": (None if not custo or not custo_area else
                                fmt_pct(custo / custo_area, 1)),
        "excedente_fmt": None if not excedente_reais else fmt_reais(excedente_reais),
        "excedente_pct_fmt": (None if not excedente_reais or not custo else
                              fmt_pct(excedente_reais / custo)),
    }


def repeticao_do_exame_na_area(pacientes: dict | None,
                               n_carteira: int | None = None) -> dict | None:
    """Repetição por beneficiário, no conjunto em cena.

    Distingue "muitos pacientes uma vez" de "poucos pacientes muitas vezes" —
    dois excedentes idênticos no número e diferentes na conversa. É a leitura de
    beneficiário que sobrevive à mudança de unidade: a lista de quem concentra,
    que o painel do dossiê traz, aqui seria sempre vazia (um beneficiário
    responder por mais de 10% das solicitações de um exame na ÁREA inteira não
    acontece), e lista vazia num painel lê como dado faltando.
    """
    if not pacientes or not pacientes.get("n_pacientes"):
        return None
    n = int(pacientes["n_pacientes"])
    return {
        "n_beneficiarios": n,
        "n_beneficiarios_fmt": fmt(n, 0),
        "n_carteira_fmt": None if not n_carteira else fmt(n_carteira, 0),
        "itens_por_beneficiario_fmt": (None if not pacientes.get("itens_por_paciente")
                                       else fmt(pacientes["itens_por_paciente"], 1)),
        "pct_repetem_fmt": (None if pacientes.get("pct_repetem") is None
                            else fmt_pct(pacientes["pct_repetem"])),
        "n_repetem_fmt": fmt(pacientes.get("n_repetem") or 0, 0),
        "intervalo_fmt": (None if not pacientes.get("intervalo_mediano_dias")
                          else fmt(pacientes["intervalo_mediano_dias"], 0)),
    }


def autorreferencia_da_area(linhas_autorref, ids: list[str] | None) -> dict:
    """A parcela do exame executada por quem o pediu, somada no recorte.

    Soma os NUMERADORES e os DENOMINADORES, nunca a média das taxas: cada
    cooperado tem uma cobertura diferente, e a média simples daria a cada um o
    mesmo peso independentemente de quantas solicitações ele tem.

    O portão de cobertura é o mesmo do painel do dossiê, aplicado ao agregado —
    e no agregado ele passa com folga, que é justamente por que a leitura vale
    mais aqui do que por par.
    """
    vazio = {"apresentavel": False, "motivo": "Sem solicitações no período",
             "taxa_fmt": None, "cobertura_fmt": None}
    if linhas_autorref is None or not len(linhas_autorref):
        return vazio
    df = linhas_autorref
    if ids is not None:
        df = df[df["ID_COOPERADO"].isin(list(ids))]
    if not len(df):
        return vazio
    itens = float(df["itens"].sum())
    com_conta = float(df["itens_com_conta"].sum())
    autos = float((df["taxa_autorref"].fillna(0.0) * df["itens_com_conta"]).sum())
    if not itens:
        return vazio
    cobertura = com_conta / itens
    ok = (com_conta >= config.MIN_ITENS_AUTORREF_PROC
          and cobertura >= config.MIN_COBERTURA_AUTORREF_PROC)
    return {
        "apresentavel": bool(ok),
        "taxa_fmt": fmt_pct(autos / com_conta) if ok and com_conta else None,
        "cobertura_fmt": fmt_pct(cobertura),
        "itens": int(round(itens)),
        "itens_fmt": fmt(itens, 0),
        "itens_com_conta": int(round(com_conta)),
        "itens_com_conta_fmt": fmt(com_conta, 0),
        "n_cooperados": int(df["ID_COOPERADO"].nunique()),
        "motivo": None if ok else "Não apurável",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Principais oportunidades: o degrau "o que eu faço agora" (2026-09-07)
# ─────────────────────────────────────────────────────────────────────────────

def principais_oportunidades(pares: pd.DataFrame, rs: pd.DataFrame,
                             conf: pd.DataFrame | None, ids: list[str] | None,
                             excedente_reais_area: float | None,
                             alvo: str, gatilho: str | None, n_fatias: int,
                             escopo: str = "da área",
                             n_visiveis: int = config.N_OPORTUNIDADES_VISIVEIS
                             ) -> dict | None:
    """Uma linha por PAR (cooperado × procedimento), do maior custo excedente ao
    menor, entre os casos qualificados.

    ── por que este bloco existe ────────────────────────────────────────────
    O app ordena cooperados DENTRO de um procedimento (o painel lateral) e
    procedimentos DENTRO de um cooperado (a tabela do dossiê). O cruzamento, os
    pares de toda a área numa lista só, não existia em superfície nenhuma, e é
    ele que responde a pergunta com que o auditor abre a tela: por onde começar.

    Nenhuma medida nova é calculada aqui. Os pares, o custo excedente de cada um
    e a régua de cada procedimento já viajam prontos no mesmo endpoint; este
    bloco junta e ordena.

    ── só CASOS QUALIFICADOS, e isso é metade do valor do bloco ─────────────
    Entra só quem chega ao último degrau da cascata. Uma lista de todos os que
    estão acima do critério poria em primeiro lugar o cooperado cujo fator de
    contexto explica o volume, que é o pior caso para abrir uma conversa
    (rigor-estatistico §4). Como a condição vale para TODAS as linhas, ela é
    dita uma vez no rodapé, e não repetida linha a linha.

    ── as DUAS LENTES, e o denominador ─────────────────────────────────────
    A ordem é pelo custo excedente (magnitude, onde agir) e a razão viaja na
    linha (intensidade). Ordenar só por razão traria procedimento raro; só por
    custo, volume clínico (rigor §3). Frequência, referência da área e consultas
    ficam ao lado: número de indivíduo não se publica sem a referência do grupo
    (LEXICO, princípio 6) nem sem o denominador (rigor §1).

    ── o que a ordem por R$ deixa de fora, dito em voz alta ─────────────────
    Par qualificado cujo procedimento não tem preço apurado nas contas não tem
    valor e não pode ser ordenado. Ele não some calado: `sem_preco` conta
    quantos são, e o rodapé declara.

    Parâmetros:
        ids: cooperados em cena. O bloco é ACHADO e segue o recorte (Lei 0).
        escopo: de que conjunto o denominador fala. O MESMO bloco serve a duas
            escalas, os pares de uma área e os de todas as áreas com régua, e a
            única coisa que muda é contra que total as fatias são lidas. Dizer
            "da área" numa tela da especialidade seria o percentual apontando
            para o conjunto errado.
        excedente_reais_area: excedente da área inteira, denominador da fatia
            que o cabeçalho declara. Sem ele a soma do topo não tem tamanho.
        alvo, gatilho: os níveis ativos, para o rodapé nomear a régua em vez de
            o leitor supor qual delas produziu a lista.
        n_fatias: trimestres completos da janela, para o rodapé dizer em quantos
            a variação se repetiu.
    """
    if pares is None or not len(pares):
        return None
    qualificados = pares[pares[cascata.DEGRAU_QUALIFICADO]]
    if ids is not None:
        qualificados = qualificados[qualificados["ID_COOPERADO"].isin(ids)]
    if not len(qualificados):
        return None

    reais = {}
    if rs is not None and len(rs):
        reais = {(r.ID_COOPERADO, r.CD_PROCEDIMENTO): float(r.excedente_reais)
                 for r in rs.itertuples()}

    linhas, sem_preco = [], 0
    for r in qualificados.itertuples():
        valor = reais.get((r.ID_COOPERADO, r.CD_PROCEDIMENTO))
        if valor is None:
            sem_preco += 1
            continue
        referencia = getattr(r, alvo, None)
        tem_razao = not pd.isna(r.razao_vs_alvo)
        fracao = (valor / excedente_reais_area) if excedente_reais_area else None
        linhas.append({
            "id": r.ID_COOPERADO,
            # A ÁREA de cada par: numa tela que junta áreas, a linha precisa
            # dizer contra qual régua ela foi medida. Na tela de Área a coluna
            # não aparece (seria a mesma palavra em todas as linhas).
            "area": apr.rotulo_exibicao(str(r.AREA_ATUACAO)),
            "codigo": str(r.CD_PROCEDIMENTO),
            "descricao": str(r.DS_PROCEDIMENTO).strip(),
            "razao": None if not tem_razao else round(float(r.razao_vs_alvo), 2),
            "razao_fmt": (config.SEM_MEDIDA if not tem_razao
                          else f"{fmt(r.razao_vs_alvo, 1)}×"),
            # A FREQUÊNCIA, A RÉGUA E O DENOMINADOR não ocupam colunas: a razão
            # já é a comparação com o grupo, e as três juntas eram a tabela do
            # dossiê repetida aqui. Viajam na leitura da célula da razão, a um
            # hover de distância — que é o que o guia exige do denominador
            # (DIRETRIZES §13: alcançável no momento da leitura), e não que ele
            # ocupe uma coluna própria.
            "leitura_razao": (
                f"{fmt_frequencia(r.taxa)} solicitações por consulta, "
                f"em {fmt(r.consultas_totais, 0)} consultas do período. "
                + ("Referência da área para este procedimento: "
                   f"{fmt_frequencia(referencia)}."
                   if referencia is not None and not pd.isna(referencia)
                   else "Sem referência publicada para este procedimento.")),
            "excedente_itens": round(float(r.excedente_itens), 2),
            "excedente_itens_fmt": fmt(r.excedente_itens, 0),
            "excedente_reais": round(valor, 2),
            "excedente_reais_fmt": fmt_reais(valor),
            # QUANTO ESTE CASO MOVE, que é a pergunta da tela: um par de R$ 47
            # mil não diz por si se vale uma conversa; 1% do excedente da área
            # diz. É a coluna que separa este bloco de mais uma lista ordenada.
            "fracao_area": None if fracao is None else round(fracao, 4),
            "fracao_area_fmt": (config.SEM_MEDIDA if fracao is None
                                else fmt_pct(fracao, 1)),
        })
    if not linhas:
        return None

    # SEM TETO DE CARGA (set/2026). Houve um, de 20 pares: o argumento era que
    # 228 linhas num cartão acima das abas viram uma terceira tabela fora do
    # lugar onde as tabelas moram. O argumento valia para a ALTURA, e altura se
    # resolve com rolagem dentro do cartão — não cortando o dado. Com o corte,
    # quem abria a lista inteira via 20 casos sob um cabeçalho que anunciava
    # 228, sem caminho para os outros 208.
    linhas.sort(key=lambda l: -l["excedente_reais"])
    n_total = len(linhas)
    corte = min(n_visiveis, len(linhas))

    # O CABEÇALHO declara sobre que denominador a soma se apoia. Sem ele, um
    # total de cinco linhas lê como o problema inteiro da área, e tratar cinco
    # casos passaria a parecer tratar a área.
    #
    # DOIS RESUMOS, prontos, porque a lista tem dois tamanhos: o padrão e o
    # expandido. O front alterna a frase, não a calcula — a soma e a fração são
    # números do método, e recalculá-los no navegador seria o segundo lugar em
    # que eles nascem (Lei 1). Antes só o primeiro viajava, e revelar o resto
    # deixava o cabeçalho falando de cinco casos com vinte na tela.
    def _resumo(ate: int) -> str:
        soma = sum(l["excedente_reais"] for l in linhas[:ate])
        txt = f"{ate} de {n_total} casos qualificados · {fmt_reais(soma)}"
        if excedente_reais_area:
            txt += (f", {fmt_pct(soma / excedente_reais_area)} do custo "
                    f"excedente {escopo}")
        return txt

    resumo = _resumo(corte)
    resumo_todos = _resumo(len(linhas))

    # A QUALIFICAÇÃO dita UMA VEZ, e não linha a linha: ela vale para todas, e
    # repeti-la em cada linha gastava três linhas de texto por caso sem separar
    # um caso do outro.
    regra = ["Casos qualificados: variação acima do critério de revisão"]
    if gatilho:
        regra[0] += f" ({gatilho.upper()} da área)"
    regra[0] += (f" em todos os {n_fatias} trimestres do período"
                 if n_fatias else " em todo o período")
    regra.append("sem fator de contexto verificado")
    regra.append("com intervalo de confiança calculável")
    notas = [", ".join(regra) + "."]
    if sem_preco:
        notas.append(f"{fmt(sem_preco, 0)} casos qualificados ficam fora desta "
                     "ordem por não ter preço apurado nas contas do período.")

    return {
        "titulo": "Principais oportunidades",
        "subtitulo": ("Os maiores excessos por cooperado e procedimento, "
                      "entre os casos qualificados"),
        "resumo": resumo,
        # a mesma frase para a lista inteira, para o cabeçalho acompanhar quem
        # revela o resto em vez de continuar falando dos cinco primeiros
        "resumo_todos": resumo_todos,
        "resumo_titulo": ("Custo excedente somado dos casos em cena, sobre o "
                          f"custo excedente {escopo} no mesmo recorte."),
        # o rótulo da coluna de fatia acompanha o escopo: a coluna diz de que
        # total ela é fração, e o front imprime o que o motor redige
        "rotulo_fracao": f"% do excedente {escopo}",
        # a coluna da área só entra quando há mais de uma em cena: numa tela de
        # área só ela repetiria a mesma palavra em todas as linhas
        "mostrar_area": len({l["area"] for l in linhas}) > 1,
        "linhas": linhas,
        # `n` é o total de casos qualificados da área; `linhas` traz os maiores
        # até o teto de carga. Os dois números são diferentes de propósito, e o
        # cabeçalho imprime o primeiro para o bloco nunca parecer exaustivo.
        "n": n_total,
        "n_visiveis": corte,
        "resto": max(0, len(linhas) - corte),
        "sem_preco": sem_preco,
        "notas": notas,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Panorama da especialidade: a porta de entrada (2026-09-07, etapa 1)
# ─────────────────────────────────────────────────────────────────────────────

def panorama_da_especialidade(especialidade: str, areas: list[dict],
                              totais: dict[str, dict],
                              area_pendente: str) -> dict:
    """O topo do Panorama: escopo da especialidade, onde o excesso está, e quem
    ainda não pode ser medido.

    ── por que esta página não é a soma de duas telas de Área ───────────────
    O Panorama é o único lugar que junta as áreas, e junta pessoas e valores,
    NUNCA réguas: cada excedente foi medido contra a referência da área do
    próprio cooperado, e é por isso que a unidade comum entre áreas é o excesso
    (solicitações e R$) e não a posição. Posição comparando médicos de áreas
    diferentes seria o pecado capital do método, e por isso ela não existe aqui.

    ── TODAS as áreas aparecem, e a ordem carrega a hierarquia ──────────────
    A especialidade tem sete áreas de atuação e apenas DUAS sustentam referência
    (118 dos 200 cooperados); as outras cinco somam nove pessoas. Todas viram
    cartão: a tela é o catálogo da especialidade, e uma área que não aparece é
    uma área que ninguém lembra de classificar.

    O que separa as duas famílias não é a presença, é o CONTEÚDO do cartão.
    Quem tem régua mostra excedente, fatia e casos qualificados. Quem não tem
    mostra a população e o motivo de não sinalizar, no lugar dos números que
    não existem — porque ali não há excedente medido, e imprimir zero seria
    afirmar ausência de variação onde o que falta é norma.

    A ordem é: com régua primeiro, pelo excedente; depois as demais, pelo
    tamanho. Sem ordem, cinco cartões de uma a quatro pessoas se intercalariam
    com os dois que carregam os R$ 5,3 mi.

    ── a CLASSIFICAÇÃO PENDENTE é achado, não rodapé ────────────────────────
    72 dos 200 cooperados não têm área de atuação atribuída. É mais de um terço
    da especialidade, e é o único número desta tela cuja ação não passa por
    comitê: é triagem clínica, trabalho de cadastro. Espremido entre os cartões
    de área ele vira nota de rodapé, e some justamente o que dá para resolver.

    Parâmetros:
        areas: o catálogo já resolvido (`_areas_resolvidas`), com n, estado e
            comparabilidade de cada área. Nada é reclassificado aqui.
        totais: por id de área, o que a cascata daquela área já somou:
            `excedente_itens`, `excedente_reais`, `n_qualificados`,
            `n_pares_qualificados` e `n_com_excedente`.
            Só as áreas com régua aparecem, porque só nelas há excedente medido.
        area_pendente: o nome interno da área de classificação pendente, para o
            bloco reconhecê-la sem repetir a regra que o config já declara.
    """
    com_regua, sem_regua, pendente = [], [], None
    for a in areas:
        if a["nome"] == area_pendente:
            pendente = a
        elif a["comparavel"]:
            com_regua.append(a)
        else:
            sem_regua.append(a)

    exc_itens = sum(totais.get(a["id"], {}).get("excedente_itens", 0.0)
                    for a in com_regua)
    exc_reais = sum(totais.get(a["id"], {}).get("excedente_reais", 0.0)
                    for a in com_regua)
    n_com_exc = sum(totais.get(a["id"], {}).get("n_com_excedente", 0)
                    for a in com_regua)
    n_coop = sum(a["n_total"] for a in areas)
    n_comparaveis = sum(a["n_avaliaveis"] for a in com_regua)
    n_pendente = pendente["n_total"] if pendente else 0
    n_sem_regua = sum(a["n_total"] for a in sem_regua)

    # ── a linha de contexto: o ESCOPO, que não se move com nada ──────────────
    # Mesma forma da linha da tela de Área: fatos separados por ponto médio,
    # cada um com a própria leitura no hover. É texto e não cartão porque
    # descreve o alcance da medição, e cartão promete grandeza comparável.
    contexto = [
        {"texto": f"{fmt(n_coop, 0)} cooperados",
         "titulo": "Cooperados da especialidade com atividade registrada no período."},
        {"texto": (f"{fmt(n_comparaveis, 0)} comparáveis em "
                   f"{fmt(len(com_regua), 0)} "
                   f"{'áreas' if len(com_regua) != 1 else 'área'} com referência"),
         "titulo": ("Volume suficiente para comparação, cada um dentro da "
                    "própria área de atuação.")},
    ]
    if n_pendente:
        contexto.append({
            "texto": f"{fmt(n_pendente, 0)} em classificação pendente",
            "titulo": ("Sem área de atuação atribuída. Seguem listados e não "
                       "sinalizam, porque não há grupo contra o qual comparar.")})
    if n_sem_regua:
        contexto.append({
            "texto": f"{fmt(n_sem_regua, 0)} em áreas sem referência",
            "titulo": ("Áreas pequenas demais para sustentar percentil. A "
                       "posição aparece como posto descritivo.")})
    contexto.append({
        "texto": (f"{fmt(exc_itens, 0)} solicitações excedentes de "
                  f"{fmt(n_com_exc, 0)} cooperados"),
        "titulo": ("Solicitações acima da referência da própria área, somadas "
                   "procedimento a procedimento.")})
    contexto.append({
        "texto": fmt_reais(exc_reais),
        "titulo": ("As mesmas solicitações excedentes valoradas a preços de "
                   "referência internos derivados das contas do período.")})

    # ── onde o excesso está ─────────────────────────────────────────────────
    # A barra é a fatia da ÁREA no excedente da especialidade, não a fatia da
    # maior: a pergunta é quanto do problema mora ali, e normalizar pela maior
    # faria a segunda área parecer maior do que é sempre que a primeira encolhe.
    # ── TODO CARTÃO DIZ AS MESMAS TRÊS COISAS ────────────────────────────────
    # Custo total, % excedente e valor excedente, na mesma ordem, em todas as
    # áreas. Cartão que muda de campos conforme a área obriga o leitor a
    # reaprender o desenho a cada um, e some com a comparação, que é a razão de
    # eles estarem lado a lado.
    #
    # Onde não há medida, a linha aparece com `SEM_MEDIDA` e o motivo ao lado.
    # Nunca zero e nunca célula vazia: zero afirmaria ausência de variação onde
    # o que falta é contra quem medir, e vazio faria o leitor procurar o número
    # que não existe (ajuste 4 do CLAUDE.md).
    #
    # O % EXCEDENTE é a única das três comparável entre áreas de tamanhos
    # diferentes: R$ 2,9 mi numa área e R$ 2,5 mi noutra não dizem qual pede
    # mais fora do padrão; 28% e 24% dizem.
    def _linhas_do_cartao(a: dict, t: dict) -> list[dict]:
        custo = t.get("custo_total")
        exc = t.get("excedente_reais") if a["comparavel"] else None
        pct = (exc / custo) if (custo and exc is not None) else None
        return [
            {"rotulo": "Custo total",
             "valor_fmt": config.SEM_MEDIDA if not custo else fmt_reais(custo),
             "motivo": None if custo else "sem procedimento com preço apurado",
             "titulo": ("Valor de tudo que os cooperados comparáveis desta área "
                        "solicitaram no período, a preços de referência "
                        "internos derivados das contas.")},
            # O % ANDA COM O VALOR, não em linha própria: é a mesma medida em
            # duas leituras (quanto é, e quanto pesa), e uma linha para cada
            # fazia o cartão parecer ter três medidas onde há duas.
            {"rotulo": "Custo excedente",
             "valor_fmt": config.SEM_MEDIDA if exc is None else fmt_reais(exc),
             "apoio": None if pct is None else fmt_pct(pct),
             "titulo_apoio": ("Parte do custo solicitado desta área que está "
                              "acima da própria referência."),
             "motivo": (None if exc is not None else
                        "sem referência da área para medir excesso"),
             "destaque": True,
             "titulo": ("Solicitações acima da referência da própria área, "
                        "valoradas aos mesmos preços internos.")},
        ]

    cartoes = []
    for a in sorted(areas,
                    key=lambda x: (not x["comparavel"],
                                   -(totais.get(x["id"], {}).get("excedente_reais") or 0.0),
                                   -x["n_total"])):
        if a["nome"] == area_pendente:
            continue
        t = totais.get(a["id"], {})
        cartoes.append({
            "id": a["id"], "nome": a["titulo"], "comparavel": a["comparavel"],
            "linhas": _linhas_do_cartao(a, t),
            # a POPULAÇÃO fecha o cartão, e é ela que sustenta as três de cima:
            # taxa sem denominador não diz se é prática ou ruído (rigor §1)
            "populacao": (f"{fmt(a['n_avaliaveis'], 0)} "
                          f"{'comparáveis' if a['n_avaliaveis'] != 1 else 'comparável'}"
                          f" de {fmt(a['n_total'], 0)}"),
            "qualificados": (f"{fmt(t.get('n_qualificados', 0), 0)} casos qualificados"
                             if a["comparavel"] else
                             ("nenhum cooperado forma a referência"
                              if not a["n_formam_referencia"] else
                              "cooperados insuficientes para sustentar percentil")),
            "titulo_qualificados": (
                "Cooperados que atravessam todos os degraus de qualificação "
                "nesta área: variação persistente em todos os trimestres, sem "
                "fator de contexto verificado, com intervalo de confiança "
                "calculável." if a["comparavel"] else
                "Sem cooperados suficientes para sustentar percentil e critério "
                "de revisão. A posição aparece como posto descritivo, e ninguém "
                "é sinalizado."),
            "acao": (f"Abrir {a['titulo']} com o mesmo período e os mesmos "
                     "critérios."),
        })

    # ── a classificação pendente, com faixa própria ─────────────────────────
    bloco_pendente = None
    if pendente and n_pendente:
        fracao = n_pendente / n_coop if n_coop else None
        bloco_pendente = {
            "id": pendente["id"],
            "titulo": "Classificação pendente",
            "valor_fmt": fmt(n_pendente, 0),
            "unidade": "cooperados sem área de atuação atribuída",
            "frase": (f"{fmt_pct(fracao)} da especialidade segue fora da "
                      "medição enquanto a área de atuação não é atribuída."
                      if fracao is not None else
                      "Seguem fora da medição enquanto a área de atuação não é "
                      "atribuída."),
            "acao": "Ver os cooperados em classificação pendente",
        }

    return {
        "titulo": especialidade,
        "pergunta": "Onde está o custo excedente, e por onde começar?",
        "contexto": contexto,
        "areas": {
            # O TÍTULO NÃO PROMETE "onde o excesso está" (set/2026). Sete
            # cartões lado a lado são o CATÁLOGO da especialidade: dizem o que
            # existe, quanto cada área carrega e quem não pode ser medido. Onde
            # o excesso se concentra é pergunta de Pareto, e ela tem seção
            # própria mais abaixo na página. Um título que promete concentração
            # sobre uma grade que lista faz o leitor procurar ali uma resposta
            # que o desenho não dá.
            "titulo": "Áreas de atuação",
            "subtitulo": ("Cada área é medida contra a própria referência; o "
                          "excesso é a única grandeza comparável entre elas"),
            "cartoes": cartoes,
            "n_com_referencia": len(com_regua),
            "n_sem_referencia": len(sem_regua),
        },
        "pendente": bloco_pendente,
        "totais": {
            "cooperados": n_coop,
            "comparaveis": n_comparaveis,
            "areas_com_referencia": len(com_regua),
            "excedente_itens": round(exc_itens, 2),
            "excedente_reais": round(exc_reais, 2),
            "n_com_excedente": n_com_exc,
        },
    }


def concentracao_da_especialidade(reais_coop: dict[str, float],
                                  custos_coop: dict[str, float],
                                  areas_por_coop: dict[str, str],
                                  reais_area: dict[str, float] | None = None,
                                  custos_area: dict[str, float] | None = None
                                  ) -> dict | None:
    """Onde o excesso se concentra, em DUAS agregações alternáveis: por área de
    atuação e por cooperado.

    O mesmo Pareto da tela de Área com o conjunto trocado. Junta pessoas e
    valores, nunca réguas: cada excedente já foi medido contra a referência da
    própria área do cooperado, e é isso que torna a soma legítima.

    ── as duas agregações respondem perguntas diferentes ───────────────────
    Por ÁREA diz onde a operação concentra o excesso, e é a leitura de quem
    decide onde alocar auditoria. Por COOPERADO diz quantas conversas resolvem
    quanto, e é a leitura de quem vai conduzi-las. O total é o mesmo nas duas;
    o que muda é o tamanho do passo.

    Trocar de agregação é LEITURA e não recorte: o conjunto medido é o mesmo, e
    por isso as duas viajam prontas no mesmo payload, no envelope que o Pareto
    já usa para as ordens.

    A ÁREA de cada um entra na leitura da linha do cooperado, porque numa lista
    que cruza áreas a barra sozinha não diz contra o que a pessoa foi medida.
    """
    linhas = [{"id": coop, "area": areas_por_coop.get(coop)}
              for coop in reais_coop]
    p = pareto_cooperados(reais_coop, linhas, None, None, custos_coop)
    if not p:
        return None
    # O TÍTULO é o do bloco, não o do Pareto genérico: os dois Paretos desta tela
    # somam o MESMO total, e "Concentração do custo excedente · R$ 5,3 mi" nos
    # dois cabeçalhos é a mesma frase dita duas vezes a vinte centímetros de
    # distância. O que os distingue é o eixo, e é isso que o título passa a dizer.
    for bloco in (p.get("dados") or {}).values():
        bloco["titulo"] = "Onde o excesso se concentra"
        for linha in bloco.get("linhas", []):
            area = areas_por_coop.get(linha["id"])
            if area:
                linha["detalhes"] = [f"Área de atuação: {area}"] + [
                    d for d in linha.get("detalhes", [])]

    # ── a agregação POR ÁREA, no mesmo envelope ─────────────────────────────
    # O Pareto é genérico sobre um dicionário de id -> valor; aqui os "ids" são
    # as áreas. Reusar o mesmo bloco é o que garante que as duas agregações
    # somem o mesmo total e desenhem a barra com a mesma gramática.
    por_area = None
    if reais_area:
        linhas_a = [{"id": nome} for nome in reais_area]
        por_area = pareto_cooperados(reais_area, linhas_a, None, None,
                                     custos_area or {})
    if not por_area:
        return p

    def _bloco(env: dict, titulo: str, unidade: str | None = None) -> dict:
        b = (env.get("dados") or {}).get("excedente") or env
        # SEM SUBTÍTULO: o título já diz a pergunta e o segmentado ao lado diz a
        # agregação em cena. Uma terceira linha repetindo "por cooperado" logo
        # abaixo de um controle que mostra "Cooperado" marcado é o mesmo fato
        # dito duas vezes a dois centímetros de distância.
        b["titulo"], b["subtitulo"] = titulo, None
        # O PARETO é genérico sobre id -> valor, e o rótulo dele é "Cooperado".
        # Na agregação por área as linhas são áreas, e a coluna e a leitura de
        # concentração precisam dizer isso: "2 de 2 cooperados" sobre uma lista
        # de duas áreas é o texto contradizendo a tabela.
        if unidade:
            b["colunas"] = {**b["colunas"], "rotulo": unidade}
            for chave in ("leitura_concentracao", "leitura_titulo"):
                if b.get(chave):
                    b[chave] = (b[chave].replace("cooperados", "áreas")
                                .replace("cooperado ", "área "))
        return b

    return {
        # POR ÁREA primeiro: a pergunta da tela é onde olhar, e ela se responde
        # no passo maior antes do menor.
        "ordem_default": "area",
        "rotulo_controle": "Agrupar por",
        "ordens": [{"chave": "area", "rotulo": "Área de atuação"},
                   {"chave": "cooperado", "rotulo": "Cooperado"}],
        "dados": {
            "area": _bloco(por_area, "Onde o excesso se concentra",
                           unidade="Área de atuação"),
            "cooperado": _bloco(p, "Onde o excesso se concentra"),
        },
    }


def procedimentos_transversais(rs: pd.DataFrame,
                               custo_pares: pd.DataFrame | None) -> dict | None:
    """Os procedimentos que concentram o excesso da especialidade, com em
    quantas ÁREAS cada um aparece.

    É a leitura que só existe aqui: a tela de Área mostra os procedimentos de
    uma área, e nenhuma delas mostra que o mesmo procedimento puxa excedente nas
    duas. A distinção muda a ação — excedente alto em mais de uma área é
    conversa de protocolo, não conversa individual.

    O Pareto é o MESMO da aba Procedimentos; o que este bloco acrescenta é a
    contagem de áreas na leitura de cada linha.
    """
    if rs is None or not len(rs):
        return None
    p = pareto_procedimentos(rs, None, None, custo_pares)
    if not p:
        return None
    n_areas = rs.groupby("CD_PROCEDIMENTO")["AREA_ATUACAO"].nunique().to_dict()
    for bloco in (p.get("dados") or {}).values():
        bloco["titulo"] = "Procedimentos transversais"
        # sem subtítulo, pelo mesmo motivo do bloco ao lado: as colunas já dizem
        # o que cada número é, e a leitura de concentração diz quantos
        # concentram quanto
        bloco["subtitulo"] = None
        for linha in bloco.get("linhas", []):
            n = int(n_areas.get(linha["id"], 0))
            if not n:
                continue
            linha["detalhes"] = [
                f"Aparece em {fmt(n, 0)} {'áreas' if n != 1 else 'área'} "
                "de atuação"] + [d for d in linha.get("detalhes", [])]
    return p


# ─────────────────────────────────────────────────────────────────────────────
# Índice de procedimentos: a porta da quarta dimensão (2026-09-08)
# ─────────────────────────────────────────────────────────────────────────────

def indice_de_procedimentos(posproc_rs: pd.DataFrame,
                            areas_com_regua: set[str]) -> dict:
    """Um procedimento por linha, somado entre as áreas com referência.

    ── por que esta lista TEM números, e a de cooperados não ────────────────
    O índice de cooperados é uma porta sem número nenhum, e por regra: ele
    atravessa as áreas, e coluna ordenável ali convida a ler a lista como
    ranking — comparar médicos de áreas diferentes é a comparação entre peer
    groups que o método proíbe.

    Com PROCEDIMENTO a soma é legítima, e a diferença é o que torna esta página
    possível: o excedente de cada par já foi medido contra a referência da
    ÁREA daquele cooperado. Somar entre áreas junta dinheiro já comparado, nunca
    réguas. É a mesma soma que o Pareto de procedimentos transversais do
    Panorama publica.

    ── SÓ ÁREAS COM RÉGUA contribuem excedente ─────────────────────────────
    Área sem critério não sinaliza ninguém, e um procedimento que só existe lá
    aparece com volume e custo, sem excedente. Não é zero de excedente: é
    ausência de medida, e a linha declara com `SEM_MEDIDA` em vez de imprimir
    zero, que afirmaria ausência de variação.

    ── as áreas em que ele aparece ─────────────────────────────────────────
    `n_areas` conta em quantas áreas COM RÉGUA o procedimento tem excedente, e é
    a coluna que só esta tela dá: excedente alto em mais de uma área é conversa
    de protocolo, não conversa individual. Dos 259 procedimentos com excedente
    em Ginecologia e GO, 213 estão nas duas e carregam 94% do dinheiro.
    """
    vazio = {"linhas": [], "total": 0, "n_com_excedente": 0, "n_multiarea": 0,
             "excedente_total_fmt": config.SEM_MEDIDA,
             "resumo": "Nenhum procedimento solicitado no período."}
    if posproc_rs is None or not len(posproc_rs):
        return vazio

    base = posproc_rs[posproc_rs["avaliavel"]].copy()
    com_preco = base["preco_mediano"].notna()
    base["_solicitacoes"] = base["taxa"] * base["consultas_totais"]
    base["_custo"] = base["_solicitacoes"] * base["preco_mediano"].fillna(0.0)
    # o EXCEDENTE só conta de par sinalizado e com preço: é o mesmo filtro que
    # produz todo R$ excedente do app (`filtrar_sinalizados`, Lei 1)
    sinal = base["sinalizado"] & com_preco & base["AREA_ATUACAO"].isin(areas_com_regua)
    base["_exc"] = base["excedente_reais"].where(sinal, 0.0)
    base["_exc_itens"] = base["excedente_itens"].where(sinal, 0.0)

    linhas = []
    for (cd, ds), g in base.groupby(["CD_PROCEDIMENTO", "DS_PROCEDIMENTO"],
                                    sort=False):
        acima = g[g["_exc"] > 0]
        exc = float(g["_exc"].sum())
        custo = float(g["_custo"].sum())
        tem_regua = bool(g["AREA_ATUACAO"].isin(areas_com_regua).any())
        linhas.append({
            "codigo": str(cd),
            "descricao": str(ds).strip(),
            "solicitantes": int(g["ID_COOPERADO"].nunique()),
            "solicitacoes": round(float(g["_solicitacoes"].sum()), 2),
            "solicitacoes_fmt": fmt(g["_solicitacoes"].sum(), 0),
            # ÁREAS COM EXCEDENTE, não áreas em que o procedimento aparece:
            # a leitura da coluna é "isto é padrão de mais de um grupo", e
            # presença sozinha não diz isso — quase tudo aparece em todas.
            "n_areas": int(acima["AREA_ATUACAO"].nunique()),
            "areas_fmt": (fmt(acima["AREA_ATUACAO"].nunique(), 0) if tem_regua
                          else config.SEM_MEDIDA),
            "custo": round(custo, 2),
            "custo_fmt": fmt_reais(custo) if custo else config.SEM_MEDIDA,
            "n_acima": int(acima["ID_COOPERADO"].nunique()),
            "n_acima_fmt": (fmt(acima["ID_COOPERADO"].nunique(), 0) if tem_regua
                            else config.SEM_MEDIDA),
            "excedente_reais": round(exc, 2),
            "excedente_fmt": fmt_reais(exc) if tem_regua else config.SEM_MEDIDA,
            "excedente_itens_fmt": (fmt(g["_exc_itens"].sum(), 0) if tem_regua
                                    else config.SEM_MEDIDA),
            # a fração é o que torna a linha comparável entre procedimentos de
            # portes diferentes: R$ 460 mil sobre um custo de R$ 894 mil é outra
            # conversa que os mesmos R$ 460 mil sobre R$ 12 mi
            "fracao": (round(exc / custo, 4) if custo and tem_regua else None),
            "fracao_fmt": (fmt_pct(exc / custo) if custo and tem_regua
                           else config.SEM_MEDIDA),
        })
    linhas.sort(key=lambda l: -l["excedente_reais"])

    # O RESUMO é montado aqui, e não na tela: contar quantas linhas cruzam um
    # limiar é cálculo, e cálculo não vive no JavaScript (CLAUDE.md).
    com_exc = [l for l in linhas if l["excedente_reais"] > 0]
    multi = [l for l in com_exc if l["n_areas"] >= 2]
    total_exc = float(sum(l["excedente_reais"] for l in linhas))
    resumo = (f"{fmt(len(linhas), 0)} procedimentos solicitados no período. "
              f"{fmt(len(com_exc), 0)} têm custo acima da referência, "
              f"{fmt(len(multi), 0)} deles em mais de uma área de atuação.")
    return {
        "linhas": linhas,
        "total": len(linhas),
        "n_com_excedente": len(com_exc),
        "n_multiarea": len(multi),
        "excedente_total_fmt": fmt_reais(total_exc) if total_exc else config.SEM_MEDIDA,
        "resumo": resumo,
    }


def retrato_do_procedimento(posproc_rs: pd.DataFrame, norma_proc: pd.DataFrame,
                            codigo: str, areas_com_regua: set[str],
                            criterio: str, referencia: str,
                            n_minimo: int) -> dict:
    """UM procedimento, visto da especialidade inteira.

    A tela que faltava. Até aqui o procedimento só existia DENTRO de uma área:
    a gaveta da tela de Área é sempre "este procedimento na Ginecologia", e
    quem quisesse o procedimento inteiro somava as áreas de cabeça.

    ── três blocos, três perguntas ─────────────────────────────────────────
    LEITURA        quanto se pede, quanto custa, quanto está acima. O mesmo
                   desenho da Leitura da área, com a unidade trocada.
    POR ÁREA       as réguas lado a lado. A seção que só esta tela dá.
    QUEM PEDE      os cooperados acima do critério, cada um medido contra a
                   régua da PRÓPRIA área, com a área declarada na linha.

    ── as réguas lado a lado NÃO são um ranking entre áreas ─────────────────
    Pôr a mediana da Ginecologia ao lado da mediana de GO parece violar o peer
    group, e é o oposto: o que a tabela publica é que a RÉGUA é outra, e que um
    número que sinaliza num grupo pode ser rotina no outro. Nenhuma linha desta
    tabela mede um cooperado contra a referência alheia, e é justamente por isso
    que ela precisa existir — sem ela, quem lê o excedente somado supõe uma
    régua única onde há várias. A nota da seção diz isso na tela.

    ── o dinheiro SOMA, e por quê ──────────────────────────────────────────
    Cada excedente já foi medido contra a referência da área do próprio
    cooperado. Somar entre áreas junta dinheiro já comparado, nunca réguas. É a
    mesma soma que o Pareto de procedimentos transversais do Panorama publica.
    """
    vazio = {"existe": False, "codigo": codigo}
    if posproc_rs is None or not len(posproc_rs):
        return vazio

    todo = posproc_rs[posproc_rs["CD_PROCEDIMENTO"] == codigo]
    base = todo[todo["avaliavel"].astype(bool)].copy()
    if base.empty:
        return vazio

    descricao = str(base["DS_PROCEDIMENTO"].iloc[0]).strip()
    preco = base["preco_mediano"].dropna()
    preco_val = float(preco.iloc[0]) if len(preco) else None
    n_exec = base["n_execucoes"].dropna()
    n_exec_val = int(n_exec.iloc[0]) if len(n_exec) else None

    base["_solicitacoes"] = base["taxa"] * base["consultas_totais"]
    base["_custo"] = base["_solicitacoes"] * base["preco_mediano"].fillna(0.0)
    # o mesmo filtro que produz todo R$ excedente do app (Lei 1)
    sinal = (base["sinalizado"].astype(bool) & base["preco_mediano"].notna()
             & base["AREA_ATUACAO"].isin(areas_com_regua))
    base["_exc"] = base["excedente_reais"].where(sinal, 0.0)
    base["_exc_itens"] = base["excedente_itens"].where(sinal, 0.0)

    solicitacoes = float(base["_solicitacoes"].sum())
    custo = float(base["_custo"].sum())
    exc = float(base["_exc"].sum())
    exc_itens = float(base["_exc_itens"].sum())
    acima = base[base["_exc"] > 0]
    tem_regua = bool(base["AREA_ATUACAO"].isin(areas_com_regua).any())
    com_preco = preco_val is not None

    # ── LEITURA ──────────────────────────────────────────────────────────────
    grupos = [
        {"rotulo": "Volume no período", "linhas": [
            {"rotulo": "solicitações", "valor_fmt": fmt(solicitacoes, 0),
             "apoio": None,
             "titulo_longo": ("Quantidade solicitada deste procedimento no "
                              "período, somando as áreas de atuação.")},
            {"rotulo": "solicitantes", "valor_fmt": fmt(base["ID_COOPERADO"].nunique(), 0),
             "apoio": None,
             "titulo_longo": ("Cooperados que pediram este procedimento e têm "
                              "volume de consultas para entrar na comparação.")},
        ]},
        {"rotulo": "Preço de referência", "linhas": [
            {"rotulo": "valor unitário",
             "valor_fmt": (fmt_reais_unitario(preco_val) if com_preco
                           else config.SEM_MEDIDA),
             "apoio": (f"mediana de {fmt(n_exec_val, 0)} execuções"
                       if com_preco and n_exec_val else None),
             "titulo_longo": ("Mediana do valor unitário pago nas contas do "
                              "período. Vem do lado executante, e por isso não "
                              "existe para procedimento que foi pedido aqui e "
                              "pago fora deste recorte.")},
            {"rotulo": "custo total",
             "valor_fmt": fmt_reais(custo) if custo else config.SEM_MEDIDA,
             "apoio": None,
             "titulo_longo": ("Valor de tudo que foi solicitado deste "
                              "procedimento no período.")},
        ]},
        {"rotulo": "Alcance do excesso", "linhas": [
            {"rotulo": "áreas com excedente",
             "valor_fmt": (fmt(acima["AREA_ATUACAO"].nunique(), 0) if tem_regua
                           else config.SEM_MEDIDA),
             "apoio": None,
             "titulo_longo": ("Em quantas áreas de atuação este procedimento "
                              "tem custo acima da referência. Excedente em mais "
                              "de uma área é conversa de protocolo, e não "
                              "conversa individual.")},
            {"rotulo": "acima do critério",
             "valor_fmt": (fmt(acima["ID_COOPERADO"].nunique(), 0) if tem_regua
                           else config.SEM_MEDIDA),
             "apoio": None,
             "titulo_longo": ("Cooperados que passaram o critério de revisão da "
                              "própria área neste procedimento.")},
        ]},
    ]

    frase = (f"{fmt(base['ID_COOPERADO'].nunique(), 0)} cooperados pediram este "
             f"procedimento {fmt(solicitacoes, 0)} vezes no período.")
    notas = [("A referência é a de cada área de atuação, e nenhuma linha desta "
              "tela mede um cooperado contra a régua de outro grupo.")]
    if not com_preco:
        notas.append("Sem preço apurado nas contas do período, o custo e a "
                     "variação excedente não são calculáveis.")

    leitura = {
        "titulo": "Leitura do procedimento",
        "frase": frase,
        "grupos": grupos,
        "destaque": {
            "valor_fmt": fmt_reais(exc) if tem_regua and exc else config.SEM_MEDIDA,
            "apoio": ((f"de variação excedente, {fmt_pct(exc / custo)} do custo "
                       f"deste procedimento") if tem_regua and exc and custo
                      else "de variação excedente"),
        },
        "notas": notas,
    }

    # ── POR ÁREA: as réguas lado a lado ─────────────────────────────────────
    npc = (norma_proc[norma_proc["CD_PROCEDIMENTO"] == codigo]
           if norma_proc is not None and len(norma_proc) else None)
    por_area = []
    for area, g in base.groupby("AREA_ATUACAO", sort=False):
        n_linha = None
        if npc is not None and len(npc):
            achou = npc[npc["AREA_ATUACAO"] == area]
            n_linha = achou.iloc[0] if len(achou) else None
        regua = area in areas_com_regua and n_linha is not None
        apresentavel = bool(regua and n_linha.get("apresentavel"))
        g_acima = g[g["_exc"] > 0]
        c_area = float(g["_custo"].sum())
        e_area = float(g["_exc"].sum())
        por_area.append({
            "area": apr.rotulo_exibicao(str(area)),
            "solicitantes": int(g["ID_COOPERADO"].nunique()),
            "solicitacoes_fmt": fmt(g["_solicitacoes"].sum(), 0),
            "prevalencia_fmt": (fmt_pct(n_linha["prevalencia"]) if apresentavel
                                else config.SEM_MEDIDA),
            "referencia_fmt": (fmt_frequencia(n_linha[referencia])
                               if apresentavel and referencia in n_linha
                               else config.SEM_MEDIDA),
            "criterio_fmt": (fmt_frequencia(n_linha[criterio])
                             if apresentavel and criterio in n_linha
                             else config.SEM_MEDIDA),
            "n_acima_fmt": (fmt(g_acima["ID_COOPERADO"].nunique(), 0) if apresentavel
                            else config.SEM_MEDIDA),
            "custo_fmt": fmt_reais(c_area) if c_area else config.SEM_MEDIDA,
            "excedente_reais": round(e_area, 2),
            "excedente_fmt": fmt_reais(e_area) if apresentavel else config.SEM_MEDIDA,
            "motivo": (None if apresentavel else
                       ("área sem referência nesta janela" if not regua else
                        f"menos de {fmt(n_minimo, 0)} solicitantes para "
                        "referência conclusiva")),
        })
    por_area.sort(key=lambda l: -l["excedente_reais"])

    areas_bloco = {
        "titulo": "Onde ele é pedido, por área de atuação",
        # a nota é o que impede a leitura errada da seção, e por isso é dela
        "nota": ("Cada área tem a própria referência, e as réguas não se "
                 "comparam entre si: a mesma frequência pode ser rotina em um "
                 "grupo e sinal em outro."),
        "linhas": por_area,
    }

    # ── QUEM PEDE: os pares acima do critério, cada um contra a própria régua ─
    linhas_coop = []
    for _, l in acima.sort_values("_exc", ascending=False).iterrows():
        razao = l.get("razao_vs_alvo")
        linhas_coop.append({
            "id": str(l["ID_COOPERADO"]),
            "area": apr.rotulo_exibicao(str(l["AREA_ATUACAO"])),
            "taxa_fmt": fmt_frequencia(l["taxa"]),
            "referencia_fmt": fmt_frequencia(l.get(referencia)),
            "razao_fmt": (f"{fmt(float(razao), 1)}×" if pd.notna(razao)
                          else config.SEM_MEDIDA),
            "consultas_fmt": fmt(l["consultas_totais"], 0),
            "excedente_itens_fmt": fmt(l["_exc_itens"], 0),
            "excedente_reais": round(float(l["_exc"]), 2),
            "excedente_fmt": fmt_reais(float(l["_exc"])),
        })

    quem_bloco = {
        "titulo": "Quem pede acima da referência",
        "nota": ("Cada cooperado é medido contra a referência da própria área "
                 "de atuação, e a coluna da área declara qual foi."),
        "linhas": linhas_coop,
        "vazio": ("Nenhum cooperado passou o critério de revisão neste "
                  "procedimento."),
    }

    return {
        "existe": True,
        "codigo": codigo,
        "descricao": descricao,
        "leitura": leitura,
        "areas": areas_bloco,
        "solicitantes": quem_bloco,
    }
