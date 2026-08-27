"""cascata, a qualificação em degraus: de "todos os medidos" à fila de trabalho.

Cada degrau é um FILTRO CUMULATIVO sobre os pares (cooperado, procedimento).
A cascata existe por dois motivos:

  1. tria, a lente do agregado sozinha não separa (quase todo mundo tem algum
     procedimento acima do critério, por construção: são centenas de percentis
     testados por área; ver rigor-estatistico, nota de comparações múltiplas);
  2. ENSINA, os degraus, expostos como chips do mais estrito ao mais amplo,
     mostram ao usuário por que a fila é curta e o que cada filtro remove.

Natureza dos degraus (não confundir):
  - VALIDADE, sem eles o número não é defensável: os três portões, a
                 consistência entre janelas, o piso de confiança.
  - TRIAGEM, não afetam a defensabilidade, só a ordem de trabalho:
                 materialidade (config.FRACAO_PARETO_MATERIAL).
  - ARTEFATO, o caso sai porque a CLASSIFICAÇÃO está sob revisão, não porque
                 a prática foi explicada: classificação em revisão.
  - CONTEXTO, há explicação plausível para o excedente (urgência, regime):
                 fator de contexto verificado.

Nenhum degrau deleta alguém da análise: todos permanecem na tabela, e o chip
apenas escolhe o recorte visível.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config

# (chave, rótulo de UI, natureza) — do MAIS AMPLO ao MAIS ESTRITO.
# Os rótulos seguem o LEXICO_PRODUTO.md; a UI não inventa a própria frase.
DEGRAUS = (
    # RÓTULOS: cada um diz O QUE O GRUPO É, em português comum. As definições
    # não repetem o rótulo — dizem POR QUE o filtro existe, que é o que o leitor
    # precisa no hover. Reescritos em 2026-08-19: saíram par, portão,
    # apresentável, confundidor e Pareto, que só significam algo para quem
    # construiu o método.
    ("medidos", "Todos os medidos", "escopo",
     "Cooperados da área com atividade registrada no período."),
    ("acima_do_criterio", "Com algum exame acima do critério", "validade",
     "Solicita acima do P90 dos pares em ao menos um exame."),
    ("persistente", "Repetem em todos os trimestres", "validade",
     "O excesso se repete em todos os trimestres do período, e não em um "
     "pico isolado."),
    ("material", f"Entre os que somam {config.FRACAO_PARETO_MATERIAL:.0%} "
     "do excedente", "triagem",
     f"Está entre os cooperados que concentram "
     f"{config.FRACAO_PARETO_MATERIAL:.0%} do excedente da área; o excedente "
     "dos demais é cauda pequena diante do total."),
    # NÃO é degrau de método, e por isso não aparece como opção no seletor de
    # recorte: é pendência de CADASTRO. Continua na cadeia porque levar a
    # comitê um caso cuja área está em revisão é o pior erro possível do
    # produto — a defesa pronta é "eu nem sou dessa área". A tela o declara
    # como exclusão, com a contagem, em vez de escondê-lo numa queda.
    ("classificacao_firme", "Com classificação de área resolvida", "artefato",
     "A área de atuação registrada não está em revisão. Enquanto estiver, a "
     "comparação com os pares desta área não se sustenta."),
    ("sem_fator_de_contexto", "Sem explicação de contexto", "contexto",
     "Não há urgência nem atendimento de pronto-socorro que explique o volume "
     "solicitado."),
    ("confianca_calculavel", "Com confiança estatística", "validade",
     f"Há pacientes suficientes (≥ {config.MIN_PACIENTES_BOOTSTRAP}) para "
     "calcular o intervalo de confiança do excesso."),
)

# O ÚLTIMO degrau: quem chegou aqui passou toda a cascata, e é o que a tela
# chama de "Qualificados". Sai daqui, e não escrito à mão em quem consome, para
# que acrescentar um degrau ao fim não deixe leitores apontando para o penúltimo.
DEGRAU_QUALIFICADO = DEGRAUS[-1][0]


def _pareto_material(pares: pd.DataFrame, fracao: float) -> pd.Series:
    """Máscara do topo do Pareto que concentra `fracao` do excedente da área.

    O par que CRUZA o limiar entra (a fração é piso, não teto): cortar no meio
    do caso que atravessa a linha esconderia justamente o maior deles.
    """
    if pares.empty:
        return pd.Series(dtype=bool)
    ordenado = pares.sort_values("excedente_itens", ascending=False)
    total = float(ordenado["excedente_itens"].sum())
    if total <= 0:
        return pd.Series(False, index=pares.index)
    acumulado = ordenado["excedente_itens"].cumsum() / total
    # inclui o primeiro par que alcança/ultrapassa a fração
    dentro = acumulado.shift(fill_value=0.0) < fracao
    return dentro.reindex(pares.index, fill_value=False)


def qualificar(sinal: pd.DataFrame, persistencia: pd.DataFrame | None,
               n_fatias: int, confundidores: set[str] | None,
               confiabilidade: pd.DataFrame | None,
               fracao_material: float = config.FRACAO_PARETO_MATERIAL) -> pd.DataFrame:
    """Marca cada par (cooperado, procedimento) com o degrau CUMULATIVO alcançado.

    Parâmetros:
        sinal: pares que já passam os três portões (pipeline.filtrar_sinalizados).
        persistencia: 'por_procedimento' da persistencia_temporal, restrita à
            área; None quando a janela não comporta trimestres suficientes.
        n_fatias: nº de trimestres completos da janela (denominador do 4/4).
        confundidores: IDs com fator de contexto verificado; None = não avaliado.
        confiabilidade: saída do controlador_confiabilidade (coluna 'calculavel');
            None = não avaliado.
        fracao_material: fração do Pareto que define material.

    Retorna: `sinal` + uma coluna booleana por degrau, cada uma já CUMULATIVA
    (quem é 'material' também é 'persistente' e 'acima_do_criterio').
    """
    df = sinal.copy()
    df["medidos"] = True
    df["acima_do_criterio"] = True          # `sinal` já é o resultado dos 3 portões

    # persistência máxima: sinalizado em TODAS as janelas avaliáveis, e avaliável
    # em todas as fatias da janela (o 1/1 nunca desfila como 4/4)
    if persistencia is None or persistencia.empty:
        persistentes = set()
    else:
        p = persistencia[persistencia["reportavel"]
                         & (persistencia["persistencia"] == 1.0)
                         & (persistencia["n_janelas_avaliaveis"] == n_fatias)]
        persistentes = set(zip(p["ID_COOPERADO"], p["CD_PROCEDIMENTO"]))
    chave = list(zip(df["ID_COOPERADO"], df["CD_PROCEDIMENTO"]))
    df["persistente"] = df["acima_do_criterio"] & np.array(
        [k in persistentes for k in chave], dtype=bool)

    # material: Pareto calculado ENTRE OS PERSISTENTES (o degrau anterior),
    # não sobre todos os sinalizados — cada degrau tria o que sobrou do anterior
    df["material"] = False
    persist = df[df["persistente"]]
    if len(persist):
        df.loc[persist.index, "material"] = _pareto_material(persist, fracao_material)

    em_revisao = set(config.COOPERADOS_CLASSIFICACAO_EM_REVISAO)
    df["classificacao_firme"] = df["material"] & ~df["ID_COOPERADO"].isin(em_revisao)

    df["sem_fator_de_contexto"] = df["classificacao_firme"]
    if confundidores:
        df["sem_fator_de_contexto"] &= ~df["ID_COOPERADO"].isin(confundidores)

    df["confianca_calculavel"] = df["sem_fator_de_contexto"]
    if confiabilidade is not None and len(confiabilidade):
        calculaveis = set(zip(
            confiabilidade.loc[confiabilidade["calculavel"], "ID_COOPERADO"],
            confiabilidade.loc[confiabilidade["calculavel"], "CD_PROCEDIMENTO"]))
        df["confianca_calculavel"] &= np.array(
            [k in calculaveis for k in chave], dtype=bool)
    return df


def funil(qualificados: pd.DataFrame, n_medidos: int) -> list[dict]:
    """Um registro por degrau: n de cooperados, n de pares e excedente somado.

    `n_medidos` é o total de cooperados da área (o degrau 0 conta gente que nem
    aparece em `sinal`, por não ter nenhum par sinalizado).
    """
    linhas = []
    for chave, rotulo, natureza, definicao in DEGRAUS:
        if chave == "medidos":
            n_coop, n_pares, excedente = n_medidos, len(qualificados), \
                float(qualificados["excedente_itens"].sum())
        else:
            sub = qualificados[qualificados[chave]]
            n_coop = int(sub["ID_COOPERADO"].nunique())
            n_pares = len(sub)
            excedente = float(sub["excedente_itens"].sum())
        linhas.append({
            "chave": chave, "rotulo": rotulo, "natureza": natureza,
            "definicao": definicao,
            "n_cooperados": n_coop, "n_pares": n_pares,
            "excedente_itens": round(excedente, 2),
        })
    return linhas


def escolher_default(funil_linhas: list[dict], minimo_casos: int = 5,
                     teto_fila: int = 30) -> dict:
    """O default é o degrau MAIS ESTRITO que ainda retém `minimo_casos` cooperados.

    Se nenhum degrau desce abaixo de `teto_fila`, a triagem não separou: isso é
    ACHADO, não falha, a variação da área é generalizada (padrão coletivo, não
    outlier). Nesse caso o default é o degrau mais estrito disponível e a
    resposta carrega o achado, para que a leitura mude junto.
    """
    candidatos = [linha for linha in funil_linhas
                  if linha["chave"] != "medidos"
                  and linha["n_cooperados"] >= minimo_casos]
    mais_estrito = candidatos[-1] if candidatos else funil_linhas[1]
    triou = any(linha["n_cooperados"] < teto_fila for linha in funil_linhas[1:])
    return {
        "chave": mais_estrito["chave"],
        "n_cooperados": mais_estrito["n_cooperados"],
        "triou": triou,
        "achado": None if triou else {
            "codigo": "variacao_generalizada",
            "titulo": "Variação generalizada nesta área",
            "texto": ("Nenhum degrau da cascata reduz a lista à ordem de grandeza "
                      "de uma fila de trabalho: o padrão desta área é coletivo, "
                      "não de outlier. A conversa não é sobre alguns cooperados, "
                      "é sobre a prática da área."),
        },
    }
