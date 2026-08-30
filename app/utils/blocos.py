"""blocos, monta os BLOCOS DA TELA "Área de atuação" a partir da saída dos motores.

Esta camada não calcula nada (Lei 1): ela LÊ o resultado do pipeline canônico e
o reorganiza no formato que cada bloco do contrato visual consome. Cada função
daqui corresponde a um componente do guia visual (Claude Design, projeto
"Medyx - Style tile Enterprise", ver CLAUDE.md § Contrato visual):

    composicao_referencia  -> §08 "Barra de composição segmentada" (+ excluídos)
    contexto_da_area       -> linha de texto sob o título; ocupou o lugar da
                              §08 "Faixa de estatísticas" em 2026-08-19
    distribuicao           -> §05 "Distribuição do índice de solicitação"
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
from utils.pipeline import filtrar_sinalizados

# Estados de uma área — governam o que a tela pode mostrar (espec funcional, regra 5).
# Cada um tem tratamento visual próprio no guia; nenhum é silencioso.
#
# Área SEM NENHUM formador de norma (Reprodução, Ultrassonografista) NÃO é um
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
#   provisoria — exclusão por regra da classificação v1.0 ainda em validação;
#                quando se sabe que a regra produz falso positivo naquela área,
#                o status de triagem pendente aparece na tela e alimenta o loop
#                de correção da classificação (o app não esconde a pendência).
# Nenhum destes cooperados sai da análise: seguem MEDIDOS contra a referência.

MOTIVO_ULTRASSONOGRAFISTA = "perfil_ultrassonografista"
MOTIVO_ALERTA_MASCULINO = "alerta_perfil_masculino"
MOTIVO_CONFIANCA_BAIXA = "confianca_baixa"
MOTIVO_CLASSIFICACAO_PENDENTE = "classificacao_pendente"
MOTIVO_DIVERGENCIA = "classificacao_em_revisao"
MOTIVO_VOLUME = "volume_abaixo_do_minimo"
MOTIVO_PERFIL_FORA_DA_ESPECIALIDADE = "perfil_fora_da_especialidade"

_CATALOGO_MOTIVOS = {
    MOTIVO_ULTRASSONOGRAFISTA: {
        "rotulo": "perfil de execução: não solicita",
        "natureza": "definitiva",
        "detalhe": ("Atua no lado da execução; a referência mede solicitação. "
                    "Exclusão por desenho da análise: não é achado sobre o "
                    "cooperado, e não há classificação a corrigir."),
    },
    MOTIVO_ALERTA_MASCULINO: {
        "rotulo": "alerta de perfil (pacientes homens)",
        "natureza": "provisoria",
        "detalhe": ("Fração atípica de pacientes homens para a área. Regra "
                    "provisória da classificação v1.0, em validação clínica."),
    },
    MOTIVO_CONFIANCA_BAIXA: {
        "rotulo": "confiança baixa da classificação",
        "natureza": "provisoria",
        "detalhe": ("A classificação de área foi atribuída com confiança baixa; "
                    "até a validação, o cooperado não define a referência."),
    },
    MOTIVO_CLASSIFICACAO_PENDENTE: {
        "rotulo": "classificação pendente",
        "natureza": "provisoria",
        "detalhe": ("Sem área de atuação atribuída: sem grupo de pares, fora de "
                    "comparação até a triagem clínica."),
    },
    MOTIVO_DIVERGENCIA: {
        "rotulo": "classificação em revisão (divergência com o médico)",
        "natureza": "provisoria",
        "detalhe": ("O rótulo do médico diverge da leitura estatística; o caso "
                    "voltou ao médico. Artefato de classificação, não achado."),
    },
    MOTIVO_PERFIL_FORA_DA_ESPECIALIDADE: {
        "rotulo": "perfil de solicitação fora da especialidade",
        "natureza": "provisoria",
        "detalhe": ("O que este cooperado solicita não pertence ao escopo da "
                    "especialidade classificada. Possível erro de classificação, "
                    "não achado sobre a prática: até a triagem clínica decidir, "
                    "ele não forma referência nenhuma."),
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

    O alerta de perfil masculino recebe tratamento especial nas especialidades
    em que o paciente homem é assinatura da prática
    (config.ESPECIALIDADES_PACIENTE_MASCULINO_ESPERADO): a exclusão permanece ,
    a regra v1.0 vigora e não se burla regra em silêncio, mas viaja marcada
    como falso positivo previsível, com o status de triagem clínica pendente que
    alimenta o loop de correção da classificação.
    """
    saida: dict[str, list[dict]] = {}
    for _, linha in classificacao.iterrows():
        coop = linha["ID_COOPERADO"]
        especialidade = linha.get("especialidade")
        motivos = []
        if linha.get("sub_ultrassonografista"):
            motivos.append(_motivo(MOTIVO_ULTRASSONOGRAFISTA))
        if linha.get("alerta_perfil_masculino"):
            esperado = especialidade in config.ESPECIALIDADES_PACIENTE_MASCULINO_ESPERADO
            motivos.append(_motivo(
                MOTIVO_ALERTA_MASCULINO,
                detalhe_extra=(
                    f"Em {especialidade}, o paciente masculino é assinatura da "
                    "especialidade (espermograma), não anomalia. A regra v1.0 "
                    "que gerou esta exclusão é provisória e produz aqui um falso "
                    "positivo previsível."
                ) if esperado else None,
                revisao={
                    "pendente": True,
                    "rotulo": "triagem clínica pendente",
                    "falso_positivo_previsivel": True,
                    "acao": ("confirmar com o médico e reclassificar; "
                             "alimenta o loop de correção da classificação"),
                } if esperado else None,
            ))
        if linha.get("confianca") == "baixa":
            motivos.append(_motivo(MOTIVO_CONFIANCA_BAIXA))
        if especialidade == config.AREA_INDEFINIDA:
            motivos.append(_motivo(MOTIVO_CLASSIFICACAO_PENDENTE))
        if coop in config.COOPERADOS_CLASSIFICACAO_EM_REVISAO:
            motivos.append(_motivo(MOTIVO_DIVERGENCIA, revisao={
                "pendente": True,
                "rotulo": "classificação em revisão",
                "falso_positivo_previsivel": False,
                "acao": "aguardando retorno do médico sobre a divergência",
            }))
        # Mesma fila das divergências acima, motivo diferente: lá o rótulo do
        # médico diverge da leitura estatística; aqui o perfil de solicitação
        # não pertence à especialidade inteira.
        if coop in config.COOPERADOS_PERFIL_FORA_DA_ESPECIALIDADE:
            motivos.append(_motivo(MOTIVO_PERFIL_FORA_DA_ESPECIALIDADE, revisao={
                "pendente": True,
                "rotulo": "triagem clínica pendente",
                "falso_positivo_previsivel": False,
                "acao": ("confirmar a especialidade com o médico; o que ele "
                         "solicita é de outra área"),
            }))
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
    credibilidade. Abaixo de 0,1 a escala pede uma terceira casa.
    """
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return config.SEM_MEDIDA
    v = float(valor)
    if 0 < v < 0.001:
        return "< 0,001"
    return fmt(v, 3 if v < 0.1 else 2)


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
            "titulo": "Sem grupo de pares",
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
            "titulo": "Grupo de pares insuficiente para análise comparativa",
            "frase_apoio": (
                "sem referência: nenhum cooperado desta área forma a norma, "
                "motivos abaixo" if sem_formadores else
                "grupo de pares insuficiente para análise comparativa"),
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
                "titulo": ("nenhum solicitante elegível no grupo de pares"
                           if sem_formadores else
                           f"n<{config.N_MINIMO_P75} solicitantes no grupo de pares"),
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
                "titulo": f"n<{config.N_MINIMO_P90} solicitantes no grupo de pares",
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
    """A declaração de população dos blocos de achado. Sem ela, dois blocos da
    mesma tela somam conjuntos diferentes sem dizer qual é qual — que é
    exatamente o defeito que este recorte veio corrigir."""
    return f"excedente somado sobre: {rotulo} ({fmt(n, 0)})"


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
         "titulo_longo": ("exames solicitados dividido por consultas atendidas, "
                          "somando todos os cooperados em cena")},
        {"chave": "custo_por_consulta", "rotulo": "Custo por consulta",
         "valor": None if custo_cons is None else round(custo_cons, 2),
         "valor_fmt": (config.SEM_MEDIDA if custo_cons is None
                       else fmt_reais(custo_cons)),
         "apoio": "em quarentena",
         "titulo_longo": ("o valor de tudo que se solicitou dividido pelas "
                          "consultas atendidas · preço provisório até a tabela "
                          "contratual entrar no pipeline")},
        {"chave": "itens", "rotulo": "Excesso de solicitações",
         "valor": itens, "valor_fmt": fmt(itens, 0),
         "apoio": "acima do padrão do grupo",
         "titulo_longo": None},
        {"chave": "reais", "rotulo": "Excesso em R$",
         "valor": round(reais, 2), "valor_fmt": fmt_reais(reais),
         # o apoio cabe em UMA linha: o pontilhado de hover sublinha o texto
         # inteiro, e em duas linhas ele risca o KPI de ponta a ponta. O custo
         # dos N exames é o que o card ao lado já diz; aqui fica a ressalva.
         "apoio": "em quarentena",
         "titulo_longo": (f"o custo dos {fmt(itens, 0)} exames acima do padrão, "
                          "calculado exame a exame contra a referência de cada "
                          "um · preço provisório até a tabela contratual. Não "
                          "é economia realizada")},
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


def subtitulo_recorte(rotulo: str, n: int) -> str:
    """A declaração de população dos blocos de achado. Sem ela, dois blocos da
    mesma tela somam conjuntos diferentes sem dizer qual é qual — que é
    exatamente o defeito que este recorte veio corrigir."""
    return f"excedente somado sobre: {rotulo} ({fmt(n, 0)})"


def contexto_da_area(gatilho_usado: str | None, criterio_pedido: str,
                     excedente_itens: float, excedente_reais: float | None,
                     n_sinalizados: int, n_comparaveis: int,
                     n_total: int, n_excluidos: int,
                     estado_codigo: str, n_formam: int | None = None,
                     n_com_excedente: int | None = None) -> dict:
    """O CONTEXTO FIXO DA ÁREA, em uma linha de texto sob o título:

        64 na área · 63 comparáveis (ver os 6 fora da referência) ·
        8 acima do critério · 96.048 solicitações excedentes ·
        R$ 3,1 mi (em quarentena)

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
    motivo = ("sem grupo de pares · classificação de área de atuação pendente"
              if estado_codigo == ESTADO_SEM_PEER_GROUP else
              "grupo insuficiente para formar referência")

    # Nomear o índice não é redundância com "acima do critério": a parte diz que
    # está acima, o hover diz acima do quê. O mesmo cooperado pode estar dentro
    # no agregado e acima em procedimentos específicos.
    hover_revisao = "cooperados acima do critério de revisão no índice agregado"
    if ajustado:
        hover_revisao += (f" · critério {gatilho_usado.upper()}, "
                          "ajustado ao tamanho do grupo")

    # `valor` cru ao lado do texto em toda parte, como manda a regra de
    # formatação do módulo: o front imprime `texto`, e quem cruza número com
    # número (as provas, uma exportação futura) lê `valor` sem reparsear frase.
    partes = [
        {"chave": "na_area", "valor": n_total,
         "texto": f"{fmt(n_total, 0)} na área",
         "acao": None,
         "titulo_longo": "cooperados da área com atividade no período"},
        {"chave": "comparaveis", "valor": n_comparaveis,
         "texto": f"{fmt(n_comparaveis, 0)} comparáveis",
         # o link mora DENTRO da parte, entre parênteses, porque é o complemento
         # deste número e de nenhum outro: quem não entrou na formação da régua
         "acao": (None if not n_excluidos else
                  {"chave": "excluidos",
                   "rotulo": f"ver {'o' if n_excluidos == 1 else 'os'} "
                             f"{fmt(n_excluidos, 0)} fora da referência"}),
         "titulo_longo": (
             "volume suficiente para comparação; é o mesmo conjunto do recorte "
             "Comparáveis"
             + ("" if n_formam is None else
                f". A referência é formada por {fmt(n_formam, 0)} deles, e "
                "define o padrão contra o qual todos são medidos, inclusive "
                "quem não entra nela"))},
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
             "titulo_longo": ("cooperados com ao menos um procedimento acima do "
                              "critério DAQUELE exame; é a população que gera o "
                              "excedente e o R$ da página")})
    partes.append(
        {"chave": "em_revisao", "valor": n_sinalizados,
         # "também" amarra esta leitura à anterior em vez de abrir uma
         # contagem paralela; "no índice agregado" diz de que eixo ela fala
         "texto": f"{fmt(n_sinalizados, 0)} também atípicos no índice agregado",
         "acao": None, "titulo_longo": hover_revisao})
    partes.append(
        {"chave": "excedente", "valor": float(excedente_itens),
         "texto": f"{fmt(excedente_itens, 0)} solicitações excedentes",
         "acao": None,
         "titulo_longo": ("solicitações acima da referência de adequação, entre "
                          "os casos acima do critério")})
    # o R$ é a MESMA grandeza em outra unidade, e por isso parte própria em vez
    # de emenda na anterior: duas medições independentes é o que ele não é
    if excedente_reais is not None:
        partes.append(
            {"chave": "excedente_reais", "valor": float(excedente_reais),
             "texto": f"{fmt_reais(excedente_reais)} (em quarentena)",
             "acao": None,
             "titulo_longo": ("as mesmas solicitações excedentes valoradas a "
                              "preços de referência internos (mediana das contas "
                              "por procedimento), até a tabela oficial da Unimed "
                              "ser injetada no pipeline")})
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

def distribuicao(posicao_area: pd.DataFrame, norma_linha, gatilho_usado: str | None,
                 rotulos_posicao: pd.Series, referencia: str = "mediana",
                 excedente_por_coop: dict[str, float] | None = None) -> dict | None:
    """Um ponto por cooperado avaliável, com as linhas de referência rotuladas.

    Devolve None quando a área não sustenta distribuição (grupo insuficiente,
    sem referência, sem peer group): o guia proíbe gráfico sem critério visível.

    ── a COR passou a ser o DINHEIRO (2026-08-20) ───────────────────────────
    Cada ponto é tingido pelo EXCEDENTE EM R$ do cooperado, do neutro ao
    vermelho. Antes a cor era severidade — cinza / acima do P75 / acima do
    critério —, e havia dois problemas nisso.

    O primeiro: o critério agregado não governa nada. Não filtra a cascata, não
    entra em nenhum R$, não decide quem vai a comitê. Produzia uma contagem na
    tela e a cor dos pontos, e nada mais. Era régua que não media.

    O segundo, que é o grave: 46 dos 63 cooperados ficavam CINZA com a legenda
    "abaixo do P75", e esses 46 carregavam 34% do dinheiro da área. O gráfico
    convidava a concluir que o problema eram os 8 vermelhos, quando metade do
    excedente estava fora deles.

    Com a cor no dinheiro, o gráfico responde uma pergunta por canal: POSIÇÃO
    diz quanto o cooperado pede, COR diz quanto isso custa, e a caixa IQR diz
    como o grupo se espalha. Nenhuma régua fingida.

    A escala é por QUANTIL, não por valor: o excedente vai de dezenas de milhares
    a centenas de milhares, e uma rampa linear pintaria dois pontos vermelhos e
    sessenta e um quase brancos. Quantil dá gradação em toda a nuvem — e a
    escolha viaja declarada na legenda, porque escala de cor sem método anunciado
    faz o leitor supor proporcionalidade que não existe.

    As LINHAS de referência e critério saíram junto: sem paleta de severidade,
    elas eram as últimas réguas decorativas do bloco. Quem quiser ver régua de
    verdade vê no gráfico por exame, onde ela de fato rege.
    """
    if norma_linha is None or gatilho_usado is None:
        return None
    av = posicao_area[posicao_area["avaliavel"]]
    if av.empty:
        return None

    p25, p75 = float(norma_linha["p25"]), float(norma_linha["p75"])
    mediana = float(norma_linha["mediana"])
    taxas = av["taxa_exames_por_consulta"].astype(float).tolist()
    escala = _escala(taxas + [p25, p75])

    # ── a rampa de cor: posição do cooperado na ORDEM dos excedentes ─────────
    # Quem não tem excedente valorado fica em 0 (o extremo neutro da rampa) —
    # é ausência de dinheiro, e a rampa começa exatamente aí.
    exc = {c: float(v) for c, v in (excedente_por_coop or {}).items() if v > 0}
    ordem = sorted(exc.values())
    def _intensidade(coop: str) -> float:
        v = exc.get(coop)
        if v is None or len(ordem) < 2:
            return 0.0
        # fração de quem ele supera: 0 no menor, 1 no maior
        return round(ordem.index(v) / (len(ordem) - 1), 4)

    pontos = []
    for _, linha in av.sort_values("taxa_exames_por_consulta").iterrows():
        taxa = float(linha["taxa_exames_por_consulta"])
        rotulo_pos = rotulos_posicao.get(linha.name, config.SEM_MEDIDA)
        traducao = apr.traduzir_percentil(rotulo_pos)
        pontos.append({
            "id": linha["ID_COOPERADO"],
            "valor": round(taxa, 4), "valor_fmt": fmt(taxa),
            "pos_pct": _pos(taxa, escala),
            # `intensidade` é DADO (0–1); a tinta sai dele no CSS
            "intensidade": _intensidade(linha["ID_COOPERADO"]),
            "excedente_reais": round(exc.get(linha["ID_COOPERADO"], 0.0), 2),
            "excedente_reais_fmt": (fmt_reais(exc[linha["ID_COOPERADO"]])
                                    if linha["ID_COOPERADO"] in exc else None),
            "consultas": int(linha["consultas_totais"]),
            "consultas_fmt": fmt(linha["consultas_totais"], 0),
            "percentil": rotulo_pos,
            "leitura": traducao or "dentro da referência da área",
        })

    # A HASTE do box: do menor ao maior valor observado. Vem do motor e não da
    # leitura dos pontos no front, para a tela não precisar varrer a lista para
    # saber onde a distribuição começa e termina.
    menor, maior = min(taxas), max(taxas)

    return {
        "escala": {"min": round(escala["min"], 4), "max": round(escala["max"], 4)},
        "haste": {"de": round(menor, 4), "ate": round(maior, 4),
                  "de_fmt": fmt(menor), "ate_fmt": fmt(maior),
                  "pos_pct": _pos(menor, escala),
                  "largura_pct": round(_pos(maior, escala) - _pos(menor, escala), 2)},
        "faixa_iqr": {"rotulo": "IQR", "de": round(p25, 4), "ate": round(p75, 4),
                      "pos_pct": _pos(p25, escala),
                      "largura_pct": round(_pos(p75, escala) - _pos(p25, escala), 2)},
        # SEM linhas de referência e de critério (2026-08-20): o critério
        # agregado não governa nada e a referência que conta é a de cada exame,
        # não a do índice. Régua desenhada que não mede é o defeito que este
        # bloco carregava — ver a docstring.
        "referencias": [],
        # o eixo carrega os extremos observados e o meio da faixa interquartil,
        # que é a única marca de grupo que sobrou e é descritiva
        "eixo": [{"valor": round(v, 4), "valor_fmt": fmt(v), "pos_pct": _pos(v, escala)}
                 for v in dict.fromkeys([min(taxas), p25, p75, max(taxas)])],
        "pontos": pontos,
        # ── a legenda da RAMPA, com valores ─────────────────────────────────
        # "menor → maior" faria a cor virar sensação. As pontas e o meio em R$,
        # e o método da escala declarado: sem isso o leitor supõe que o dobro de
        # tinta é o dobro de dinheiro, e não é — é o dobro de posição na fila.
        "rampa": None if len(ordem) < 2 else {
            "rotulo": "excedente em R$",
            "metodo": "tinta por ordem de excedente, não por valor",
            "marcas": [
                {"intensidade": 0.0, "valor_fmt": fmt_reais(ordem[0])},
                {"intensidade": 0.5, "valor_fmt": fmt_reais(ordem[len(ordem) // 2])},
                {"intensidade": 1.0, "valor_fmt": fmt_reais(ordem[-1])},
            ],
        },
        "legenda": [{"classe": "band", "rotulo": "faixa P25–P75"}],
        "subtitulo": ("Cada ponto é um cooperado avaliável · solicitações por "
                      "consulta na janela"),
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
            "leitura": (f"{fmt_reais(y)} por consulta · {fmt(x)} exames por "
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
        "eixo_x": {"rotulo": "exames solicitados por consulta",
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
        "metodo": _PARETO_METODO,
    }


# ─────────────────────────────────────────────────────────────────────────────
# §04 — Tabela "Cooperados da área"
# ─────────────────────────────────────────────────────────────────────────────

_BADGES = (
    ("sub_opera", "opera"),
    ("sub_alto_risco", "alto risco"),
    ("sub_plantao_ps", "plantão"),
    ("sub_ptgi", "ptgi"),
    ("sub_ultrassonografista", "ultrassonografia"),
)


def _sub_perfis(flags_coop) -> list[dict]:
    """Badges de identidade (espec funcional, regra 2). Ajuste 1 do handoff:
    ausência de atributo NÃO vira etiqueta, a célula fica vazia.

    Cada badge viaja com a frase que diz o que ele MUDA na comparação
    (config.AJUDA_SUBPERFIL). Sem ela, "opera" é um rótulo de duas palavras que
    não informa se o cooperado entra ou não na referência — e a resposta é "entra,
    menos numa cesta", que ninguém adivinha.
    """
    if flags_coop is None:
        return []
    return [{"chave": coluna, "rotulo": rotulo,
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
            "excedente_itens", "razao_vs_mediana"]
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
            "razao": (None if pd.isna(r.razao_vs_mediana)
                      else round(float(r.razao_vs_mediana), 2)),
            "razao_fmt": (config.SEM_MEDIDA if pd.isna(r.razao_vs_mediana)
                          else f"{fmt(r.razao_vs_mediana, 1)}×"),
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
            "leitura": (f"concentra {fmt_pct(linhas[0]['pct'])} do excedente"
                        if concentrado else
                        f"excedente distribuído em {len(g)} procedimentos"),
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
        "texto": (f"{n_sin} de {len(serie)} trimestres com ao menos um "
                  f"procedimento acima do critério {seta} {rotulo}"),
        "detalhe": (f"Exames por consulta: {fmt(ini)} no primeiro trimestre "
                    f"medido, {fmt(fim)} no último ({fmt_pct(variacao)})."),
    }


def _em_revisao(coop: str) -> dict | None:
    """O cooperado está na fila de triagem clínica? Motivo do catálogo.

    Duas listas, um estado: divergência entre o rótulo do médico e a leitura
    estatística, e perfil de solicitação fora do escopo da especialidade. As
    duas voltaram para o médico e nenhuma é achado sobre a prática dele.
    """
    if coop in config.COOPERADOS_CLASSIFICACAO_EM_REVISAO:
        codigo = MOTIVO_DIVERGENCIA
    elif coop in config.COOPERADOS_PERFIL_FORA_DA_ESPECIALIDADE:
        codigo = MOTIVO_PERFIL_FORA_DA_ESPECIALIDADE
    else:
        return None
    m = _CATALOGO_MOTIVOS[codigo]
    return {"rotulo": "classificação em revisão",
            "motivo": m["rotulo"], "detalhe": m["detalhe"]}


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
            "em_revisao": _em_revisao(coop),
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

def _pareto_montar(valores: list[tuple[str, float]], unidade: str) -> tuple | None:
    """Núcleo comum dos Paretos: ordena, acumula, marca o núcleo do limiar e
    redige a leitura de concentração. `valores` = [(id, reais)]; `unidade` é a
    palavra da frase ("cooperados", "procedimentos"). Devolve (linhas, total,
    leitura, n_nucleo) ou None sem valor a distribuir."""
    total = float(sum(v for _, v in valores))
    if not valores or total <= 0:
        return None
    linhas, acum = [], 0.0
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
    leitura_hover = (f"os {len(linhas)} {unidade} do denominador são os que têm "
                     f"variação excedente valorada, não os comparáveis da área; "
                     f"os {len(nucleo)} do núcleo ({fmt_pct(len(nucleo) / len(linhas))} "
                     f"deles) somam {pct_nucleo} do total")
    return linhas, total, leitura, len(nucleo), leitura_hover


# A ressalva de MÉTODO aparece UMA vez, no primeiro Pareto (cooperados); o
# subtítulo de cada bloco já carrega "estimativa com preço interno provisório",
# e repetir o parágrafo inteiro no bloco seguinte era ruído, não ressalva.
# A ressalva diz o que o NÚMERO é, e para aí. A versão anterior emendava um
# conselho de uso ("a fila de trabalho é o recorte Qualificados") — orientação
# de método no rodapé de um gráfico, onde ninguém a procura e onde ela competia
# com a única coisa que o rodapé precisa dizer: que este R$ é teto.
# "provisório" saiu em 2026-08-19: descrevia o ESTADO DO PROJETO (a tabela
# contratual ainda não chegou), não a natureza do número, e num material de
# diretoria lê-se como rascunho. O que a ressalva precisa dizer continua inteiro
# e continua conservador — a base de preço é interna, o valor é teto, e teto não
# é economia realizada.
_PARETO_METODO = ("Estimativa de teto: valora a preços de referência internos "
                  "todas as solicitações, e nem toda solicitação é executada. "
                  "Não representa economia realizada.")


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


def _par_da_area(rotulo: str, valor_fmt: str, mediana_area, titulo: str) -> dict:
    """Um número do cooperado com a REFERÊNCIA DA ÁREA ao lado (espec §3: todo
    número do cabeçalho viaja acompanhado).

    O rótulo diz "referência" e não "mediana dos comparáveis" (27/ago):
    "comparáveis" é vocabulário do método, e a tela não deve exigir que o leitor
    o conheça para ler um número. Como a referência é construída fica no hover
    da própria linha.
    """
    return {"rotulo": rotulo, "valor_fmt": valor_fmt,
            "par_fmt": (config.SEM_MEDIDA if mediana_area is None
                        else f"referência: {mediana_area}"),
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
                     "Contagem agregada, sem identificação individual."),
        _par_da_area("Pacientes distintos",
                     config.SEM_MEDIDA if pac_coop is None else fmt(pac_coop, 0),
                     fmt(pac_comp.median(), 0) if len(pac_comp) else None,
                     "Beneficiários distintos atendidos no período. Contagem agregada, sem "
                     "identificação individual."),
        _par_da_area("Solicitações", linha["solicitacoes_fmt"],
                     fmt(comp["total_itens"].median(), 0) if len(comp) else None,
                     "Total de exames e procedimentos solicitados no período."),
        _par_da_area("SADT por consulta", linha["indice_fmt"],
                     fmt(comp["taxa_exames_por_consulta"].median()) if len(comp) else None,
                     "Exames solicitados por consulta atendida no período."),
        # ── R$ (mesma quarentena do excedente em R$: preço interno derivado) ──
        _par_da_area("Custo por consulta",
                     linha.get("custo_por_consulta_fmt") or config.SEM_MEDIDA,
                     _mediana_das_linhas(linhas_area, "custo_por_consulta", -1),
                     "Valor do que foi solicitado no período, dividido pelas consultas "
                     "atendidas. Preços internos provisórios, ainda não "
                     "homologados contra a tabela contratual."),
        _par_da_area("Custo total",
                     linha.get("valor_total_fmt") or config.SEM_MEDIDA,
                     _mediana_das_linhas(linhas_area, "valor_total", -1),
                     "Valor total do que foi solicitado no período. Mede o porte da "
                     "atividade, não o desvio. Preços internos provisórios."),
        _par_da_area("Custo do excesso",
                     linha.get("excedente_reais_fmt") or config.SEM_MEDIDA,
                     _mediana_das_linhas(linhas_area, "excedente_reais", -1),
                     "Valor das solicitações acima da referência da área. Indica "
                     "oportunidade de revisão, não economia já realizada."),
    ]


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
            "razao": (None if not medido or pd.isna(r["razao_vs_mediana"])
                      else round(float(r["razao_vs_mediana"]), 2)),
            "razao_fmt": (config.SEM_MEDIDA
                          if not medido or pd.isna(r["razao_vs_mediana"])
                          else f"{fmt(r['razao_vs_mediana'], 1)}×"),
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
    linhas.sort(key=lambda l: (-(l["excedente_itens"] or 0), -(l["razao"] or 0)))
    n_sin = sum(1 for l in linhas if l["sinalizado"])
    # o piso agregado do caso: soma dos pisos dos pares calculáveis (o cenário
    # conservador do que já tem faixa de confiança)
    piso_total = sum((l["confianca"] or {}).get("piso_itens") or 0 for l in linhas)
    n_medidos = sum(1 for l in linhas if l["medido"])
    return {
        # o sentinel de ausência, para o front não repetir a constante do
        # config em JavaScript (uma frase, dois lugares, é como elas divergem)
        "sem_medida": config.SEM_MEDIDA,
        "total_medidos": len(linhas),
        "com_referencia": n_medidos,
        "sem_referencia": len(linhas) - n_medidos,
        "em_revisao": n_sin,
        "piso_total": round(piso_total, 2) if piso_total else None,
        "piso_total_fmt": fmt(piso_total, 0) if piso_total else None,
        "ordenado_por": "variação excedente",
        "linhas": linhas,
    }


def frase_do_caso(linha: dict) -> str | None:
    """O caso numa FRASE, para o subtítulo da Leitura do caso: posição, origem
    e consistência na língua do leitor — o que este médico é, nunca a regra do
    método (a regra mora na Nota Metodológica e nos hovers)."""
    partes = []
    pos = linha.get("posicao") or {}
    if pos.get("traducao"):
        partes.append(pos["traducao"])
    elif pos.get("indisponivel_motivo"):
        partes.append(pos["indisponivel_motivo"])
    origem = linha.get("origem_excedente") or {}
    topo = origem.get("topo") or {}
    n_procs = linha.get("procedimentos_em_revisao") or 0
    if origem.get("concentrado") and topo.get("descricao"):
        partes.append(f"variação concentrada em {topo['descricao'].strip()}")
    elif n_procs:
        partes.append(f"excedente distribuído em {n_procs} procedimentos")
    c = linha.get("consistencia") or {}
    n_sin, n_av = c.get("janelas_sinalizado"), c.get("janelas_avaliaveis")
    if n_sin is not None and n_av:
        partes.append(f"padrão sustentado nos {n_av} trimestres" if n_sin == n_av
                      else f"acima do critério em {n_sin} de {n_av} trimestres")
    return ", ".join(partes) if partes else None


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


def _densidade(valores: list[float], escala: dict, n: int = 48) -> list[float]:
    """Curva de densidade dos pares, em alturas 0–1 prontas para desenhar.

    Kernel gaussiano com largura de Silverman, avaliado em `n` pontos do eixo.
    Feito aqui e não no front pela mesma razão de todo o resto: a tela imprime,
    não calcula — e uma segunda implementação em JS divergiria da primeira no
    dia em que alguém mexesse numa só.

    A curva é NORMALIZADA pelo próprio máximo: a altura comunica onde a massa
    está, não quantos cooperados são. O `n` do grupo viaja como número ao lado.
    """
    v = np.asarray([x for x in valores if x is not None and not np.isnan(x)], dtype=float)
    if len(v) < 2:
        return []
    dp = float(v.std(ddof=1))
    iqr = float(np.subtract(*np.percentile(v, [75, 25])))
    escalar = min(dp, iqr / 1.349) if iqr > 0 else dp
    if not escalar or np.isnan(escalar):
        escalar = max((v.max() - v.min()) / 6, 1e-9)
    h = 0.9 * escalar * len(v) ** (-1 / 5) or 1e-9

    grade = np.linspace(escala["min"], escala["max"], n)
    z = (grade[:, None] - v[None, :]) / h
    dens = np.exp(-0.5 * z ** 2).sum(axis=1)
    topo = dens.max()
    return [round(float(d / topo), 4) for d in dens] if topo else []


def regua_do_procedimento(linha_par, p25: float | None, taxa: float,
                          criterio_pedido: str, taxas_pares=None) -> dict | None:
    """A posição do cooperado na distribuição DESTE procedimento, em uma régua.

    Por que régua e não o gráfico de pontos: no painel a pergunta é "onde ELE
    está", não "qual a forma da distribuição da área" — essa é a pergunta da
    tela de Área, que continua com o gráfico completo a um clique. Cinquenta e
    seis pontos numa coluna de 380px viram ruído, e o painel deixa de caber sem
    rolagem justo quando o gesto seguinte é clicar na próxima linha da tabela.

    Reusa o `.ruler` do contrato visual e a MESMA geometria (`_escala`/`_pos`)
    da régua da tabela: é o que faz a marca cair no mesmo lugar nas duas telas
    (componente-assinatura, guia §04).

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

    # a escala cobre tudo que vai ser desenhado: sem incluir a marca, um
    # cooperado muito acima do grupo sai do eixo e a régua mente por omissão
    escala = _escala([v for v in (p25, p75, referencia, valor_crit, taxa, 0.0)
                      if v is not None])

    razao = (taxa / referencia) if referencia else None
    return {
        # curva de densidade + caixa: a curva mostra ONDE o grupo se acumula, a
        # caixa dá os quartis, e a marca dá a posição dele. A régua de linhas
        # finas que havia aqui era exata e ilegível — três traços de 1px num
        # eixo de 18px, indistinguíveis sem legenda.
        "densidade": _densidade(list(taxas_pares) if taxas_pares is not None else [], escala),
        "n_pares": int(len(taxas_pares)) if taxas_pares is not None else 0,
        "iqr": {"pos_pct": _pos(p25, escala),
                "largura_pct": (round(_pos(p75, escala) - _pos(p25, escala), 2)
                                if p75 is not None else 0.0),
                "rotulo": "metade central dos pares"},
        # Léxico: alvo -> "referência de adequação"; gatilho -> "critério de
        # revisão". O nível ativo vem junto porque é ele que muda de lugar
        # quando o parâmetro muda.
        "referencia": {"valor_fmt": fmt_frequencia(referencia),
                       "pos_pct": _pos(referencia, escala),
                       "rotulo": f"referência de adequação ({_ROTULO_NIVEL.get(alvo, alvo)})"},
        "criterio": (None if valor_crit is None else
                     {"valor_fmt": fmt_frequencia(valor_crit),
                      "pos_pct": _pos(valor_crit, escala),
                      "rotulo": f"critério de revisão ({gatilho.upper()})",
                      "ajustado": gatilho != criterio_pedido}),
        "marca": {"valor_fmt": fmt_frequencia(taxa),
                  "pos_pct": _pos(taxa, escala),
                  "classe": {"crit": "critmk", "read": "warnmk", "neutro": ""}[
                      _classe_ponto(taxa, p75, valor_crit)]},
        "razao_fmt": None if razao is None else f"{fmt(razao, 1)}×",
        "sem_criterio_motivo": (None if valor_crit is not None else
                                "grupo de pares insuficiente para sustentar "
                                "percentil: posição descritiva, sem critério"),
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
    # As duas que ficaram andam com a referência do grupo de pares ao lado, como
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
        "motivo": (f"pouco volume: menos de {config.MIN_PACIENTES_PAINEL} "
                   "beneficiários com este procedimento"
                   if pouco else
                   "grupo de pares insuficiente para análise comparativa"
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
            # espalhado que o grupo de pares" é conclusão sem prova, e o leitor
            # não tem como saber se a diferença é de 1 ponto ou de 20.
            n_top = (math.ceil(config.FRAC_TOP_CONCENTRACAO * pacientes["n_pacientes"])
                     if pacientes["n_pacientes"] else 0)
            comparacao = (f"Os {n_top} que mais receberam concentram "
                          f"{fmt_pct(share, 1)} das solicitações. "
                          f"No grupo de pares, {fmt_pct(share_pares, 1)}.")
            apoio = None
        else:
            comparacao = apoio = None

        if destacados:
            titulo = (f"{len(destacados)} "
                      f"{'beneficiário concentra' if len(destacados) == 1 else 'beneficiários concentram'} "
                      f"{fmt_pct(pacientes['pct_destacados'], 1)} das solicitações "
                      f"deste procedimento")
        else:
            titulo = (f"Nenhum beneficiário concentra mais de "
                      f"{fmt_pct(pacientes['limiar'])} das solicitações. O maior "
                      f"recebeu {fmt_pct(pacientes['maior_pct'], 1)}.")
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
        autorreferencia = {"apresentavel": False, "motivo": "sem itens na janela",
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
            "motivo": None if ok else "não é possível apurar",
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


def pareto_custo_do_cooperado(rs_coop: pd.DataFrame) -> dict | None:
    """Onde está o dinheiro deste cooperado, por procedimento — nos dois eixos.

    Devolve DOIS Paretos completos, um por eixo, e a tela alterna entre eles:

      custo       tudo que ele solicitou, valorado — "onde está o dinheiro";
      excedente   só a parcela acima da referência do grupo de pares — "onde
                  está a oportunidade".

    Alternar o BLOCO INTEIRO, e não só a ordenação: num Pareto a barra, a ordem
    e o acumulado são a mesma grandeza. Ordenar por um eixo desenhando o outro
    deixaria a coluna de acumulado somando uma coisa numa ordem ditada por
    outra — número certo, leitura falsa.

    Sem realce de núcleo: os dois eixos já respondem "onde está o dinheiro" pela
    ordem e pelo acumulado, e a divisão em duas tintas dizia uma terceira coisa
    que ninguém tinha perguntado.

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

    def _eixo(coluna: str, titulo: str, grandeza: str, sub: str) -> dict | None:
        sub_d = d[d[coluna] > 0]
        if not len(sub_d):
            return None
        base = _pareto_montar(list(zip(sub_d["CD_PROCEDIMENTO"], sub_d[coluna])),
                              "procedimentos")
        if base is None:
            return None
        linhas, total, leitura, n_nucleo, leitura_hover = base
        por_cd = sub_d.set_index("CD_PROCEDIMENTO")
        for linha in linhas:
            cd = linha["id"]
            r = por_cd.loc[cd]
            if isinstance(r, pd.DataFrame):
                r = r.iloc[0]
            desc = str(r.get("DS_PROCEDIMENTO", config.SEM_MEDIDA)).strip()
            linha["rotulo_linha"] = desc
            linha["rotulo_tooltip"] = desc
            linha["detalhes"] = [
                f"Código TUSS: {cd}",
                f"{fmt(r['n_solicitacoes'], 0)} solicitações · "
                f"{fmt_reais(r['preco_mediano'])} cada",
                f"Custo total no período: {fmt_reais(r['custo'])}",
                (f"Acima da referência: {fmt_reais(r['excedente'])}"
                 if r["excedente"] > 0 else "Dentro da referência do grupo de pares"),
            ]
        return {
            "titulo": f"{titulo} · {fmt_reais(total)}",
            "subtitulo": sub,
            "colunas": {"rotulo": "Procedimento", "valor": "R$",
                        "acumulado_reais": "Acumulado (R$)", "acumulado": "% acum."},
            "total": round(total, 2), "total_fmt": fmt_reais(total),
            "linhas": linhas,
            "leitura": leitura,
            "leitura_hover": leitura_hover,
            "n_nucleo": n_nucleo,
            "limiar_concentracao": config.LIMIAR_CONCENTRACAO_PARETO,
            "grandeza": grandeza,
            # barra em tinta única: ver a docstring
            "destacar_nucleo": False,
        }

    quarentena = ("Preços internos provisórios, ainda não homologados contra a "
                  "tabela contratual.")
    eixos = {
        "custo": _eixo("custo", "Custo das solicitações", "do custo", quarentena),
        "excedente": _eixo("excedente", "Custo acima da referência",
                           "do valor acima da referência", quarentena),
    }
    if eixos["custo"] is None:
        return None
    return {
        "default": "custo",
        "eixos": [e for e in ({"chave": "custo", "rotulo": "Custo total"},
                              {"chave": "excedente", "rotulo": "Acima da referência"})
                  if eixos[e["chave"]] is not None],
        "dados": {k: v for k, v in eixos.items() if v is not None},
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
        "metodo": _PARETO_METODO,
        "linhas": [],
    }


def pareto_cooperados(reais_coop: dict[str, float],
                      linhas_coop: list[dict],
                      ids: list[str] | None = None,
                      subtitulo: str | None = None) -> dict | None:
    """Pareto do EXCESSO EM R$ por cooperado, dentro do recorte.

    A barra = soma dos procedimentos em que o cooperado passou o critério,
    medidos contra a referência do grupo, a preços de referência internos.

    `ids` é QUEM ESTÁ EM CENA. Sendo `None`, é a área inteira. Total, ordem,
    % acumulado e o número do título são todos do conjunto recortado — este é
    um bloco de ACHADO, e achado segue o filtro (CLAUDE.md). Antes o acumulado
    era sempre da área e a tela apenas apagava as linhas fora de cena: a barra
    de um cooperado dizia "12% do total" sobre um total que a lista visível não
    somava mais.

    A RÉGUA não entra aqui: nenhum número deste bloco é referência, mediana ou
    critério — são somas de excedente já medido contra a régua da área, que
    permanece a mesma sob qualquer recorte.

    Ordem, acumulado e textos nascem AQUI (motor). `None` quando não há
    excedente valorado em cena (sem referência plena, sem sinalizados, ou
    recorte que não alcança ninguém com R$).
    """
    em_cena = None if ids is None else set(ids)
    valores = [(c, v) for c, v in reais_coop.items()
               if em_cena is None or c in em_cena]
    base = _pareto_montar(valores, "cooperados")
    if base is None:
        # sem recorte, área sem excedente valorado: o bloco não existe. COM
        # recorte, ele existe e está vazio — some da tela seria pior, porque o
        # leitor acabou de filtrar e não saberia se apagou o bloco ou se não
        # há nada ali.
        return None if em_cena is None else _pareto_vazio(
            "Excesso em R$ por cooperado",
            {"rotulo": "Cooperado", "valor": "Excesso (R$)",
             "acumulado_reais": "Acumulado (R$)", "acumulado": "% acum."},
            subtitulo, len(em_cena))
    linhas, total, leitura, n_nuc, leitura_hover = base
    # o denominador do "% do total" é o que ESTE bloco soma, e a frase diz qual é
    de_quem = "do total da área" if em_cena is None else "do total em cena"
    por_id = {l["id"]: l for l in linhas_coop}
    for linha in linhas:
        l = por_id.get(linha["id"], {})
        origem = l.get("origem_excedente") or {}
        topo = origem.get("topo") or {}
        pos = (l.get("posicao") or {}).get("rotulo")
        linha["rotulo_linha"] = linha["id"]
        linha["rotulo_tooltip"] = (f"{linha['id']} · posição {pos} na área"
                                   if pos else linha["id"])
        linha["detalhes"] = [
            f"Variação excedente: {linha['reais_fmt']} (em quarentena)",
            (f"Solicitações excedentes: {l.get('excedente_fmt', config.SEM_MEDIDA)}"
             f" · {linha['pct_do_total_fmt']} {de_quem}"),
        ]
        if topo.get("descricao"):
            linha["detalhes"].append(
                f"Principal procedimento: {topo['descricao'].strip()} "
                f"({topo['razao_fmt']} a referência do grupo)")
        elif origem.get("leitura"):
            linha["detalhes"].append(f"Origem: {origem['leitura']}")
    return {
        "titulo": f"Excesso em R$ por cooperado · {fmt_reais(total)}",
        "subtitulo": subtitulo,
        "colunas": {"rotulo": "Cooperado", "valor": "Excesso (R$)",
                    "acumulado_reais": "Acumulado (R$)",
                    "acumulado": "% acum."},
        "total": round(total, 2), "total_fmt": fmt_reais(total),
        "n_nucleo": n_nuc,
        "limiar_concentracao": config.LIMIAR_CONCENTRACAO_PARETO,
        "leitura_concentracao": leitura,
        "leitura_titulo": leitura_hover,

        "metodo": _PARETO_METODO,
        "linhas": linhas,
    }


def pareto_procedimentos(rs_area: pd.DataFrame,
                         ids: list[str] | None = None,
                         subtitulo: str | None = None) -> dict | None:
    """Pareto do EXCESSO EM R$ por procedimento: O QUE está sendo
    pedido em excesso, valorado. Mesma fonte do Pareto de cooperados (pares
    sinalizados com preço), agregada pelo outro eixo — os dois totais são,
    por construção, idênticos, e seguem idênticos sob recorte porque o corte
    é o MESMO conjunto de cooperados aplicado antes das duas agregações.

    `rs_area` = pares sinalizados com preço da área (posicao_proc_rs filtrado).
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
    base = _pareto_montar(list(agg["reais"].items()), "procedimentos")
    if base is None:
        return None if vazio is None else vazio()
    linhas, total, leitura, n_nuc, leitura_hover = base
    for linha in linhas:
        cd = linha["id"]
        desc = str(descricoes.get(cd, config.SEM_MEDIDA)).strip()
        # na linha vai a descrição (o que se lê); o código TUSS fica no tooltip
        linha["rotulo_linha"] = desc
        linha["rotulo_tooltip"] = desc
        linha["detalhes"] = [
            f"Código TUSS: {cd}",
            f"Variação excedente: {linha['reais_fmt']} (em quarentena)",
            (f"Solicitações excedentes: {fmt(agg['itens'][cd], 0)}"
             f" · {linha['pct_do_total_fmt']} "
             f"{'do total da área' if ids is None else 'do total em cena'}"),
            f"Cooperados acima do critério neste procedimento: {int(agg['n_coop'][cd])}",
        ]
    return {
        "titulo": f"Excesso em R$ por procedimento · {fmt_reais(total)}",
        "subtitulo": subtitulo,
        "colunas": colunas,
        "total": round(total, 2), "total_fmt": fmt_reais(total),
        "n_nucleo": n_nuc,
        "limiar_concentracao": config.LIMIAR_CONCENTRACAO_PARETO,
        "leitura_concentracao": leitura,
        "leitura_titulo": leitura_hover,

        "metodo": _PARETO_METODO,
        "linhas": linhas,
    }


def linhas_procedimentos(norma_proc_area: pd.DataFrame, posproc_area: pd.DataFrame,
                         gatilho_pedido: str, alvo: str,
                         reais_proc: dict[str, float] | None = None,
                         ids: list[str] | None = None) -> list[dict]:
    """Uma linha por procedimento da área: prevalência, solicitantes elegíveis,
    referência (mediana/P75/P90), qualidade da referência, quantos estão acima
    do critério, variação excedente e % acumulado.

    Ordenado por variação excedente (magnitude = onde agir). A razão viaja junto
    como segunda lente: razão sozinha favorece o raro (rigor-estatistico §3).
    O % acumulado é do Pareto DESTA lista, declarado no campo, não implícito.

    ── o recorte entra por METADE da tabela ─────────────────────────────────
    `ids` são os cooperados em cena. Ele filtra SÓ o achado — quantos estão
    acima do critério, variação excedente, R$, razão e % acumulado. As colunas
    de RÉGUA (prevalência, solicitantes elegíveis, referência, qualidade)
    ficam imóveis, vindas de `norma_proc_area` intacto.

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
    sinal = filtrar_sinalizados(posproc_area)
    if ids is not None:
        sinal = sinal[sinal["ID_COOPERADO"].isin(list(ids))]
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
