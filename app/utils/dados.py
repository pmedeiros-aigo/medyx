"""dados, carga cacheada dos marts e chamadas cacheadas dos motores.

É a ÚNICA porta de entrada da camada de apresentação para dado e cálculo
(Lei 1: quem apresenta nunca calcula; Lei 3: a escolha do analista chega POR
ARGUMENTO, os wrappers daqui só repassam, nunca leem default do config no
meio do cálculo).

Cache: `functools.lru_cache` com chave = argumentos. O fato NÃO entra na chave
(é estático por sessão de dados, os wrappers o buscam da carga cacheada por
dentro, o que evita hashear ~1M de linhas a cada chamada). Os resultados são
compartilhados entre requisições: NÃO mutar os DataFrames devolvidos ,
`.copy()` antes de qualquer alteração.
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

import config
from utils import pipeline as pl


# ─────────────────────────────────────────────────────────────────────────────
# Cargas (marts gerados pelo notebook/preparar_fato — ver config.CAMINHO_*)
# ─────────────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def carregar_fato() -> pd.DataFrame:
    """Fato analítico: 1 linha por item solicitado, já com AREA_ATUACAO
    (classificação v1.0) e elegivel_norma."""
    return pd.read_parquet(config.CAMINHO_FATO_SOLICITACOES)


@lru_cache(maxsize=1)
def carregar_classificacao() -> pd.DataFrame:
    """Dim da classificação v1.0 (não homologada): especialidade, sub-perfis,
    confiança, alerta e elegivel_norma por cooperado."""
    return pd.read_csv(config.CAMINHO_DIM_CLASSIFICACAO)


@lru_cache(maxsize=1)
def carregar_contas() -> pd.DataFrame:
    """Base de contas (lado executante), preço derivado e confundidores."""
    return pd.read_parquet(config.CAMINHO_CONTAS)


@lru_cache(maxsize=1)
def carregar_executantes() -> pd.DataFrame:
    """Dim executante -> cooperado (2+ cadastros por cooperado possíveis)."""
    return pd.read_parquet(config.CAMINHO_DIM_EXECUTANTES)


@lru_cache(maxsize=1)
def exclusao_por_par() -> frozenset:
    """Conjunto de exclusão por par (Mov 5) montado das regras do config."""
    return frozenset(
        pl.montar_exclusao_por_par(carregar_classificacao(), carregar_fato()))


@lru_cache(maxsize=1)
def meses_disponiveis() -> tuple[str, str]:
    """(primeiro, último) mês com dado, em AAAA-MM. É o que o seletor de
    período pode oferecer: mês fora disto devolveria zero solicitações por
    FALTA DE BASE, e zero por falta de base lê igual a zero por comportamento."""
    ini, fim = janela_dados()
    return ini[:7], fim[:7]


def resolver_intervalo(ini_mes: str, fim_mes: str) -> tuple[str, str]:
    """(AAAA-MM, AAAA-MM) -> (primeiro dia do mês inicial, último dia do final).

    MESES CHEIOS de propósito. Início no meio do mês produz resto no
    fatiamento em trimestres (uma janela de 10,5 meses rendia 47 dias fora) e
    fronteiras de trimestre que ninguém consegue explicar numa reunião.
    """
    ini = pd.Timestamp(f"{ini_mes}-01")
    fim = pd.Timestamp(f"{fim_mes}-01") + pd.offsets.MonthEnd(0)
    return str(ini.date()), str(fim.date())


def meses_na_janela(janela_ini: str, janela_fim: str) -> int:
    """Duração da janela em meses cheios, para validar o mínimo e para a tela
    dizer o que está sendo analisado."""
    a, b = pd.Timestamp(janela_ini), pd.Timestamp(janela_fim)
    return (b.year - a.year) * 12 + (b.month - a.month) + 1


def janela_dados() -> tuple[str, str]:
    """(min, max) de DATA_REQUISICAO no fato, âncora das janelas da UI."""
    f = carregar_fato()
    return (str(f["DATA_REQUISICAO"].min().date()),
            str(f["DATA_REQUISICAO"].max().date()))


# ─────────────────────────────────────────────────────────────────────────────
# Motores cacheados (chave = argumentos vindos da camada de apresentação)
# ─────────────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=32)
def rodar_pipeline(janela_ini: str, janela_fim: str, piso: int, n_minimo: int,
                   area: str | None, gatilho: str, alvo: str, incluir_ps: bool):
    """pipeline() do lado da solicitação, com exclusão por par ativa."""
    return pl.pipeline(
        carregar_fato(), janela_ini, janela_fim, piso=piso, n_minimo=n_minimo,
        area=area, gatilho=gatilho, alvo=alvo, incluir_ps=incluir_ps,
        exclusoes_por_par=exclusao_por_par(),
    )


@lru_cache(maxsize=32)
def rodar_pipeline_execucao(janela_ini: str, janela_fim: str, piso: int,
                            n_minimo: int, piso_execucoes: int,
                            q_confundidor: float, area: str | None,
                            gatilho: str, alvo: str, incluir_ps: bool):
    """pipeline_execucao(): R$ derivado (quarentena) + confundidores."""
    return pl.pipeline_execucao(
        carregar_fato(), carregar_contas(), janela_ini, janela_fim,
        piso=piso, n_minimo=n_minimo, piso_execucoes=piso_execucoes,
        q_confundidor=q_confundidor, mapa_executantes=carregar_executantes(),
        area=area, gatilho=gatilho, alvo=alvo, incluir_ps=incluir_ps,
        exclusoes_por_par=exclusao_por_par(),
    )


@lru_cache(maxsize=32)
def rodar_persistencia(janelas: tuple, piso: int, n_minimo: int,
                       gatilho: str, alvo: str, area: str | None,
                       min_janelas_avaliaveis: int, incluir_ps: bool):
    """persistencia_temporal() sobre janelas disjuntas (tupla de (ini, fim))."""
    return pl.persistencia_temporal(
        carregar_fato(), list(janelas), piso=piso, n_minimo=n_minimo,
        gatilho=gatilho, alvo=alvo, area=area,
        min_janelas_avaliaveis=min_janelas_avaliaveis, incluir_ps=incluir_ps,
        exclusoes_por_par=exclusao_por_par(),
    )


@lru_cache(maxsize=32)
def rodar_pacientes_distintos(janela_ini: str, janela_fim: str, incluir_ps: bool):
    """pacientes_distintos() por cooperado na janela (descritivo do dossiê)."""
    return pl.pacientes_distintos(carregar_fato(), janela_ini, janela_fim,
                                  incluir_ps=incluir_ps)


@lru_cache(maxsize=32)
def rodar_concentracao(janela_ini: str, janela_fim: str, piso: int,
                       n_minimo: int, area: str, incluir_ps: bool):
    """concentracao_por_beneficiario() de uma área, memoizado.

    Custa ~0,8 s para uma área de 64 cooperados (9.187 pares), então roda para
    todos e não só para quem tem variação persistente. O cache é por combinação
    de parâmetros: trocar a régua recalcula, reabrir a mesma tela não.
    """
    return pl.concentracao_por_beneficiario(
        carregar_fato(), janela_ini, janela_fim, piso=piso, n_minimo=n_minimo,
        area=area, incluir_ps=incluir_ps,
    )


def posicao_na_area(posicao_area: pd.DataFrame) -> pd.Series:
    """Coluna de POSIÇÃO por cooperado, a natureza muda com a régua disponível:

    - com régua (gatilho_usado não-nulo): PERCENTIL entre os formadores da norma
      ("P94" = taxa acima de 94% dos elegíveis);
    - sem régua (grupo pequeno, gatilho degradado a nenhum): POSTO descritivo
      entre os avaliáveis ("2º de 8"), sem percentil, sem sinalização.

    A mudança de natureza fica visível no rótulo (espec funcional, regra 5).
    """
    df = posicao_area
    col = "taxa_exames_por_consulta"
    taxas_formadores = df.loc[
        df["avaliavel"] & df["elegivel_norma"].astype(bool), col
    ].to_numpy(dtype=float)
    n_avaliaveis = int(df["avaliavel"].sum())
    postos = df[col].where(df["avaliavel"]).rank(ascending=False, method="min")

    def _rotulo(linha):
        if not linha["avaliavel"]:
            return config.SEM_MEDIDA
        if pd.notna(linha["gatilho_usado"]) and len(taxas_formadores):
            pct = (taxas_formadores <= linha[col]).mean()
            return f"P{round(pct * 100):.0f}"
        return f"{int(postos[linha.name])}º de {n_avaliaveis}"

    return df.apply(_rotulo, axis=1)


# Os motivos de não formar a referência moraram aqui como texto corrido; agora
# são estruturados (código, natureza definitiva/provisória, status de revisão)
# em utils.blocos.motivos_por_cooperado — a natureza da exclusão é informação de
# tela, e a UI precisa distinguir "por desenho" de "regra provisória em revisão".


def fatiar_trimestres(janela_ini: str, janela_fim: str) -> tuple:
    """Fatia a janela em trimestres disjuntos alinhados ao mês, o fatiamento
    da persistência (config.JANELA_MINIMA é trimestral). Janela de 12 meses vira
    4 fatias, idênticas aos trimestres do notebook.

    Só devolve trimestres COMPLETOS. Um resto de fim de janela mais curto que um
    trimestre é descartado, nunca devolvido como fatia: uma "janela" de poucos
    dias entraria no denominador da persistência e produziria um 2/2 sustentado
    por um único dia de dado, anedota vestida de evidência (rigor-estatistico
    §2, disciplina do 1/1). O resto descartado é reportado por
    `resto_fora_dos_trimestres`, para que o descarte apareça na tela.
    """
    ini = pd.Timestamp(janela_ini)
    fim = pd.Timestamp(janela_fim)
    fatias = []
    while ini <= fim:
        fim_fatia = ini + pd.DateOffset(months=3) - pd.Timedelta(days=1)
        if fim_fatia > fim:          # resto incompleto: fora do fatiamento
            break
        fatias.append((str(ini.date()), str(fim_fatia.date())))
        ini = fim_fatia + pd.Timedelta(days=1)
    return tuple(fatias)


def resto_fora_dos_trimestres(janela_ini: str, janela_fim: str) -> int:
    """Dias no fim da janela que não formam um trimestre completo e ficam fora
    da persistência. Zero na janela de 12m. Nada é descartado em silêncio."""
    fatias = fatiar_trimestres(janela_ini, janela_fim)
    if not fatias:
        return (pd.Timestamp(janela_fim) - pd.Timestamp(janela_ini)).days + 1
    return (pd.Timestamp(janela_fim) - pd.Timestamp(fatias[-1][1])).days


def resolver_janela(rotulo: str) -> tuple[str, str]:
    """Rótulo de janela da UI ('3m'/'6m'/'12m') -> (ini, fim) ancorados no FIM
    da amostra. É aqui que o rótulo vira argumento do motor, o motor recebe
    datas, nunca rótulos (Lei 3)."""
    ini_dados, fim_dados = janela_dados()
    fim = pd.Timestamp(fim_dados)
    ini = max(pd.Timestamp(ini_dados),
              fim - pd.DateOffset(months=config.JANELAS_UI[rotulo])
              + pd.Timedelta(days=1))
    return str(ini.date()), str(fim.date())
