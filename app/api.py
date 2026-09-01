"""api, FastAPI servindo JSON e os estáticos da tela "Área de atuação".

Escopo desta sessão: só o que a tela de Área consome. Sem Dossiê, sem Panorama.

Contrato:
  - A API **não calcula**: cada endpoint chama o pipeline canônico
    (`utils.dados`) e entrega o resultado organizado nos BLOCOS DA TELA
    (`utils.blocos`). Nenhum número nasce aqui.
  - Todo parâmetro da análise entra por query e é ecoado de volta no bloco de
    proveniência, o que a tela mostra sempre diz sob que régua foi calculado.
  - Os defaults vêm do `config.py` e viajam marcados como `recomendado`
    (ajuste 3 do handoff: o padrão se anuncia; o desvio se avisa).

Rodar:
    source ~/.venvs/global-env/bin/activate
    fastapi dev app/api.py          # ou: uvicorn app.api:app --reload
"""
from __future__ import annotations

import re
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from functools import lru_cache
from typing import Annotated, Any

_RAIZ = Path(__file__).resolve().parent.parent
for _p in (str(_RAIZ), str(_RAIZ / "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pandas as pd  # noqa: E402
from fastapi import (Depends, FastAPI, HTTPException, Path as PathParam,  # noqa: E402
                     Query, Request)
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import config  # noqa: E402
import sessao  # noqa: E402
from utils import apresentacao as apr  # noqa: E402
from utils import blocos, cascata, dados  # noqa: E402
from utils import pipeline as pl  # noqa: E402
from utils.pipeline import filtrar_sinalizados  # noqa: E402

ESTATICOS = Path(__file__).parent / "static"

@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI):
    """Confere os marts antes de aceitar requisição. Sem isto o servidor sobe
    normalmente e só quebra na primeira consulta — ver dados.verificar_marts."""
    dados.verificar_marts()
    yield


app = FastAPI(
    title="Medyx · API da tela Área de atuação",
    description=("JSON dos blocos da tela + estáticos. Nenhum número é calculado "
                 "aqui: tudo vem do pipeline canônico (app/utils/pipeline.py)."),
    version=config.PIPELINE_VERSAO,
    lifespan=_ciclo_de_vida,
)


# ─────────────────────────────────────────────────────────────────────────────
# Parâmetros da análise — a régua, por query, em todos os endpoints
# ─────────────────────────────────────────────────────────────────────────────

class Parametros(BaseModel):
    """A escolha do analista, resolvida e validada. Vai por ARGUMENTO ao motor
    (Lei 3) e volta na proveniência de toda resposta."""
    rotulo_janela: str
    janela_ini: str
    janela_fim: str
    criterio: str          # gatilho, quem entra em revisão
    referencia: str        # alvo, contra o que a variação excedente é medida
    confianca: float
    piso: int
    n_minimo: int
    incluir_ps: bool

    @property
    def base(self) -> str:
        from utils.pipeline import carimbo_base
        return carimbo_base(self.incluir_ps)


_ORDEM_NIVEL = {"mediana": 0, "p75": 1, "p90": 2}


def obter_parametros(
    janela: Annotated[str, Query(description="Janela de análise ancorada no fim da amostra (atalho); ignorada quando ini/fim vêm preenchidos")] = config.JANELA_DEFAULT,
    ini: Annotated[str | None, Query(description="Início da janela em AAAA-MM (mês cheio). Com fim, substitui o atalho `janela`")] = None,
    fim: Annotated[str | None, Query(description="Fim da janela em AAAA-MM (mês cheio, inclusive)")] = None,
    criterio: Annotated[str, Query(description="Critério de revisão (gatilho): percentil do grupo acima do qual o caso entra em revisão")] = config.GATILHO_DEFAULT,
    referencia: Annotated[str, Query(description="Referência de adequação (alvo) contra a qual a variação excedente é medida; deve ser <= criterio")] = config.ALVO_DEFAULT,
    confianca: Annotated[float, Query(ge=0.5, lt=1.0, description="Confiança do piso da variação excedente")] = config.NIVEL_CONFIANCA_DEFAULT,
    piso: Annotated[int, Query(ge=config.LIMITES_CONTROLES["piso"]["minimo"], description="Volume mínimo para avaliação, em consultas/ano; escalado à janela pelo motor")] = config.PISO_CONSULTAS_ANO["_default"],
    n_minimo: Annotated[int, Query(ge=config.LIMITES_CONTROLES["n_minimo"]["minimo"], description="Mínimo de solicitantes elegíveis para a referência de um procedimento ser apresentável")] = config.N_MINIMO_PEER_GROUP,
    incluir_ps: Annotated[bool, Query(description="Incluir episódios de pronto-socorro; o padrão analisa a base eletiva")] = config.INCLUIR_PS_DEFAULT,
) -> Parametros:
    """Valida a régua e resolve o rótulo de janela em datas.

    A única regra estrutural imposta aqui é `referencia <= criterio`: medir todo
    mundo acima do P75 até o P75 condenaria o quartil superior por construção
    (METODOLOGIA §7.1). O motor também a exige, a validação aqui só devolve 422
    em vez de estourar um assert.
    """
    if (ini is None) != (fim is None):
        raise HTTPException(422, "janela por intervalo exige `ini` E `fim` (AAAA-MM)")
    if ini is None and janela not in config.JANELAS_UI:
        raise HTTPException(422, f"janela inválida: {janela!r}; use {list(config.JANELAS_UI)}")
    if criterio not in config.GATILHOS_UI:
        raise HTTPException(422, f"criterio inválido: {criterio!r}; use {list(config.GATILHOS_UI)}")
    if referencia not in config.ALVOS_UI:
        raise HTTPException(422, f"referencia inválida: {referencia!r}; use {list(config.ALVOS_UI)}")
    if _ORDEM_NIVEL[referencia] > _ORDEM_NIVEL[criterio]:
        raise HTTPException(
            422, f"referencia ({referencia}) deve ser <= criterio ({criterio}): "
                 "sinaliza-se no extremo e mede-se contra a referência; usar o "
                 "mesmo nível nos dois condenaria o quartil superior por construção")
    if ini is not None:
        rotulo, janela_ini, janela_fim = _janela_por_intervalo(ini, fim)
    else:
        rotulo = janela
        janela_ini, janela_fim = dados.resolver_janela(janela)
    return Parametros(
        rotulo_janela=rotulo, janela_ini=janela_ini, janela_fim=janela_fim, criterio=criterio,
        referencia=referencia, confianca=confianca, piso=piso, n_minimo=n_minimo,
        incluir_ps=incluir_ps,
    )


def _janela_por_intervalo(ini: str, fim: str) -> tuple[str, str, str]:
    """Valida um intervalo AAAA-MM e devolve (rótulo, data_ini, data_fim).

    Três recusas, e nenhuma é preciosismo:

    · FORA DA AMOSTRA — mês sem base devolveria zero solicitações por falta de
      dado, e na tela isso lê igual a zero por comportamento;
    · INVERTIDO — janela negativa não é janela;
    · ABAIXO DO MÍNIMO (config.JANELA_MINIMA_MESES, a forma numérica da decisão
      §5.1 "menor janela analisável"): sob o piso escalado a coorte esvazia e a
      norma desestabiliza. Com os atalhos 3/6/12 este limite nunca era exercido;
      com intervalo livre, ele é a única coisa entre o analista e uma janela que
      não sustenta comparação.
    """
    if not re.fullmatch(r"\d{4}-\d{2}", ini or "") or not re.fullmatch(r"\d{4}-\d{2}", fim or ""):
        raise HTTPException(422, "ini e fim devem estar em AAAA-MM (mês cheio)")
    primeiro, ultimo = dados.meses_disponiveis()
    if ini < primeiro or fim > ultimo:
        raise HTTPException(
            422, f"intervalo fora da base disponível ({primeiro} a {ultimo}): "
                 f"mês sem dado devolveria zero por falta de base, que na tela "
                 f"lê igual a zero por comportamento")
    if ini > fim:
        raise HTTPException(422, f"início ({ini}) depois do fim ({fim})")
    janela_ini, janela_fim = dados.resolver_intervalo(ini, fim)
    meses = dados.meses_na_janela(janela_ini, janela_fim)
    if meses < config.JANELA_MINIMA_MESES:
        raise HTTPException(
            422, f"janela de {meses} mês(es): o mínimo analisável é "
                 f"{config.JANELA_MINIMA_MESES} meses (janela {config.JANELA_MINIMA}). "
                 f"Abaixo disso a maioria cai sob o piso escalado e a norma "
                 f"do grupo deixa de se sustentar")
    return apr.rotulo_intervalo(ini, fim), janela_ini, janela_fim


ParametrosDep = Annotated[Parametros, Depends(obter_parametros)]

# ── o RECORTE, que não é régua ───────────────────────────────────────────────
# Fora de `Parametros` de propósito: régua (janela, critério, referência, piso)
# entra na chave dos motores memoizados, e o recorte não pode entrar — ele não
# muda cálculo nenhum do pipeline, só QUEM ENTRA NA SOMA depois que o pipeline
# terminou. Misturá-lo ali multiplicaria o cache por cada combinação de chips.
RecorteQ = Annotated[str | None, Query(
    description="degrau do recorte (todos | comparaveis | persistente | "
                "qualificados). Alcança só os blocos de achado; régua, "
                "distribuição e estatísticas do topo são sempre da área")]
PerfilQ = Annotated[str | None, Query(
    description="sub-perfis escolhidos, separados por vírgula (união, não "
                "interseção). Recorta por cima do degrau")]


# ─────────────────────────────────────────────────────────────────────────────
# Blocos comuns a toda resposta
# ─────────────────────────────────────────────────────────────────────────────

def _bloco_desvios(p: Parametros) -> dict:
    """Quais controles saíram do recomendado, e a frase que a tela imprime.

    Antes esta checagem ignorava `confianca`, um analista podia baixar a
    confiança de 90% para 80% e nada avisava, que é justamente a manobra mais
    barata para transformar diferença não significativa em achado.
    """
    def _desvio(controle, ativo, recomendado, rotulo, formato=str):
        if ativo == recomendado:
            return None
        return {"controle": controle, "ativo": ativo, "recomendado": recomendado,
                "rotulo": rotulo,
                "texto": f"{rotulo} {formato(ativo)} (recomendado {formato(recomendado)})"}

    pct = lambda v: f"{v:.0%}"                                        # noqa: E731
    desvios = [d for d in (
        _desvio("janela", p.rotulo_janela, config.JANELA_DEFAULT, "janela"),
        _desvio("criterio", p.criterio, config.GATILHO_DEFAULT, "critério", str.upper),
        _desvio("referencia", p.referencia, config.ALVO_DEFAULT, "referência"),
        _desvio("confianca", p.confianca, config.NIVEL_CONFIANCA_DEFAULT, "confiança", pct),
        _desvio("piso", p.piso, config.PISO_CONSULTAS_ANO["_default"], "volume mínimo"),
        _desvio("n_minimo", p.n_minimo, config.N_MINIMO_PEER_GROUP, "n mínimo"),
    ) if d]

    if not desvios:
        aviso = None
    elif len(desvios) == 1:
        aviso = f"{desvios[0]['texto'].capitalize()}, fora do recomendado."
    else:
        nomes = ", ".join(d["rotulo"] for d in desvios[:-1])
        aviso = (f"{nomes} e {desvios[-1]['rotulo']} fora do recomendado.").capitalize()

    return {"desvios_do_recomendado": desvios, "aviso_desvio": aviso}


UNIDADE_PISO = "consultas/ano"


def _leitura_da_janela(p: Parametros) -> dict:
    """O que a janela escolhida IMPLICA, para a tela dizer no ato da escolha.

    A janela define o universo (METODOLOGIA §5.1: norma e indivíduo saem sempre
    da MESMA janela), e o fatiamento dela em trimestres é o que sustenta a
    consistência. Duas consequências que ninguém adivinha e que a tela precisa
    declarar:

    · trimestres = parte inteira de meses/3, e o resto é DESCARTADO do
      fatiamento (mas continua contando no agregado);
    · abaixo de config.MIN_JANELAS_AVALIAVEIS trimestres a consistência não é
      reportável, e como a cascata é cumulativa, o degrau "persistente" e o
      "qualificados" ficam VAZIOS. Metade do produto sai de cena, e isso tem de
      ser sabido antes de escolher, não depois.
    """
    fatias = dados.fatiar_trimestres(p.janela_ini, p.janela_fim)
    meses = dados.meses_na_janela(p.janela_ini, p.janela_fim)
    reportavel = len(fatias) >= config.MIN_JANELAS_AVALIAVEIS
    return {
        "meses": meses,
        "trimestres": len(fatias),
        "resto_dias": dados.resto_fora_dos_trimestres(p.janela_ini, p.janela_fim),
        "consistencia_reportavel": reportavel,
        "aviso": (None if reportavel else
                  "nesta janela a consistência entre trimestres não é "
                  "calculável, e com ela saem os recortes de variação "
                  "persistente e qualificados"),
    }


def _faixa_criterios(p: Parametros, desvios: list[dict]) -> list[dict]:
    """Os seis pares rótulo/valor da faixa de critérios do cabeçalho.

    A faixa declara sob que regra TODO número da tela foi calculado, e por isso
    carrega a régua inteira: janela, critério, referência e confiança, mais os
    dois pisos — volume mínimo, que decide quem é comparado, e mínimo de
    solicitantes, que decide qual procedimento entra na norma. Régua parcial na
    tela é pior que régua nenhuma, porque parece completa.

    Os rótulos são CURTOS de propósito: os seis pares têm de caber em linha
    única na coluna de conteúdo mais estreita que existe (~1000px). Não são os
    mesmos rótulos do diálogo, que tem espaço para a forma longa.

    `fora_do_padrao` sai da mesma checagem que alimenta o aviso de desvio: um
    controle, uma fonte de verdade sobre estar ou não no recomendado.
    """
    fora = {d["controle"] for d in desvios}
    meses = config.JANELAS_UI.get(p.rotulo_janela)
    pares = [
        ("janela", "Janela", f"{meses} meses" if meses else p.rotulo_janela),
        ("criterio", "Critério de revisão", p.criterio.upper()),
        ("referencia", "Referência do grupo", p.referencia),
        ("confianca", "Confiança exigida", f"{p.confianca:.0%}"),
        ("piso", "Volume mínimo", f"{p.piso} {UNIDADE_PISO}"),
        ("n_minimo", "Solicitantes mín.", f"{p.n_minimo} por procedimento"),
    ]
    return [{"chave": chave, "rotulo": rotulo, "valor_fmt": valor,
             "fora_do_padrao": chave in fora}
            for chave, rotulo, valor in pares]


def _proveniencia(p: Parametros, resultado: dict) -> dict:
    """Governança visível como texto (léxico): o carimbo que fecha toda tela."""
    return {
        "carimbo": apr.carimbo_proveniencia(p.janela_ini, p.janela_fim, resultado["base"],
                                            p.criterio, p.referencia, p.confianca),
        # A RÉGUA ATIVA — o que o analista escolheu e pode mudar. É isto que sobe
        # para a barra superior. Pipeline, período, base e versão da classificação
        # NÃO entram aqui: são carimbo de proveniência, e o léxico os define como
        # texto de rodapé. Misturar os dois estoura a barra e some com o breadcrumb.
        "chips_criterio": [
            {"rotulo": f"critério {p.criterio.upper()}", "alerta": False},
            {"rotulo": f"referência {p.referencia}", "alerta": False},
            {"rotulo": f"confiança {p.confianca:.0%}", "alerta": False},
            {"rotulo": f"janela {p.rotulo_janela}", "alerta": False},
        ],
        "tags": [
            {"rotulo": f"critério {p.criterio.upper()}", "alerta": False},
            {"rotulo": f"referência {p.referencia}", "alerta": False},
            {"rotulo": f"confiança {p.confianca:.0%}", "alerta": False},
            {"rotulo": f"pipeline {config.PIPELINE_VERSAO}", "alerta": False},
            {"rotulo": f"dados {p.janela_ini} → {p.janela_fim}", "alerta": False},
            {"rotulo": "base eletiva" if not p.incluir_ps else "PS incluído",
             "alerta": p.incluir_ps},
            {"rotulo": f"classificação {config.CLASSIFICACAO_VERSAO}",
             "alerta": not config.CLASSIFICACAO_HOMOLOGADA},
        ],
        "base": resultado["base"],
        "classificacao": resultado["classificacao"],
        "classificacao_homologada": config.CLASSIFICACAO_HOMOLOGADA,
        "pipeline": config.PIPELINE_VERSAO,
        "janela": {**_leitura_da_janela(p), "rotulo": p.rotulo_janela, "inicio": p.janela_ini,
                   "fim": p.janela_fim, "dias": resultado["janela_dias"],
                   # o chip da barra superior: vigência dos dados em duas
                   # palavras, que é o que cabe numa barra de 56px
                   "chip": (f"dados {apr.mes_ano(p.janela_ini)}–"
                            f"{apr.mes_ano(p.janela_fim)}")},
        "piso_ano": p.piso,
        "piso_aplicado_na_janela": resultado["piso_aplicado"],
        "n_minimo": p.n_minimo,
        "exclusoes_por_par": resultado["exclusoes_por_par"],
        "parametros": p.model_dump(),
    }


def _rodar(p: Parametros) -> dict:
    """Pipeline da janela, sempre com area=None: a norma de cada área já é
    calculada por área lá dentro, e um único resultado serve a todas as telas
    (cache quente entre áreas)."""
    return dados.rodar_pipeline(
        p.janela_ini, p.janela_fim, p.piso, p.n_minimo, None,
        p.criterio, p.referencia, p.incluir_ps)


def _norma_linha(resultado: dict, area: str):
    n = resultado["norma"]
    n = n[n["AREA_ATUACAO"] == area]
    return None if n.empty else n.iloc[0]


def _gatilho_da_area(posicao_area: pd.DataFrame) -> str | None:
    """O gatilho EFETIVO da área, degradado pelo n que o sustenta. Sai do
    motor (coluna gatilho_usado), nunca recalculado aqui."""
    for g in posicao_area["gatilho_usado"]:
        if pd.notna(g):
            return str(g)
    return None


# Grupos da navegação — a área é escolhida pelo que a tela CONSEGUE fazer com
# ela, não por ordem alfabética. Cada estado do motor cai num grupo; o auditor
# lê a capacidade antes de clicar, em vez de descobrir depois.
GRUPOS_DE_AREAS = (
    ("com_referencia", "Com referência do grupo",
     "sustentam percentil e critério de revisão",
     (blocos.ESTADO_PLENA, blocos.ESTADO_AJUSTADA)),
    ("grupo_insuficiente", "Grupo insuficiente",
     "posição descritiva por posto; sem percentil e sem sinalização",
     (blocos.ESTADO_INSUFICIENTE,)),
    ("fora_de_comparacao", "Fora de comparação",
     "sem grupo de pares: leitura por cooperado",
     (blocos.ESTADO_SEM_PEER_GROUP,)),
)

MARCA_SEM_REFERENCIA = "∅"


def _areas_resolvidas(resultado: dict, criterio: str) -> list[dict]:
    """Catálogo de áreas da janela, com n, elegíveis, gatilho efetivo e estado."""
    pos, norma = resultado["posicao"], resultado["norma"].set_index("AREA_ATUACAO")
    grupo_de = {estado: chave
                for chave, _, _, estados in GRUPOS_DE_AREAS for estado in estados}
    saida = []
    for area, linhas in pos.groupby("AREA_ATUACAO", sort=False):
        n_norma = int(norma["n_na_norma"].get(area, 0))
        gatilho = _gatilho_da_area(linhas)
        estado = blocos.estado_area(area, n_norma, gatilho, criterio)
        pendente = area == config.AREA_INDEFINIDA
        n_total = len(linhas)
        n_comparaveis = int(linhas["avaliavel"].sum())
        # contador da navegação: elegíveis onde há referência; sem referência, o
        # total da área com a marca ∅ — "n=0" ao lado de 72 pessoas leria como
        # área vazia, e o que falta ali não é gente, é norma.
        if n_norma:
            contador = f"n={n_norma}"
            contador_titulo = (
                f"{n_norma} cooperado{'s' if n_norma != 1 else ''} "
                f"form{'am' if n_norma != 1 else 'a'} a referência desta área")
        else:
            contador = (f"{n_total} cooperado{'s' if n_total != 1 else ''} "
                        f"· {MARCA_SEM_REFERENCIA}")
            contador_titulo = (
                f"{MARCA_SEM_REFERENCIA} "
                + (f"o único cooperado da área não forma" if n_total == 1 else
                   f"nenhum dos {n_total} cooperados forma")
                + " a referência: sem grupo de pares para comparar")
        saida.append({
            "id": blocos.slug(area), "nome": area,
            # o nome que a tela imprime — o interno "INDEFINIDO" nunca vaza (léxico)
            "titulo": apr.rotulo_exibicao(area),
            "contador": contador, "contador_titulo": contador_titulo,
            # rótulo da <option> no seletor: nome + o que sustenta a comparação.
            # Montado aqui, não no front — a UI imprime, não redige (léxico).
            "rotulo_opcao": (
                f"{apr.rotulo_exibicao(area)} · {n_total} cooperados" if pendente else
                f"{apr.rotulo_exibicao(area)} · {n_comparaveis} "
                f"comparáve{'is' if n_comparaveis != 1 else 'l'} de {n_total}"
                if n_norma else
                f"{apr.rotulo_exibicao(area)} · sem referência ({n_total} cooperado"
                f"{'s' if n_total != 1 else ''})"),
            # o que distingue esta área das vizinhas, numa linha — vai para o
            # `title` da opção do seletor. Redigido no config (léxico: a UI imprime)
            "perfil": apr.perfil_area(area),
            "sem_referencia": n_norma == 0,
            # texto curto da coluna .ometa da opção no popover
            "opcao_meta": (f"{n_total} cooperados" if pendente else
                           f"n={n_norma}" if n_norma else
                           f"{n_total} cooperado{'s' if n_total != 1 else ''} · sem norma"),
            # .opt-off: a opção existe e é escolhível, mas não sustenta comparação
            "opcao_esmaecida": not estado["comparavel"],
            # etiqueta de ressalva no gatilho, quando o grupo não sustenta o critério
            "ressalva": (None if estado["ressalva"] is None else "ressalva"),
            "rotulo": apr.rotulo_area(area, n_comparaveis, n_total),
            "n_total": n_total,
            "n_avaliaveis": n_comparaveis,
            "n_formam_referencia": n_norma,
            "gatilho_usado": gatilho,
            "criterio_ajustado": gatilho is not None and gatilho != criterio,
            "estado": estado["codigo"],
            "grupo": grupo_de.get(estado["codigo"], "fora_de_comparacao"),
            "comparavel": estado["comparavel"],
        })
    # dentro do grupo: quem sustenta mais referência primeiro, depois por tamanho
    saida.sort(key=lambda a: (-a["n_formam_referencia"], -a["n_total"]))
    return saida


def _agrupar_areas(areas: list[dict]) -> list[dict]:
    """As áreas na ordem em que servem ao trabalho, com título por grupo.
    Grupo sem nenhuma área não aparece, cabeçalho órfão não é informação."""
    return [
        {"chave": chave, "rotulo": rotulo, "descricao": descricao,
         "areas": [a for a in areas if a["grupo"] == chave]}
        for chave, rotulo, descricao, _ in GRUPOS_DE_AREAS
        if any(a["grupo"] == chave for a in areas)
    ]


@lru_cache(maxsize=32)
def _cascata_area(area: str, janela_ini: str, janela_fim: str, piso: int,
                  n_minimo: int, criterio: str, referencia: str,
                  incluir_ps: bool) -> dict:
    """A cascata de qualificação da área, os degraus que viram chips.

    Roda os motores que os degraus exigem (persistência, execução para os
    fatores de contexto, bootstrap para o piso de confiança) com os MESMOS
    parâmetros do pipeline. Cacheado por argumentos: a primeira chamada de cada
    régua paga o bootstrap; as seguintes são instantâneas.
    """
    r = dados.rodar_pipeline(janela_ini, janela_fim, piso, n_minimo, None,
                             criterio, referencia, incluir_ps)
    posicao = r["posicao"][r["posicao"]["AREA_ATUACAO"] == area]
    posproc = r["posicao_proc"][r["posicao_proc"]["AREA_ATUACAO"] == area]
    sinal = filtrar_sinalizados(posproc)
    n_medidos = int(posicao["ID_COOPERADO"].nunique())

    fatias = dados.fatiar_trimestres(janela_ini, janela_fim)
    persist = None
    if len(fatias) >= config.MIN_JANELAS_AVALIAVEIS:
        pers = dados.rodar_persistencia(fatias, piso, n_minimo, criterio,
                                        referencia, None,
                                        config.MIN_JANELAS_AVALIAVEIS, incluir_ps)
        pp = pers["por_procedimento"]
        persist = pp[pp["ID_COOPERADO"].isin(posicao["ID_COOPERADO"])]

    # fatores de contexto verificados (urgência na solicitação, regime na execução)
    re_ = dados.rodar_pipeline_execucao(
        janela_ini, janela_fim, piso, n_minimo, config.PISO_EXECUCOES_ANO,
        config.Q_CONFUNDIDOR, None, criterio, referencia, incluir_ps)
    perfil, resumo = re_["perfil_execucao"], re_["resumo_coop"]
    confundidores = (set(perfil.loc[perfil["confundidor_regime"], "ID_COOPERADO"])
                     | set(resumo.loc[resumo["confundidor_urgencia"].fillna(False),
                                      "ID_COOPERADO"]))
    confundidores &= set(posicao["ID_COOPERADO"])

    # piso de confiança: bootstrap só nos pares que chegam ao degrau anterior
    parcial = cascata.qualificar(sinal, persist, len(fatias), confundidores, None)
    pares_boot = (parcial[parcial["sem_fator_de_contexto"]]
                  [["ID_COOPERADO", "CD_PROCEDIMENTO", referencia]]
                  .rename(columns={referencia: "alvo_valor"}))
    conf = None
    if len(pares_boot):
        conf = pl.controlador_confiabilidade(
            dados.carregar_fato(), pares_boot, janela_ini, janela_fim,
            seed=config.SEED_BOOTSTRAP,
            nivel_confianca=config.NIVEL_CONFIANCA_DEFAULT,
            n_bootstrap=config.N_BOOTSTRAP,
            min_pacientes_proc=config.MIN_PACIENTES_BOOTSTRAP, area=area,
            incluir_ps=incluir_ps)

    q = cascata.qualificar(sinal, persist, len(fatias), confundidores, conf)
    linhas_funil = cascata.funil(q, n_medidos)
    escolha = cascata.escolher_default(linhas_funil)

    # impacto em R$: excedente × preço mediano derivado das contas. ESTIMATIVA
    # (decisão 2026-08-13: volta à tela rotulada como estimativa com preço
    # interno provisório) — a tabela contratual não chegou
    # (config.PRECO_POR_PROCEDIMENTO is None); quando chegar, é injetada no
    # pipeline por argumento e estas somas viram números plenos.
    rs_bruto = re_["posicao_proc_rs"]
    rs_bruto = rs_bruto[rs_bruto["AREA_ATUACAO"] == area]
    # VALOR TOTAL SOLICITADO (não só o excedente): taxa × consultas × preço, por
    # par, somado por cooperado. Parcial por construção — só entra procedimento
    # com preço nas contas. Alimenta o eixo Y e o tamanho da dispersão.
    com_preco = rs_bruto[rs_bruto["preco_mediano"].notna()]
    valor_total_coop = (
        (com_preco["taxa"] * com_preco["consultas_totais"]
         * com_preco["preco_mediano"])
        .groupby(com_preco["ID_COOPERADO"]).sum().to_dict()
        if len(com_preco) else {})
    rs = filtrar_sinalizados(rs_bruto, exigir_preco=True)
    excedente_reais = float(rs["excedente_reais"].sum()) if len(rs) else None
    # as MESMAS somas, por cooperado e por procedimento, para a tabela e a aba
    reais_coop = (rs.groupby("ID_COOPERADO")["excedente_reais"].sum().to_dict()
                  if len(rs) else {})
    reais_proc = (rs.groupby("CD_PROCEDIMENTO")["excedente_reais"].sum().to_dict()
                  if len(rs) else {})

    # ── o piso (segunda passada, contra o critério) ──────────────────────────
    # A passada acima mede o excedente contra a REFERÊNCIA de adequação (alvo
    # escolhido pelo analista, mediana por default): é o TETO, o que sobraria
    # se cada qualificado descesse até o padrão do grupo.
    #
    # Esta segunda passada mede contra o próprio CRITÉRIO de revisão: o mínimo
    # que sobraria, trazendo cada um só até a borda a partir da
    # qual ele foi sinalizado. Nada mais é feito aqui: é o mesmo motor, o mesmo
    # recorte e a mesma população, com `alvo` diferente — a única coisa que
    # muda é de onde se conta a distância. O piso é ≤ teto por construção:
    # critério ≥ referência (o motor exige `alvo <= gatilho`), e excedente é
    # (taxa − alvo) truncado em zero, que só encolhe quando o alvo sobe.
    #
    # Custo: `rodar_pipeline_execucao` já é memoizado por argumentos e `alvo`
    # está na chave, então a segunda combinação vira mais uma entrada do mesmo
    # cache. Com referência == critério nem chamada há: as duas pontas saem do
    # mesmo `rs`, a faixa colapsa, e a tela mostra um valor só.
    rs_piso = rs
    if referencia != criterio:
        re_piso = dados.rodar_pipeline_execucao(
            janela_ini, janela_fim, piso, n_minimo, config.PISO_EXECUCOES_ANO,
            config.Q_CONFUNDIDOR, None, criterio, criterio, incluir_ps)
        rp = re_piso["posicao_proc_rs"]
        rs_piso = filtrar_sinalizados(rp[rp["AREA_ATUACAO"] == area],
                                      exigir_preco=True)
    reais_coop_piso = (
        rs_piso.groupby("ID_COOPERADO")["excedente_reais"].sum().to_dict()
        if len(rs_piso) else {})

    # degraus alcançados por cooperado — o front filtra por pertencimento
    por_cooperado: dict[str, list[str]] = {
        coop: ["medidos"] for coop in posicao["ID_COOPERADO"]}
    for chave, *_ in cascata.DEGRAUS:
        if chave == "medidos":
            continue
        for coop in q.loc[q[chave], "ID_COOPERADO"].unique():
            por_cooperado.setdefault(coop, ["medidos"]).append(chave)

    n_persistentes = next(linha["n_cooperados"] for linha in linhas_funil
                          if linha["chave"] == "persistente")
    return {"funil": linhas_funil, "default": escolha,
            "por_cooperado": por_cooperado,
            "confundidores": sorted(confundidores),
            "excedente_reais": excedente_reais,
            "excedente_reais_coop": reais_coop,
            # a mesma soma medida até o critério (não usada pela tela hoje)
            "excedente_reais_coop_piso": reais_coop_piso,
            "excedente_reais_proc": reais_proc,
            # o R$ SOLICITADO por cooperado (não o excedente), para a dispersão
            "valor_total_coop": valor_total_coop,
            # os pares sinalizados COM PREÇO, crus. Saem daqui em vez do Pareto
            # pronto porque o Pareto agora depende do recorte, e esta função é
            # `lru_cache` na régua — recorte não é régua e não entra na chave.
            "rs": rs,
            # por PAR, para o dossiê: degraus da cascata e faixa de confiança
            "pares": q, "conf": conf,
            "n_persistentes": n_persistentes}


def _em_cena(recorte: str | None, perfil: str | None,
             linhas_coop: list[dict], perfis_area: list[dict]) -> tuple:
    """Traduz o recorte da URL para (ids em cena, rótulo, perfis escolhidos).

    A tela manda `recorte` (chave do degrau) e `perfil` (chaves separadas por
    vírgula), o mesmo par que já viaja na URL — e não a lista de ids. O motor
    deriva o conjunto do que ele próprio produziu, então não há como a tela
    pedir uma agregação sobre uma população que o motor não reconhece.

    Perfil não selecionável é ignorado, como no front: poucos portadores não
    sustentam leitura interna, e o chip nem responde ao clique.
    """
    chaves = [c for c in (perfil or "").split(",") if c]
    escolhidos = [pf for pf in perfis_area
                  if pf["chave"] in chaves and pf["selecionavel"]]
    ids = blocos.ids_em_cena(linhas_coop, recorte,
                             [pf["flag"] for pf in escolhidos])
    rotulo = blocos.rotulo_recorte(recorte, [pf["rotulo"] for pf in escolhidos])
    return ids, rotulo, escolhidos


def _linhas_para_recorte(posicao_area: pd.DataFrame, casc: dict,
                         perfis_area: list[dict]) -> list[dict]:
    """A linha do cooperado reduzida ao que o PREDICADO DO RECORTE lê, para os
    endpoints que precisam do conjunto em cena mas não da tabela inteira.

    Mesmos campos e mesmos nomes de `linhas_cooperados`, de propósito: os dois
    passam por `ids_em_cena`, e um campo com outro nome aqui viraria um recorte
    que discorda do da tela sem ninguém perceber.
    """
    colunas = [pf["flag"] for pf in perfis_area]
    flags = dados.carregar_classificacao().set_index("ID_COOPERADO")
    linhas = []
    for _, linha in posicao_area.iterrows():
        coop = linha["ID_COOPERADO"]
        f = flags.loc[coop] if coop in flags.index else None
        linhas.append({
            "id": coop,
            "avaliavel": bool(linha["avaliavel"]),
            "grupos": casc["por_cooperado"].get(coop, ["medidos"]),
            "sub_perfis": ([] if f is None else
                           [{"chave": c} for c in colunas if bool(f.get(c))]),
        })
    return linhas


def _blocos_de_achado(casc: dict, linhas_coop: list[dict], ids: list[str],
                      rotulo: str, recorte: str | None,
                      n_comparaveis: int) -> dict:
    """Os blocos que SEGUEM O RECORTE: os três cards e os dois Paretos. Um lugar só para montá-los, porque a carga inicial da página e a
    troca de recorte precisam produzir exatamente o mesmo formato — se
    divergirem, a tela mostra uma coisa ao abrir e outra ao clicar no mesmo
    recorte que já estava ativo.

    A régua não aparece em nenhum deles: são somas de excedente já medido
    contra a referência da área, que não se move.
    """
    sub = blocos.subtitulo_recorte(rotulo, len(ids))
    itens_por_coop = {l["id"]: (l.get("excedente_itens") or 0)
                      for l in linhas_coop}
    # magnitude por cooperado para os cards de média (SADT e custo por consulta)
    base_por_coop = {l["id"]: {"consultas": l.get("consultas"),
                               "solicitacoes": l.get("solicitacoes"),
                               "valor_total": l.get("valor_total")}
                     for l in linhas_coop}
    return {
        "recorte": {"chave": recorte, "rotulo": rotulo, "n": len(ids)},
        "cards": blocos.cards_do_recorte(casc["excedente_reais_coop"],
                                         itens_por_coop, ids, rotulo,
                                         n_comparaveis, base_por_coop),
        "pareto_cooperados": blocos.pareto_cooperados(
            casc["excedente_reais_coop"], linhas_coop, ids, sub),
        "pareto_procedimentos": blocos.pareto_procedimentos(
            casc["rs"], ids, sub),
    }


def _peso_na_especialidade(resultado: dict, area: str) -> dict | None:
    """Quanto esta área representa da especialidade inteira.

    Fração das SOLICITAÇÕES (o que gera custo), com a contagem de cooperados ao
    lado, percentual sem denominador não é leitura (rigor-estatistico §1).
    """
    ta = resultado["taxa_agregada"]
    total_itens = float(ta["total_itens"].sum())
    if not total_itens:
        return None
    da_area = ta[ta["AREA_ATUACAO"] == area]
    return {
        "fracao_solicitacoes": round(float(da_area["total_itens"].sum()) / total_itens, 4),
        "solicitacoes": int(da_area["total_itens"].sum()),
        "solicitacoes_especialidade": int(total_itens),
        "cooperados": int(da_area["ID_COOPERADO"].nunique()),
        "cooperados_especialidade": int(ta["ID_COOPERADO"].nunique()),
    }


def _chips_cascata(casc: dict) -> list[dict]:
    """Os chips SÃO os degraus da cascata, do mais estrito ao mais amplo.

    Filtrar vira aprendizado: a ordem mostra o método (validade → triagem →
    artefato → contexto), e cada chip carrega a definição do próprio degrau.
    """
    ordem_estrito_primeiro = list(reversed(casc["funil"]))
    padrao = casc["default"]["chave"]
    return [
        {"chave": d["chave"], "rotulo": d["rotulo"], "descricao": d["definicao"],
         "natureza": d["natureza"], "n": d["n_cooperados"], "n_pares": d["n_pares"],
         "excedente_itens": d["excedente_itens"], "default": d["chave"] == padrao}
        for d in ordem_estrito_primeiro
    ]


def _resolver_area(resultado: dict, area_id: str) -> str:
    """Slug de URL -> nome da área. 404 com a lista do que existe."""
    for area in resultado["posicao"]["AREA_ATUACAO"].unique():
        if blocos.slug(area) == area_id.lower():
            return str(area)
    disponiveis = sorted({blocos.slug(a)
                          for a in resultado["posicao"]["AREA_ATUACAO"].unique()})
    raise HTTPException(404, f"área {area_id!r} não existe nesta janela, "
                             f"disponíveis: {disponiveis}")


# ─────────────────────────────────────────────────────────────────────────────
# /api/meta — o que a shell precisa antes de escolher a área
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/meta", tags=["tela área"])
def meta(p: ParametrosDep) -> dict[str, Any]:
    """Áreas com n e elegíveis, opções dos controles, período e proveniência.

    Alimenta: seletor de área da sidebar, chips de critério do topo fixo e o
    banner de homologação.
    """
    r = _rodar(p)
    ini_dados, fim_dados = dados.janela_dados()

    def _opcoes(valores, default, formato=str):
        return [{"valor": v, "rotulo": formato(v), "recomendado": v == default}
                for v in valores]

    areas = _areas_resolvidas(r, p.criterio)
    n_coop = int(r["taxa_agregada"]["ID_COOPERADO"].nunique())
    # uma checagem só de desvio: alimenta a marca na faixa E o aviso redigido
    desvios = _bloco_desvios(p)
    return {
        "especialidade": config.ESPECIALIDADE_MVP,
        # Primeiro nível da cascata. Uma só nesta base — o controle fica travado
        # (.sel-locked), mas a hierarquia já existe para quando a segunda entrar.
        "especialidades": [{
            "id": "gineco-obst", "nome": config.ESPECIALIDADE_MVP,
            "meta": f"{n_coop} cooperados · {len(areas)} áreas",
            "ativa": True,
        }],
        "especialidade_unica": True,
        "periodo_dados": {"inicio": ini_dados, "fim": fim_dados},
        "areas": areas,
        "grupos_de_areas": _agrupar_areas(areas),
        # PERÍODO: o que o seletor de janela pode oferecer e o que a escolha
        # atual implica. Sem o intervalo disponível, o seletor ofereceria meses
        # sem base — e zero por falta de dado lê igual a zero por comportamento.
        "periodo": {
            "disponivel": dict(zip(("primeiro", "ultimo"), dados.meses_disponiveis())),
            "minimo_meses": config.JANELA_MINIMA_MESES,
            "min_trimestres": config.MIN_JANELAS_AVALIAVEIS,
            "atual": {"rotulo": p.rotulo_janela,
                      "ini": p.janela_ini[:7], "fim": p.janela_fim[:7],
                      **_leitura_da_janela(p)},
        },
        "controles": {
            # `rotulo` é a forma LONGA, do diálogo, onde há espaço; a curta, da
            # faixa, vem em `faixa_criterios`. `ajuda` é a linha que explica o
            # que o controle decide — texto institucional, redigido aqui (léxico:
            # a UI imprime, não redige). Ambos vêm de "Criterios da Analise.html".
            "janela": {"opcoes": _opcoes(config.JANELAS_UI, config.JANELA_DEFAULT,
                                         lambda v: f"{config.JANELAS_UI[v]} meses"),
                       "ativo": p.rotulo_janela, "recomendado": config.JANELA_DEFAULT,
                       "rotulo": "Janela de apuração",
                       "ajuda": ("Período de solicitações somado no cálculo; "
                                 "janelas curtas oscilam mais")},
            "criterio": {"opcoes": _opcoes(config.GATILHOS_UI, config.GATILHO_DEFAULT,
                                           str.upper),
                         "ativo": p.criterio, "recomendado": config.GATILHO_DEFAULT,
                         "rotulo": "Critério de revisão",
                         "ajuda": ("Distância dos pares a partir da qual o "
                                   "cooperado entra na lista")},
            "referencia": {"opcoes": _opcoes(
                [a for a in config.ALVOS_UI
                 if _ORDEM_NIVEL[a] <= _ORDEM_NIVEL[p.criterio]], config.ALVO_DEFAULT),
                "ativo": p.referencia, "recomendado": config.ALVO_DEFAULT,
                "rotulo": "Referência do grupo",
                "ajuda": ("Ponto tomado como uso adequado; é dele que se mede o "
                          "excedente. Sempre ≤ critério"),
                "regra": "sempre ≤ critério de revisão"},
            "confianca": {"opcoes": _opcoes(config.NIVEIS_CONFIANCA_UI,
                                            config.NIVEL_CONFIANCA_DEFAULT,
                                            lambda v: f"{v:.0%}"),
                          "ativo": p.confianca,
                          "recomendado": config.NIVEL_CONFIANCA_DEFAULT,
                          "rotulo": "Confiança exigida",
                          "ajuda": ("Margem para afirmar que a diferença não é "
                                    "do acaso")},
            # Controles numéricos viajam com as RESTRIÇÕES (minimo/maximo/passo/
            # unidade) ao lado de ativo/recomendado. O front não conhece regra
            # nenhuma — desenha o que recebe e valida contra o que recebe. Os
            # limites vêm de config.LIMITES_CONTROLES, a mesma fonte que alimenta
            # o `ge=` da assinatura acima: um número, um lugar.
            "piso": {"ativo": p.piso,
                     "recomendado": config.PISO_CONSULTAS_ANO["_default"],
                     "rotulo": "Volume mínimo para avaliação",
                     "ajuda": "Abaixo disso o cooperado é listado sem comparação",
                     "unidade": UNIDADE_PISO, "unidade_curta": "consultas",
                     **config.LIMITES_CONTROLES["piso"]},
            "n_minimo": {"ativo": p.n_minimo, "recomendado": config.N_MINIMO_PEER_GROUP,
                         "rotulo": "Mínimo de solicitantes por procedimento",
                         "ajuda": ("Procedimento com menos solicitantes não entra "
                                   "na norma"),
                         "unidade": "solicitantes", "unidade_curta": "solicitantes",
                         **config.LIMITES_CONTROLES["n_minimo"]},
        },
        # A FAIXA DE CRITÉRIOS do cabeçalho, redigida. Substituiu a linha-resumo
        # do bloco Análise recolhido (`resumo_criterios`), que existia para
        # anunciar a régua sem abrir o painel: a faixa já é essa frase, e nunca
        # está recolhida. Ela também fecha um buraco do arranjo anterior — o
        # resumo mostrava quatro controles e omitia os dois pisos, então desviar
        # o volume mínimo não aparecia em lugar nenhum da tela.
        "faixa_criterios": _faixa_criterios(p, desvios["desvios_do_recomendado"]),
        # DESVIO DA RÉGUA RECOMENDADA — ajuste 3 do handoff.
        # A régua tem dezenas de combinações válidas e todas produzem números
        # defensáveis isoladamente. O que não se sustenta é ESCOLHER a combinação
        # depois de ver o resultado. Por isso o desvio é anunciado: quem desviou
        # fica sabendo, e a tela oferece um caminho de volta.
        # `aviso_desvio` vem redigido daqui, não montado no front (léxico: a UI
        # imprime, não redige).
        **desvios,
        "banner": {
            "texto": config.BANNER_HOMOLOGACAO,
            "detalhe": (f"Classificação de áreas de atuação {config.CLASSIFICACAO_VERSAO}. "
                        "Resultados preliminares, não destinados a deliberação de comitê."),
            "ativo": not config.CLASSIFICACAO_HOMOLOGADA,
        },
        "proveniencia": _proveniencia(p, r),
    }


# ─────────────────────────────────────────────────────────────────────────────
# /api/area/{area_id} — a tela inteira, bloco a bloco
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/cooperados", tags=["busca"])
def cooperados_para_busca(p: ParametrosDep) -> dict[str, Any]:
    """O elenco de cooperados, para a busca da barra superior.

    Duas fontes, de propósito:

      - a CLASSIFICAÇÃO diz quem existe (202). É o elenco completo, e não
        depende de janela nenhuma.
      - o PIPELINE da janela diz quem tem dossiê renderizável (200 nesta).

    Quem existe mas não tem atividade no período viaja com `disponivel: false`
    e o motivo ao lado, em vez de sumir da lista: some, e quem procura conclui
    que o cooperado não está na base — que é exatamente o beco que esta busca
    veio resolver. A tela o mostra como opção não escolhível (`.opt.opt-na`).

    NENHUM NÚMERO, nem de contagem. Esta lista é uma PORTA: quem procura um
    cooperado quer achá-lo e entrar. Número aqui seria ruído, e pior, convidaria
    a ler a lista como ranking — e ranquear cooperados de áreas diferentes é a
    comparação entre peer groups que o CLAUDE.md proíbe. Quem quer medida abre o
    dossiê, onde há régua; quem quer fila por oportunidade usa o Panorama.
    """
    ativos = set(_rodar(p)["posicao"]["ID_COOPERADO"])
    cls = dados.carregar_classificacao()

    def ordem(id_coop: str) -> tuple:
        """`cooperado_9` antes de `cooperado_10`: ordem alfabética põe o 10 na
        frente do 2, e uma lista de nomes numerados fora de ordem parece
        embaralhada."""
        cauda = id_coop.rsplit("_", 1)[-1]
        return (0, int(cauda)) if cauda.isdigit() else (1, 0)

    linhas = []
    for _, r in cls.iterrows():
        id_coop = str(r["ID_COOPERADO"])
        disponivel = id_coop in ativos
        area = str(r["especialidade"])
        linhas.append({
            "id": id_coop,
            "area": apr.rotulo_exibicao(area),
            # o SLUG, para o seletor de área filtrar a lista: o rótulo é para
            # ler, o id é para casar
            "area_id": blocos.slug(area),
            "disponivel": disponivel,
            "motivo": None if disponivel else "sem atividade no período",
        })
    linhas.sort(key=lambda l: ordem(l["id"]))
    return {"cooperados": linhas, "total": len(linhas),
            "n_disponiveis": sum(1 for l in linhas if l["disponivel"])}


@app.get("/api/area/{area_id}", tags=["tela área"])
def area(area_id: Annotated[str, PathParam(description="id da área (slug), de /api/meta")],
         p: ParametrosDep,
         recorte: RecorteQ = None, perfil: PerfilQ = None) -> dict[str, Any]:
    """Título, justificativa, composição da referência, estatísticas,
    distribuição e lista de cooperados, na ordem dos blocos da tela.

    `recorte`/`perfil` só alcançam os blocos de ACHADO (os dois Paretos e a
    três cards); a linha de contexto, a distribuição, a régua e a lista de
    cooperados vêm sempre da área inteira — a tela é que esconde linhas.
    Vêm na carga inicial para que um link compartilhado com recorte já abra
    certo, em vez de pintar a área e corrigir no quadro seguinte."""
    r = _rodar(p)
    nome = _resolver_area(r, area_id)

    posicao = r["posicao"][r["posicao"]["AREA_ATUACAO"] == nome].copy()
    posproc = r["posicao_proc"][r["posicao_proc"]["AREA_ATUACAO"] == nome]
    norma_linha = _norma_linha(r, nome)
    n_formam = int(norma_linha["n_na_norma"]) if norma_linha is not None else 0
    gatilho = _gatilho_da_area(posicao)
    estado = blocos.estado_area(nome, n_formam, gatilho, p.criterio)

    classificacao = dados.carregar_classificacao()
    rotulos_posicao = dados.posicao_na_area(posicao)
    sinal = filtrar_sinalizados(posproc)
    n_sinalizados = int((posicao["avaliavel"] & posicao["acima_gatilho"]).sum())

    # consistência entre trimestres — só quando a janela comporta fatias suficientes.
    # Trimestre incompleto no fim da janela fica FORA (senão o denominador da
    # persistência absorveria uma "janela" de poucos dias); o resto é declarado
    # na proveniência, nunca descartado em silêncio.
    fatias = dados.fatiar_trimestres(p.janela_ini, p.janela_fim)
    resto_dias = dados.resto_fora_dos_trimestres(p.janela_ini, p.janela_fim)
    persistencia = None
    if len(fatias) >= config.MIN_JANELAS_AVALIAVEIS:
        pers = dados.rodar_persistencia(
            fatias, p.piso, p.n_minimo, p.criterio, p.referencia, None,
            config.MIN_JANELAS_AVALIAVEIS, p.incluir_ps)
        pp = pers["por_procedimento"]
        da_area = pp["ID_COOPERADO"].isin(posicao["ID_COOPERADO"])
        pj = pers["por_janela"]
        persistencia = {
            "por_procedimento": pp[da_area],
            # a grade crua vira a SÉRIE por trimestre da coluna Consistência;
            # o índice por janela dá a altura das barras e a direção
            "por_janela": pj[pj["ID_COOPERADO"].isin(posicao["ID_COOPERADO"])],
            "por_janela_cooperado": pers["por_janela_cooperado"][
                pers["por_janela_cooperado"]["ID_COOPERADO"]
                .isin(posicao["ID_COOPERADO"])],
        }

    casc = _cascata_area(nome, p.janela_ini, p.janela_fim, p.piso, p.n_minimo,
                         p.criterio, p.referencia, p.incluir_ps)

    # ── evidência por cooperado ──────────────────────────────────────────────
    # As três são AGREGAÇÃO do que os motores já produziram: nenhuma mede nada
    # novo. Origem e concentração leem o MESMO procedimento (o que puxa o
    # excedente), para que as duas células da linha falem do mesmo assunto.
    origem = blocos.origem_do_excedente(sinal)
    conc = dados.rodar_concentracao(p.janela_ini, p.janela_fim, p.piso,
                                    p.n_minimo, nome, p.incluir_ps)
    concentracao = blocos.leitura_concentracao(conc, origem)
    serie = blocos.serie_por_trimestre(persistencia, len(fatias))

    # CUSTO POR COOPERADO (colunas "Custo por consulta" e "Valor total"). Mesma
    # chamada memoizada que `_cascata_area` já fez com estes parâmetros, então é
    # acerto de cache, não um segundo passe sobre a base.
    custo_coop = dados.rodar_pipeline_execucao(
        p.janela_ini, p.janela_fim, p.piso, p.n_minimo, config.PISO_EXECUCOES_ANO,
        config.Q_CONFUNDIDOR, None, p.criterio, p.referencia,
        p.incluir_ps)["custo_coop"].set_index("ID_COOPERADO").to_dict("index")

    linhas_coop = sorted(
        blocos.linhas_cooperados(posicao, norma_linha, gatilho, classificacao,
                                 sinal, persistencia, len(fatias), rotulos_posicao,
                                 casc["por_cooperado"], origem, concentracao,
                                 serie, dados.exclusao_por_par(),
                                 blocos.postos_por_perfil(posicao, classificacao),
                                 casc["excedente_reais_coop"], custo_coop),
        key=lambda linha: (-(linha["excedente_itens"] or 0), -linha["indice"]))

    rotulo_titulo = apr.rotulo_exibicao(nome)
    # A barra de composição saiu da tela, mas o BLOCO continua: dele vem a lista
    # de excluídos que a estatística "Comparáveis" abre, e o n que ela anuncia.
    composicao = blocos.composicao_referencia(
        posicao, classificacao, r["piso_aplicado"])

    # os perfis sobem para cá porque o recorte precisa deles para traduzir
    # `?perfil=opera` na coluna de classificação correspondente
    perfis_area = blocos.perfis_da_area(posicao, classificacao)
    ids, rotulo_rec, _ = _em_cena(recorte, perfil, linhas_coop, perfis_area)
    achado = _blocos_de_achado(casc, linhas_coop, ids, rotulo_rec, recorte,
                               int(posicao["avaliavel"].sum()))
    return {
        "area": {
            "id": blocos.slug(nome), "nome": nome, "titulo": rotulo_titulo,
            "pergunta": "O que é normal aqui, e quem está fora?",
            "periodo": apr.periodo_texto(p.rotulo_janela, p.janela_ini, p.janela_fim),
            # `subtitulo` sai da tela de área em 2026-08-19: ele dizia
            # "64 cooperados na área", e a linha de contexto logo abaixo abre
            # com "64 na área". Duas linhas seguidas com o mesmo número e quase
            # as mesmas palavras. A função continua em `apresentacao` para o
            # caminho de exportação sem chassi que a docstring dela prevê.
            "subtitulo": None,
            "n_total": len(posicao),
            "n_avaliaveis": int(posicao["avaliavel"].sum()),
            "n_formam_referencia": n_formam,
            "gatilho_usado": gatilho,
            # contador da aba Procedimentos. Vem daqui e não do endpoint da aba
            # porque a aba precisa anunciar o tamanho ANTES de ser aberta — sem
            # isso, a única saída seria abrir sem número ou carregar os dois
            # blocos de uma vez, e a aba fechada não paga o segundo cálculo.
            #
            # A contagem sai de `norma_proc`, a MESMA base das linhas da aba, e
            # não de `posproc`: nem todo par (cooperado, procedimento) medido
            # produz linha de norma, e contar por ali dava 685 para uma tabela de
            # 662 linhas — contador que não bate com a lista é pior que nenhum.
            "n_procedimentos": int(
                r["norma_proc"][r["norma_proc"]["AREA_ATUACAO"] == nome]
                ["CD_PROCEDIMENTO"].nunique()),
        },
        "estado": estado,
        "justificativa": apr.linha_justificativa(
            rotulo_titulo, int(posicao["avaliavel"].sum()), r["base"],
            gatilho, p.referencia,
            sum(1 for linha in linhas_coop if linha["em_revisao"])),
        "composicao": composicao,
        # o contexto fixo da área, em UMA linha sob o título. Era a faixa de
        # três números-herói até 2026-08-19: mesmo conteúdo, sem o tamanho.
        "contexto": blocos.contexto_da_area(
            gatilho, p.criterio, float(sinal["excedente_itens"].sum()),
            casc["excedente_reais"], n_sinalizados,
            int(posicao["avaliavel"].sum()), len(posicao),
            len(composicao["excluidos"]), estado["codigo"], n_formam,
            # a população do ACHADO: quem tem excedente em algum procedimento.
            # Mesma fonte do 87.816 ao lado (`sinal`, já filtrado por
            # sinalizado), para os dois números não poderem discordar.
            sum(1 for linha in linhas_coop
                if (linha.get("excedente_itens") or 0) > 0)),
        # Fora da faixa de propósito: é comparação ENTRE áreas, e o lugar dela é
        # o Panorama. Fica no payload porque o cálculo já está feito e a tela do
        # Panorama vai pedi-lo inteiro.
        "peso_na_especialidade": _peso_na_especialidade(r, nome),
        # TRÊS medidas num payload só (2026-08-31): exames, custo e excesso por
        # consulta. Trocar de medida é LEITURA, não recorte, e por isso viajam
        # juntas: uma ida ao servidor para mudar de eixo faria parecer que o
        # conjunto medido mudou junto.
        # A COR dos pontos é o excedente em R$ nas três (2026-08-20), da mesma
        # fonte que alimenta o Pareto e os KPIs: um dinheiro só, três blocos.
        # `custo_coop` é a MESMA fonte da coluna "Custo por consulta" da tabela,
        # já buscada acima: gráfico e lista não podem discordar do mesmo número.
        "distribuicao": blocos.distribuicao(posicao, norma_linha, gatilho,
                                            rotulos_posicao, p.referencia,
                                            casc["excedente_reais_coop"],
                                            piso=r["piso_aplicado"],
                                            custo_por_coop=custo_coop),
        # bloco experimental: quantidade no X, custo no Y, porte no tamanho
        "dispersao": blocos.dispersao(posicao, casc["valor_total_coop"],
                                      rotulos_posicao,
                                      casc["excedente_reais_coop"]),
        # Blocos de ACHADO (os três cards e os dois Paretos): os únicos deste
        # payload que seguem o recorte.
        # Os dois Paretos somam o mesmo total por construção, sob qualquer
        # recorte, porque o corte é o mesmo conjunto antes das duas agregações.
        **achado,
        "cooperados": {
            "total": len(posicao),
            "ordenado_por": "variação excedente",
            "filtros": _chips_cascata(casc),
            # RECORTE POR PERFIL: quem aparece, nunca contra quem se compara
            "perfis": perfis_area,
            # fecha a conta da composição: comparáveis sem nenhum sub-perfil
            "sem_perfil": blocos.sem_sub_perfil(posicao, classificacao),
            "linhas": linhas_coop,
            "rodape": {
                "esquerda": (f"{n_formam} formam a referência · "
                             f"{int((~posicao['avaliavel']).sum())} abaixo do volume "
                             f"mínimo, listados sem comparação"),
                "direita": (f"referência: n={n_formam}" if norma_linha is None else
                            f"referência: n={n_formam} · "
                            f"mediana {blocos.fmt(norma_linha['mediana'])} · "
                            f"P75 {blocos.fmt(norma_linha['p75'])} · "
                            f"P90 {blocos.fmt(norma_linha['p90'])}"),
            },
        },
        # Classificação pendente: a fila REAL é quem passa o piso — só esses
        # têm volume para uma triagem clínica render decisão. O restante é baixo
        # volume, indefinido legítimo: fica listado, fora da fila.
        "fila_classificacao_pendente": None if nome != config.AREA_INDEFINIDA else {
            "n_fila": int(posicao["avaliavel"].sum()),
            "n_baixo_volume": int((~posicao["avaliavel"]).sum()),
            "n_total": len(posicao),
            "ids_fila": sorted(posicao.loc[posicao["avaliavel"], "ID_COOPERADO"]),
            "nota": (f"{int(posicao['avaliavel'].sum())} cooperados têm volume "
                     f"para triagem clínica; os outros "
                     f"{int((~posicao['avaliavel']).sum())} estão abaixo do "
                     "volume mínimo, indefinido legítimo, sem fila."),
        },
        "cascata": {
            "degraus": casc["funil"],
            "default": casc["default"]["chave"],
            "triou": casc["default"]["triou"],
            "achado": casc["default"]["achado"],
            "fatores_de_contexto": casc["confundidores"],
            "nota": ("Cada degrau filtra o que sobrou do anterior. Validade "
                     "sustenta o número; triagem só ordena o trabalho."),
        },
        "consistencia": {
            "reportavel": persistencia is not None,
            "n_trimestres": len(fatias),
            "trimestres": [{"inicio": i, "fim": f} for i, f in fatias],
            "resto_dias_fora": resto_dias,
            "motivo": (None if persistencia is not None else
                       f"a janela comporta {len(fatias)} trimestre(s) completo(s), "
                       f"mínimo de {config.MIN_JANELAS_AVALIAVEIS} para a "
                       "consistência ser reportável"),
        },
        "caption": ("Todos os números desta tela são calculados apenas entre os "
                    "cooperados desta área de atuação. Quem aparece acima do "
                    "critério de revisão está acima em relação a estes pares, "
                    "não à cooperativa inteira. Cada dedução é verificada e "
                    "auditável; a conclusão é do comitê."),
        "proveniencia": _proveniencia(p, r),
    }


@app.get("/api/area/{area_id}/achados", tags=["tela área"])
def area_achados(area_id: Annotated[str, PathParam(description="id da área (slug), de /api/meta")],
                 p: ParametrosDep,
                 recorte: RecorteQ = None, perfil: PerfilQ = None) -> dict[str, Any]:
    """Só os blocos que SEGUEM O RECORTE: os três cards e os dois Paretos.

    Existe para a troca de chip não ter de rebuscar a área inteira. Devolve
    exatamente as mesmas chaves que `/api/area/{id}` traz na carga inicial —
    é a mesma função que monta as duas, e é por isso que clicar no recorte que
    já estava ativo não muda nada na tela.
    """
    return {k: v for k, v in area(area_id, p, recorte, perfil).items()
            if k in ("recorte", "cards", "pareto_cooperados",
                     "pareto_procedimentos")}


@app.get("/api/area/{area_id}/procedimentos", tags=["tela área"])
def area_procedimentos(area_id: Annotated[str, PathParam(description="id da área (slug), de /api/meta")],
                       p: ParametrosDep,
                       recorte: RecorteQ = None, perfil: PerfilQ = None) -> dict[str, Any]:
    """Aba Procedimentos: prevalência, solicitantes elegíveis, referência,
    qualidade da referência, quantos estão acima do critério, variação
    excedente e % acumulado.

    O recorte alcança METADE da tabela — o achado (acima do critério, variação
    excedente, R$, % acumulado). Prevalência, solicitantes, referência e
    qualidade são RÉGUA e não se movem; ver `blocos.linhas_procedimentos`.
    """
    r = _rodar(p)
    nome = _resolver_area(r, area_id)

    posproc = r["posicao_proc"][r["posicao_proc"]["AREA_ATUACAO"] == nome]
    norma_proc = r["norma_proc"][r["norma_proc"]["AREA_ATUACAO"] == nome].copy()
    posicao = r["posicao"][r["posicao"]["AREA_ATUACAO"] == nome]
    gatilho = _gatilho_da_area(posicao)
    n_formam = int(_norma_linha(r, nome)["n_na_norma"]) if _norma_linha(r, nome) is not None else 0

    # o gatilho efetivo de CADA par vem do motor (degrada pelo n de solicitantes
    # daquele procedimento, não pelo n da área) — lido, nunca recalculado aqui
    gat_por_proc = (posproc.drop_duplicates("CD_PROCEDIMENTO")
                    .set_index("CD_PROCEDIMENTO")["gatilho_usado"])
    norma_proc["gatilho_usado"] = norma_proc["CD_PROCEDIMENTO"].map(gat_por_proc)

    # R$ estimado por procedimento: a MESMA soma da cascata, lida do run de
    # execução em cache — nada nasce aqui
    re_ = dados.rodar_pipeline_execucao(
        p.janela_ini, p.janela_fim, p.piso, p.n_minimo, config.PISO_EXECUCOES_ANO,
        config.Q_CONFUNDIDOR, None, p.criterio, p.referencia, p.incluir_ps)
    rs = re_["posicao_proc_rs"]
    rs = filtrar_sinalizados(rs[rs["AREA_ATUACAO"] == nome], exigir_preco=True)

    # ── o recorte, que só alcança o achado ───────────────────────────────────
    casc = _cascata_area(nome, p.janela_ini, p.janela_fim, p.piso, p.n_minimo,
                         p.criterio, p.referencia, p.incluir_ps)
    perfis_area = blocos.perfis_da_area(posicao, dados.carregar_classificacao())
    ids, rotulo_rec, _ = _em_cena(
        recorte, perfil, _linhas_para_recorte(posicao, casc, perfis_area),
        perfis_area)
    # o R$ por procedimento é achado, e é cortado pelo MESMO conjunto que corta
    # as demais colunas de achado — dois cortes diferentes na mesma linha
    # dariam R$ de uma população e excedente de outra
    rs_em_cena = rs[rs["ID_COOPERADO"].isin(ids)] if len(rs) else rs
    reais_proc = (rs_em_cena.groupby("CD_PROCEDIMENTO")["excedente_reais"]
                  .sum().to_dict() if len(rs_em_cena) else {})

    linhas = blocos.linhas_procedimentos(norma_proc, posproc, p.criterio,
                                         p.referencia, reais_proc, ids)
    apresentaveis = sum(1 for linha in linhas if linha["qualidade"]["apresentavel"])
    return {
        "area": {"id": blocos.slug(nome), "nome": nome,
                 "n_formam_referencia": n_formam, "gatilho_usado": gatilho},
        "estado": blocos.estado_area(nome, n_formam, gatilho, p.criterio),
        "recorte": {"chave": recorte, "rotulo": rotulo_rec, "n": len(ids)},
        "resumo": {
            "total": len(linhas),
            "com_referencia_apresentavel": apresentaveis,
            "sem_referencia_apresentavel": len(linhas) - apresentaveis,
            "excedente_total": round(sum(linha["excedente_itens"] for linha in linhas), 2),
            "nota_n_minimo": (f"referência conclusiva exige ≥ {p.n_minimo} "
                              "solicitantes"),
            # a declaração de população, para o subtítulo da aba: régua imóvel
            # de um lado, achado recortado do outro, dito em voz alta
            "subtitulo_recorte": blocos.subtitulo_recorte(rotulo_rec, len(ids)),
        },
        "ordenado_por": "variação excedente (magnitude); razão acompanha como 2ª lente",
        "linhas": linhas,
        "proveniencia": _proveniencia(p, r),
    }


@app.get("/api/cooperado/{cooperado_id}", tags=["tela dossiê"])
def cooperado_dossie(cooperado_id: Annotated[str, PathParam(description="id do cooperado (ex.: cooperado_85)")],
                     p: ParametrosDep) -> dict[str, Any]:
    """Dossiê do cooperado (espec §3): a evidência de UM caso, montada dos
    MESMOS motores da tela de área — tudo em cache, nenhum número novo nasce
    aqui. A linha do cooperado vem da própria montagem da área (concordância
    por construção), e o dossiê acrescenta o que a tabela não tem espaço para
    mostrar: a lente por procedimento, o contexto e a confiança."""
    r = _rodar(p)
    pos_all = r["posicao"]
    sel = pos_all[pos_all["ID_COOPERADO"] == cooperado_id]
    if sel.empty:
        raise HTTPException(404, f"cooperado desconhecido: {cooperado_id}")
    nome = str(sel.iloc[0]["AREA_ATUACAO"])

    # a tela de área já monta linha, estado, paretos e proveniência: reusa
    base = area(area_id=blocos.slug(nome), p=p)
    linha = next((l for l in base["cooperados"]["linhas"]
                  if l["id"] == cooperado_id), None)
    if linha is None:
        raise HTTPException(404, f"cooperado fora da área {nome}: {cooperado_id}")

    posicao_area = pos_all[pos_all["AREA_ATUACAO"] == nome]
    pacientes = dados.rodar_pacientes_distintos(p.janela_ini, p.janela_fim,
                                                p.incluir_ps)

    casc = _cascata_area(nome, p.janela_ini, p.janela_fim, p.piso, p.n_minimo,
                         p.criterio, p.referencia, p.incluir_ps)
    posproc = r["posicao_proc"]
    posproc_coop = posproc[(posproc["AREA_ATUACAO"] == nome)
                           & (posproc["ID_COOPERADO"] == cooperado_id)]

    fatias = dados.fatiar_trimestres(p.janela_ini, p.janela_fim)
    persist_coop = None
    if len(fatias) >= config.MIN_JANELAS_AVALIAVEIS:
        pers = dados.rodar_persistencia(fatias, p.piso, p.n_minimo, p.criterio,
                                        p.referencia, None,
                                        config.MIN_JANELAS_AVALIAVEIS, p.incluir_ps)
        pp = pers["por_procedimento"]
        persist_coop = pp[pp["ID_COOPERADO"] == cooperado_id]

    pares, conf = casc.get("pares"), casc.get("conf")
    pares_coop = (pares[pares["ID_COOPERADO"] == cooperado_id]
                  if pares is not None and len(pares) else None)
    conf_coop = (conf[conf["ID_COOPERADO"] == cooperado_id]
                 if conf is not None and len(conf) else None)

    re_ = dados.rodar_pipeline_execucao(
        p.janela_ini, p.janela_fim, p.piso, p.n_minimo,
        config.PISO_EXECUCOES_ANO, config.Q_CONFUNDIDOR, None,
        p.criterio, p.referencia, p.incluir_ps)
    rs = re_["posicao_proc_rs"]
    rs_coop = filtrar_sinalizados(
        rs[(rs["AREA_ATUACAO"] == nome) & (rs["ID_COOPERADO"] == cooperado_id)],
        exigir_preco=True)
    reais_por_proc = (rs_coop.groupby("CD_PROCEDIMENTO")["excedente_reais"]
                      .sum().to_dict() if len(rs_coop) else {})

    resumo = re_["resumo_coop"]
    m = resumo[resumo["ID_COOPERADO"] == cooperado_id]
    resumo_row = m.iloc[0].to_dict() if len(m) else None
    perfil = re_["perfil_execucao"]
    m = perfil[perfil["ID_COOPERADO"] == cooperado_id]
    perfil_row = m.iloc[0].to_dict() if len(m) else None

    # o lugar dele no Pareto da área: leitura da ordem já entregue pelo motor
    par = base.get("pareto_cooperados") or {}
    barra = next(({"posto": i, "total": len(par["linhas"]),
                   "pct_do_total_fmt": l["pct_do_total_fmt"],
                   "no_nucleo": l["no_nucleo"]}
                  for i, l in enumerate(par.get("linhas", []), start=1)
                  if l["id"] == cooperado_id), None)

    # preço de TODOS os procedimentos dele (não só os sinalizados): a tabela
    # também tem o recorte "todos", e custo unitário vazio ali seria ausência
    # inventada, não ausência real
    rs_todos = rs[(rs["AREA_ATUACAO"] == nome) & (rs["ID_COOPERADO"] == cooperado_id)]
    preco_por_proc = (rs_todos.set_index("CD_PROCEDIMENTO")["preco_mediano"].to_dict()
                      if len(rs_todos) else {})
    janelas_coop = None
    if persist_coop is not None:
        pj = pers["por_janela"]
        janelas_coop = pj[pj["ID_COOPERADO"] == cooperado_id]

    procs = blocos.procedimentos_do_cooperado(
        posproc_coop, persist_coop, pares_coop, conf_coop,
        reais_por_proc, len(fatias), preco_por_proc, janelas_coop,
        linha.get("solicitacoes"))

    return {
        "cooperado": {
            "id": cooperado_id,
            "area": base["area"],
            "sub_perfis": linha["sub_perfis"],
            "postos_perfil": linha["postos_perfil"],
            "em_revisao": linha["em_revisao"],
            "avaliavel": linha["avaliavel"],
            "forma_referencia": linha["forma_referencia"],
        },
        "estado": base["estado"],
        "cabecalho": blocos.cabecalho_dossie(
            linha, posicao_area, pacientes, base["cooperados"]["linhas"]),
        "leitura": {
            # o caso numa frase: subtítulo da Leitura, redigido no motor
            "frase": blocos.frase_do_caso(linha),
            "posicao": linha["posicao"],
            "estado_linha": linha["estado_linha"],
            "consistencia": linha["consistencia"],
            "origem_excedente": linha["origem_excedente"],
            "concentracao": linha["concentracao"],
            "excedente": {
                "itens_fmt": linha["excedente_fmt"],
                "motivo": linha["excedente_motivo"],
                "reais_fmt": linha["excedente_reais_fmt"],
                "piso_fmt": procs["piso_total_fmt"],
                "pareto": barra,
            },
            "grupos": linha["grupos"],
        },
        "procedimentos": procs,
        # onde está o dinheiro DELE, por procedimento, com a parcela acima da
        # referência dentro de cada barra. `rs_todos` já está montado acima para
        # o preço da tabela — nenhum motor novo roda por causa deste bloco.
        "pareto_custo": blocos.pareto_custo_do_cooperado(rs_todos),
        "contexto": blocos.contexto_do_cooperado(resumo_row, perfil_row),
        "justificativa": base.get("justificativa"),
        "proveniencia": base.get("proveniencia"),
    }


@app.get("/api/cooperado/{cooperado_id}/procedimento/{cd}", tags=["tela dossiê"])
def painel_procedimento(cooperado_id: Annotated[str, PathParam(description="id do cooperado")],
                        cd: Annotated[str, PathParam(description="código do procedimento")],
                        p: ParametrosDep) -> dict[str, Any]:
    """Painel lateral de UM procedimento do dossiê (espec §3).

    Segundo nível de evidência: abre quando uma linha da tabela chama atenção e
    responde "de onde vem esse volume". Nenhum número novo nasce aqui — todos
    saem dos mesmos motores da tela de área, em cache.

    É endpoint próprio, e não campo do dossiê, porque o custo é por
    procedimento: montar isto para os 269 procedimentos de um cooperado seria
    pagar 269 vezes por um painel que se abre uma vez.
    """
    r = _rodar(p)
    pos_all = r["posicao"]
    sel = pos_all[pos_all["ID_COOPERADO"] == cooperado_id]
    if sel.empty:
        raise HTTPException(404, f"cooperado desconhecido: {cooperado_id}")
    nome = str(sel.iloc[0]["AREA_ATUACAO"])

    posproc = r["posicao_proc"]
    par = posproc[(posproc["ID_COOPERADO"] == cooperado_id)
                  & (posproc["CD_PROCEDIMENTO"] == cd)]
    if par.empty:
        raise HTTPException(404, f"procedimento não solicitado por {cooperado_id}: {cd}")
    linha_par = par.iloc[0]

    # POSIÇÃO na distribuição do procedimento, em RÉGUA e não em gráfico de
    # pontos: aqui a pergunta é "onde ele está", e a forma da distribuição é
    # pergunta da tela de Área, que segue com o gráfico completo a um clique.
    #
    # O p25 não viaja em norma_proc (que carrega mediana/p75/p90): sai da MESMA
    # população que produziu os outros percentis — os formadores da norma neste
    # procedimento —, nunca de outra amostra.
    do_proc = posproc[(posproc["AREA_ATUACAO"] == nome)
                      & (posproc["CD_PROCEDIMENTO"] == cd)]
    formadores = do_proc[do_proc["elegivel_norma"].astype(bool)
                         & do_proc["avaliavel"]]["taxa"]
    regua = None
    if (bool(linha_par["apresentavel"]) and bool(linha_par["avaliavel"])
            and len(formadores)):
        regua = blocos.regua_do_procedimento(
            linha_par, float(formadores.quantile(0.25)),
            float(linha_par["taxa"]), p.criterio,
            taxas_pares=formadores.to_numpy())

    conc = dados.rodar_concentracao(p.janela_ini, p.janela_fim, p.piso,
                                    p.n_minimo, nome, p.incluir_ps)
    c = conc[(conc["ID_COOPERADO"] == cooperado_id) & (conc["CD_PROCEDIMENTO"] == cd)]
    conc_row = c.iloc[0] if len(c) else None

    pacientes = dados.pacientes_do_procedimento(cooperado_id, cd, p.janela_ini,
                                                p.janela_fim, p.incluir_ps)

    aut = dados.rodar_autorref_proc(p.janela_ini, p.janela_fim, nome, p.incluir_ps)
    a = aut[(aut["ID_COOPERADO"] == cooperado_id) & (aut["CD_PROCEDIMENTO"] == cd)]
    autorref_row = a.iloc[0] if len(a) else None

    # série de trimestres e piso de confiança: já calculados para o dossiê e até
    # hoje não exibidos por procedimento
    fatias = dados.fatiar_trimestres(p.janela_ini, p.janela_fim)
    serie = None
    if len(fatias) >= config.MIN_JANELAS_AVALIAVEIS:
        pers = dados.rodar_persistencia(fatias, p.piso, p.n_minimo, p.criterio,
                                        p.referencia, None,
                                        config.MIN_JANELAS_AVALIAVEIS, p.incluir_ps)
        pj = pers["por_janela"]
        serie = blocos._serie_do_procedimento(
            pj[pj["ID_COOPERADO"] == cooperado_id], cd, len(fatias))

    casc = _cascata_area(nome, p.janela_ini, p.janela_fim, p.piso, p.n_minimo,
                         p.criterio, p.referencia, p.incluir_ps)
    conf = casc.get("conf")
    conf_row = None
    if conf is not None and len(conf):
        cc = conf[(conf["ID_COOPERADO"] == cooperado_id) & (conf["CD_PROCEDIMENTO"] == cd)]
        conf_row = cc.iloc[0] if len(cc) else None

    # PESO E DINHEIRO deste procedimento. Vem dos mesmos motores em cache, e não
    # de uma chamada ao dossiê inteiro: montar as 269 linhas da tabela para ler
    # uma é pagar 269 vezes por um número.
    re_ = dados.rodar_pipeline_execucao(
        p.janela_ini, p.janela_fim, p.piso, p.n_minimo,
        config.PISO_EXECUCOES_ANO, config.Q_CONFUNDIDOR, None,
        p.criterio, p.referencia, p.incluir_ps)
    rs = re_["posicao_proc_rs"]
    linha_rs = rs[(rs["ID_COOPERADO"] == cooperado_id)
                  & (rs["CD_PROCEDIMENTO"] == cd)]
    preco = (float(linha_rs.iloc[0]["preco_mediano"])
             if len(linha_rs) and pd.notna(linha_rs.iloc[0]["preco_mediano"]) else None)
    # denominador do peso: tudo que o cooperado solicitou na janela
    total_coop = float(posproc[posproc["ID_COOPERADO"] == cooperado_id]
                       ["n_solicitacoes"].sum())

    return blocos.painel_do_procedimento(
        cd, str(linha_par.get("DS_PROCEDIMENTO", config.SEM_MEDIDA)).strip(),
        conc_row, pacientes, autorref_row, regua, serie,
        blocos._confianca_do_par(conf_row), linha_par, conc_row, preco, total_coop)


# ─────────────────────────────────────────────────────────────────────────────
# /api/conta — quem está usando o app (tela Minha conta + bloco da lateral)
# ─────────────────────────────────────────────────────────────────────────────
#
# Único endpoint do app que não fala de análise, e por isso não recebe
# `ParametrosDep`: a régua não governa nada aqui.
#
# Contato de suporte: fica `None` até existir um endereço de verdade. A tela
# OMITE a linha quando não há valor, em vez de imprimir um lugar vazio (ajuste
# 1 do CLAUDE.md, ausência de atributo não vira etiqueta).
CONTATO_SUPORTE: str | None = None


@app.get("/api/conta", tags=["conta"])
def conta(request: Request) -> dict[str, Any]:
    """Identidade da sessão, estado da segurança e versão do app.

    Sempre 200, inclusive sem sessão: "ninguém autenticado" é um ESTADO que a
    tela desenha, não um erro que ela trata. 401 aqui faria a própria tela de
    conta cair no banner de falha genérico, que é o oposto do que ela existe
    para fazer.
    """
    usuario = sessao.usuario_da_requisicao(request)
    app_ = {
        "versao": config.PIPELINE_VERSAO,
        "classificacao": config.CLASSIFICACAO_VERSAO,
        "suporte": CONTATO_SUPORTE,
    }
    if usuario is None:
        return {
            "autenticado": False,
            # A tela mostra esta frase; ela diz o que está acontecendo, não o
            # que deu errado, porque nada deu errado.
            "motivo": "A autenticação de acesso ainda não foi ativada neste ambiente.",
            "app": app_,
        }
    return {
        "autenticado": True,
        "usuario": usuario.para_tela(),
        # Tudo `None` enquanto não há provedor: a tela declara o estado em vez
        # de oferecer botão que não leva a lugar nenhum.
        #
        # `duas_etapas` tem TRÊS valores, e a distinção é de produto:
        #   True  -> ativa
        #   False -> prevista na política de acesso, ainda não configurada
        #   None  -> FORA da política; a tela OMITE a linha
        # O MVP vai SEM segundo fator (decisão de 29/ago), então aqui segue
        # `None` mesmo depois que o provedor entrar. Vira `False` no dia em que
        # a política do pool passar a prever MFA.
        "seguranca": {
            "provedor": None,
            "url_senha": None,
            "url_duas_etapas": None,
            "duas_etapas": None,
        },
        "app": app_,
    }


@app.get("/sair", include_in_schema=False)
def sair(request: Request):
    """Encerra a sessão e devolve à porta de entrada.

    Apaga o cookie mesmo quando não há provedor configurado: o dia em que
    houver, só falta acrescentar o redirecionamento ao logout dele, e o resto
    do caminho (botão, rota, limpeza) já estará provado em uso.
    """
    resposta = RedirectResponse("/", status_code=303)
    resposta.delete_cookie(sessao.COOKIE_SESSAO, httponly=True, samesite="lax")
    return resposta


# ─────────────────────────────────────────────────────────────────────────────
# Estáticos — o contrato visual servido pela mesma origem da API
# ─────────────────────────────────────────────────────────────────────────────

# UM hospedeiro para todas as telas: `index.html` carrega o contrato visual e
# `inicio.js` escolhe o módulo da página pela rota. Tela nova = um arquivo em
# static/paginas/ + uma linha em inicio.js + uma rota aqui; o HTML não muda.
PAGINA = ESTATICOS / "index.html"


# ── as telas ────────────────────────────────────────────────────────────────
# O CAMINHO diz o que se olha; a QUERY diz como (a régua da análise). Área e
# cooperado são coisas e viajam no caminho; janela, critério e piso viajam na
# query, iguais em toda tela. O mapa completo está em static/lib/rotas.js.

@app.get("/", include_in_schema=False)
def raiz(area: Annotated[str | None, Query(include_in_schema=False)] = None):
    """Panorama de oportunidades, a porta de entrada (espec §1).

    `?area=` era como a Área de atuação vivia aqui, quando era a única tela.
    Links assim já foram compartilhados, então continuam funcionando: viram um
    redirecionamento para o caminho novo em vez de abrir a tela errada.
    """
    if area:
        return RedirectResponse(f"/area/{area}", status_code=308)
    return FileResponse(PAGINA)


@app.get("/area/{area_id}", include_in_schema=False)
def tela_area(area_id: str):
    """Área de atuação: o peer group visível (espec §2)."""
    return FileResponse(PAGINA)


@app.get("/cooperados", include_in_schema=False)
def tela_cooperados():
    """Índice de cooperados: a porta para um caso quando não se sabe a área.

    Plural porque é a COLEÇÃO. `/cooperado/{id}`, no singular, é o dossiê de um.
    """
    return FileResponse(PAGINA)


@app.get("/cooperado/{cooperado_id}", include_in_schema=False)
def tela_cooperado(cooperado_id: str):
    """Dossiê do cooperado: a evidência de um caso (espec §3).

    O nome da rota é a COISA (cooperado), não a tela (dossiê) — é o que a API
    já expunha em /api/cooperado/{id}, e é o que sobrevive a um redesenho.
    """
    return FileResponse(PAGINA)


@app.get("/metodologia", include_in_schema=False)
def tela_metodologia():
    """Nota metodológica: o método e as defesas escritas (espec §4)."""
    return FileResponse(PAGINA)


@app.get("/conta", include_in_schema=False)
def tela_conta():
    """Minha conta: identidade da sessão e segurança do acesso.

    Não está na espec funcional porque não é tela de análise: nenhum motor a
    alimenta e nenhum número dela é comparado. É o entorno que todo app tem, e
    a porta é o bloco de conta no rodapé da lateral.
    """
    return FileResponse(PAGINA)


# ── rotas antigas ───────────────────────────────────────────────────────────
# Links de evidência são mandados por e-mail e sobrevivem à refatoração; quebrar
# um deles é quebrar a confiança no produto. 308 preserva o método e a query.

@app.get("/dossie/{cooperado_id}", include_in_schema=False)
def dossie_legado(cooperado_id: str):
    return RedirectResponse(f"/cooperado/{cooperado_id}", status_code=308)


@app.get("/dossie", include_in_schema=False)
def dossie_escolha_legado():
    """A escolha de cooperado saiu (14/ago): duplicava a tabela da Área, e é de
    lá (ou do Panorama) que se chega a um caso. Volta como busca global se um
    dia a busca da barra superior for construída."""
    return RedirectResponse("/", status_code=308)


# O contrato visual não mora mais em disco: a fonte da verdade é o projeto do
# Claude Design (ver CLAUDE.md § Contrato visual). A rota sobrevive como atalho
# para não quebrar o hábito de abrir /guia ao lado da tela.
GUIA_VISUAL = "https://claude.ai/design/p/3a94742c-5e71-4672-aaa8-8ac768f9a7fd"


@app.get("/guia", include_in_schema=False)
def guia_visual():
    """Redireciona ao contrato visual no Claude Design (exige login)."""
    return RedirectResponse(GUIA_VISUAL)


app.mount("/static", StaticFiles(directory=ESTATICOS), name="static")


@app.middleware("http")
async def _sem_cache_no_front(request, call_next):
    """`no-cache` em TUDO que o navegador guarda do front: estáticos e as rotas
    de página.

    Sem Cache-Control o navegador aplica cache heurístico e segura a resposta
    antiga sem revalidar. Cobria só `/static`, e o buraco apareceu na
    reestruturação de rotas (14/ago): `/` servia `area.html` até então, e quem
    tinha a tela aberta continuou vendo a Área no lugar do Panorama, com a
    navegação antiga na lateral.

    `no-cache` não desliga o cache: o navegador revalida a cada carga e recebe
    304 quando nada mudou. Só o impede de ficar cego a uma mudança."""
    resposta = await call_next(request)
    if not request.url.path.startswith("/api"):
        resposta.headers["Cache-Control"] = "no-cache"
    return resposta
