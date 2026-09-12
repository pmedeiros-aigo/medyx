"""
pipeline, os 5 motores analíticos do Medyx, migrados fielmente do notebook
unimed_natal/calculos_iniciais.ipynb (as docstrings são a documentação de método).

Leis (CLAUDE.md / METODOLOGIA_ANALITICA.md):
  1. Pipeline único, todo cálculo passa por aqui; proibido recalcular em UI.
  2. Zero número cravado, defaults vêm do config.py; a UI passa a escolha e o
     motor recebe POR ARGUMENTO (nunca lê o config no meio do cálculo).
  3. Norma e indivíduo saem sempre da MESMA janela.

Motores: pipeline (solicitação), pipeline_execucao (execução/R$/confundidores),
persistencia_temporal, concentracao_por_beneficiario, controlador_confiabilidade.
Classificação v1.0 (não homologada): a norma é formada só por elegivel_norma=True;
todos são MEDIDOS contra ela. Exclusão por par (Mov 5): montar_exclusao_por_par.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config


# ── Contexto de PS (doc §5.6, notebook §12): regra por CONTEXTO ──
# A norma é treinada e aplicada sobre consultas NÃO-PS de todo mundo; a consulta-PS
# sai INTEIRA (EPISODIO_PS é marca de consulta, propagada aos itens no preparar_fato,
# então filtrar linhas remove numerador e denominador juntos). O filtro que muda
# todos os números se anuncia em todos os números: toda saída carrega o carimbo 'base'.
BASE_ELETIVA = "consultas eletivas (episódios de PS excluídos)"
BASE_COMPLETA = "todas as consultas (episódios de PS INCLUÍDOS, fora da regra padrão)"


def filtrar_ps(f, incluir_ps):
    """Aplica a regra de contexto de PS: incluir_ps=False remove a consulta-PS inteira."""
    return f if incluir_ps else f[~f["EPISODIO_PS"]]


def carimbo_base(incluir_ps):
    """Carimbo de proveniência da regra de PS que toda saída dos motores carrega."""
    return BASE_COMPLETA if incluir_ps else BASE_ELETIVA


def filtrar_sinalizados(df, exigir_preco=False):
    """Os três portões da metodologia num filtro nomeado e ÚNICO: avaliavel
    (cooperado acima do piso) & apresentavel (norma com n mínimo) & sinalizado
    (acima do gatilho). exigir_preco=True adiciona preco_mediano.notna(), para
    agregações em R$. É o único ponto do código que define "quem conta" ,
    qualquer tela ou soma importa daqui (Lei 1)."""
    m = df["avaliavel"] & df["apresentavel"] & df["sinalizado"]
    if exigir_preco:
        m &= df["preco_mediano"].notna()
    return df[m]


def pacientes_distintos(fato, janela_ini, janela_fim,
                        incluir_ps=config.INCLUIR_PS_DEFAULT):
    """Pacientes distintos por cooperado na janela (descritivo do dossiê).

    Mesma base das tabelas de análise (regra de PS aplicada em filtrar_ps).
    Nunca identifica paciente: sai só a CONTAGEM por cooperado.
    """
    f = fato[(fato["DATA_REQUISICAO"] >= janela_ini)
             & (fato["DATA_REQUISICAO"] <= janela_fim)]
    f = filtrar_ps(f, incluir_ps)
    return f.groupby("ID_COOPERADO")["ID_BENEFICIARIO"].nunique()


def _gatilho_efetivo(n, gatilho, n_min_p90, n_min_p75):
    """O critério pedido vale onde o n de elegíveis o sustenta; onde não
    sustenta, NÃO há critério (None): sem sinalização, posição só descritiva.
    Nunca se substitui o percentil pedido por outro (decisão 2026-09-11: o que
    o controle mostra é o que se calcula). Retorna array por linha (coluna
    gatilho_usado)."""
    n = pd.Series(n).fillna(0).to_numpy(dtype=float)
    minimo = n_min_p90 if gatilho == "p90" else n_min_p75
    return np.where(n >= minimo, gatilho, None)


def norma_por_area(
     taxa_agregada, 
     piso,
     col_area="AREA_ATUACAO", 
     col_taxa="taxa_exames_por_consulta",
     col_vol="consultas_totais"
):
    """Norma da área: o que é "normal" pedir, por área de atuação.

    Método:
        Entram só os cooperados elegíveis (volume >= piso), taxa de quem tem
        poucas consultas é ruído e contaminaria a referência. Dentro de cada área,
        a distribuição das taxas individuais é resumida por mediana, P75 e P90.
        Mediana (e não média) porque as distribuições são de cauda-longa
        (verificado na calibração): a média seria puxada pelos extremos, que são
        exatamente o que se quer detectar, não o que deve definir o normal.
        Quem está abaixo do piso não some da análise: só não define a norma.

    Parâmetros:
        taxa_agregada: tabela cooperado × taxa agregada, com área e volume.
        piso: mínimo de consultas na janela para entrar na construção da norma.
        col_area, col_taxa, col_vol: nomes das colunas de área, taxa e volume.

    Retorna: DataFrame por área com n_na_norma (quantos definiram a norma),
    mediana, p75 e p90.
    """
    # forma a norma: acima do piso E elegível pela classificação (INDEFINIDO, confiança
    # baixa, alerta masculino, ultrassonografista NÃO formam — mas seguem medidos)
    # p25 acompanha para o IQR (P75−P25) da leitura robusta — não é régua de sinalização
    elegiveis = taxa_agregada[(taxa_agregada[col_vol] >= piso) & taxa_agregada["elegivel_norma"]]
    # `.quantile()` do groupby, não `.agg(lambda s: s.quantile(...))`: a lambda
    # constrói um Series por grupo em Python, o método nativo roda em C. Mesmo
    # resultado (ambos skipna, mesma interpolação linear).
    g = elegiveis.groupby(col_area)[col_taxa]
    return pd.concat([g.count().rename("n_na_norma"),
                      g.quantile(.25).rename("p25"),
                      g.median().rename("mediana"),
                      g.quantile(.75).rename("p75"),
                      g.quantile(.90).rename("p90")], axis=1).reset_index()


def posicao_vs_norma(taxa_agregada, norma, piso, gatilho=config.GATILHO_DEFAULT,
                     n_min_p90=config.N_MINIMO_P90, n_min_p75=config.N_MINIMO_P75,
                     col_area="AREA_ATUACAO", col_taxa="taxa_exames_por_consulta", col_vol="consultas_totais"):
    """Posição de cada cooperado contra a norma da SUA área (nunca de outra).

    Método:
        Cada cooperado é comparado apenas com a referência da própria área:
        razao_vs_mediana = taxa do cooperado ÷ mediana da área (2.0 = pede o
        dobro do típico dos pares); acima_gatilho marca quem supera o percentil-
        gatilho da área (candidato a investigação, não veredito). Quem está abaixo do piso
        recebe avaliavel=False: a posição dele é exibida, mas não é confiável
        e não deve entrar em ranking. Ninguém é removido do resultado.

    Parâmetros:
        taxa_agregada: tabela cooperado × taxa agregada, com área e volume.
        norma: saída de norma_por_area.
        piso: mínimo de consultas para a taxa ser confiável (define a flag 'avaliavel').
        gatilho: percentil da área que sinaliza ('p75' ou 'p90'), o MESMO critério
            do drill-down por procedimento, para as telas nunca discordarem.
        n_min_p90, n_min_p75: n de elegíveis que sustenta cada percentil como
            régua; o gatilho degrada automaticamente (p90 -> p75 -> nenhum) e
            gatilho_usado registra o EFETIVO por linha.
        col_area, col_taxa, col_vol: nomes das colunas de área, taxa e volume.

    Retorna: taxa_agregada + mediana/p75/p90 da área, avaliavel, razao_vs_mediana,
    acima_gatilho e gatilho_usado (rastreabilidade).
    """
    assert gatilho in ("p75", "p90")
    df = taxa_agregada.merge(
        norma[[col_area, "n_na_norma", "mediana", "p75", "p90"]],
        on=col_area, how="left"
    )
    df["avaliavel"] = df[col_vol] >= piso            # abaixo do piso: taxa não confiável
    df["razao_vs_mediana"] = df[col_taxa] / df["mediana"]
    # gatilho degradado pelo n do grupo: percentil só é régua com amostra que o sustente
    df["gatilho_usado"] = _gatilho_efetivo(df["n_na_norma"], gatilho, n_min_p90, n_min_p75)
    _limiar = np.where(df["gatilho_usado"] == "p90", df["p90"].to_numpy(dtype=float),
              np.where(df["gatilho_usado"] == "p75", df["p75"].to_numpy(dtype=float), np.nan))
    df["acima_gatilho"] = np.greater(df[col_taxa].to_numpy(dtype=float), _limiar)
    return df.sort_values("razao_vs_mediana", ascending=False)


def prevalencia_por_procedimento(
    taxa_agregada, taxa_por_procedimento, piso, exclusoes=None,
    col_area="AREA_ATUACAO", col_proc="CD_PROCEDIMENTO", col_vol="consultas_totais"
):
    """Prevalência: que fração da área pede cada procedimento.

    Método:
        Para cada (área, procedimento): nº de cooperados elegíveis (volume >= piso)
        que solicitaram o procedimento ao menos uma vez ÷ nº total de elegíveis da
        área. Serve a dois propósitos: (1) é o n por trás da norma daquele
        procedimento, mediana sustentada por 3 solicitantes não é referência;
        (2) separa "pede pouco" de "não pede": quem não pede não tem taxa zero,
        tem prevalência, são dimensões diferentes.

    Parâmetros:
        taxa_agregada: tabela cooperado × taxa agregada (fonte da elegibilidade).
        taxa_por_procedimento: tabela longa cooperado × procedimento × taxa.
        piso: mínimo de consultas para o cooperado contar como elegível.
        exclusoes: conjunto de tuplas (ID_COOPERADO, área, procedimento) fora da
            formação da norma daquele par (Mov 5); None = sem exclusão.
        col_area, col_proc, col_vol: nomes das colunas.

    Retorna: DataFrame (área, procedimento) com n_solicitantes_elegiveis,
    n_elegiveis_area e prevalencia.
    """
    elegiveis = taxa_agregada.loc[
        (taxa_agregada[col_vol] >= piso) & taxa_agregada["elegivel_norma"],
        ["ID_COOPERADO", col_area]]
    n_elegiveis_area = elegiveis.groupby(col_area)["ID_COOPERADO"].nunique().rename("n_elegiveis_area")

    formadores = taxa_por_procedimento.merge(elegiveis[["ID_COOPERADO"]], on="ID_COOPERADO", how="inner")
    if exclusoes:   # Mov 5: portador excluído não conta no n da norma daquele par
        _k = zip(formadores["ID_COOPERADO"], formadores[col_area], formadores[col_proc])
        formadores = formadores[[t not in exclusoes for t in _k]]
    n_solicitantes = (
        formadores.groupby([col_area, col_proc])["ID_COOPERADO"].nunique()
        .rename("n_solicitantes_elegiveis")
    )

    return (
        n_solicitantes.reset_index()
        .merge(n_elegiveis_area, on=col_area, how="left")
        .assign(prevalencia=lambda d: d["n_solicitantes_elegiveis"] / d["n_elegiveis_area"])
    )


def norma_por_procedimento(
    taxa_por_procedimento, taxa_agregada, piso, n_minimo, exclusoes=None,
    col_area="AREA_ATUACAO", col_proc="CD_PROCEDIMENTO",
    col_taxa="taxa", col_vol="consultas_totais"
):
    """Norma por (área, procedimento): quanto é normal pedir CADA exame, entre quem pede.

    Método:
        Mesma máquina da norma agregada, descida ao nível do procedimento, com uma
        regra central: a norma é calculada ENTRE QUEM SOLICITA o procedimento ,
        cooperados com zero solicitações não entram como taxa 0 (isso puxaria a
        mediana para baixo e condenaria quem pede o exame por praticar algo que
        os outros não praticam). "Não pede" vira prevalência, dimensão separada.
        A norma só é 'apresentavel' com n_minimo+ solicitantes elegíveis: percentil
        de grupo minúsculo é instável (um cooperado muda tudo) e não deve ser
        exibido como referência sólida.

    Parâmetros:
        taxa_por_procedimento: tabela longa cooperado × procedimento × taxa.
        taxa_agregada: tabela cooperado × taxa agregada (fonte da elegibilidade).
        piso: mínimo de consultas para o cooperado entrar na norma.
        n_minimo: mínimo de solicitantes elegíveis para a norma ser 'apresentavel'.
        exclusoes: conjunto de tuplas (ID_COOPERADO, área, procedimento) fora da
            formação da norma daquele par (Mov 5); None = sem exclusão.
        col_area, col_proc, col_taxa, col_vol: nomes das colunas.

    Retorna: DataFrame (área, procedimento) com prevalência, mediana, p75, p90
    e a flag apresentavel.
    """
    prev = prevalencia_por_procedimento(taxa_agregada, taxa_por_procedimento, piso,
                                        exclusoes, col_area, col_proc, col_vol)

    elegiveis_ids = taxa_agregada.loc[
        (taxa_agregada[col_vol] >= piso) & taxa_agregada["elegivel_norma"], "ID_COOPERADO"]
    elegiveis = taxa_por_procedimento[taxa_por_procedimento["ID_COOPERADO"].isin(elegiveis_ids)]
    if exclusoes:
        # Mov 5: portadores de sub-perfil não FORMAM a norma dos pares onde distorcem
        # (>LIMIAR_DISTORCAO_EXCLUSAO); seguem medidos contra ela. Ativado:
        # (v1: sub_alto_risco em GO, sub_opera em Gin; v2: nenhuma). Limiar PROVISÓRIO —
        # re-roda na homologação.
        _k = zip(elegiveis["ID_COOPERADO"], elegiveis[col_area], elegiveis[col_proc])
        elegiveis = elegiveis[[t not in exclusoes for t in _k]]

    # idem: aqui são milhares de grupos (área x procedimento), e a lambda por
    # grupo era o segundo maior custo da requisição.
    g = elegiveis.groupby([col_area, col_proc])[col_taxa]
    stats = pd.concat([g.median().rename("mediana"),
                       g.quantile(.75).rename("p75"),
                       g.quantile(.90).rename("p90")], axis=1).reset_index()

    norma = prev.merge(stats, on=[col_area, col_proc], how="left")
    norma["apresentavel"] = norma["n_solicitantes_elegiveis"] >= n_minimo
    return norma


def posicao_vs_norma_procedimento(
    taxa_por_procedimento,
    norma_proc,
    piso,
    gatilho=config.GATILHO_DEFAULT,
    n_min_p90=config.N_MINIMO_P90,
    n_min_p75=config.N_MINIMO_P75,               # <- runtime: quem é SINALIZADO ("p75" ou "p90")
    alvo=config.ALVO_DEFAULT,              # <- runtime: até onde medir ("mediana", "p75" ou "p90")
    col_area="AREA_ATUACAO",
    col_proc="CD_PROCEDIMENTO",
    col_taxa="taxa",
    col_vol="consultas_totais"
):
    """Posição e excedente de cada (cooperado, procedimento) contra a norma da área.

    Método:
        Duas decisões separadas, com réguas separadas:
        - SINALIZAR (gatilho): o cooperado é marcado num procedimento se a taxa
          dele supera o percentil-gatilho da área (ex.: P90 = só o decil extremo).
        - MEDIR (alvo): o excedente é calculado contra um nível plausível de
          convergência: excedente_itens = (taxa − alvo) × consultas do cooperado,
          ou seja, quantos itens ele pediu além do que o alvo preveria para o
          volume de consultas dele na janela.
        Gatilho e alvo NUNCA são o mesmo valor: trazer todos acima do P75 para o
        P75 condenaria o quartil superior inteiro por construção, sempre existe
        um quartil superior, mesmo numa área eficiente. Sinaliza-se no extremo;
        mede-se contra a referência. razao_vs_mediana acompanha como medida de
        intensidade (lente complementar ao excedente, que é magnitude).

    Parâmetros:
        taxa_por_procedimento: tabela longa cooperado × procedimento × taxa.
        norma_proc: saída de norma_por_procedimento.
        piso: mínimo de consultas para a taxa ser confiável (flag 'avaliavel').
        gatilho: percentil que SINALIZA ('p75' ou 'p90'), define quem entra no Pareto.
        n_min_p90, n_min_p75: n de solicitantes elegíveis que sustenta cada
            percentil como régua; o gatilho degrada automaticamente
            (p90 -> p75 -> nenhum) e gatilho_usado registra o EFETIVO por linha.
        alvo: nível contra o qual o excedente é medido ('mediana', 'p75' ou 'p90').
              Regra: alvo <= gatilho.
        col_area, col_proc, col_taxa, col_vol: nomes das colunas.

    Retorna: tabela longa com razao_vs_mediana (intensidade fixa),
    razao_vs_alvo (contra a referência ativa, que é a que a tela mostra),
    sinalizado, excedente_itens e o gatilho/alvo usados (rastreabilidade).
    """
    ordem = {"mediana": 0, "p75": 1, "p90": 2}
    assert gatilho in ("p75", "p90") and alvo in ordem
    assert ordem[alvo] <= ordem[gatilho], "alvo deve ser <= gatilho"

    df = taxa_por_procedimento.merge(
        norma_proc[[col_area, col_proc, "mediana", "p75", "p90",
                    "n_solicitantes_elegiveis", "prevalencia", "apresentavel"]],
        on=[col_area, col_proc], how="left"
    )
    df["avaliavel"] = df[col_vol] >= piso
    df["razao_vs_mediana"] = df[col_taxa] / df["mediana"]
    # gatilho degradado pelo n de solicitantes elegíveis que sustenta o percentil
    df["gatilho_usado"] = _gatilho_efetivo(df["n_solicitantes_elegiveis"],
                                           gatilho, n_min_p90, n_min_p75)
    _limiar = np.where(df["gatilho_usado"] == "p90", df["p90"].to_numpy(dtype=float),
              np.where(df["gatilho_usado"] == "p75", df["p75"].to_numpy(dtype=float), np.nan))
    df["sinalizado"] = np.greater(df[col_taxa].to_numpy(dtype=float), _limiar)
    # a referência pedida é a que vale, em toda linha (nunca substituída)
    df["alvo_usado"] = alvo
    df["alvo_valor"] = df[alvo].to_numpy(dtype=float)
    df["excedente_itens"] = (df[col_taxa] - df["alvo_valor"]).clip(lower=0) * df[col_vol]
    # A MESMA razão, medida contra a REFERÊNCIA ATIVA (o alvo escolhido), e não
    # contra a mediana. As duas coincidem no default (alvo = mediana), e é por
    # isso que a diferença ficou invisível até a tela rodar em `referencia=p75`:
    # a tabela do dossiê mostrava "referência 0,011" e, na coluna ao lado,
    # "12,2×", que é a razão contra a mediana. Quem lê divide as duas colunas e
    # não fecha. Toda superfície cujo rótulo diz "a referência" lê ESTA coluna;
    # `razao_vs_mediana` fica para quem quer a intensidade fixa, que não se move
    # quando o analista troca o alvo.
    df["razao_vs_alvo"] = df[col_taxa] / df["alvo_valor"]
    return df.sort_values("excedente_itens", ascending=False)


def pipeline(fato, janela_ini, janela_fim, piso, n_minimo, area=None, gatilho=config.GATILHO_DEFAULT,
             alvo=config.ALVO_DEFAULT, incluir_ps=config.INCLUIR_PS_DEFAULT,
             exclusoes_por_par=None):
    """Motor do lado da solicitação: FATO + parâmetros -> tabelas de análise.

    Método (sequência fixa, mesma janela para tudo):
        1. Filtra o fato pela DATA_REQUISICAO (o evento clínico que gera o custo).
        2. Exclui episódios de PS por padrão (incluir_ps, doc §5.6): a consulta-PS
           sai INTEIRA, numerador e denominador caem juntos.
        3. Escala o piso anual à janela: piso_janela = piso × dias/365, senão
           janelas curtas esvaziariam a coorte.
        4. Denominador: consultas inferidas (nº de ID_CONSULTA distintos) por
           cooperado. Numerador: soma de QT_EFETIVO. Taxa = razão de totais.
        5. Norma da área (mediana/percentis entre os que FORMAM a norma: acima do
           piso E elegivel_norma=True) e posição de TODOS contra ela (inelegíveis
           e INDEFINIDO são medidos, só não formam).
        6. Mesmo cálculo descido a (área, procedimento), com prevalência e
           excedente por item.
        Norma e indivíduo saem SEMPRE da mesma janela, comparar janelas
        diferentes é viés garantido. Nada é lido de cache ou de default global:
        cada chamada recalcula tudo a partir dos argumentos.

    Parâmetros:
        fato: fato_solicitacoes (uma linha por item solicitado).
        janela_ini, janela_fim: janela de análise pela DATA_REQUISICAO (inclusivas).
        piso: piso de consultas declarado POR ANO; escalado pela duração da janela.
        n_minimo: mínimo de solicitantes elegíveis para norma de procedimento
                  apresentável (contagem de pessoas, NÃO escala com a janela).
        area: se informada, restringe a análise a essa área de atuação.
        gatilho: percentil que sinaliza outlier ('p75' ou 'p90').
        alvo: nível contra o qual o excedente é medido ('mediana', 'p75' ou 'p90').
        incluir_ps: False (default do config) EXCLUI episódios de PS (doc §5.6);
            True mantém, a escolha fica na assinatura, auditável e reversível.
        exclusoes_por_par: conjunto de tuplas (ID_COOPERADO, área, procedimento)
            fora da formação da norma daquele par (Mov 5, montar_exclusao_por_par);
            None = sem exclusão.

    Retorna: dict com taxa_agregada, norma, posicao, norma_proc, posicao_proc,
    piso_aplicado, janela_dias, base (carimbo da regra de PS), classificacao
    (versão/status da classificação injetada) e exclusoes_por_par (contagem).
    """
    f = fato[(fato["DATA_REQUISICAO"] >= janela_ini) & (fato["DATA_REQUISICAO"] <= janela_fim)]
    if area is not None:
        f = f[f["AREA_ATUACAO"] == area]
    f = filtrar_ps(f, incluir_ps)

    dias = (pd.Timestamp(janela_fim) - pd.Timestamp(janela_ini)).days + 1
    piso_janela = max(1, round(piso * dias / 365))

    consultas = f.groupby("ID_COOPERADO")["ID_CONSULTA"].nunique().rename("consultas_totais")
    itens = f.groupby("ID_COOPERADO")["QT_EFETIVO"].sum().rename("total_itens")
    area_map = f.drop_duplicates("ID_COOPERADO")[["ID_COOPERADO", "AREA_ATUACAO", "elegivel_norma"]]

    tx_agg = (
        pd.concat([itens, consultas], axis=1)
          .assign(taxa_exames_por_consulta=lambda d: d["total_itens"] / d["consultas_totais"])
          .reset_index()
          .merge(area_map, on="ID_COOPERADO", how="left")
    )

    n_proc = (
        f.groupby(["ID_COOPERADO", "CD_PROCEDIMENTO"])["QT_EFETIVO"].sum()
         .rename("n_solicitacoes").reset_index()
    )
    tx_proc = (
        n_proc
        .merge(consultas.reset_index(), on="ID_COOPERADO", how="left")
        .merge(area_map, on="ID_COOPERADO", how="left")
        .assign(taxa=lambda d: d["n_solicitacoes"] / d["consultas_totais"])
        .merge(f.drop_duplicates("CD_PROCEDIMENTO")[["CD_PROCEDIMENTO", "DS_PROCEDIMENTO"]],
               on="CD_PROCEDIMENTO", how="left")
    )

    norma = norma_por_area(tx_agg, piso_janela)
    posicao = posicao_vs_norma(tx_agg, norma, piso_janela, gatilho=gatilho)
    normap = norma_por_procedimento(tx_proc, tx_agg, piso_janela, n_minimo,
                                    exclusoes=exclusoes_por_par)
    posproc = posicao_vs_norma_procedimento(tx_proc, normap, piso_janela, gatilho=gatilho, alvo=alvo)

    return {
        "taxa_agregada": tx_agg, "norma": norma, "posicao": posicao,
        "norma_proc": normap, "posicao_proc": posproc,
        "piso_aplicado": piso_janela, "janela_dias": dias,
        "base": carimbo_base(incluir_ps),
        "classificacao": config.CLASSIFICACAO_VERSAO,
        "exclusoes_por_par": 0 if not exclusoes_por_par else len(exclusoes_por_par),
    }


def precos_por_procedimento(contas_da_janela):
    """Preço mediano por código: mediana de VALORTOTAL/QUANTIDADEEXECUTADA.

    Saiu de dentro do `pipeline_execucao` (set/2026) quando a série trimestral
    passou a precisar da MESMA tabela. Duas medianas calculadas em lugares
    diferentes divergem no dia em que alguém mexer numa só, e aqui elas TÊM de
    ser idênticas: a série do dossiê é uma decomposição do total da janela, e
    decomposição que não soma o todo é erro de leitura garantido.

    Mediana, e não média, porque a distribuição de valor unitário tem cauda
    (pacote, urgência, tabela negociada) e a média seguiria o extremo.
    """
    v = contas_da_janela[(contas_da_janela["QUANTIDADEEXECUTADA"] > 0)
                         & (contas_da_janela["VALORTOTAL"] > 0)].copy()
    v["valor_unitario"] = v["VALORTOTAL"] / v["QUANTIDADEEXECUTADA"]
    return (v.groupby("CODIGO")["valor_unitario"]
            .agg(preco_mediano="median", n_execucoes="count").reset_index()
            .rename(columns={"CODIGO": "CD_PROCEDIMENTO"}))


def pipeline_execucao(fato, contas, janela_ini, janela_fim, piso, n_minimo,
                      piso_execucoes, q_confundidor, mapa_executantes,
                      area=None, gatilho=config.GATILHO_DEFAULT, alvo=config.ALVO_DEFAULT, preco=None,
                      incluir_ps=config.INCLUIR_PS_DEFAULT, exclusoes_por_par=None):
    """Motor do lado da execução, em cima do pipeline() da MESMA janela: converte o
    excedente em R$ e anexa o contexto (confundidores) que evita acusação injusta.

    Método:
        1. Roda o pipeline() da solicitação com os mesmos janela/parâmetros.
        2. PREÇO: mediana de VALORTOTAL ÷ QUANTIDADEEXECUTADA por código, nas
           contas da janela (robusta a outliers de cobrança). Se 'preco' for
           injetado (tabela oficial), usa-o no lugar.
        3. EXCEDENTE EM R$ = excedente_itens × preço mediano. Entram no total
           apenas linhas que passam os três portões: avaliavel (cooperado acima
           do piso) + apresentavel (norma com n mínimo) + sinalizado (acima do
           gatilho). Pareto = soma por procedimento, ordenado, com % acumulado.
        3b. CUSTO SOLICITADO por cooperado (magnitude, não desvio): todo item
           solicitado × preço mediano, ponderado por QT_EFETIVO e sobre a MESMA
           base eletiva de consultas_totais. Entrega valor_total_solicitado,
           custo_por_consulta e a cobertura de preço que os sustenta.
        4. PERFIL DE EXECUÇÃO: das execuções do cooperado nas contas, % que ele
           mesmo solicitou (taxa_autorref) e mix de regime (% pronto-socorro,
           % internação). Piso de execuções escalado à janela; quantis calculados
           só entre os sólidos.
        5. CONFUNDIDORES (contexto, NÃO alteram nenhum número): flags para quem
           está acima do quantil q_confundidor dos pares elegíveis em % de
           urgência (provável plantonista) ou % de pronto-socorro. Dizem "o
           excedente deste cooperado pode ser perfil, não excesso, investigue
           com essa lente" (metodologia §7.3: confundidor antes de conclusão).
        6. AUTORREFERÊNCIA POR ITEM (lado da solicitação): casa cada item
           solicitado com contas por (requisição + código); taxa = % de
           autoexecução APENAS entre os itens com match. PREMISSA (não
           verificada): itens sem conta se comportam como os observados ,
           indicador investigativo, não flag; nunca apresentar sem cobertura_join.

    Parâmetros:
        fato: fato_solicitacoes (uma linha por item solicitado).
        contas: base de contas (lado executante), valores/quantidades já numéricos.
        janela_ini, janela_fim: janela pela DATA_REQUISICAO (fato) e DATA_EXECUCAO (contas).
        piso: piso de consultas POR ANO, escalado pela janela, elegibilidade do cooperado.
        n_minimo: mínimo de solicitantes elegíveis para norma de procedimento apresentável.
        piso_execucoes: piso de execuções POR ANO, escalado pela janela, lado da execução.
        q_confundidor: quantil (0–1) que marca confundidor de urgência/regime:
                       0.90 = flag para os 10% mais altos entre os pares elegíveis.
        mapa_executantes: dim executante -> cooperado (2+ cadastros por cooperado possíveis).
        area: se informada, restringe a essa área de atuação.
        gatilho, alvo: como no pipeline().
        preco: tabela código -> preço injetada (ex.: tabela oficial da Unimed);
               None deriva o preço mediano das contas da própria janela.
        incluir_ps: repassado ao pipeline() (default do config = análise eletiva).
            Perfis e confundidores ficam na base COMPLETA da janela (ver nota abaixo).

    Retorna: dict do pipeline() + preco, custo_coop (valor solicitado e custo por
    consulta), posicao_proc_rs, sinal (sinalizados com preço),
    pareto_rs, perfil_execucao, autorref, resumo_coop e piso_execucoes_aplicado.
    O carimbo 'base' (herdado do pipeline) descreve as tabelas de ANÁLISE; perfil de
    execução, confundidores e autorref são CONTEXTO calculado na base completa da janela.
    """
    res = pipeline(fato, janela_ini, janela_fim, piso, n_minimo, area, gatilho, alvo,
                   incluir_ps=incluir_ps, exclusoes_por_par=exclusoes_por_par)

    # solicitações e contas da MESMA janela
    f = fato[(fato["DATA_REQUISICAO"] >= janela_ini) & (fato["DATA_REQUISICAO"] <= janela_fim)]
    if area is not None:
        f = f[f["AREA_ATUACAO"] == area]
    c = contas[(contas["DATA_EXECUCAO"] >= janela_ini) & (contas["DATA_EXECUCAO"] <= janela_fim)]

    # preço: mediana de VALORTOTAL/QUANTIDADEEXECUTADA por código na janela
    if preco is None:
        preco = precos_por_procedimento(c)

    # CUSTO SOLICITADO por cooperado: TODO item que ele solicitou, valorado ao
    # preço mediano — não só os excedentes. Responde "quanto custa uma consulta
    # dele", que é pergunta de magnitude, não de desvio.
    #
    # Base ELETIVA (filtrar_ps), a MESMA de consultas_totais: o numerador vem do
    # item e o denominador da consulta, e tirar PS de um só daria numerador e
    # denominador de conjuntos diferentes (rigor-estatistico §9).
    #
    # Ponderado por QT_EFETIVO, e não por linha, porque é assim que
    # `total_itens` e `taxa_exames_por_consulta` são contados no pipeline(). Sem
    # isso, custo_por_consulta ÷ exames_por_consulta não daria o preço médio por
    # exame, e as duas colunas da tabela se contradiriam.
    f_eletiva = filtrar_ps(f, incluir_ps)
    val = f_eletiva.merge(preco[["CD_PROCEDIMENTO", "preco_mediano"]],
                          on="CD_PROCEDIMENTO", how="left")
    val["valor_solicitado"] = val["QT_EFETIVO"] * val["preco_mediano"]
    custo_coop = (
        val.groupby("ID_COOPERADO")
        .agg(valor_total_solicitado=("valor_solicitado", "sum"),
             itens_com_preco=("preco_mediano", "count"),
             itens_avaliados=("preco_mediano", "size"))
        .reset_index()
        .merge(res["taxa_agregada"][["ID_COOPERADO", "consultas_totais"]],
               on="ID_COOPERADO", how="left")
    )
    # cobertura viaja junto: valor total é SOMA, e soma com buraco parece menor,
    # não parece incompleta. Quem lê precisa saber sobre que fração ela se apoia.
    custo_coop["cobertura_preco"] = (custo_coop["itens_com_preco"]
                                     / custo_coop["itens_avaliados"])
    custo_coop["custo_por_consulta"] = (custo_coop["valor_total_solicitado"]
                                        / custo_coop["consultas_totais"])
    custo_coop["base"] = carimbo_base(incluir_ps)

    # excedente em R$ = excedente_itens × preço (sinaliza no gatilho, mede contra o alvo)
    posproc_rs = res["posicao_proc"].merge(preco, on="CD_PROCEDIMENTO", how="left")
    posproc_rs["excedente_reais"] = posproc_rs["excedente_itens"] * posproc_rs["preco_mediano"]
    sinal = filtrar_sinalizados(posproc_rs, exigir_preco=True)
    pareto_rs = (
        sinal.groupby(["CD_PROCEDIMENTO", "DS_PROCEDIMENTO"])
        .agg(excedente_reais=("excedente_reais", "sum"),
             excedente_itens=("excedente_itens", "sum"),
             n_cooperados=("ID_COOPERADO", "nunique"),
             preco_mediano=("preco_mediano", "first"))
        .sort_values("excedente_reais", ascending=False)
        .reset_index()
    )
    pareto_rs["pct_acumulado"] = (pareto_rs["excedente_reais"].cumsum()
                                  / pareto_rs["excedente_reais"].sum() * 100).round(1)

    # perfil de execução: autorreferência (das execuções dele, % que ele mesmo pediu)
    # e mix de regime — só cooperados-executantes (premissa do projeto: executante
    # sem nenhum 'S' não é cooperado desta análise).
    piso_exec_jan = max(1, round(piso_execucoes * res["janela_dias"] / 365))
    exec_coop = c.merge(mapa_executantes, on="IDENTIFICADOR_EXECUTANTE", how="inner")
    perfil_execucao = (
        exec_coop.groupby("ID_COOPERADO")
        .agg(execucoes=("NR_SEQ_REQUISICAO", "count"),
             taxa_autorref=("SOLIC_IGUAL_EXEC", lambda s: (s == "S").mean()),
             pct_pronto_socorro=("REGIMEATENDIMENTO", lambda s: (s == "Pronto Socorro").mean()),
             pct_internacao=("REGIMEATENDIMENTO", lambda s: (s == "Internação").mean()))
        .reset_index()
    )
    # abaixo do piso: fica no dataset com flag, mas fora de ranking e de quantil
    perfil_execucao["avaliavel_exec"] = perfil_execucao["execucoes"] >= piso_exec_jan
    solidos = perfil_execucao[perfil_execucao["avaliavel_exec"]]
    corte_ps = solidos["pct_pronto_socorro"].quantile(q_confundidor)
    perfil_execucao["confundidor_regime"] = (
        perfil_execucao["avaliavel_exec"] & (perfil_execucao["pct_pronto_socorro"] > corte_ps)
    )

    # confundidor de urgência (lado da solicitação); quantil só entre elegíveis.
    # CONTEXTO na base COMPLETA da janela (sem filtro de PS): numa base eletiva,
    # pct_urgencia é 0 por construção (qualquer item URG marca a consulta como
    # episódio-PS) — o confundidor descreve a PESSOA; o filtro se aplica à ANÁLISE.
    mix_carater = (
        f.groupby("ID_COOPERADO")["CARATER_ATENDIMENTO"]
        .apply(lambda s: (s == config.STRING_URGENCIA).mean()).rename("pct_urgencia").reset_index()
        .merge(res["taxa_agregada"][["ID_COOPERADO", "consultas_totais"]],
               on="ID_COOPERADO", how="left")
    )
    eleg = mix_carater["consultas_totais"] >= res["piso_aplicado"]
    corte_urg = mix_carater.loc[eleg, "pct_urgencia"].quantile(q_confundidor)
    mix_carater["confundidor_urgencia"] = eleg & (mix_carater["pct_urgencia"] > corte_urg)

    # autorreferência POR ITEM (lado da solicitação): só itens com match em contas.
    # PREMISSA (não verificada): itens sem conta se autorreferem como os observados.
    # Indicador investigativo, não flag — nunca apresentar sem a cobertura ao lado.
    # `.any()` NATIVO do groupby, não `.agg(lambda s: (s == "S").any())`: são
    # ~884 mil grupos (requisição x código), e a lambda paga um Series novo por
    # grupo — 23 s contra 0,3 s, saída idêntica (verificado 31/ago/2026).
    cont_item = (
        c.assign(autoexec=(c["SOLIC_IGUAL_EXEC"] == "S"))
        .groupby(["NR_SEQ_REQUISICAO", "CODIGO"])["autoexec"].any().reset_index()
        .rename(columns={"CODIGO": "CD_PROCEDIMENTO"})
    )
    rc = f.merge(cont_item, on=["NR_SEQ_REQUISICAO", "CD_PROCEDIMENTO"], how="left")
    autorref = (
        rc.groupby("ID_COOPERADO")
        .agg(itens=("NR_SEQ_REQUISICAO", "count"),
             itens_com_conta=("autoexec", lambda s: s.notna().sum()),
             taxa_autorref_solic=("autoexec", lambda s: s.dropna().mean()))
        .reset_index()
    )
    autorref["cobertura_join"] = autorref["itens_com_conta"] / autorref["itens"]

    resumo_coop = (
        sinal.groupby("ID_COOPERADO")
        .agg(excedente_reais_total=("excedente_reais", "sum"),
             n_procs_sinalizados=("CD_PROCEDIMENTO", "nunique"))
        .reset_index()
        .merge(mix_carater[["ID_COOPERADO", "pct_urgencia", "confundidor_urgencia"]],
               on="ID_COOPERADO", how="left")
        .merge(autorref[["ID_COOPERADO", "taxa_autorref_solic", "cobertura_join"]],
               on="ID_COOPERADO", how="left")
        .sort_values("excedente_reais_total", ascending=False)
    )

    return {**res,
            "preco": preco, "custo_coop": custo_coop,
            "posicao_proc_rs": posproc_rs, "sinal": sinal,
            "pareto_rs": pareto_rs, "perfil_execucao": perfil_execucao,
            "autorref": autorref, "resumo_coop": resumo_coop,
            "piso_execucoes_aplicado": piso_exec_jan}


def persistencia_temporal(fato, janelas, piso, n_minimo, gatilho=config.GATILHO_DEFAULT, alvo=config.ALVO_DEFAULT,
                          area=None, min_janelas_avaliaveis=config.MIN_JANELAS_AVALIAVEIS,
                          incluir_ps=config.INCLUIR_PS_DEFAULT, exclusoes_por_par=None,
                          precos=None):
    """Consistência do sinal através de janelas disjuntas, com norma recalculada.

    Método:
        Roda o pipeline() em cada janela, com os MESMOS parâmetros e norma
        recalculada por janela: a persistência mede quantas vezes o cooperado foi
        sinalizado sob a régua do próprio período. A alegação é CONSISTÊNCIA, não
        independência estatística, os mesmos pacientes e protocolos atravessam
        janelas; o argumento honesto é "o padrão se repete em N janelas distintas,
        cada uma comparada com a norma do próprio período".

        Para cada (cooperado, procedimento):
          denominador = janelas em que o sinal era POSSÍVEL: cooperado avaliável
            (volume >= piso escalado à janela) E norma do procedimento
            apresentável na área. Janela em que ele não pediu o procedimento
            CONTA no denominador (não pediu => não sinalizado), regra
            conservadora, favorável ao médico.
          numerador   = janelas em que foi sinalizado (taxa > gatilho da área).
          persistencia = numerador / denominador.

        Disciplina do 1/1: a razão NUNCA viaja sem n_janelas_avaliaveis ao lado
        (1/1 = 1.0 é evidência fraca vestida de forte). Ordenação por
        (persistencia, n_janelas_avaliaveis); reportavel marca quem tem o mínimo
        de janelas, flag, nada é deletado.

        Nota (comparações múltiplas): testar milhares de pares cooperado ×
        procedimento contra um percentil garante falsos positivos por acaso em
        janela única; sinal que se repete em 3–4 janelas recalculadas é o filtro
        que o acaso não atravessa.

    Parâmetros:
        fato: fato_solicitacoes (uma linha por item solicitado).
        janelas: lista de (inicio, fim) DISJUNTAS, ex.: 4 trimestres.
        piso, n_minimo, gatilho, alvo, area: como no pipeline(), idênticos em
            todas as janelas.
        min_janelas_avaliaveis: mínimo de janelas avaliáveis para a persistência
            ser reportável (parâmetro do analista; default 2, provisório).
        incluir_ps: repassado ao pipeline() de CADA janela (default do config =
            análise eletiva), mesma base em todas as janelas, por construção.

    Retorna: dict com
        'por_janela_cooperado': (cooperado, janela) com o índice agregado e se
            era avaliável — a MAGNITUDE que a grade binária não carrega, e de
            onde sai a direção da série;
        'por_janela': a grade CRUA (cooperado, procedimento, janela, sinalizado)
            de onde as contagens saem. Devolvida porque a tela precisa da SÉRIE,
            não só da soma: "3/4" não diz se os três foram os três primeiros
            trimestres (padrão que persiste) ou o 1º, o 2º e o 4º (padrão
            intermitente), e a diferença muda a conversa com o médico;
        'por_procedimento': (cooperado, procedimento) com n_janelas_avaliaveis,
            n_janelas_sinalizado, persistencia e reportavel;
        'por_cooperado': agregado para a fila, nº de procedimentos reportáveis,
            nº com persistencia == 1.0 e nº com persistencia >= 0.75.
    """
    # ── A CESTA E A RÉGUA DO ANO ────────────────────────────────────────────
    # Regra do projeto (METODOLOGIA §5.4): régua RECALCULADA para sinalizar,
    # régua CONGELADA para acompanhar. O laço abaixo recalcula a norma em cada
    # trimestre, e é dele que sai a mini-série de consistência: ali a pergunta é
    # "ele foi sinalizado sob a régua do próprio período".
    #
    # O DINHEIRO não sai de lá. Ele é a decomposição do excedente do ANO, e por
    # isso precisa da régua do ano: a cesta de pares sinalizados, o alvo e o
    # preço são todos anuais, e o trimestre só distribui itens e consultas.
    # Medir dinheiro com régua móvel faria o excedente cair quando a área
    # inteira aumentasse o consumo, mostrando melhora onde não houve.
    cesta = k_por_cooperado = None
    if precos is not None and len(precos) and janelas:
        anual = pipeline(fato, janelas[0][0], janelas[-1][1], piso, n_minimo,
                         area, gatilho, alvo, incluir_ps=incluir_ps,
                         exclusoes_por_par=exclusoes_por_par)
        c = anual["posicao_proc"].merge(
            precos[["CD_PROCEDIMENTO", "preco_mediano"]],
            on="CD_PROCEDIMENTO", how="left")
        c = filtrar_sinalizados(c, exigir_preco=True)
        if len(c):
            cesta = c[["ID_COOPERADO", "CD_PROCEDIMENTO", "preco_mediano"]].copy()
            # o ALVO é a taxa contra a qual o excedente do ano foi medido; em R$,
            # ele vira "quanto de dinheiro por consulta a referência prevê"
            cesta["alvo_x_preco"] = c["alvo_valor"].astype(float) * c["preco_mediano"]
            k_por_cooperado = (cesta.groupby("ID_COOPERADO")["alvo_x_preco"].sum()
                               .rename("k_referencia").reset_index())

    registros, indices, evolucao = [], [], []
    for k, (ini, fim) in enumerate(janelas, start=1):
        r = pipeline(fato, ini, fim, piso, n_minimo, area, gatilho, alvo,
                     incluir_ps=incluir_ps, exclusoes_por_par=exclusoes_por_par)
        avaliaveis = r["posicao"].loc[r["posicao"]["avaliavel"],
                                      ["ID_COOPERADO", "AREA_ATUACAO"]]
        apresentaveis = r["norma_proc"].loc[r["norma_proc"]["apresentavel"],
                                            ["AREA_ATUACAO", "CD_PROCEDIMENTO"]]
        # grade do possível: cooperado avaliável × procedimento apresentável na área dele
        grade = avaliaveis.merge(apresentaveis, on="AREA_ATUACAO")
        sinalizados = r["posicao_proc"].loc[r["posicao_proc"]["sinalizado"],
                                            ["ID_COOPERADO", "CD_PROCEDIMENTO"]]
        g = grade.merge(sinalizados, on=["ID_COOPERADO", "CD_PROCEDIMENTO"],
                        how="left", indicator=True)
        g["sinalizado"] = g["_merge"] == "both"
        g["janela"] = k
        registros.append(g[["ID_COOPERADO", "CD_PROCEDIMENTO", "janela", "sinalizado"]])

        # o ÍNDICE agregado do cooperado naquela janela, sob a norma daquela
        # janela. A grade acima diz SE ele foi sinalizado; esta diz QUANTO —
        # sem ela a série é binária e não tem direção.
        pos = (r["posicao"][["ID_COOPERADO", "taxa_exames_por_consulta", "avaliavel",
                             "consultas_totais", "total_itens"]]
               .rename(columns={"taxa_exames_por_consulta": "taxa"}).copy())
        pos["janela"] = k
        # o PISO daquele trimestre viaja junto: quem cai abaixo dele não é
        # medido ali, e a tela precisa dizer abaixo de QUÊ, não só que não mediu
        pos["piso"] = r["piso_aplicado"]
        # PACIENTES DISTINTOS do trimestre: é o outro denominador do período, o
        # que separa "atendeu mais gente" de "pediu mais para a mesma gente".
        # Contagem, nunca identidade (ver `pacientes_distintos`).
        pac = pacientes_distintos(fato, ini, fim, incluir_ps=incluir_ps)
        pos["pacientes"] = pos["ID_COOPERADO"].map(pac)
        indices.append(pos)

        # ── EVOLUÇÃO: o R$ do trimestre, quando há preço ────────────────────
        # Agregado AQUI, dentro do laço, e não devolvido cru: a grade
        # (cooperado × procedimento × janela) valorada é grande, e o que a tela
        # consome é uma linha por trimestre.
        #
        # O PREÇO É O DA JANELA INTEIRA, não o do trimestre. De propósito: com
        # preço por trimestre, uma barra maior poderia ser reajuste de tabela em
        # vez de mais solicitação, e a série existe para responder volume. Preço
        # constante isola a variação que a tela afirma estar medindo.
        if precos is not None and len(precos):
            pp = r["posicao_proc"].merge(
                precos[["CD_PROCEDIMENTO", "preco_mediano"]],
                on="CD_PROCEDIMENTO", how="left")
            pp = pp[pp["preco_mediano"].notna()]
            if len(pp):
                ev = (pp.assign(custo=pp["n_solicitacoes"] * pp["preco_mediano"])
                      .groupby("ID_COOPERADO")
                      .agg(custo=("custo", "sum")).reset_index())
                # o VALOR SOLICITADO no trimestre, restrito à cesta do ano. É a
                # primeira metade de `n_tri − alvo × consultas_tri`; a segunda
                # entra depois do laço, porque depende das consultas do
                # trimestre e da constante anual do cooperado.
                if cesta is not None:
                    vt = (pp.merge(cesta, on=["ID_COOPERADO", "CD_PROCEDIMENTO"],
                                   how="inner", suffixes=("", "_c")))
                    if len(vt):
                        vt = (vt.assign(v=vt["n_solicitacoes"] * vt["preco_mediano"])
                              .groupby("ID_COOPERADO")["v"].sum()
                              .rename("valor_cesta").reset_index())
                        ev = ev.merge(vt, on="ID_COOPERADO", how="left")
                ev["janela"] = k
                evolucao.append(ev)

    todas = pd.concat(registros, ignore_index=True)
    por_janela_cooperado = pd.concat(indices, ignore_index=True)
    custo_por_janela = (pd.concat(evolucao, ignore_index=True) if evolucao
                        else pd.DataFrame(columns=["ID_COOPERADO", "custo",
                                                   "excedente_reais", "janela"]))
    if len(custo_por_janela) and k_por_cooperado is not None:
        # excedente_tri = Σ n_tri × preço  −  consultas_tri × Σ (alvo × preço)
        #
        # SEM CLIP. Trimestre em que ele ficou abaixo da referência do ano dá
        # negativo, e é isso que faz a soma dos quatro fechar EXATAMENTE com o
        # excedente do ano: os dois lados são lineares em itens e consultas, e
        # clipar por trimestre quebraria a identidade. O negativo também é
        # leitura: naquele trimestre ele pediu menos do que a referência previa.
        cj = custo_por_janela.merge(k_por_cooperado, on="ID_COOPERADO", how="left")
        cj = cj.merge(por_janela_cooperado[["ID_COOPERADO", "janela",
                                            "consultas_totais"]],
                      on=["ID_COOPERADO", "janela"], how="left")
        cj["valor_cesta"] = cj.get("valor_cesta", 0.0)
        cj["excedente_reais"] = (cj["valor_cesta"].fillna(0.0)
                                 - cj["consultas_totais"].fillna(0.0)
                                 * cj["k_referencia"].fillna(0.0))
        # quem não tem cesta (nenhum par sinalizado no ano) não tem excedente a
        # distribuir: zero é a resposta certa, e não um negativo vindo do K
        # ausente na junção
        cj.loc[cj["k_referencia"].isna(), "excedente_reais"] = 0.0
        custo_por_janela = cj
    por_procedimento = (
        todas.groupby(["ID_COOPERADO", "CD_PROCEDIMENTO"])
        .agg(n_janelas_avaliaveis=("janela", "nunique"),
             n_janelas_sinalizado=("sinalizado", "sum"))
        .reset_index()
    )
    por_procedimento["persistencia"] = (por_procedimento["n_janelas_sinalizado"]
                                        / por_procedimento["n_janelas_avaliaveis"])
    por_procedimento["reportavel"] = (por_procedimento["n_janelas_avaliaveis"]
                                      >= min_janelas_avaliaveis)
    desc = fato.drop_duplicates("CD_PROCEDIMENTO")[["CD_PROCEDIMENTO", "DS_PROCEDIMENTO"]]
    por_procedimento = (por_procedimento.merge(desc, on="CD_PROCEDIMENTO", how="left")
                        .sort_values(["persistencia", "n_janelas_avaliaveis"],
                                     ascending=False))

    reportaveis = por_procedimento[por_procedimento["reportavel"]]
    por_cooperado = (
        reportaveis.groupby("ID_COOPERADO")
        .agg(procs_reportaveis=("CD_PROCEDIMENTO", "nunique"),
             procs_persistencia_1=("persistencia", lambda s: int((s == 1.0).sum())),
             procs_persistencia_075=("persistencia", lambda s: int((s >= 0.75).sum())))
        .sort_values(["procs_persistencia_1", "procs_persistencia_075"], ascending=False)
        .reset_index()
    )
    return {"por_janela": todas,
            "por_janela_cooperado": por_janela_cooperado,
            # uma linha por (cooperado, janela): custo valorado e excedente em
            # R$ do trimestre. Vazio quando `precos` não foi passado.
            "custo_por_janela": custo_por_janela,
            "por_procedimento": por_procedimento, "por_cooperado": por_cooperado,
            "base": carimbo_base(incluir_ps)}


def custo_mensal(fato, janela_ini, janela_fim, precos, area=None,
                 cooperado=None, incluir_ps=config.INCLUIR_PS_DEFAULT):
    """O custo das solicitações MÊS A MÊS, ao mesmo preço da janela inteira.

    É a série trimestral vista de perto, e por construção soma-se a ela: o custo
    do trimestre é Σ solicitações × preço mediano da JANELA (constante entre as
    fatias, ver `persistencia_temporal`), e solicitação é aditiva sobre os meses.
    Os três meses de um trimestre somam o trimestre na casa do centavo, sem que
    nada seja medido duas vezes — e é por isso que o preço tem de continuar sendo
    o da janela: preço por mês faria uma barra maior poder ser reajuste de tabela
    em vez de mais solicitação.

    ── o que NÃO desce ao mês ──────────────────────────────────────────────────
    O EXCEDENTE. Ele é a diferença entre o que foi solicitado e o que a
    referência do período previa para as CONSULTAS do período, e a unidade de
    apuração é o trimestre (config.JANELA_MINIMA, e a persistência inteira é
    construída sobre ela). Excedente mensal seria uma medida que a metodologia
    não fez, com um denominador de um mês por trás — exatamente o que o piso de
    volume existe para impedir (rigor-estatistico §2).

    Mês sem nenhuma solicitação com preço apurado sai com `custo` nulo, nunca
    zero: zero é afirmação sobre o custo, ausência de preço não é.

    `area` e `cooperado` são recortes independentes e combináveis: a tela de
    Área passa a primeira, o dossiê passa o segundo, e o cálculo é o mesmo.

    Devolve uma linha por mês do calendário coberto pela janela, na ordem do
    tempo: `mes` ('2025-05'), `custo`, `itens`, `itens_com_preco`, `consultas`.
    """
    f = fato[(fato["DATA_REQUISICAO"] >= janela_ini)
             & (fato["DATA_REQUISICAO"] <= janela_fim)]
    if area is not None:
        f = f[f["AREA_ATUACAO"] == area]
    # O RECORTE POR COOPERADO é o mesmo cálculo com outro sujeito, e é por isso
    # que ele entra aqui em vez de virar uma segunda função: a identidade que
    # faz os meses somarem o trimestre não depende de quem está em cena, só de
    # o preço ser o da janela. Dois motores dariam duas chances de divergir.
    if cooperado is not None:
        f = f[f["ID_COOPERADO"] == cooperado]
    f = filtrar_ps(f, incluir_ps)
    vazio = pd.DataFrame(columns=["mes", "custo", "itens", "itens_com_preco",
                                  "consultas"])
    if not len(f):
        return vazio

    consultas = f.groupby("PERIODO_REQUISICAO")["ID_CONSULTA"].nunique().rename("consultas")
    itens = f.groupby("PERIODO_REQUISICAO")["QT_EFETIVO"].sum().rename("itens")

    custo = pd.Series(dtype=float, name="custo")
    com_preco = pd.Series(dtype=float, name="itens_com_preco")
    if precos is not None and len(precos):
        pp = (f.groupby(["PERIODO_REQUISICAO", "CD_PROCEDIMENTO"])["QT_EFETIVO"]
              .sum().reset_index()
              .merge(precos[["CD_PROCEDIMENTO", "preco_mediano"]],
                     on="CD_PROCEDIMENTO", how="left"))
        pp = pp[pp["preco_mediano"].notna()]
        if len(pp):
            pp = pp.assign(valor=pp["QT_EFETIVO"] * pp["preco_mediano"])
            custo = pp.groupby("PERIODO_REQUISICAO")["valor"].sum().rename("custo")
            com_preco = (pp.groupby("PERIODO_REQUISICAO")["QT_EFETIVO"].sum()
                         .rename("itens_com_preco"))

    out = (pd.concat([consultas, itens, custo, com_preco], axis=1)
           .rename_axis("mes").reset_index().sort_values("mes"))
    return out.reset_index(drop=True)

def composicao_da_carteira(fato, perfil, janela_ini, janela_fim, area,
                           cooperado=None, incluir_ps=config.INCLUIR_PS_DEFAULT,
                           faixas=config.FAIXAS_ETARIAS):
    """Composição etária dos beneficiários atendidos na janela.

    Sem `cooperado`, descreve a ÁREA inteira; com ele, a carteira de um. As duas
    saem da MESMA função e da mesma janela porque a leitura é a comparação entre
    elas, e duas implementações divergiriam no dia em que alguém mexesse numa só.

    ── o que este número é, e o que ele não é ─────────────────────────────────
    É FATOR DE CONTEXTO, não medida de desempenho (METODOLOGIA §7.3). Carteira
    mais velha eleva a frequência ESPERADA de rastreio, e é isso que a comparação
    com a área permite perguntar antes de concluir. Ele não entra em cálculo
    nenhum: nenhuma taxa, nenhum excedente e nenhuma norma leem esta saída.

    O que ele explicitamente NÃO autoriza é distribuir custo por faixa. Para
    isso seria preciso a idade do beneficiário na DATA de cada solicitação, e
    ratear o excedente pela composição da carteira produziria um número inventado
    com aparência de medida — sobre um médico.

    ── denominador ───────────────────────────────────────────────────────────
    BENEFICIÁRIO DISTINTO, não solicitação: a pergunta é "quem ele atende", e
    contar por solicitação daria peso maior a quem pede mais exames, que é
    justamente a variável sob investigação (rigor §10, razão de totais).

    A cobertura é apurada e devolvida: a idade vem das contas e não alcança todo
    mundo. As frações são sobre os COBERTOS, e a tela declara quantos são.

    Retorna: dict com n_beneficiarios, n_com_idade, cobertura, idade_mediana e
    faixas (rótulo, n, fracao). None quando não há beneficiário na janela.
    """
    f = fato[(fato["DATA_REQUISICAO"] >= janela_ini)
             & (fato["DATA_REQUISICAO"] <= janela_fim)]
    f = f[f["AREA_ATUACAO"] == area]
    f = filtrar_ps(f, incluir_ps)
    if cooperado is not None:
        f = f[f["ID_COOPERADO"] == cooperado]
    ids = f["ID_BENEFICIARIO"].unique()
    if not len(ids):
        return None

    idades = (pd.DataFrame({"ID_BENEFICIARIO": ids})
              .merge(perfil, on="ID_BENEFICIARIO", how="left")["idade"])
    com = idades.dropna()
    n, n_com = int(len(ids)), int(len(com))
    linhas = []
    for lo, hi, rotulo in faixas:
        na_faixa = int(((com >= lo) & (com <= hi)).sum())
        linhas.append({"rotulo": rotulo, "de": lo, "ate": hi, "n": na_faixa,
                       "fracao": (na_faixa / n_com) if n_com else None})
    return {
        "n_beneficiarios": n,
        "n_com_idade": n_com,
        "cobertura": (n_com / n) if n else 0.0,
        "idade_mediana": float(com.median()) if n_com else None,
        "faixas": linhas,
    }


def solicitacoes_por_faixa(fato, perfil, janela_ini, janela_fim, area, cd,
                           cooperado, incluir_ps=config.INCLUIR_PS_DEFAULT,
                           faixas=config.FAIXAS_ETARIAS):
    """Quantas solicitações DESTE exame o cooperado fez em cada faixa etária, e
    como a área reparte as dela.

    ── por que a contagem viaja com a fatia ──────────────────────────────────
    Porque contagem de indivíduo não tem contrapartida no grupo: a área tem 63
    cooperados, e "281 dele contra 1.108 da área" compararia um médico com uma
    especialidade inteira. O que compara é a REPARTIÇÃO — 44% das solicitações
    dele contra 28% das da área na mesma faixa —, e o léxico não publica número
    de indivíduo sem referência ao lado (princípio 6).

    ── atribuição, não rateio ────────────────────────────────────────────────
    Cada solicitação carrega o beneficiário, e cada beneficiário carrega a idade
    (dim_beneficiarios, cobertura plena). A faixa sai da idade de quem recebeu o
    exame, uma a uma. Nada é distribuído proporcionalmente à composição da
    carteira, que produziria um número inventado com aparência de medida.

    NÃO ENTRA EM CÁLCULO. É lente: diz para quem ele pede, e a comparação com a
    área diz se a repartição dele destoa. Nenhuma taxa, norma ou excedente lê
    esta saída.

    Retorna: dict com total, total_area e faixas (rótulo, n, fracao,
    fracao_area). None quando o par não tem solicitação na janela.
    """
    f = fato[(fato["DATA_REQUISICAO"] >= janela_ini)
             & (fato["DATA_REQUISICAO"] <= janela_fim)]
    f = filtrar_ps(f[f["AREA_ATUACAO"] == area], incluir_ps)
    f = f[f["CD_PROCEDIMENTO"] == cd]
    if not len(f):
        return None
    f = f.merge(perfil[["ID_BENEFICIARIO", "idade"]], on="ID_BENEFICIARIO",
                how="left")

    def _por_faixa(df):
        idades = df["idade"].to_numpy(dtype="float64")
        qt = df["QT_EFETIVO"].to_numpy(dtype="float64")
        return [float(qt[(idades >= lo) & (idades <= hi)].sum())
                for lo, hi, _ in faixas]

    # `cooperado` aceita UM id ou uma COLEÇÃO. No painel do dossiê é o médico
    # contra a área; no painel do exame na área é o RECORTE em cena contra a
    # área inteira, que é a mesma leitura com o sujeito trocado — e quando o
    # recorte é a área toda, as duas barras coincidem e a comparação some
    # sozinha, sem caso especial.
    dele = f[f["ID_COOPERADO"] == cooperado if isinstance(cooperado, str)
             else f["ID_COOPERADO"].isin(list(cooperado))]
    if not len(dele):
        return None
    n_dele, n_area = _por_faixa(dele), _por_faixa(f)
    total, total_area = sum(n_dele), sum(n_area)
    if not total:
        return None
    return {
        "total": total, "total_area": total_area,
        "faixas": [
            {"rotulo": rot, "n": n,
             "fracao": (n / total) if total else None,
             "fracao_area": (a / total_area) if total_area else None}
            for (_, _, rot), n, a in zip(faixas, n_dele, n_area)],
    }


def concentracao_por_beneficiario(fato, janela_ini, janela_fim, piso, n_minimo,
                                  area=None, q_alto=config.Q_ALTO_CONCENTRACAO, min_pacientes=config.MIN_PACIENTES_CONCENTRACAO,
                                  frac_top=config.FRAC_TOP_CONCENTRACAO,
                                  incluir_ps=config.INCLUIR_PS_DEFAULT):
    """Como os itens de cada procedimento se distribuem entre os pacientes do cooperado.

    Método:
        O objeto é a DISTRIBUIÇÃO dos itens entre pacientes, não "excedente por
        paciente", que exigiria atribuir a pacientes específicos um agregado que
        não pertence a nenhum deles. A decomposição usada:

            taxa = pct_carteira × itens_por_paciente_media × (carteira / consultas)

        A identidade multiplicativa FECHA com a média (auditável: os fatores
        reconstroem a taxa). A mediana de itens/paciente acompanha como coluna de
        leitura robusta, cada estatística no seu papel, nunca trocadas.

        Duas margens, comparadas com os pares elegíveis da área que solicitam o
        procedimento (quantil q_alto como corte de "alto"):
          extensiva = pct_carteira (fração da carteira que recebe o exame);
          intensiva = itens por paciente recebedor (mediana).
        Leitura (coluna categórica): referência dos pares fraca (< n_minimo
        solicitantes elegíveis) = "referência insuficiente" (precede todas ,
        estatística de grupo minúsculo não sustenta leitura); n_pacientes_proc <
        min_pacientes = "pouco volume"; extensiva alta = "protocolo carimbado";
        intensiva alta = "case-mix a investigar" (a defesa do médico); ambas =
        "material (extensiva+intensiva)"; nenhuma = "sem padrão distinto".

        Guardrails: janela ANUAL, fatiar por trimestre derruba n_pacientes_proc
        para um dígito e a métrica vira anedota; a dimensão temporal é da
        persistência, a dimensão paciente é desta. Carteiras têm tamanhos muito
        diferentes (pct sobre 40 pacientes ≠ pct sobre 2.000): n_pacientes_proc e
        n_pacientes_carteira viajam como colunas obrigatórias ao lado de qualquer
        percentual. Contexto, não cálculo: nada aqui altera excedente/sinalização.

    Parâmetros:
        fato: fato_solicitacoes (uma linha por item solicitado).
        janela_ini, janela_fim: janela pela DATA_REQUISICAO (recomendada: anual).
        piso: piso de consultas POR ANO, escalado pela janela, elegibilidade.
        n_minimo: mínimo de solicitantes elegíveis para a referência de pares
            ser sólida (flag referencia_solida).
        area: se informada, restringe a essa área de atuação.
        q_alto: quantil dos pares que define margem "alta" (parâmetro do analista).
        min_pacientes: mínimo de pacientes para a leitura não ser "pouco volume"
            (parâmetro do analista).
        frac_top: fração de pacientes do share de concentração (0.10 = top 10%).
        incluir_ps: False (default do config) EXCLUI episódios de PS (doc §5.6) ,
            mesma base da análise que gerou os pares; a proveniência é ecoada na
            coluna 'base' de cada linha.

    Retorna: DataFrame (cooperado × procedimento) com as duas margens, share_top,
    referências dos pares, ns obrigatórios, leitura_concentracao e base.
    """
    f = fato[(fato["DATA_REQUISICAO"] >= janela_ini) & (fato["DATA_REQUISICAO"] <= janela_fim)]
    if area is not None:
        f = f[f["AREA_ATUACAO"] == area]
    f = filtrar_ps(f, incluir_ps)
    dias = (pd.Timestamp(janela_fim) - pd.Timestamp(janela_ini)).days + 1
    piso_jan = max(1, round(piso * dias / 365))

    base_coop = (
        f.groupby("ID_COOPERADO")
        .agg(consultas_totais=("ID_CONSULTA", "nunique"),
             n_pacientes_carteira=("ID_BENEFICIARIO", "nunique"),
             elegivel_norma=("elegivel_norma", "first"))
        .reset_index()
    )
    # referência de pares = quem FORMA a norma (piso E classificação), coerente com norma_por_area
    base_coop["elegivel"] = ((base_coop["consultas_totais"] >= piso_jan)
                             & base_coop["elegivel_norma"].astype(bool))
    area_map = f.drop_duplicates("ID_COOPERADO")[["ID_COOPERADO", "AREA_ATUACAO"]]

    # itens por (cooperado, procedimento, paciente)
    #
    # OCASIÕES ao lado dos ITENS (ago/2026): itens soma QT_EFETIVO e empata "5
    # unidades num pedido" com "5 pedidos em 5 datas" — clinicamente o oposto.
    # Ocasião é consulta distinta (ID_CONSULTA), que desde ago/2026 é atendimento
    # inferido por intervalo e não mais "o dia". O INTERVALO entre a primeira e a
    # última solicitação divide pelo número de repetições: 5 pedidos em 12 meses é
    # acompanhamento, 5 em 6 semanas é outra conversa, e a contagem não separa os dois.
    ipp = (f.groupby(["ID_COOPERADO", "CD_PROCEDIMENTO", "ID_BENEFICIARIO"])
           .agg(itens=("QT_EFETIVO", "sum"),
                ocasioes=("ID_CONSULTA", "nunique"),
                _ini=("TS_REQUISICAO", "min"),
                _fim=("TS_REQUISICAO", "max"))
           .reset_index())
    _vaos = (ipp["ocasioes"] - 1).clip(lower=1)
    ipp["intervalo_dias"] = np.where(
        ipp["ocasioes"] > 1,
        (ipp["_fim"] - ipp["_ini"]).dt.total_seconds() / 86400 / _vaos,
        np.nan)
    ipp = ipp.drop(columns=["_ini", "_fim"])

    conc = (
        ipp.groupby(["ID_COOPERADO", "CD_PROCEDIMENTO"])
        .agg(n_pacientes_proc=("itens", "size"),
             itens_total=("itens", "sum"),
             itens_por_paciente_media=("itens", "mean"),
             itens_por_paciente_mediana=("itens", "median"),
             ocasioes_por_paciente_mediana=("ocasioes", "median"),
             n_pacientes_repetem=("ocasioes", lambda s: int((s >= 2).sum())),
             intervalo_mediano_dias=("intervalo_dias", "median"))
        .reset_index()
    )

    # share do top frac_top de pacientes (vetorizado: posição dentro do grupo ordenado)
    ipp = ipp.sort_values("itens", ascending=False)
    grp = ipp.groupby(["ID_COOPERADO", "CD_PROCEDIMENTO"])
    ipp["_pos"] = grp.cumcount()
    ipp["_k"] = np.ceil(frac_top * grp["itens"].transform("size")).clip(lower=1)
    itens_top = (ipp[ipp["_pos"] < ipp["_k"]]
                 .groupby(["ID_COOPERADO", "CD_PROCEDIMENTO"])["itens"].sum()
                 .rename("itens_top").reset_index())
    conc = conc.merge(itens_top, on=["ID_COOPERADO", "CD_PROCEDIMENTO"], how="left")
    conc["share_top"] = conc["itens_top"] / conc["itens_total"]

    conc = conc.merge(base_coop, on="ID_COOPERADO").merge(area_map, on="ID_COOPERADO")
    conc["pct_carteira"] = conc["n_pacientes_proc"] / conc["n_pacientes_carteira"]
    # fração dos pacientes do procedimento que receberam o exame mais de uma vez.
    # Média de ocasiões esconde o caso de um paciente com 40 pedidos entre 80 com
    # um só; a fração que repete é robusta a esse desenho.
    conc["pct_pacientes_repetem"] = (conc["n_pacientes_repetem"]
                                     / conc["n_pacientes_proc"])

    # referência dos pares: solicitantes elegíveis do procedimento na área
    eleg = conc[conc["elegivel"]]
    # medianas numa passada nativa; os três quantis de q_alto noutra. A versão
    # anterior chamava uma lambda por grupo para cada quantil.
    gref = eleg.groupby(["AREA_ATUACAO", "CD_PROCEDIMENTO"])
    _med = gref.agg(
        n_solicitantes_ref=("ID_COOPERADO", "nunique"),
        pct_carteira_mediana_pares=("pct_carteira", "median"),
        intensidade_mediana_pares=("itens_por_paciente_mediana", "median"),
        share_top_mediana_pares=("share_top", "median"),
        intervalo_mediano_pares=("intervalo_mediano_dias", "median"),
        repeticao_mediana_pares=("ocasioes_por_paciente_mediana", "median"),
        pct_repetem_mediana_pares=("pct_pacientes_repetem", "median"))
    _alt = (gref[["pct_carteira", "itens_por_paciente_mediana",
                  "ocasioes_por_paciente_mediana"]].quantile(q_alto)
            .rename(columns={"pct_carteira": "pct_carteira_alto_pares",
                             "itens_por_paciente_mediana": "intensidade_alto_pares",
                             "ocasioes_por_paciente_mediana": "repeticao_alta_pares"}))
    ref = _med.join(_alt).reset_index()
    conc = conc.merge(ref, on=["AREA_ATUACAO", "CD_PROCEDIMENTO"], how="left")
    conc["referencia_solida"] = conc["n_solicitantes_ref"] >= n_minimo

    # comparações sobre dtypes anuláveis produzem máscara 'boolean' (NA quando o
    # par não tem referência) -> converter para bool puro, NA conta como False
    extensiva_alta = (conc["pct_carteira"] > conc["pct_carteira_alto_pares"]) \
        .fillna(False).to_numpy(dtype=bool)
    intensiva_alta = (conc["itens_por_paciente_mediana"] > conc["intensidade_alto_pares"]) \
        .fillna(False).to_numpy(dtype=bool)
    # referência fraca não sustenta leitura: precede todas as categorias
    ref_fraca = (~conc["referencia_solida"]).fillna(True).to_numpy(dtype=bool)
    conc["leitura_concentracao"] = np.select(
        [ref_fraca,
         (conc["n_pacientes_proc"] < min_pacientes).to_numpy(dtype=bool),
         extensiva_alta & intensiva_alta,
         extensiva_alta,
         intensiva_alta],
        ["referência insuficiente", "pouco volume", "material (extensiva+intensiva)",
         "protocolo carimbado", "case-mix a investigar"],
        default="sem padrão distinto",
    )

    desc = fato.drop_duplicates("CD_PROCEDIMENTO")[["CD_PROCEDIMENTO", "DS_PROCEDIMENTO"]]
    conc = conc.merge(desc, on="CD_PROCEDIMENTO", how="left")
    conc["base"] = carimbo_base(incluir_ps)   # proveniência por linha, como os ns obrigatórios
    return conc


def pacientes_do_procedimento(fato, cooperado, cd_procedimento, janela_ini, janela_fim,
                              limiar=config.LIMIAR_CONCENTRACAO_PACIENTE,
                              incluir_ps=config.INCLUIR_PS_DEFAULT):
    """Os pacientes que mais concentram UM procedimento de UM cooperado.

    Método:
        Descreve a distribuição observada — quantas ocasiões, que fração das
        solicitações do exame, com que intervalo. NÃO atribui excedente a
        paciente: excedente é a diferença entre a frequência do cooperado e a
        referência do grupo sobre a prática INTEIRA, e não pertence a nenhum
        paciente em particular (mesma razão declarada em
        concentracao_por_beneficiario). "Este paciente responde por 18% das
        solicitações" é fato; "por 18% do excedente" seria invenção.

        A identidade que sai daqui é o ID_BENEFICIARIO do mapa
        (`beneficiario_N`), nunca o hash de origem — que não sai do
        dim_beneficiarios. Nenhum dado clínico ou demográfico acompanha.

    Parâmetros:
        fato: fato_solicitacoes.
        cooperado, cd_procedimento: o par em cena.
        janela_ini, janela_fim: janela pela DATA_REQUISICAO.
        limiar: participação a partir da qual um paciente é listado. Lista por
            LIMIAR e não por "os N maiores": com top-N sempre há uma lista, mesmo
            quando ninguém concentra nada, e cinco linhas de 1% lidas em sequência
            sugerem um achado que não existe. Por limiar, ausência de concentração
            produz lista vazia — que é a resposta certa.
        incluir_ps: default do config.

    Retorna: dict com linhas (topo), resto, e os totais do par. None se o par
    não existe na janela.
    """
    # `cooperado` aceita UM id ou uma COLEÇÃO deles: o painel do dossiê pergunta
    # por um par (cooperado, exame) e o painel do exame na área pergunta pelo
    # mesmo exame entre os cooperados em cena. Mesma conta, dois recortes.
    quem = (fato["ID_COOPERADO"] == cooperado if isinstance(cooperado, str)
            else fato["ID_COOPERADO"].isin(list(cooperado)))
    f = fato[(fato["DATA_REQUISICAO"] >= janela_ini) & (fato["DATA_REQUISICAO"] <= janela_fim)
             & quem & (fato["CD_PROCEDIMENTO"] == cd_procedimento)]
    f = filtrar_ps(f, incluir_ps)
    if not len(f):
        return None

    por_pac = (f.groupby("ID_BENEFICIARIO")
               .agg(ocasioes=("ID_CONSULTA", "nunique"),
                    itens=("QT_EFETIVO", "sum"),
                    _ini=("TS_REQUISICAO", "min"),
                    _fim=("TS_REQUISICAO", "max"))
               .reset_index())
    vaos = (por_pac["ocasioes"] - 1).clip(lower=1)
    por_pac["intervalo_dias"] = np.where(
        por_pac["ocasioes"] > 1,
        (por_pac["_fim"] - por_pac["_ini"]).dt.total_seconds() / 86400 / vaos,
        np.nan)
    por_pac = por_pac.drop(columns=["_ini", "_fim"])

    total_itens = float(por_pac["itens"].sum())
    por_pac["pct_do_procedimento"] = por_pac["itens"] / total_itens
    # ordem: quem mais concentra primeiro; empate resolvido por ocasiões, para a
    # lista não trocar de ordem entre execuções (mesma janela, mesmo resultado)
    por_pac = por_pac.sort_values(["itens", "ocasioes", "ID_BENEFICIARIO"],
                                  ascending=[False, False, True])

    destacados = por_pac[por_pac["pct_do_procedimento"] > limiar]
    # REPETIÇÃO, da mesma varredura: quantos voltaram e com que intervalo. Sai
    # daqui, e não de uma segunda função, porque é a mesma tabela por paciente
    # que já foi montada — e duas varreduras é como os dois números passam a
    # divergir de filtro no dia em que alguém mexer numa só.
    repetem = por_pac[por_pac["ocasioes"] > 1]
    return {
        "linhas": destacados.to_dict("records"),
        "pct_repetem": (float(len(repetem)) / len(por_pac)) if len(por_pac) else None,
        "n_repetem": int(len(repetem)),
        "itens_por_paciente": (total_itens / len(por_pac)) if len(por_pac) else None,
        "intervalo_mediano_dias": (float(repetem["intervalo_dias"].median())
                                   if len(repetem) else None),
        "pct_destacados": float(destacados["pct_do_procedimento"].sum()),
        "maior_pct": float(por_pac["pct_do_procedimento"].max()) if len(por_pac) else 0.0,
        "limiar": float(limiar),
        "n_pacientes": int(len(por_pac)),
        "itens_total": total_itens,
        "base": carimbo_base(incluir_ps),
    }


def autorreferencia_por_procedimento(fato, contas, janela_ini, janela_fim, area=None,
                                     incluir_ps=config.INCLUIR_PS_DEFAULT):
    """Autorreferência por (cooperado, procedimento), com a cobertura ao lado.

    Método:
        Mesmo cruzamento do agregado em pipeline_execucao (item da solicitação
        contra a conta, por NR_SEQ_REQUISICAO + código), só que sem colapsar o
        procedimento. A PREMISSA continua a mesma e continua não verificada:
        itens sem conta localizada se autorreferem como os observados.

        A diferença é de escala e é ela que exige portão: o cruzamento acha 31%
        dos itens no agregado, mas a mediana por (cooperado, procedimento) cai
        para 11%, e sobre 11% a taxa salta entre 0% e 100%. Por isso
        `apresentavel` viaja na saída, governado por MIN_ITENS_AUTORREF_PROC e
        MIN_COBERTURA_AUTORREF_PROC — indicador investigativo, nunca flag, e
        nunca exibido sem a cobertura.

    Retorna: DataFrame (cooperado × procedimento) com taxa_autorref, cobertura,
    itens, itens_com_conta e apresentavel.
    """
    f = fato[(fato["DATA_REQUISICAO"] >= janela_ini) & (fato["DATA_REQUISICAO"] <= janela_fim)]
    if area is not None:
        f = f[f["AREA_ATUACAO"] == area]
    f = filtrar_ps(f, incluir_ps)
    c = contas[(contas["DATA_EXECUCAO"] >= janela_ini) & (contas["DATA_EXECUCAO"] <= janela_fim)]

    # Sem lambda em groupby: a coluna booleana nasce vetorizada e o .any() é a
    # agregação nativa. Com lambda esta função levava 20s — tempo de request, não
    # de motor. Mesma conta, ~40x mais rápida.
    c = c.assign(_auto=(c["SOLIC_IGUAL_EXEC"] == "S"))
    cont_item = (
        c.groupby(["NR_SEQ_REQUISICAO", "CODIGO"])["_auto"].any()
        .rename("autoexec").reset_index()
        .rename(columns={"CODIGO": "CD_PROCEDIMENTO"})
    )
    rc = f.merge(cont_item, on=["NR_SEQ_REQUISICAO", "CD_PROCEDIMENTO"], how="left")
    # NaN = item sem conta localizada; separar "tem conta" de "se autorreferiu"
    # deixa as duas contas serem soma simples, e a taxa sai da razão entre elas
    rc = rc.assign(_com_conta=rc["autoexec"].notna(),
                   _auto=rc["autoexec"].eq(True))   # NaN -> False, sem downcast
    out = (
        rc.groupby(["ID_COOPERADO", "CD_PROCEDIMENTO"])
        .agg(itens=("_com_conta", "size"),
             itens_com_conta=("_com_conta", "sum"),
             _autos=("_auto", "sum"))
        .reset_index()
    )
    out["taxa_autorref"] = (out["_autos"] / out["itens_com_conta"]).where(
        out["itens_com_conta"] > 0)
    out = out.drop(columns=["_autos"])
    out["cobertura"] = out["itens_com_conta"] / out["itens"]
    out["apresentavel"] = ((out["itens_com_conta"] >= config.MIN_ITENS_AUTORREF_PROC)
                           & (out["cobertura"] >= config.MIN_COBERTURA_AUTORREF_PROC))
    out["base"] = carimbo_base(incluir_ps)
    return out


def controlador_confiabilidade(fato, pares, janela_ini, janela_fim, seed,
                               nivel_confianca=config.NIVEL_CONFIANCA_DEFAULT, n_bootstrap=config.N_BOOTSTRAP,
                               min_pacientes_proc=config.MIN_PACIENTES_BOOTSTRAP, area=None,
                               incluir_ps=config.INCLUIR_PS_DEFAULT):
    """Faixa de incerteza do excedente por bootstrap com cluster de PACIENTE.

    Método:
        Para cada par (cooperado, procedimento), reamostra-se COM REPOSIÇÃO os
        pacientes da carteira INTEIRA do cooperado na janela, incluindo os que
        têm zero itens do procedimento. Cada paciente sorteado traz todas as suas
        consultas e itens; a taxa da reamostra é razão de totais (soma de itens ÷
        soma de consultas dos sorteados). Assim as margens extensiva e intensiva
        variam juntas, e a correlação de itens dentro de consulta e de consultas
        dentro de paciente (painéis, monitoramento seriado) é preservada ,
        reamostrar itens ou consultas soltas estreitaria o intervalo falsamente.

        excedente da reamostra = max(0, taxa_b − alvo) × consultas reais do
        cooperado (volume real fixo; a incerteza medida é a da taxa).
        O piso reportado é o quantil (1 − nivel_confianca) da distribuição
        bootstrap: "com nivel_confianca de confiança, o excedente é PELO MENOS Y".

        PREMISSAS E APROXIMAÇÕES (declaradas):
        - A norma/alvo é tratada como régua FIXA da análise, a incerteza
          reportada é a do cooperado, não a dos pares (o n mínimo do peer group
          já protege contra normas frágeis).
        - Intervalo percentílico, sem correção BCa, aproximação padrão.
        - O piso é POR PAR, sem correção de multiplicidade, o papel é ordenação
          conservadora, não teste de hipótese; a seleção já é filtrada pela
          persistência.
        - O piso em R$ herda a quarentena do preço derivado (não reportável).
        - Portão: menos de min_pacientes_proc pacientes recebendo o procedimento
          => "intervalo não calculável" (flag), nunca um número frágil.
        - seed é OBRIGATÓRIA: mesmo dado + mesmos parâmetros => mesmo número
          (auditabilidade). Piso, estimativa central e n viajam SEMPRE juntos.
        - As mesmas reamostras são reutilizadas entre os procedimentos de um
          mesmo cooperado: os pisos dele compartilham o ruído amostral ,
          comparáveis entre si por construção, não independentes.

    Parâmetros:
        fato: fato_solicitacoes (uma linha por item solicitado).
        pares: DataFrame com ID_COOPERADO, CD_PROCEDIMENTO e alvo_valor (o nível
            numérico contra o qual o excedente é medido, ex.: mediana da área).
        janela_ini, janela_fim: janela pela DATA_REQUISICAO (a MESMA da análise
            que gerou os pares e o alvo).
        seed: semente do gerador (obrigatória, reprodutibilidade).
        nivel_confianca: confiança do piso (0.90 => piso = quantil 10%).
        n_bootstrap: número de reamostras.
        min_pacientes_proc: mínimo de pacientes recebedores para calcular.
        area: se informada, restringe a essa área de atuação.
        incluir_ps: DEVE espelhar a análise que gerou pares e alvo (default do
            config = eletiva), bootstrap noutra base quebra a comparação com o alvo.

    Retorna: DataFrame por par com excedente_central, excedente_piso, calculavel,
    n_pacientes_carteira (clusters), n_pacientes_proc e os parâmetros ecoados
    (incluindo o carimbo 'base').
    """
    f = fato[(fato["DATA_REQUISICAO"] >= janela_ini) & (fato["DATA_REQUISICAO"] <= janela_fim)]
    if area is not None:
        f = f[f["AREA_ATUACAO"] == area]
    f = filtrar_ps(f, incluir_ps)
    rng = np.random.default_rng(seed)
    out = []
    for coop, pares_c in pares.groupby("ID_COOPERADO", sort=True):
        fc = f[f["ID_COOPERADO"] == coop]
        cons_pac = fc.groupby("ID_BENEFICIARIO")["ID_CONSULTA"].nunique()
        pacientes = cons_pac.index
        n_consultas_pac = cons_pac.to_numpy(dtype=float)
        n_pac = len(pacientes)
        consultas_reais = float(fc["ID_CONSULTA"].nunique())
        # mesmas reamostras para todos os procedimentos do cooperado
        idx = rng.integers(0, n_pac, size=(n_bootstrap, n_pac))
        denominadores = n_consultas_pac[idx].sum(axis=1)
        for _, par in pares_c.sort_values("CD_PROCEDIMENTO").iterrows():
            alvo = float(par["alvo_valor"])
            itens = (fc[fc["CD_PROCEDIMENTO"] == par["CD_PROCEDIMENTO"]]
                     .groupby("ID_BENEFICIARIO")["QT_EFETIVO"].sum())
            n_recebem = int((itens > 0).sum())
            itens_pac = itens.reindex(pacientes).fillna(0).to_numpy(dtype=float)
            taxa_real = itens_pac.sum() / consultas_reais
            central = max(0.0, taxa_real - alvo) * consultas_reais
            registro = {"ID_COOPERADO": coop, "CD_PROCEDIMENTO": par["CD_PROCEDIMENTO"],
                        "excedente_central": central, "n_pacientes_carteira": n_pac,
                        "n_pacientes_proc": n_recebem,
                        "nivel_confianca": nivel_confianca, "seed": seed,
                        "base": carimbo_base(incluir_ps)}
            if n_recebem < min_pacientes_proc:
                registro.update(calculavel=False, excedente_piso=np.nan)
            else:
                taxas_b = itens_pac[idx].sum(axis=1) / denominadores
                exc_b = np.clip(taxas_b - alvo, 0, None) * consultas_reais
                registro.update(calculavel=True,
                                excedente_piso=float(np.quantile(exc_b, 1 - nivel_confianca)))
            out.append(registro)
    return pd.DataFrame(out)


def montar_exclusao_por_par(classificacao, fato, regras=config.EXCLUSOES_SUBPERFIL):
    """Constrói o conjunto de exclusão por par (Mov 5): tuplas
    (ID_COOPERADO, área, CD_PROCEDIMENTO) fora da FORMAÇÃO da norma.

    Método:
        Portadores de sub-perfil não formam a norma dos pares (área, procedimento)
        onde o teste de distorção mostrou movimento de mediana acima do limiar
        (config.LIMIAR_DISTORCAO_EXCLUSAO); seguem MEDIDOS contra ela. Cada regra
        é (flag de sub-perfil, área onde a exclusão vale, regex da cesta de
        procedimentos sobre DS_PROCEDIMENTO), a cesta é resolvida em códigos no
        próprio fato, então procedimentos novos com a mesma descrição entram
        automaticamente. Regras ativas e limiar: config (PROVISÓRIO, o teste de
        distorção re-roda na homologação e confirma/ajusta a ativação).

    Parâmetros:
        classificacao: dim da classificação (ID_COOPERADO + flags sub_*).
        fato: fato_solicitacoes (fonte de CD_PROCEDIMENTO × DS_PROCEDIMENTO).
        regras: iterável de (flag, área, regex), default config.EXCLUSOES_SUBPERFIL.

    Retorna: set de tuplas (ID_COOPERADO, área, CD_PROCEDIMENTO).
    """
    desc = (fato.drop_duplicates("CD_PROCEDIMENTO")
            .set_index("CD_PROCEDIMENTO")["DS_PROCEDIMENTO"])
    exclusoes = set()
    for flag, area, regex in regras:
        cds = set(desc[desc.str.contains(regex, case=False, na=False)].index)
        portadores = set(classificacao.loc[classificacao[flag].astype(bool), "ID_COOPERADO"])
        exclusoes |= {(c, area, cd) for c in portadores for cd in cds}
    return exclusoes
