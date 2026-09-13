"""smoke_fase3 — prova de que os motores migrados reproduzem o notebook.

Roda o pipeline canônico (app/utils/pipeline.py) sobre o fato dos marts, com os
MESMOS argumentos do teste de aceitação registrado em config (SMOKE_*), e
confere contra o gabarito. Python puro: sem Streamlit, sem API, sem UI.

Uso:
    source ~/.venvs/global-env/bin/activate
    python smoke_fase3.py
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path[:0] = [str(RAIZ), str(RAIZ / "app")]

import pandas as pd

import config
from utils import dados, pipeline as pl


def main() -> int:
    janela_ini, janela_fim = config.SMOKE_JANELA
    gatilho = config.GATILHO_DEFAULT
    alvo = config.ALVO_DEFAULT
    incluir_ps = config.INCLUIR_PS_DEFAULT
    piso = config.PISO_CONSULTAS_ANO["_default"]
    n_minimo = config.N_MINIMO_PEER_GROUP

    fato = pd.read_parquet(config.CAMINHO_FATO_SOLICITACOES)
    classificacao = pd.read_csv(config.CAMINHO_DIM_CLASSIFICACAO)
    exclusoes = pl.montar_exclusao_por_par(classificacao, fato)

    print("─" * 78)
    print(f"FATO: {len(fato):,} linhas | "
          f"{fato['ID_COOPERADO'].nunique()} cooperados | "
          f"{fato['DATA_REQUISICAO'].min().date()} a {fato['DATA_REQUISICAO'].max().date()}")
    print(f"ARGUMENTOS  janela={janela_ini}..{janela_fim}  gatilho={gatilho}  "
          f"alvo={alvo}  incluir_ps={incluir_ps}  piso={piso}/ano  n_minimo={n_minimo}")
    print(f"EXCLUSÃO POR PAR (Mov 5): {len(exclusoes):,} tuplas")

    r = pl.pipeline(fato, janela_ini, janela_fim, piso=piso, n_minimo=n_minimo,
                    area=None, gatilho=gatilho, alvo=alvo, incluir_ps=incluir_ps,
                    exclusoes_por_par=exclusoes)

    print(f"BASE: {r['base']}")
    print(f"CLASSIFICAÇÃO: {r['classificacao']}")
    print(f"piso aplicado na janela: {r['piso_aplicado']} consultas "
          f"({r['janela_dias']} dias)")
    print("─" * 78)

    norma = r["norma"].copy()
    pos = r["posicao"]
    # quantos cooperados a área tem no total (medidos), além dos que FORMAM a norma
    totais = (pos.groupby("AREA_ATUACAO")["ID_COOPERADO"].nunique()
                 .rename("n_total_area").reset_index())
    tabela = norma.merge(totais, on="AREA_ATUACAO", how="left")
    tabela["gatilho_usado"] = pl._gatilho_efetivo(
        tabela["n_na_norma"], gatilho, config.N_MINIMO_P90, config.N_MINIMO_P75)

    print("NORMA POR ÁREA (mediana/percentis entre os que FORMAM a norma)")
    print(tabela[["AREA_ATUACAO", "n_total_area", "n_na_norma", "p25", "mediana",
                  "p75", "p90", "gatilho_usado"]]
          .to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print("─" * 78)

    gin = tabela[tabela["AREA_ATUACAO"] == config.SMOKE_AREA_REFERENCIA].iloc[0]
    n_norma = int(gin["n_na_norma"])
    mediana = float(gin["mediana"])
    n_total = int(gin["n_total_area"])

    print(f"{config.SMOKE_AREA_REFERENCIA.upper()} — conferência contra o gabarito "
          "(config.SMOKE_*)")
    checks = [
        ("elegíveis que formam a norma", n_norma, config.SMOKE_N_NA_NORMA_AREA),
        ("mediana da área", round(mediana, 2), config.SMOKE_MEDIANA_AREA),
        ("cooperados na área (medidos)", n_total, config.SMOKE_N_TOTAL_AREA),
    ]

    # lado agregado (notebook §9, bloco "ANO"): quantos são avaliáveis e o topo por razão
    avaliaveis = pos[pos["avaliavel"]]
    checks.append(("avaliáveis (todas as áreas)", int(len(avaliaveis)),
                   config.SMOKE_N_AVALIAVEIS))
    checks.append(("topo por razão vs mediana",
                   tuple(avaliaveis.head(3)["ID_COOPERADO"]), config.SMOKE_TOPO_RAZAO))

    # as 4 previsões do notebook §13.4: pares (cooperado, procedimento) que passam
    # os TRÊS portões — avaliavel & apresentavel & sinalizado (Lei 1: filtro único)
    conf = pl.filtrar_sinalizados(r["posicao_proc"])
    n_por_coop = conf.groupby("ID_COOPERADO")["CD_PROCEDIMENTO"].nunique()
    conf_area = conf[conf["nivel_referencia"] == config.NIVEL_REFERENCIA_AREA]
    n_area = conf_area.groupby("ID_COOPERADO")["CD_PROCEDIMENTO"].nunique()
    for coop, esperado in config.SMOKE_SINALIZADOS_ESPERADOS.items():
        checks.append((f"{coop}: procedimentos sinalizados (área + especialidade)",
                       int(n_por_coop.get(coop, 0)), esperado))
    for coop, esperado in config.SMOKE_SINALIZADOS_AREA_ESPERADOS.items():
        checks.append((f"{coop}: procedimentos sinalizados com referência da área",
                       int(n_area.get(coop, 0)), esperado))
    for coop in config.SMOKE_NAO_SINALIZADOS_ESPERADOS:
        checks.append((f"{coop}: sinalizados com referência da área (deve ser zero)",
                       int(n_area.get(coop, 0)), 0))
    checks.append(("classificação pendente: nenhum par medido, em nível nenhum",
                   int((conf["AREA_ATUACAO"] == config.AREA_INDEFINIDA).sum()), 0))

    falhas = 0
    for rotulo, obtido, esperado in checks:
        ok = obtido == esperado
        falhas += not ok
        print(f"  [{'ok' if ok else 'FALHA'}] {rotulo}: {obtido}"
              + ("" if ok else f"   (esperado {esperado})"))

    print(f"\n  taxa mediana {config.SMOKE_AREA_REFERENCIA} = {mediana:.6f} "
          "itens por consulta inferida")
    print(f"  IQR (p75−p25) = {gin['p75'] - gin['p25']:.4f}  |  "
          f"p75 = {gin['p75']:.4f}  |  p90 (gatilho) = {gin['p90']:.4f}")
    print(f"  pares sinalizados (3 portões): {len(conf):,} | "
          f"cooperados com ao menos 1: {conf['ID_COOPERADO'].nunique()}")
    print("─" * 78)
    falhas += conferir_excedente(fato, exclusoes, janela_ini, janela_fim,
                                 piso, n_minimo, gatilho, alvo, incluir_ps)
    print("─" * 78)
    print("RESULTADO:", "REPRODUZ O NOTEBOOK" if not falhas
          else f"{falhas} divergência(s)")
    return 1 if falhas else 0


def conferir_excedente(fato, exclusoes, janela_ini, janela_fim, piso, n_minimo,
                       gatilho, alvo, incluir_ps) -> int:
    """A regra do excedente (METODOLOGIA §5.4.1) contra o GABARITO calculado
    sem o motor (unimed_natal/verificacao_excedente_trimestral.ipynb), par a
    par e fatia a fatia, mais as identidades que valem por construção."""
    print("EXCEDENTE POR FATIA, RÉGUA ANUAL (13/set/2026) — gabarito do notebook")
    gab = pd.read_parquet(config.CAMINHO_GABARITO_EXCEDENTE)
    r = pl.pipeline_execucao(
        fato, dados.carregar_contas(), janela_ini, janela_fim, piso=piso,
        n_minimo=n_minimo, piso_execucoes=config.PISO_EXECUCOES_ANO,
        q_confundidor=config.Q_CONFUNDIDOR,
        mapa_executantes=dados.carregar_executantes(), area=None,
        gatilho=gatilho, alvo=alvo, incluir_ps=incluir_ps,
        exclusoes_por_par=exclusoes)
    areas = r["posicao_proc_rs"][["ID_COOPERADO", "CD_PROCEDIMENTO", "AREA_ATUACAO"]]
    fat = r["excedente_por_fatia_rs"].merge(areas, on=["ID_COOPERADO", "CD_PROCEDIMENTO"])
    fat = fat[fat["AREA_ATUACAO"].isin(config.SMOKE_AREAS_GABARITO)]
    fat = fat.merge(r["posicao_proc_rs"][["ID_COOPERADO", "CD_PROCEDIMENTO", "nivel_referencia"]],
                    on=["ID_COOPERADO", "CD_PROCEDIMENTO"])
    m = gab.merge(fat, on=["AREA_ATUACAO", "ID_COOPERADO", "CD_PROCEDIMENTO", "fatia"],
                  how="outer", suffixes=("_gab", "_motor"), indicator=True)
    nivel_ok = bool((m["nivel_referencia_gab"].astype(str)
                     == m["nivel_referencia_motor"].astype(str)).all())
    dif_itens = float((m["excedente_itens_gab"] - m["excedente_itens_motor"]).abs().max())
    dif_reais = float((m["excedente_reais_gab"] - m["excedente_reais_motor"]).abs().max())

    sinal = r["sinal"].set_index(["ID_COOPERADO", "CD_PROCEDIMENTO"])
    soma_par = (r["excedente_por_fatia_rs"]
                .groupby(["ID_COOPERADO", "CD_PROCEDIMENTO"])["excedente_reais"].sum())
    dif_par = float((sinal["excedente_reais"] - soma_par.reindex(sinal.index)).abs().max())
    soma_coop = r["sinal"].groupby("ID_COOPERADO")["excedente_reais"].sum()
    resumo = r["resumo_coop"].set_index("ID_COOPERADO")["excedente_reais_total"]
    dif_coop = float((resumo - soma_coop.reindex(resumo.index)).abs().max())

    pers = pl.persistencia_temporal(
        fato, janela_ini, janela_fim, piso, n_minimo, gatilho, alvo,
        incluir_ps=incluir_ps, exclusoes_por_par=exclusoes, precos=r["preco"])
    pp = pers["por_procedimento"]
    grade = pers["por_janela"]
    positivas = grade.groupby(["ID_COOPERADO", "CD_PROCEDIMENTO"])["sinalizado"].sum()
    pp_i = pp.set_index(["ID_COOPERADO", "CD_PROCEDIMENTO"])
    persist_ok = bool(((pp_i["persistencia"] == 1.0)
                       == (positivas.reindex(pp_i.index) == pers["n_fatias"])).all())
    cj = pers["custo_por_janela"]
    soma_tri = cj.groupby("ID_COOPERADO")["excedente_reais"].sum()
    dif_tri = float((soma_tri - soma_coop.reindex(soma_tri.index).fillna(0.0)).abs().max())

    checks = [
        ("gabarito: mesmas linhas (área, cooperado, procedimento, fatia)",
         (int((m["_merge"] == "both").sum()), int((m["_merge"] != "both").sum())),
         (len(gab), 0)),
        ("gabarito: nível da referência (área / especialidade) igual em todo par", nivel_ok, True),
        ("gabarito: excedente em itens, maior diferença <= 0,01", dif_itens <= 0.01, True),
        ("gabarito: excedente em R$, maior diferença <= 0,01", dif_reais <= 0.01, True),
        ("identidade: soma das fatias == par", dif_par <= 0.01, True),
        ("identidade: soma dos pares == cooperado", dif_coop <= 0.01, True),
        ("identidade: soma dos trimestres == cooperado (sem resto na janela)",
         dif_tri <= 0.01 and pers["resto"] is None, True),
        ("nenhuma fatia negativa",
         int((r["excedente_por_fatia"]["excedente_itens"] < 0).sum()), 0),
        ("persistente <=> todas as fatias completas positivas", persist_ok, True),
    ]
    falhas = 0
    for rotulo, obtido, esperado in checks:
        ok = obtido == esperado
        falhas += not ok
        print(f"  [{'ok' if ok else 'FALHA'}] {rotulo}: {obtido}"
              + ("" if ok else f"   (esperado {esperado})"))
    # AJUSTE DE CONFIANÇA (doc §8): invariantes do motor com um nível escolhido
    r9 = pl.pipeline(fato, janela_ini, janela_fim, piso, n_minimo, None, gatilho, alvo,
                     incluir_ps=incluir_ps, exclusoes_por_par=exclusoes, confianca=0.90)
    s0 = pl.filtrar_sinalizados(r["posicao_proc"]).set_index(["ID_COOPERADO", "CD_PROCEDIMENTO"])
    s9 = pl.filtrar_sinalizados(r9["posicao_proc"]).set_index(["ID_COOPERADO", "CD_PROCEDIMENTO"])
    cons = s9["ajuste_confianca"] == "conservador"
    med = s9["ajuste_confianca"] == "medido"
    checks9 = [
        ("ajuste: a cesta não muda com a confiança", set(s0.index) == set(s9.index), True),
        ("ajuste: todo par sinalizado é conservador ou medido", bool((cons | med).all()), True),
        ("ajuste: conservador <= medido",
         bool((s9.loc[cons, "excedente_itens"] <= s9.loc[cons, "excedente_itens_medido"] + 1e-9).all()), True),
        ("ajuste: sem ajuste == medido, e só abaixo do mínimo de pacientes",
         bool((s9.loc[med, "excedente_itens"] == s9.loc[med, "excedente_itens_medido"]).all()
              and (s9.loc[med, "n_pacientes_proc"] < config.MIN_PACIENTES_AJUSTE_CONFIANCA).all()), True),
        ("ajuste: o medido guardado é o excedente sem ajuste",
         float((s9["excedente_itens_medido"] - s0["excedente_itens"].reindex(s9.index)).abs().max()) < 1e-9, True),
        ("ajuste: mesma semente, mesmo número",
         float((pl.pipeline(fato, janela_ini, janela_fim, piso, n_minimo, None, gatilho, alvo,
                            incluir_ps=incluir_ps, exclusoes_por_par=exclusoes, confianca=0.90)
                ["posicao_proc"].set_index(["ID_COOPERADO", "CD_PROCEDIMENTO"])["excedente_itens"]
                .reindex(s9.index) - s9["excedente_itens"]).abs().max()) < 1e-9, True),
    ]
    for rotulo, obtido, esperado in checks9:
        ok = obtido == esperado
        falhas += not ok
        print(f"  [{'ok' if ok else 'FALHA'}] {rotulo}: {obtido}"
              + ("" if ok else f"   (esperado {esperado})"))
    print(f"  excedente em itens, todas as áreas: medido {s0['excedente_itens'].sum():,.0f} · "
          f"com 90% de confiança {s9['excedente_itens'].sum():,.0f} · "
          f"{int(med.sum())} pares sem ajuste")
    for area in config.SMOKE_AREAS_GABARITO:
        g_a = gab[gab["AREA_ATUACAO"] == area]
        esp = g_a.loc[g_a["nivel_referencia"] == config.NIVEL_REFERENCIA_ESPECIALIDADE,
                      "excedente_reais"].sum()
        print(f"  {area}: R$ {g_a['excedente_reais'].sum():,.2f} "
              f"(R$ {esp:,.2f} com {config.ROTULO_REFERENCIA_ESPECIALIDADE})")
    return falhas


if __name__ == "__main__":
    raise SystemExit(main())
