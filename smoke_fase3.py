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
from utils import pipeline as pl


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

    gin = tabela[tabela["AREA_ATUACAO"] == "Ginecologia"].iloc[0]
    n_norma = int(gin["n_na_norma"])
    mediana = float(gin["mediana"])
    n_total = int(gin["n_total_area"])

    print("GINECOLOGIA — conferência contra o gabarito do notebook (config.SMOKE_*)")
    checks = [
        ("elegíveis que formam a norma", n_norma, config.SMOKE_N_NA_NORMA_GINECOLOGIA),
        ("mediana da área", round(mediana, 2), config.SMOKE_MEDIANA_GINECOLOGIA),
        ("cooperados na área (medidos)", n_total, config.SMOKE_N_TOTAL_GINECOLOGIA),
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
    for coop, esperado in config.SMOKE_SINALIZADOS_ESPERADOS.items():
        checks.append((f"{coop}: procedimentos sinalizados",
                       int(n_por_coop.get(coop, 0)), esperado))
    for coop in config.SMOKE_NAO_SINALIZADOS_ESPERADOS:
        checks.append((f"{coop}: procedimentos sinalizados (deve ser zero)",
                       int(n_por_coop.get(coop, 0)), 0))

    falhas = 0
    for rotulo, obtido, esperado in checks:
        ok = obtido == esperado
        falhas += not ok
        print(f"  [{'ok' if ok else 'FALHA'}] {rotulo}: {obtido}"
              + ("" if ok else f"   (esperado {esperado})"))

    print(f"\n  taxa mediana Ginecologia = {mediana:.6f} itens por consulta inferida")
    print(f"  IQR (p75−p25) = {gin['p75'] - gin['p25']:.4f}  |  "
          f"p75 = {gin['p75']:.4f}  |  p90 (gatilho) = {gin['p90']:.4f}")
    print(f"  pares sinalizados (3 portões): {len(conf):,} | "
          f"cooperados com ao menos 1: {conf['ID_COOPERADO'].nunique()}")
    print("─" * 78)
    print("RESULTADO:", "REPRODUZ O NOTEBOOK" if not falhas
          else f"{falhas} divergência(s)")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
