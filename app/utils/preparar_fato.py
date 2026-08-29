"""
preparar_fato — o 6º motor: ingestão determinística das bases brutas.

Transforma os CSVs brutos (requisições + contas) no FATO analítico e nas
dimensões de identidade, aplicando as regras de qualidade de dado do config e
produzindo um RELATÓRIO de carga — NADA é tratado em silêncio.

É a única etapa persistida (marts em Parquet): tudo o mais (taxa, norma,
posição, excedente, persistência, concentração, confiança) é função de
(fato, contas, janela, parâmetros) e roda em runtime nos motores de pipeline.

Origem: unimed_natal/calculos_iniciais.ipynb (células de ingestão), migrado
fielmente — mesma ordem de ID_COOPERADO (ordem de aparição), mesmas correções
de descrição, mesma regra de QT.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# Contratos de leitura dos CSVs brutos (dtypes e encoding verificados na exploração)
# ─────────────────────────────────────────────────────────────────────────────

CONTAS_DTYPE = {
    "NR_SEQ_REQUISICAO": "Int64",
    "NUMERO_GUIA": "Int64",
    "REGIMEATENDIMENTO": "category",
    "CARATERATENDIMENTO": "category",
    "TIPOGUIA": "category",
    "IDENTIFICADOR_BENEFICIARIO": "string",
    "PLANO": "category",
    "SEXO": "category",
    "IDADE": "Int16",
    "IDENTIFICADOR_SOLICITANTE": "string",
    "CBO_SOLICITANTE": "category",
    "IDENTIFICADOR_EXECUTANTE": "string",
    "TIPO_EXECUTANTE": "category",
    "SOLIC_IGUAL_EXEC": "category",
    "CODIGO": "string",
    "DESCRICAO": "string",
    "CATEGORIA": "category",
    "VALORTOTAL": "Float32",
    "VALORPAGO": "Float32",
    "VALORGLOSADO": "Float32",
    "QUANTIDADEEXECUTADA": "string",   # vírgula decimal no bruto -> convertida na carga
    "QUANTIDADEPAGA": "string",
    "QUANTIDADEGLOSADA": "string",
}

SOLICITACOES_DTYPE = {
    "NR_SEQ_REQUISICAO": "Int64",
    "STATUS_REQUISICAO": "category",
    "IDENTIFICADOR_BENEFICIARIO": "string",
    "SEXO": "category",
    "IDADE": "Int16",
    "PLANO": "category",
    "IDENTIFICADOR_SOLICITANTE": "string",
    "COOPERADO": "category",
    "DS_CBO": "category",
    "CARATER_ATENDIMENTO": "category",
    "DS_REGIME_ATENDIMENTO": "category",
    "CD_PROCEDIMENTO": "string",
    "DS_PROCEDIMENTO": "string",
    "CD_CID": "category",
    "DS_CID": "category",
    "QT_SOLICITADO": "Int64",  # QT bruto chega a 431.649 — tipos menores estouram
    "QT_LIBERADA": "Float32",
    "ESTAGIO_ITEM": "category",
    "QT_EXECUTADA": "Float32",
}

# Descrições truncadas/ambíguas corrigidas por código (verificadas na exploração)
CODIGO_DESC_FIX_CONTAS = {
    "40901203": "Us - Órgãos Superficiais (Tireóide Ou Escroto Ou Pênis Ou Crânio)",
    "40901300": "Us - Transvaginal (Útero, Ovário, Anexos E Vagina)",
    "40901319": "Us - Transvaginal Para Controle De Ovulação (3 Ou Mais Exames)",
}

CD_TO_DS_FIX_REQUISICOES = {
    "40601099": "Ato de coleta de PAAF de órgãos ou estruturas superficiais com deslocamento do patologista",
    "40601072": "Ato de coleta de PAAF de órgãos ou estruturas superficiais sem deslocamento do patologista",
    "31303196": "Cauterização química, ou eletrocauterização, ou criocauterização de lesões de colo uterino (por sessão)",
    "31301037": "Cauterização química, ou eletrocauterização, ou criocauterização de lesões da vulva (por grupo de até 5 lesões)",
    "31302130": "Cauterização química, ou eletrocauterização, ou criocauterização de lesões da vagina (por grupo de até 5 lesões)",
    "40808203": "Marcação pré-cirúrgica por nódulo - máximo de 3 nódulos por mama, por US (não inclui exame de imagem)",
    "40808190": "Marcação pré-cirúrgica por nódulo - máximo de 3 nódulos por mama, por estereotaxia (não inclui exame de imagem)",
    "40808211": "Marcação pré-cirúrgica por nódulo - máximo de 3 nódulos por mama, por RM (não inclui exame de imagem)",
    "40403343": "Pesquisa de anticorpos séricos irregulares antieritrocitários",
    "40403351": "Pesquisa de anticorpos séricos irregulares antieritrocitários - gel teste",
    "40403408": "Prova de compatibilidade pré-transfusional completa",
    "40403416": "Prova de compatibilidade pré-transfusional completa - gel teste",
    "40808238": "Punção ou biópsia mamária percutânea por agulha fina orientada por US (não inclui o exame de base)",
    "40808220": "Punção ou biópsia mamária percutânea por agulha fina orientada por estereotaxia (não inclui o exame de base)",
    "98101340": "Pacote de Genética Sequenciamento bidirecional pelo método de Sanger ou Sequenciamento de Nova Geração dos éxons do gene KAL1 DUT110",
    "98101404": "Pacote de Genética Sequenciamento bidirecional pelo método de Sanger ou Sequenciamento de Nova Geração dos éxons dos genes BRCA1/2 TP53 ATM CHEK2 PALB2 RAD51C RAD51D NBN MLH1 MSH2 MSH6 PMS2 STK11 EPCAM APC MUTYH MITF BAP1 CDKN2A CDK4 PTEN CDH1 BMPR1A SMAD4 GREM1 POLD1 POLE BARD1 e BRIP1 DUT110",
    "98100637": "Pacote de Genética Sequenciamento de Nova Geração de toda região codificadora de BRCA1 e BRCA2 DUT110",
    "98101528": "Pacote de Sequenciamento de Nova Geração de toda região codificadora de BRCA1 e BRCA2 com 100%",
}

COLUNAS_FATO = [
    "ID_COOPERADO", "AREA_ATUACAO", "ID_BENEFICIARIO",
    "NR_SEQ_REQUISICAO", "DATA_REQUISICAO", "TS_REQUISICAO",
    "PERIODO_REQUISICAO", "ID_CONSULTA",
    "CD_PROCEDIMENTO", "DS_PROCEDIMENTO", "CARATER_ATENDIMENTO",
    "QT_SOLICITADO", "QT_EFETIVO", "EPISODIO_PS", "elegivel_norma",
]


# ─────────────────────────────────────────────────────────────────────────────
# Cargas
# ─────────────────────────────────────────────────────────────────────────────

def carregar_contas(caminho: str) -> pd.DataFrame:
    """Lê a base de contas (lado executante) e converte quantidades (vírgula decimal)."""
    contas = pd.read_csv(
        caminho, sep=";", encoding="latin1", quotechar='"',
        dtype=CONTAS_DTYPE, parse_dates=["DATA_EXECUCAO", "DATA_PAGAMENTO"],
        low_memory=False,
    )
    for col in ["QUANTIDADEEXECUTADA", "QUANTIDADEPAGA", "QUANTIDADEGLOSADA"]:
        contas[col] = contas[col].str.replace(",", ".", regex=False).astype("Float32")
    contas["DESCRICAO"] = np.where(
        contas["CODIGO"].isin(CODIGO_DESC_FIX_CONTAS),
        contas["CODIGO"].map(CODIGO_DESC_FIX_CONTAS),
        contas["DESCRICAO"],
    )
    return contas


def carregar_solicitacoes(caminho: str, coluna_data: str) -> pd.DataFrame:
    """Lê a base de requisições (lado solicitante) e deriva o eixo temporal."""
    solicitacoes = pd.read_csv(
        caminho, sep=";", encoding="latin1", quotechar='"',
        dtype=SOLICITACOES_DTYPE, parse_dates=[coluna_data], dayfirst=True,
        low_memory=False,
    )
    # TS_REQUISICAO guarda o INSTANTE (a origem traz "DD/MM/AAAA HH:MM:SS");
    # DATA_REQUISICAO segue normalizada porque é o eixo temporal de toda a
    # análise — janela, trimestre e período mensal comparam datas, não horas.
    # Até ago/2026 o horário era descartado aqui, e sem ele a consulta inferida
    # não tinha como separar atendimentos dentro do mesmo dia.
    solicitacoes["TS_REQUISICAO"] = solicitacoes[coluna_data]
    solicitacoes["DATA_REQUISICAO"] = solicitacoes[coluna_data].dt.normalize()
    solicitacoes["PERIODO_REQUISICAO"] = (
        solicitacoes["DATA_REQUISICAO"].dt.to_period("M").astype(str)
    )
    solicitacoes["DS_PROCEDIMENTO"] = np.where(
        solicitacoes["CD_PROCEDIMENTO"].isin(CD_TO_DS_FIX_REQUISICOES),
        solicitacoes["CD_PROCEDIMENTO"].map(CD_TO_DS_FIX_REQUISICOES),
        solicitacoes["DS_PROCEDIMENTO"],
    )
    return solicitacoes


# ─────────────────────────────────────────────────────────────────────────────
# O 6º motor
# ─────────────────────────────────────────────────────────────────────────────

def preparar_fato(caminho_requisicoes: str, caminho_contas: str, config,
                  classificacao: pd.DataFrame, dir_marts: str | None = None):
    """Ingestão determinística: CSVs brutos -> (fato, dims, relatorio).

    Método:
        1. Carrega as duas bases com os contratos de dtype/encoding verificados.
        2. Filtra solicitações de cooperados (COOPERADO == 'S').
        3. Consulta inferida: solicitações do mesmo cooperado, para o mesmo
           beneficiário, dentro da janela de config.JANELA_CONSULTA_MINUTOS
           entre lançamentos, com o dia como fronteira externa (doc §3.2).
        4. Episódio-PS (doc §5.6): consulta com caráter de urgência
           (config.STRING_URGENCIA) em QUALQUER item OU contendo o pacote de
           urgência (config.CD_PACOTE_URGENCIA) recebe EPISODIO_PS=True em TODOS
           os itens — marca de consulta, marcada UMA vez, na origem. É ela que
           permite aos motores excluir a consulta-PS inteira (numerador e
           denominador juntos) sob incluir_ps=False.
        5. Identidade: ID_COOPERADO por ordem de aparição; mapa executante ->
           cooperado no sentido limpo (cada executante pertence a 1 solicitante;
           um cooperado pode ter 2+ cadastros de executante) com assert de sanidade.
        6. Regra de QT (config.QT_MAX_PLAUSIVEL) com GUARDA-CORPO: quantidade
           acima do teto só é rebaixada a 1 quando NÃO é corroborada por
           liberação/execução — se o sistema liberou OU executou quantidade
           também alta, o número é real (não é typo) e usa-se o maior volume
           confirmado. A linha nunca é deletada; o QT bruto viaja no fato
           (rastreabilidade da regra por linha).
        7. Classificação v1.0: merge da classificacao por ID_COOPERADO —
           especialidade vira AREA_ATUACAO (o peer group) e elegivel_norma
           governa QUEM FORMA a norma (não quem é medido). Cobertura de 100%
           dos cooperados é verificada por assert (merge incompleto = parar).
        Todo tratamento aparece no relatório — nada é silencioso.

    Parâmetros:
        caminho_requisicoes, caminho_contas: CSVs brutos.
        config: módulo de configuração (fonte única dos valores de regra:
            QT_MAX_PLAUSIVEL, COLUNA_DATA_SOLICITACAO, CLASSIFICACAO_VERSAO).
        classificacao: DataFrame da classificação (classificacao_v1.csv) com
            ID_COOPERADO, especialidade e elegivel_norma.
        dir_marts: se informado, grava fato/dims/contas em Parquet nesse diretório.

    Retorna: (fato, dims, relatorio)
        fato: DataFrame no contrato COLUNAS_FATO (uma linha por item solicitado).
        dims: dict com dim_cooperados, dim_executantes_cooperado e contas
              (base do lado executante, preparada para pipeline_execucao).
        relatorio: dict da carga — volumes, período, tratamentos aplicados.
    """
    contas = carregar_contas(caminho_contas)
    solicitacoes = carregar_solicitacoes(caminho_requisicoes, config.COLUNA_DATA_SOLICITACAO)

    src = solicitacoes[solicitacoes["COOPERADO"] == "S"].copy()

    # beneficiário: id sequencial por ordem de aparição, MESMA forma do
    # ID_COOPERADO. O hash de 64 caracteres é chave — colecionável entre telas
    # e exportações — e não precisa sair do mapa. O registro de preenchimento
    # da origem (config.HASH_BENEFICIARIO_NAO_IDENTIFICADO) recebe id próprio e
    # declarado, em vez de se disfarçar de paciente entre os demais.
    _benef = src["IDENTIFICADOR_BENEFICIARIO"].unique()
    dim_beneficiarios = pd.DataFrame({"IDENTIFICADOR_BENEFICIARIO": _benef})
    _seq = 0
    _ids = []
    for _h in dim_beneficiarios["IDENTIFICADOR_BENEFICIARIO"]:
        if _h == config.HASH_BENEFICIARIO_NAO_IDENTIFICADO:
            _ids.append(config.ID_BENEFICIARIO_NAO_IDENTIFICADO)
        else:
            _seq += 1
            _ids.append(f"beneficiario_{_seq}")
    dim_beneficiarios["ID_BENEFICIARIO"] = _ids
    dim_beneficiarios = dim_beneficiarios[["ID_BENEFICIARIO", "IDENTIFICADOR_BENEFICIARIO"]]
    src = src.merge(dim_beneficiarios, on="IDENTIFICADOR_BENEFICIARIO", how="left")

    # consulta inferida (denominador de todas as taxas): solicitações do mesmo
    # cooperado para o mesmo beneficiário cujos lançamentos consecutivos distam
    # no máximo config.JANELA_CONSULTA_MINUTOS. O DIA é fronteira externa —
    # sessão não atravessa a meia-noite. A calibração da janela e a ressalva
    # clínica pendente estão no config, junto da constante.
    # A ordenação vive numa CÓPIA e o resultado volta pelo índice: `src` precisa
    # manter a ordem de origem, porque ID_COOPERADO é atribuído adiante por
    # ORDEM DE APARIÇÃO e reordenar aqui remapearia todos os cooperados.
    _chave = ["IDENTIFICADOR_SOLICITANTE", "ID_BENEFICIARIO", "DATA_REQUISICAO"]
    _ord = src.sort_values(_chave + ["TS_REQUISICAO"], kind="mergesort")
    _g = _ord.groupby(_chave, sort=False)
    _intervalo = _g["TS_REQUISICAO"].diff().dt.total_seconds() / 60
    _abre = (_intervalo > config.JANELA_CONSULTA_MINUTOS) | _g.cumcount().eq(0)
    src["ID_CONSULTA"] = (_abre.cumsum() - 1).reindex(src.index)

    # episódio-PS: marcado UMA vez, na origem (fato sobre o dado, não análise).
    # Caráter de urgência em qualquer item OU pacote de urgência => a marca desce
    # a TODOS os itens da consulta — filtrá-la remove numerador e denominador
    # juntos (regra por contexto, doc §5.6; constantes do config, nunca literais).
    marca_ps = ((src["CARATER_ATENDIMENTO"] == config.STRING_URGENCIA)
                | (src["CD_PROCEDIMENTO"] == config.CD_PACOTE_URGENCIA))
    src["EPISODIO_PS"] = src["ID_CONSULTA"].map(marca_ps.groupby(src["ID_CONSULTA"]).any())

    # identidade: mapa executante -> solicitante (lado limpo do dado)
    pares_se = (
        contas[contas["SOLIC_IGUAL_EXEC"] == "S"]
        [["IDENTIFICADOR_SOLICITANTE", "IDENTIFICADOR_EXECUTANTE"]]
        .drop_duplicates()
    )
    _amb = pares_se.groupby("IDENTIFICADOR_EXECUTANTE")["IDENTIFICADOR_SOLICITANTE"].nunique()
    assert (_amb == 1).all(), "executante com mais de um solicitante — revisar dado"

    dim_cooperados = pd.DataFrame({
        "IDENTIFICADOR_SOLICITANTE": src["IDENTIFICADOR_SOLICITANTE"].unique()
    })
    dim_cooperados["ID_COOPERADO"] = [
        f"cooperado_{i + 1}" for i in range(len(dim_cooperados))
    ]
    dim_cooperados = dim_cooperados[["ID_COOPERADO", "IDENTIFICADOR_SOLICITANTE"]]

    dim_executantes = (
        pares_se.merge(dim_cooperados, on="IDENTIFICADOR_SOLICITANTE", how="inner")
        [["ID_COOPERADO", "IDENTIFICADOR_EXECUTANTE"]]
        .drop_duplicates()
    )

    src = src.merge(dim_cooperados, on="IDENTIFICADOR_SOLICITANTE", how="left")

    # regra de QT (valor do config; bruto preservado no fato)
    # GUARDA-CORPO: QT implausível só é rebaixada a 1 quando NÃO é corroborada por
    # liberação/execução. Se o sistema liberou OU executou quantidade também alta,
    # o número é real (não é typo) — usa-se o maior volume confirmado (exec/lib).
    teto = config.QT_MAX_PLAUSIVEL
    qs = src["QT_SOLICITADO"].astype("float64")            # NaN preservado
    ql = src["QT_LIBERADA"].astype("float64").fillna(0.0)
    qe = src["QT_EXECUTADA"].astype("float64").fillna(0.0)
    suspeita = qs > teto                                   # quantidade implausível
    corroborada = suspeita & ((ql > teto) | (qe > teto))
    src["QT_EFETIVO"] = np.select(
        [corroborada, suspeita],       # alto+confirmado -> maior volume real; alto+não confirmado -> 1
        [np.maximum(ql, qe), 1.0],
        default=qs,                    # dentro do plausível -> o próprio pedido
    )
    src["QT_EFETIVO"] = pd.Series(src["QT_EFETIVO"], index=src.index).fillna(1.0)
    mask_tratadas = suspeita & ~corroborada

    # classificação v1.0: especialidade -> AREA_ATUACAO (peer group);
    # elegivel_norma governa QUEM FORMA a norma (não quem é medido)
    assert set(src["ID_COOPERADO"]) <= set(classificacao["ID_COOPERADO"]), \
        "cooperado sem classificação — merge incompleto"
    src = src.merge(
        classificacao[["ID_COOPERADO", "especialidade", "elegivel_norma"]],
        on="ID_COOPERADO", how="left",
    ).rename(columns={"especialidade": "AREA_ATUACAO"})

    fato = src[COLUNAS_FATO].copy()

    # duplicatas do mesmo (requisição, procedimento) somam no numerador —
    # re-solicitações legítimas; medidas no relatório para vigilância
    dup = fato.groupby(["NR_SEQ_REQUISICAO", "CD_PROCEDIMENTO"]).size()

    relatorio = {
        "periodo_coberto": (str(fato["DATA_REQUISICAO"].min().date()),
                            str(fato["DATA_REQUISICAO"].max().date())),
        "linhas_requisicoes_total": len(solicitacoes),
        "linhas_cooperados": len(fato),
        "n_cooperados": int(fato["ID_COOPERADO"].nunique()),
        "n_consultas_inferidas": int(fato["ID_CONSULTA"].nunique()),
        "n_pacientes": int(fato["ID_BENEFICIARIO"].nunique()),
        "n_procedimentos": int(fato["CD_PROCEDIMENTO"].nunique()),
        "qt_tratadas": {
            "regra": (f"QT > {teto} não corroborada por liberação/execução -> 1 "
                      "(config.QT_MAX_PLAUSIVEL, guarda-corpo)"),
            "n_suspeitas": int(suspeita.sum()),
            "n_corroboradas_preservadas": int(corroborada.sum()),
            "n_linhas": int(mask_tratadas.sum()),
            "valores": sorted(qs[mask_tratadas].astype("int64").tolist()),
            "cooperados": sorted(src.loc[mask_tratadas, "ID_COOPERADO"].unique().tolist()),
        },
        "qt_nulos_para_1": int(qs.isna().sum()),
        "pares_req_proc_duplicados": int((dup > 1).sum()),
        "episodios_ps": {
            "regra": ("consulta com caráter urgência (STRING_URGENCIA) OU pacote "
                      "(CD_PACOTE_URGENCIA) -> EPISODIO_PS; motores excluem por "
                      "default (INCLUIR_PS_DEFAULT) — doc §5.6"),
            "n_consultas_ps": int(fato.loc[fato["EPISODIO_PS"], "ID_CONSULTA"].nunique()),
            "pct_consultas": float(fato.groupby("ID_CONSULTA")["EPISODIO_PS"].first().mean()),
            "n_itens_ps": int(fato["EPISODIO_PS"].sum()),
            "pct_itens": float(fato["EPISODIO_PS"].mean()),
        },
        "identidade": {
            "cooperados": len(dim_cooperados),
            "com_cadastro_executante": int(dim_executantes["ID_COOPERADO"].nunique()),
            "ids_executante": len(dim_executantes),
        },
        "contas": {
            "linhas": len(contas),
            "janela_execucao": (str(contas["DATA_EXECUCAO"].min().date()),
                                str(contas["DATA_EXECUCAO"].max().date())),
        },
        "areas": {
            "fonte": f"classificação {config.CLASSIFICACAO_VERSAO}",
            "n_areas": int(fato["AREA_ATUACAO"].nunique()),
            "n_elegiveis_norma": int(
                fato.drop_duplicates("ID_COOPERADO")["elegivel_norma"].sum()),
            "homologada": bool(config.CLASSIFICACAO_HOMOLOGADA),
        },
    }

    dims = {
        "dim_cooperados": dim_cooperados,
        "dim_beneficiarios": dim_beneficiarios,
        "dim_executantes_cooperado": dim_executantes,
        "contas": contas,
    }

    if dir_marts is not None:
        import os
        os.makedirs(dir_marts, exist_ok=True)
        fato.to_parquet(f"{dir_marts}/fato_solicitacoes.parquet", index=False)
        dim_cooperados.to_parquet(f"{dir_marts}/dim_cooperados.parquet", index=False)
        dim_beneficiarios.to_parquet(f"{dir_marts}/dim_beneficiarios.parquet", index=False)
        dim_executantes.to_parquet(f"{dir_marts}/dim_executantes_cooperado.parquet", index=False)
        contas.to_parquet(f"{dir_marts}/contas.parquet", index=False)
        relatorio["marts_gravados_em"] = dir_marts

    return fato, dims, relatorio


def imprimir_relatorio(relatorio: dict) -> None:
    """Relatório de carga legível — nada tratado em silêncio."""
    r = relatorio
    print(f"Período coberto (solicitação): {r['periodo_coberto'][0]} a {r['periodo_coberto'][1]}")
    print(f"Linhas: {r['linhas_requisicoes_total']:,} na base | "
          f"{r['linhas_cooperados']:,} de cooperados")
    print(f"Cooperados: {r['n_cooperados']} | consultas inferidas: "
          f"{r['n_consultas_inferidas']:,} | pacientes: {r['n_pacientes']:,} | "
          f"procedimentos: {r['n_procedimentos']}")
    qt = r["qt_tratadas"]
    print(f"Regra de QT [{qt['regra']}]: {qt['n_suspeitas']} suspeitas | "
          f"{qt['n_corroboradas_preservadas']} corroboradas (preservadas) | "
          f"{qt['n_linhas']} tratadas como 1"
          + (f" | valores: {qt['valores']}" if qt["n_linhas"] else ""))
    print(f"QT nulos -> 1: {r['qt_nulos_para_1']} | pares (req, proc) repetidos: "
          f"{r['pares_req_proc_duplicados']}")
    ps = r["episodios_ps"]
    print(f"Episódios-PS: {ps['n_consultas_ps']:,} consultas ({ps['pct_consultas']:.2%}) | "
          f"{ps['n_itens_ps']:,} itens ({ps['pct_itens']:.2%}) — norma default roda "
          f"sobre eletivas (doc §5.6)")
    ident = r["identidade"]
    print(f"Identidade: {ident['cooperados']} cooperados | "
          f"{ident['com_cadastro_executante']} com cadastro de executante "
          f"({ident['ids_executante']} IDs)")
    print(f"Contas: {r['contas']['linhas']:,} linhas | execução de "
          f"{r['contas']['janela_execucao'][0]} a {r['contas']['janela_execucao'][1]}")
    a = r["areas"]
    print(f"Áreas: {a['fonte']} ({a['n_areas']}) | elegíveis para formar norma: "
          f"{a['n_elegiveis_norma']}"
          + ("" if a["homologada"] else "  ⚠ NÃO HOMOLOGADA — validação clínica pendente"))
    if "marts_gravados_em" in r:
        print(f"Marts (Parquet) gravados em: {r['marts_gravados_em']}")


# ─────────────────────────────────────────────────────────────────────────────
# Guardas de carga contínua
# ─────────────────────────────────────────────────────────────────────────────

def teste_regressao_qt(fato, pipeline_fn, janela_ini, janela_fim, piso, n_minimo,
                       tetos=(20, 127, 1000), teto_vigente=None, limiar=None):
    """A regra de QT ainda é inócua para o ranking? Roda a cada carga nova.

    Método:
        Recalcula QT_EFETIVO sob cada teto candidato (a partir do QT_SOLICITADO
        bruto preservado no fato), roda o pipeline e compara o top-15 de
        cooperados (por razão) e o top-15 de pares (por excedente) com o teto
        vigente. Estabilidade abaixo do limiar => alarme: a regra passou a
        influenciar o resultado e precisa de recalibração antes de reportar.
        O filtro de PS é herdado do default de pipeline_fn (doc §5.6): todos os
        tetos são comparados sobre a MESMA base — a comparação segue justa.

    Parâmetros:
        fato: fato com QT_SOLICITADO (bruto) e QT_EFETIVO.
        pipeline_fn: o motor pipeline() (injetado — evita import circular).
        janela_ini, janela_fim, piso, n_minimo: como no pipeline().
        tetos: tetos candidatos a comparar.
        teto_vigente: teto de referência (default: config.QT_MAX_PLAUSIVEL do fato
            em uso — passar explicitamente).
        limiar: mínimo de estabilidade (em 15) sem alarme (config.LIMIAR_REGRESSAO_QT).

    Retorna: dict {teto: {"coop": x/15, "par": y/15}} + "alarme" (bool).
    """
    qt = fato["QT_SOLICITADO"]
    tops = {}
    for teto in sorted(set(tetos) | ({teto_vigente} if teto_vigente else set())):
        fato_v = fato.assign(
            QT_EFETIVO=qt.where(qt <= teto, 1).fillna(1).astype("int64").to_numpy())
        r = pipeline_fn(fato_v, janela_ini, janela_fim, piso, n_minimo)
        pos, pp = r["posicao"], r["posicao_proc"]
        ok = pp["avaliavel"] & pp["apresentavel"] & pp["sinalizado"]
        tops[teto] = {
            "coop": set(pos[pos["avaliavel"]].head(15)["ID_COOPERADO"]),
            "par": set(map(tuple, pp[ok].sort_values("excedente_itens", ascending=False)
                           .head(15)[["ID_COOPERADO", "CD_PROCEDIMENTO"]]
                           .itertuples(index=False))),
        }
    base = teto_vigente if teto_vigente is not None else sorted(tops)[len(tops) // 2]
    resultado, pior = {}, 15
    for teto in tops:
        if teto == base:
            continue
        est_coop = len(tops[base]["coop"] & tops[teto]["coop"])
        est_par = len(tops[base]["par"] & tops[teto]["par"])
        resultado[teto] = {"coop": est_coop, "par": est_par}
        pior = min(pior, est_coop, est_par)
    resultado["teto_vigente"] = base
    resultado["alarme"] = bool(limiar is not None and pior < limiar)
    return resultado


def revalidar_calibracoes(fato, config, bins=None):
    """As calibrações registradas continuam valendo no dado novo? SINALIZA, nunca altera.

    Método:
        Recalcula, no período inteiro do fato: (1) o funil de estabilização —
        o IQR das taxas nas faixas de volume acima do piso registrado deve
        continuar travado (compara com as faixas logo abaixo); (2) a forma —
        skew da taxa agregada e % de procedimentos (n>=10 elegíveis) com skew>1,
        que sustentam a mediana como resumo. Divergência vira sinalização para
        o analista recalibrar conscientemente — a função nunca escreve valor.
        As medições rodam na MESMA base da norma (config.INCLUIR_PS_DEFAULT,
        doc §5.6): recalibrar piso/forma numa base diferente da que a norma usa
        seria comparar réguas de conjuntos distintos.

    Retorna: dict com medições atuais e lista de 'sinalizacoes' (vazia = ok).
    """
    from scipy import stats

    # mesma base da norma: default exclui episódios de PS (guarda de carga é
    # config-driven por assinatura — o config já entra por argumento aqui)
    if not config.INCLUIR_PS_DEFAULT:
        fato = fato[~fato["EPISODIO_PS"]]

    piso = config.PISO_CONSULTAS_ANO["_default"]
    g = fato.groupby("ID_COOPERADO").agg(
        consultas=("ID_CONSULTA", "nunique"), itens=("QT_EFETIVO", "sum"))
    g["taxa"] = g["itens"] / g["consultas"]

    if bins is None:
        bins = np.array([1, 5, 10, 20, 30, 50, 75, 100, 200, 400, 800, 1600, 3200])
    faixas = pd.cut(g["consultas"], bins=bins)
    estab = g.groupby(faixas, observed=True)["taxa"].agg(
        n="count", iqr=lambda s: s.quantile(.75) - s.quantile(.25))

    acima = estab[[iv.left >= piso for iv in estab.index]]
    abaixo_validas = estab[[(iv.left < piso) and n >= 10
                            for iv, n in zip(estab.index, estab["n"])]]
    iqr_acima = float(acima["iqr"].max()) if len(acima) else np.nan

    eleg = g[g["consultas"] >= piso]
    skew_agregada = float(stats.skew(eleg["taxa"]))

    por_proc = (fato[fato["ID_COOPERADO"].isin(eleg.index)]
                .groupby(["ID_COOPERADO", "CD_PROCEDIMENTO"])["QT_EFETIVO"].sum()
                .reset_index()
                .merge(g[["consultas"]], left_on="ID_COOPERADO", right_index=True))
    por_proc["taxa"] = por_proc["QT_EFETIVO"] / por_proc["consultas"]
    skews = (por_proc.groupby("CD_PROCEDIMENTO")["taxa"]
             .agg(n="count", skew=lambda s: stats.skew(s) if len(s) >= 10 else np.nan)
             .dropna())
    pct_cauda_longa = float((skews["skew"] > 1).mean()) if len(skews) else np.nan

    sinalizacoes = []
    if len(abaixo_validas) and iqr_acima > float(abaixo_validas["iqr"].min()):
        sinalizacoes.append(
            f"funil: IQR acima do piso ({iqr_acima:.2f}) não é menor que o de faixas "
            f"abaixo — o piso {piso} pode estar descalibrado")
    if skew_agregada < 0.5:
        sinalizacoes.append(
            f"forma: skew da taxa agregada caiu para {skew_agregada:.2f} — revisar "
            "se mediana segue o resumo certo (doc §5.5)")
    if pct_cauda_longa < 0.5:
        sinalizacoes.append(
            f"forma: só {pct_cauda_longa:.0%} dos procedimentos com cauda-longa — "
            "verificação de forma por análise (doc §5.5) ganha importância")

    return {
        "piso_registrado": piso,
        "iqr_maximo_acima_do_piso": iqr_acima,
        "skew_taxa_agregada": skew_agregada,
        "pct_procedimentos_cauda_longa": pct_cauda_longa,
        "n_elegiveis": int(len(eleg)),
        "sinalizacoes": sinalizacoes,
    }
