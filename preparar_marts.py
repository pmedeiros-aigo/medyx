"""Gera os marts do app a partir dos CSVs brutos e da classificação vigente.

Uso (no diretório do app, com o global-env ativo):
    python preparar_marts.py

Lê config.CAMINHO_RAW_* e config.CAMINHO_DIM_CLASSIFICACAO (dim v2, gerada
pelo notebook unimed_natal/classificacao_cooperados.ipynb, Parte 15), roda o
6º motor (app/utils/preparar_fato.py) e grava em config.DIR_MARTS:
fato_solicitacoes.parquet, contas.parquet, dim_cooperados.parquet,
dim_beneficiarios.parquet e dim_executantes_cooperado.parquet.

A AREA_ATUACAO do fato é a area_mvp da dim (config.ESPECIALIDADES); cooperado
sem área principal recebe config.AREA_INDEFINIDA. elegivel_norma vem da dim.
"""
import pandas as pd

import config
from app.utils import preparar_fato as pf


def classificacao_para_o_fato() -> pd.DataFrame:
    dim = pd.read_csv(config.CAMINHO_DIM_CLASSIFICACAO)
    area = dim["area_mvp"].fillna(config.AREA_INDEFINIDA).replace("", config.AREA_INDEFINIDA)
    fora = set(area.unique()) - set(config.ESPECIALIDADES) - {config.AREA_INDEFINIDA}
    assert not fora, f"area_mvp fora de config.ESPECIALIDADES: {fora}"
    return pd.DataFrame({
        "ID_COOPERADO": dim["ID_COOPERADO"],
        "especialidade": area,
        "elegivel_norma": dim["elegivel_norma"].astype(bool),
    })


if __name__ == "__main__":
    _, _, relatorio = pf.preparar_fato(
        str(config.CAMINHO_RAW_REQUISICOES), str(config.CAMINHO_RAW_CONTAS), config,
        classificacao_para_o_fato(), dir_marts=str(config.DIR_MARTS),
    )
    pf.imprimir_relatorio(relatorio)
