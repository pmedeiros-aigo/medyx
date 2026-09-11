"""smoke_api — a API entrega os números do notebook, e os blocos concordam entre si.

Confere, com o servidor no ar:
  1. os valores do gabarito (config.SMOKE_*) chegam pela API;
  2. os blocos da tela são COERENTES entre si sob o mesmo parâmetro
     (aceite 1 do handoff: mexer um parâmetro recalcula tudo junto);
  3. trocar o critério P90 -> P75 aumenta os sinalizados em TODOS os blocos
     (aceite 5);
  4. os estados de borda estão declarados (Mastologia n=4, Reprodução sem
     referência, INDEFINIDO sem peer group);
  5. a regra estrutural referência <= critério é recusada com 422.

Uso:
    uvicorn app.api:app --port 8770 &
    python smoke_api.py [http://127.0.0.1:8770]
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent)]
import config  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent / 'app'))
from utils.cascata import DEGRAUS as CASCATA_DEGRAUS  # noqa: E402
# o MESMO formatador do motor: reimplementar "R$ 139 mil" aqui seria a prova
# concordando com uma regra que ela própria inventou
from utils import blocos  # noqa: E402
from utils.blocos import fmt_reais  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8770"
falhas = 0


def get(caminho: str, **params):
    url = f"{BASE}{caminho}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=600) as resposta:
            return resposta.status, json.load(resposta)
    except urllib.error.HTTPError as erro:
        return erro.code, json.load(erro)


def checar(rotulo: str, obtido, esperado):
    global falhas
    ok = obtido == esperado
    falhas += not ok
    print(f"  [{'ok' if ok else 'FALHA'}] {rotulo}: {obtido}"
          + ("" if ok else f"   (esperado {esperado})"))


print("═" * 78)
print("1. GABARITO DO NOTEBOOK, PELA API  (config.SMOKE_*)")
_, meta = get("/api/meta")
AREA_REF = blocos.slug(config.SMOKE_AREA_REFERENCIA)   # "ginecologia-geral"
gin_meta = next(a for a in meta["areas"] if a["id"] == AREA_REF)
checar("meta · elegíveis da área de referência", gin_meta["n_formam_referencia"],
       config.SMOKE_N_NA_NORMA_AREA)
checar("meta · total da área de referência", gin_meta["n_total"], config.SMOKE_N_TOTAL_AREA)
checar("meta · gatilho efetivo", gin_meta["gatilho_usado"], config.GATILHO_DEFAULT)
checar("meta · avaliáveis (todas as áreas)",
       sum(a["n_avaliaveis"] for a in meta["areas"]), config.SMOKE_N_AVALIAVEIS)

_, gin = get(f"/api/area/{AREA_REF}")
# TRÊS MEDIDAS desde 2026-08-31 (exames, custo, excesso por consulta): o bloco
# deixou de ter uma geometria só e passou a ter uma por medida, todas no mesmo
# payload. As checagens abaixo valem para as três.
_medidas_gin = {m["chave"]: m for m in gin["distribuicao"]["medidas"]}
checar("area · distribuição serve as três medidas",
       sorted(_medidas_gin), ["custo", "exames", "excesso"])
# AS DUAS RÉGUAS voltaram em 2026-09-07, pelo artboard "Medyx Area de Atuacao".
# Elas tinham saído em ago/2026 com o argumento de que o critério agregado não
# governa a sinalização — o que continua verdade e está dito no rodapé do bloco.
# O que mudou é o reconhecimento de que enxame sem marca nenhuma não responde
# pergunta: o leitor vê espalhamento e não sabe onde a área diz que o normal
# acaba. As duas saem da MESMA norma que desenha a caixa.
checar("area · as três medidas desenham referência e critério",
       [[r["classe"] for r in m["referencias"]] for m in _medidas_gin.values()],
       [["median", "criterion"]] * 3)
# a linha do critério ANUNCIA qual gatilho está em cena: régua sem nome é régua
# que o leitor supõe.
checar("area · a régua do critério nomeia o gatilho ativo",
       {m["referencias"][1]["rotulo"].split()[0] for m in _medidas_gin.values()},
       {config.GATILHO_DEFAULT.upper()})
# o ponto marcado e a régua contam a MESMA história: verde à esquerda da linha
# do critério seria o desenho contradizendo a si mesmo.
checar("area · pontos marcados são exatamente os acima do critério",
       [sum(p["acima"] for p in m["pontos"])
        == sum(p["valor"] > m["referencias"][1]["valor"] for p in m["pontos"])
        for m in _medidas_gin.values()], [True, True, True])
# a rampa de cor do excedente saiu junto (variante E do artboard "Medyx Escala
# de Cor"): dois estados, sem escala e sem brilho.
checar("area · distribuição não publica rampa de cor",
       gin["distribuicao"]["rampa"], None)
checar("area · mediana também no rodapé da tabela",
       f"mediana {config.SMOKE_MEDIANA_AREA:.2f}".replace(".", ",")
       in gin["cooperados"]["rodape"]["direita"], True)
# COMPARÁVEIS, não "elegíveis": a linha do bloco, o chip de recorte e a
# estatística do cabeçalho falam do MESMO conjunto e com a MESMA palavra
# (31/jul/2026). Antes o 58 aparecia como "elegíveis" ao lado de um chip
# "Comparáveis 63", e nada dizia se eram dois recortes ou dois nomes para um.
checar("area · n na justificativa",
       f"{gin['area']['n_avaliaveis']} cooperados comparáveis"
       in gin["justificativa"]["resumo"], True)
checar("justificativa não fala em elegíveis",
       "elegíveis" in gin["justificativa"]["resumo"], False)

# os positivos do gabarito e o topo por razão vivem na área de cooperado_85
# (config.SMOKE_AREA_SINALIZADOS), que na v2 não é a área de referência
_, endo = get(f"/api/area/{blocos.slug(config.SMOKE_AREA_SINALIZADOS)}")
linhas = {linha["id"]: linha for linha in endo["cooperados"]["linhas"]}
for coop, esperado in config.SMOKE_SINALIZADOS_ESPERADOS.items():
    checar(f"area · {coop} procedimentos em revisão",
           linhas[coop]["procedimentos_em_revisao"], esperado)
checar("area · topo por razão vs mediana",
       tuple(linha["id"] for linha in
             sorted((l for l in endo["cooperados"]["linhas"] if l["razao_vs_mediana"]),
                    key=lambda l: -l["razao_vs_mediana"])[:3]),
       config.SMOKE_TOPO_RAZAO)

print("\n2. COERÊNCIA ENTRE OS BLOCOS (mesmo parâmetro, mesmo conjunto)")
comp = gin["composicao"]
segmentos = {s["chave"]: s["n"] for s in comp["segmentos"]}
checar("composição · segmentos somam o total", sum(segmentos.values()), comp["total"])
checar("composição · total == n da área", comp["total"], gin["area"]["n_total"])
checar("composição · formam referência == elegíveis do meta",
       segmentos["formam_norma"], gin_meta["n_formam_referencia"])
checar("composição · excluídos listados == não-formadores",
       len(comp["excluidos"]),
       segmentos["abaixo_volume_minimo"] + segmentos["fora_da_construcao"])
checar("composição · todo excluído tem motivo",
       all(e["motivo"] for e in comp["excluidos"]), True)

# A faixa de três números-herói virou UMA LINHA de contexto sob o título
# (2026-08-19): mesmo conteúdo, `contexto.partes` no lugar de `estatisticas`.
# Cada parte segue trazendo o valor cru ao lado do texto, e é ele que estas
# provas cruzam — prova que lê frase formatada quebra na primeira vírgula.
def parte(payload, chave):
    return next(x for x in payload["contexto"]["partes"] if x["chave"] == chave)

n_stat = parte(gin, "em_revisao")["valor"]
n_tabela = sum(1 for linha in gin["cooperados"]["linhas"] if linha["acima_do_criterio"])
# O GRÁFICO saiu deste cruzamento em ago/2026: quando a distribuição deixou de
# desenhar régua de critério (blocos.py, 2026-08-20), o ponto passou a carregar
# `intensidade` (0–1, contínua) no lugar de `classe == "crit"`. Não há mais flag
# de critério no ponto para cruzar — e inventar uma aqui seria a prova medindo
# a si mesma. Estatística e tabela continuam se cruzando.
checar("acima do critério · estatística == tabela", (n_stat, n_tabela), (n_stat, n_stat))
checar("gráfico · pontos do índice == avaliáveis",
       len(_medidas_gin["exames"]["pontos"]), gin["area"]["n_avaliaveis"])
# AUSÊNCIA NÃO É ZERO (ajuste 4): quem não tem preço nas contas, ou nenhum par
# acima do critério, sai do gráfico da medida de dinheiro em vez de virar ponto
# sobre o zero. Quem sai é CONTADO, e a conta tem de fechar contra os avaliáveis:
# ponto que some sem aparecer no rodapé é gente apagada da tela.
checar("gráfico · em cena + fora == avaliáveis, nas três medidas",
       [m["n_pontos"] + m["n_fora"] for m in _medidas_gin.values()],
       [gin["area"]["n_avaliaveis"]] * 3)
checar("gráfico · nenhum ponto de dinheiro em zero",
       all(p["valor"] > 0 for chave in ("custo", "excesso")
           for p in _medidas_gin[chave]["pontos"]), True)
checar("gráfico · toda medida declara o n da caixa no rodapé",
       all("caixa" in m["nota"].lower() for m in _medidas_gin.values()), True)
checar("tabela · linhas == total da área",
       len(gin["cooperados"]["linhas"]), gin["area"]["n_total"])
checar("gatilho_usado presente em toda linha avaliável",
       all(linha["gatilho_usado"] for linha in gin["cooperados"]["linhas"]
           if linha["avaliavel"]), True)
checar("percentil sempre com tradução (ajuste 2)",
       all(linha["posicao"]["traducao"] for linha in gin["cooperados"]["linhas"]
           if linha["posicao"]["tipo"] == "percentil"), True)

_, procs = get(f"/api/area/{AREA_REF}/procedimentos")


def linha_leitura(payload, chave):
    """Uma linha da Leitura da área, pela chave."""
    return next(l for g in payload["leitura"]["grupos"] for l in g["linhas"]
                if l["chave"] == chave)


def num_ptbr(texto):
    """'132.526' -> 132526.0. O smoke lê a TELA, e a tela é pt-BR."""
    return float(re.sub(r"[^\d,.-]", "", texto).replace(".", "").replace(",", "."))


# o excedente saiu da linha de contexto e vive na Leitura da área: a checagem
# segue o número para onde ele foi
exc_stat = num_ptbr(linha_leitura(gin, "_itens")["valor_fmt"])
checar("excedente · Leitura da área == soma da aba Procedimentos",
       round(exc_stat), round(procs["resumo"]["excedente_total"]))
checar("procedimentos · % acumulado termina em 100%",
       procs["linhas"][-1]["pct_acumulado_fmt"], "100%")

print("\n2a. LINHA DE CONTEXTO — o que o gráfico NÃO mostra (ajuste 5)")
chaves_stats = [x["chave"] for x in gin["contexto"]["partes"]]
checar("contexto · não duplica o gráfico (sem mediana/IQR/P90)",
       [k for k in ("mediana", "iqr", "criterio") if k in chaves_stats], [])
# a ordem nomeia os DOIS níveis: o achado (par cooperado×procedimento) antes da
# leitura sobre o índice agregado, que é adicional
# `excedente` e `excedente_reais` saíram da linha em 2026-09-07: a Leitura da
# área imprime os dois logo abaixo (linha do grupo, destaque e nota), e a linha
# de contexto era onde eles diziam menos. O que ela carrega é o ESCOPO.
checar("contexto · as partes, nesta ordem", chaves_stats,
       ["na_area", "comparaveis", "com_excedente", "em_revisao"])
checar("contexto · não repete o excedente da Leitura da área",
       [k for k in ("excedente", "excedente_reais") if k in chaves_stats], [])
checar("os dois níveis não se confundem: 63 gera o excedente, 8 é o agregado",
       parte(gin, "com_excedente")["valor"] >= parte(gin, "em_revisao")["valor"],
       True)
# inventário (consultas na janela) e comparação ENTRE áreas (peso) saíram da
# faixa: a primeira não responde à pergunta da página, a segunda é do Panorama
checar("contexto · sem inventário nem peso na especialidade",
       [k for k in ("consultas", "peso") if k in chaves_stats], [])
comparaveis = parte(gin, "comparaveis")
checar("comparáveis == avaliáveis (mesmo conjunto do chip de recorte)",
       comparaveis["valor"], gin["area"]["n_avaliaveis"])
checar("comparáveis NÃO é quem forma a referência",
       comparaveis["valor"] != config.SMOKE_N_NA_NORMA_AREA, True)
# o link fala "fora da referência" (revisão 2026-08-13): os excluídos são da
# FORMAÇÃO da referência, não do conjunto de comparáveis
checar("comparáveis traz a ação de quem está fora da referência",
       comparaveis["acao"]["rotulo"],
       f"ver os {len(gin['composicao']['excluidos'])} fora da referência")
# léxico revisto 14/ago: nomeia o CRITÉRIO (volume) em vez do mecanismo
# interno ("cortes de validade"), e diz o que o subconjunto FAZ. A linha de
# contexto é curta, então isso vive no `titulo_longo` — migrou para o hover em
# 2026-08-19, não sumiu.
checar("hover nomeia o critério de comparação",
       "olume suficiente para comparação" in comparaveis["titulo_longo"], True)
checar("e diz o que o subconjunto elegível faz",
       "define o padrão" in comparaveis["titulo_longo"], True)
checar("sem vocabulário interno na tela",
       "cortes de validade" in comparaveis["titulo_longo"], False)

# o denominador migrou para a parte "na área", que ABRE a linha: "64 na área ·
# 63 comparáveis" diz o que "63 de 64" dizia, sem repetir o total colado nele
checar("o total da área abre a linha", parte(gin, "na_area")["valor"],
       gin["area"]["n_total"])
revisao = parte(gin, "em_revisao")
checar("acima do critério · sem a palavra 'sinalizados' (léxico)",
       "sinalizad" in (revisao["texto"] + revisao["titulo_longo"]).lower(), False)
# LÉXICO DO R$: o valor vai à tela como número, sem adjetivo. O rótulo
# "(em quarentena)" e a nota "Estimativa de teto…" saíram do app inteiro em
# set/2026, por decisão do produto: descreviam o estado do projeto (a tabela
# contratual não chegou), não a natureza do número. O que a base de preço é
# continua na definição das colunas de R$ e no hover do valor no dossiê.
# O R$ agora é o DESTAQUE da Leitura da área, não mais uma parte da linha de
# contexto — as checagens seguem o número.
exc_txt = (gin["leitura"]["destaque"]["valor_fmt"] + " "
           + gin["leitura"]["destaque"]["apoio"])
checar("o R$ é o destaque da Leitura da área", "R$ " in exc_txt, True)
checar("sem vocabulário de quarentena", "quarentena" in exc_txt, False)
checar("sem o rótulo 'estimativa'", "estimad" in exc_txt, False)
# guia, tabela de formatos: "R$ abreviado, 1 casa · R$ 1,2 mi". Sete dígitos num
# número-herói não se leem; o valor exato pertence ao dossiê.
checar("R$ abreviado no destaque",
       bool(re.search(r"R\$ [\d.,]+ (mi|mil)\b", exc_txt)), True)

# Pareto do custo evitável potencial: ordem e acumulado nascem no motor e têm
# de concordar com a faixa (mesma fonte, casc["excedente_reais*"]).
par = gin["pareto_cooperados"]
checar("pareto · presente na área com referência", par is not None, True)


def _ordem(bloco, chave=None):
    """O Pareto agora chega como ENVELOPE de ordens (`dados`), uma por
    grandeza; sem custo apurado ele continua vindo como bloco único. Esta
    função devolve o bloco a conferir nos dois casos."""
    if not bloco or "dados" not in bloco:
        return bloco
    return bloco["dados"][chave or bloco["ordem_default"]]


checar("pareto · duas ordens prontas no motor (custo e excedente)",
       sorted((par.get("dados") or {}).keys()), ["custo", "excedente"])
checar("pareto · abre pelo excedente, que é o produto da tela",
       par.get("ordem_default"), "excedente")
par_env, par = par, _ordem(par)
checar("pareto · a barra é o custo e o trecho é o excedente dentro dele",
       all(0 <= l["largura_exc_pct"] <= 100 and l["excedente_rs"] <= l["custo"] + 0.01
           for l in par["linhas"]), True)
# cada barra é arredondada a 2 casas antes de somar; tolerância = 1 centavo/linha
checar("pareto · soma das barras é o total (tolerância de arredondamento)",
       abs(sum(l["reais"] for l in par["linhas"]) - par["total"])
       <= 0.01 * len(par["linhas"]), True)
checar("pareto · ordenado decrescente",
       all(a["reais"] >= b["reais"] for a, b in zip(par["linhas"], par["linhas"][1:])),
       True)
# a outra ordem é um bloco INTEIRO, não a mesma lista revirada: ordem, total e
# acumulado são a mesma grandeza, e misturá-las é o defeito que o envelope evita
_pc = _ordem(par_env, "custo")
checar("pareto · ordem por custo tem o próprio acumulado, fechando em 100%",
       _pc["linhas"][-1]["pct_acumulado"], 1.0)
checar("pareto · ordem por custo é decrescente NO CUSTO",
       all(a["custo"] >= b["custo"] for a, b in zip(_pc["linhas"], _pc["linhas"][1:])),
       True)
checar("pareto · as duas ordens têm as mesmas linhas",
       sorted(l["id"] for l in _pc["linhas"]) == sorted(l["id"] for l in par["linhas"]),
       True)
checar("pareto · acumulado fecha em 100%",
       par["linhas"][-1]["pct_acumulado"], 1.0)
# A nota de método do Pareto ("Estimativa de teto…") foi removida do app em
# set/2026, por decisão do produto, junto com todo o vocabulário de quarentena.
# A prova passa a garantir o CONTRÁRIO: o bloco não pode reintroduzi-la.
checar("pareto · sem nota de teto/quarentena",
       (par.get("metodo") or "").lower(), "")
# o Pareto de procedimentos agrega a MESMA fonte pelo outro eixo: os totais
# têm de ser idênticos (concordância entre blocos)
parp = _ordem(gin["pareto_procedimentos"])
checar("pareto procedimentos · presente", parp is not None, True)
checar("pareto procedimentos · mesmo total do de cooperados",
       abs(parp["total"] - par["total"]) < 0.01, True)
checar("pareto procedimentos · ordenado decrescente",
       all(a["reais"] >= b["reais"] for a, b in zip(parp["linhas"], parp["linhas"][1:])),
       True)
checar("peso na especialidade continua no payload, fora da faixa",
       gin["peso_na_especialidade"]["cooperados_especialidade"] > 0, True)

# área sem referência plena: comparáveis fica, as outras duas viram ressalva —
# nunca zero, que afirmaria que ninguém está fora
_, mast = get("/api/area/mastologia")
stats_mast = {x["chave"]: x for x in mast["contexto"]["partes"]}
checar("sem régua · comparáveis continua medindo",
       stats_mast["comparaveis"]["valor"] is not None, True)
checar("sem régua · acima do critério vira ressalva, não zero",
       (stats_mast["sem_regua"]["valor"],
        stats_mast["sem_regua"]["texto"]), (None, config.SEM_SINALIZACAO))
checar("sem régua · nenhuma parte afirma zero",
       [k for k in ("em_revisao", "excedente", "excedente_reais")
        if k in stats_mast], [])
checar("sem régua · a ressalva diz o motivo",
       stats_mast["sem_regua"]["titulo_longo"],
       "grupo insuficiente para formar referência")

print("\n2a-bis. CABEÇALHO DA PÁGINA")
# o subtítulo saiu (2026-08-19): dizia "64 cooperados na área", e a linha de
# contexto logo abaixo abre com "64 na área"
checar("subtítulo não repete o que a linha de contexto abre",
       gin["area"]["subtitulo"], None)
checar("e a janela continua no carimbo de proveniência",
       "mai/25–abr/26" in gin["proveniencia"]["carimbo"], True)

print("\n2b. EXCEDENTE = MEDIÇÃO, CRITÉRIO AGREGADO = REALCE (ajuste 4)")
com_exc_sem_realce = [linha for linha in gin["cooperados"]["linhas"]
                      if linha["excedente_itens"] and not linha["acima_do_criterio"]]
checar("há quem meça excedente sem estar acima do critério agregado",
       len(com_exc_sem_realce) > 0, True)
checar("esses trazem valor real, não travessão",
       all(linha["excedente_fmt"] != "—" for linha in com_exc_sem_realce), True)
checar("e trazem procedimento em revisão que o sustenta",
       all(linha["procedimentos_em_revisao"] > 0 for linha in com_exc_sem_realce), True)
checar("realce continua governado pelo critério agregado",
       all(linha["estado_linha"] != "acima_do_criterio" for linha in com_exc_sem_realce),
       True)
checar("sem medida só sem procedimento sinalizado",
       all((linha["excedente_fmt"] == config.SEM_MEDIDA) == (linha["procedimentos_em_revisao"] == 0)
           for linha in gin["cooperados"]["linhas"]), True)
checar("sem medida declara o motivo (não é zero medido)",
       all(linha["excedente_motivo"] for linha in gin["cooperados"]["linhas"]
           if linha["excedente_itens"] is None), True)
print(f"      {len(com_exc_sem_realce)} cooperados medem excedente sem realce agregado; "
      f"maior: {com_exc_sem_realce[0]['id']} = {com_exc_sem_realce[0]['excedente_fmt']}")

print("\n2c. CASCATA DE QUALIFICAÇÃO — os chips são os degraus")
chips = gin["cooperados"]["filtros"]
chaves = [c["chave"] for c in chips]
esperadas = [d[0] for d in reversed(CASCATA_DEGRAUS)]
checar("chips · os degraus, do mais estrito ao mais amplo", chaves, esperadas)
checar("chips · exatamente um default", sum(c["default"] for c in chips), 1)
checar("chips · default == cascata.default",
       next(c["chave"] for c in chips if c["default"]), gin["cascata"]["default"])

ns = [c["n"] for c in chips]
checar("funil · monotônico (nenhum degrau ganha cooperado)",
       all(a <= b for a, b in zip(ns, ns[1:])), True)
excs = [c["excedente_itens"] for c in chips]
checar("funil · excedente também monotônico",
       all(a <= b for a, b in zip(excs, excs[1:])), True)
checar("chips · contagem bate com o pertencimento das linhas",
       {c["chave"]: c["n"] for c in chips},
       {c["chave"]: sum(1 for linha in gin["cooperados"]["linhas"]
                        if c["chave"] in linha["grupos"]) for c in chips})
checar("chips · 'todos os medidos' == total da área",
       chips[-1]["n"], gin["area"]["n_total"])
checar("degrau default retém pelo menos 5 casos",
       next(c["n"] for c in chips if c["default"]) >= 5, True)
checar("default é o mais estrito com >=5",
       next(c["chave"] for c in chips if c["n"] >= 5), gin["cascata"]["default"])
checar("triou (algum degrau abaixo de 30)", gin["cascata"]["triou"], True)
checar("sem achado de variação generalizada", gin["cascata"]["achado"], None)
checar("cada degrau declara sua natureza",
       all(c["natureza"] for c in chips), True)
# v2: ninguém está com classificação em revisão (a etiqueta saiu da tela em
# set/2026); o degrau de artefato não retira ninguém
checar("nenhuma classificação em revisão sai no degrau de artefato",
       [linha["id"] for linha in gin["cooperados"]["linhas"]
        if "material" in linha["grupos"] and "classificacao_firme" not in linha["grupos"]],
       [])

print("\n3. TROCA DE CRITÉRIO P90 -> P75 (aceite 5)")
_, gin75 = get(f"/api/area/{AREA_REF}", criterio="p75")
n75_stat = parte(gin75, "em_revisao")["valor"]
n75_tab = sum(1 for linha in gin75["cooperados"]["linhas"] if linha["acima_do_criterio"])
print(f"      P90: {n_stat} acima do critério   ->   P75: {n75_stat}")
# Sem o gráfico: ver a nota da checagem equivalente no P90, acima — o ponto não
# carrega mais flag de critério, e a distribuição não desenha régua de critério.
checar("P75 · estatística == tabela", (n75_stat, n75_tab), (n75_stat, n75_stat))
checar("P75 sinaliza mais que P90", n75_stat > n_stat, True)
checar("P75 · carimbo de proveniência acompanha",
       "gatilho P75" in gin75["proveniencia"]["carimbo"], True)

print("\n4. ESTADOS DE BORDA — sem terceiro componente")
for area_id, estado_esperado, variante, tem_grafico in (
        ("mastologia", "grupo_insuficiente", "grupo_pequeno", False),
        ("patologia", "grupo_insuficiente", "sem_formadores", False),
        ("ultrassonografia", "grupo_insuficiente", "sem_formadores", False),
        ("indefinido", "sem_peer_group", None, False),
        ("obstetricia", "plena", None, True)):
    _, a = get(f"/api/area/{area_id}")
    checar(f"{area_id} · estado", a["estado"]["codigo"], estado_esperado)
    checar(f"{area_id} · variante", a["estado"]["variante"], variante)
    checar(f"{area_id} · distribuição servida", a["distribuicao"] is not None, tem_grafico)
    if not tem_grafico:
        checar(f"{area_id} · sem percentil (posto ou indisponível)",
               all(linha["posicao"]["tipo"] != "percentil"
                   for linha in a["cooperados"]["linhas"]), True)
        checar(f"{area_id} · ninguém sinalizado",
               any(linha["acima_do_criterio"] for linha in a["cooperados"]["linhas"]), False)

print("\n4b. A DISTINÇÃO VIVE NA COMPOSIÇÃO E NO MOTIVO POR COOPERADO")
_, mast = get("/api/area/mastologia")
# Patologia: 2 cooperados, e o que passa o volume mínimo tem a execução como
# prática principal — o motivo DEFINITIVO da v2. Ultrassonografia também é
# "sem formadores", mas os 3 ficam abaixo do volume mínimo e o motivo é o piso.
_, ultra = get("/api/area/patologia")
checar("Mastologia · frase de apoio",
       mast["estado"]["frase_apoio"],
       "cooperados insuficientes na área para análise comparativa")
checar("Patologia · frase de apoio", ultra["estado"]["frase_apoio"],
       "sem referência: nenhum cooperado desta área forma a norma, motivos abaixo")
checar("Patologia · todo excluído tem motivo",
       all(e["motivos"] for e in ultra["composicao"]["excluidos"]), True)
cods_ultra = {m["codigo"] for e in ultra["composicao"]["excluidos"] for m in e["motivos"]}
checar("Patologia · o perfil de execução está entre os motivos",
       "perfil_execucao" in cods_ultra, True)
checar("Patologia · o motivo de execução é DEFINITIVO",
       {m["natureza"] for e in ultra["composicao"]["excluidos"]
        for m in e["motivos"] if m["codigo"] == "perfil_execucao"}, {"definitiva"})
checar("Patologia · rótulo 'realiza mais do que solicita'",
       any("realiza mais do que solicita" in m["rotulo"]
           for e in ultra["composicao"]["excluidos"] for m in e["motivos"]), True)

# o cadastro agregado é o motivo PROVISÓRIO da v2: fica na área de referência,
# com confirmação pendente declarada
_, ref = get(f"/api/area/{AREA_REF}")
agregados = [e for e in ref["composicao"]["excluidos"]
             if any(m["codigo"] == "alerta_perfil_masculino" for m in e["motivos"])]
# 3 cooperados de Ginecologia Geral têm cadastro agregado; só 1 passa o volume
# mínimo e aparece como excluído da construção (os outros 2 ficam no piso)
checar("área de referência · cadastro agregado entre os excluídos", len(agregados), 1)
checar("cadastro agregado · natureza PROVISÓRIA",
       {m["natureza"] for e in agregados for m in e["motivos"]
        if m["codigo"] == "alerta_perfil_masculino"}, {"provisoria"})
checar("cadastro agregado · confirmação pendente declarada",
       {m["revisao"]["rotulo"] for e in agregados for m in e["motivos"]
        if m["codigo"] == "alerta_perfil_masculino"}, {"confirmação pendente"})
checar("naturezas são opostas entre execução e cadastro agregado",
       ultra["composicao"]["excluidos"][0]["natureza"] != agregados[0]["natureza"], True)

print("\n4c. FILA DE CLASSIFICAÇÃO PENDENTE (INDEFINIDO)")
_, indef = get("/api/area/indefinido")
fila = indef["fila_classificacao_pendente"]
checar("INDEFINIDO · fila real = quem passa o piso", fila["n_fila"], 3)
checar("INDEFINIDO · baixo volume fora da fila", fila["n_baixo_volume"], 52)
checar("INDEFINIDO · fila + baixo volume == total",
       fila["n_fila"] + fila["n_baixo_volume"], fila["n_total"])
checar("INDEFINIDO · nomes da fila listados", len(fila["ids_fila"]), fila["n_fila"])
checar("áreas comparáveis não trazem fila",
       get(f"/api/area/{AREA_REF}")[1]["fila_classificacao_pendente"], None)

print("\n5. REGRAS ESTRUTURAIS E ERROS")
codigo, corpo = get(f"/api/area/{AREA_REF}", criterio="p75", referencia="p90")
checar("referência > critério recusada com 422", codigo, 422)
checar("422 explica o porquê", "condenaria o quartil superior" in corpo["detail"], True)
codigo, _ = get("/api/area/nao-existe")
checar("área inexistente -> 404", codigo, 404)
codigo, _ = get("/api/meta", janela="7m")
checar("janela inválida -> 422", codigo, 422)

_, gin3m = get(f"/api/area/{AREA_REF}", janela="3m")
checar("janela 3m · consistência não reportável",
       all(linha["consistencia"]["rotulo"] == config.SEM_MEDIDA
           for linha in gin3m["cooperados"]["linhas"]), True)
checar("janela 3m · piso escalado à janela",
       gin3m["proveniencia"]["piso_aplicado_na_janela"] < config.PISO_CONSULTAS_ANO["_default"],
       True)

print("\n5b. JANELA LIVRE (intervalo AAAA-MM) DEFINE O UNIVERSO")
# METODOLOGIA §5.1: a norma e o indivíduo saem sempre da MESMA janela. Trocar a
# janela não muda a LÓGICA do cálculo, muda quais linhas entram — então um
# intervalo equivalente ao atalho tem de devolver exatamente os mesmos números.
_, gin_12m = get(f"/api/area/{AREA_REF}", janela="12m")
_, gin_int = get(f"/api/area/{AREA_REF}", ini="2025-05", fim="2026-04")
for chave in ("comparaveis", "em_revisao"):
    a = parte(gin_12m, chave)["valor"]
    b = parte(gin_int, chave)["valor"]
    checar(f"intervalo equivalente ao atalho reproduz {chave}", b, a)
# o excedente mudou de superfície (linha de contexto -> Leitura da área), não de
# valor: a checagem segue o número
checar("intervalo equivalente ao atalho reproduz excedente",
       linha_leitura(gin_int, "_itens")["valor_fmt"],
       linha_leitura(gin_12m, "_itens")["valor_fmt"])
checar("e o rótulo passa a nomear o intervalo",
       gin_int["proveniencia"]["janela"]["rotulo"], "mai/2025 a abr/2026")

# O fatiamento em trimestres é consequência da janela, e a API o declara para a
# tela poder avisar ANTES de o analista aplicar.
codigo, m6 = get("/api/meta", ini="2025-05", fim="2025-10")
checar("6 meses -> 2 trimestres", m6["periodo"]["atual"]["trimestres"], 2)
checar("e a consistência segue reportável",
       m6["periodo"]["atual"]["consistencia_reportavel"], True)
codigo, m5 = get("/api/meta", ini="2025-05", fim="2025-09")
checar("5 meses -> 1 trimestre", m5["periodo"]["atual"]["trimestres"], 1)
checar("com 61 dias fora do fatiamento", m5["periodo"]["atual"]["resto_dias"], 61)
checar("e a consistência deixa de ser reportável",
       m5["periodo"]["atual"]["consistencia_reportavel"], False)
checar("o aviso vem redigido da API",
       "persistente" in (m5["periodo"]["atual"]["aviso"] or ""), True)

# As três recusas: mínimo trimestral, fora da base, invertida.
codigo, _ = get(f"/api/area/{AREA_REF}", ini="2025-05", fim="2025-06")
checar("abaixo do mínimo trimestral -> 422", codigo, 422)
codigo, _ = get(f"/api/area/{AREA_REF}", ini="2024-01", fim="2026-04")
checar("fora da base disponível -> 422", codigo, 422)
codigo, _ = get(f"/api/area/{AREA_REF}", ini="2026-01", fim="2025-05")
checar("janela invertida -> 422", codigo, 422)
checar("o intervalo disponível é publicado",
       m6["periodo"]["disponivel"]["primeiro"] <= "2025-05", True)

print("\n6. PROVENIÊNCIA EM TODA RESPOSTA")
# decisão 2026-08-14: o status de homologação NÃO aparece para o usuário — o
# carimbo diz a versão e só; o status vive na documentação
for rotulo, corpo in (("meta", meta), ("area", gin), ("procedimentos", procs)):
    checar(f"{rotulo} · bloco de proveniência", "proveniencia" in corpo, True)
    checar(f"{rotulo} · carimbo com a versão da classificação",
           f"classificação {config.CLASSIFICACAO_VERSAO}" in corpo["proveniencia"]["carimbo"],
           True)
    checar(f"{rotulo} · carimbo sem status de homologação",
           "homologada" in corpo["proveniencia"]["carimbo"], False)

print("\n7. DOSSIÊ DO COOPERADO · CONCORDA COM A ÁREA")
# o dossiê é montado dos MESMOS motores da tela de área: a linha do cooperado
# nas duas superfícies tem de ser idêntica, e a soma por procedimento tem de
# devolver o agregado
alvo = next(l for l in gin["cooperados"]["linhas"]
            if l["excedente_itens"] and l["avaliavel"])
_, dossie = get(f"/api/cooperado/{alvo['id']}")
checar("dossiê · excedente igual à linha da área",
       dossie["leitura"]["excedente"]["itens_fmt"], alvo["excedente_fmt"])
checar("dossiê · posição igual à linha da área",
       dossie["leitura"]["posicao"]["rotulo"], alvo["posicao"]["rotulo"])
soma_procs = round(sum(l["excedente_itens"] or 0
                       for l in dossie["procedimentos"]["linhas"]), 1)
# arredondamento por procedimento: a soma pode diferir do agregado em 0,1
checar("dossiê · soma dos procedimentos devolve o excedente do cooperado (±0,1)",
       abs(soma_procs - alvo["excedente_itens"]) <= 0.1, True)
checar("dossiê · cabeçalho com o par da área em todo número",
       all("referência" in c["par_fmt"] for c in dossie["cabecalho"]), True)

# ── ACEITE PERMANENTE (METODOLOGIA §5.4.1) ───────────────────────────────────
# A série trimestral é a DISTRIBUIÇÃO NO TEMPO do excedente do ano, medida com a
# régua do ano. Se algum dia ela voltar a ser medida com a régua de cada
# trimestre, a soma deixa de fechar e é aqui que isso aparece. Tolerância de um
# centavo, que é ruído de arredondamento e não de método.
_ev = dossie.get("evolucao")
_par = (dossie.get("pareto_custo") or {}).get("dados", {}).get("excedente") or {}
if _ev and _par:
    _soma = sum(l["excedente_reais"] or 0 for l in _ev["linhas"])
    checar("dossiê · trimestres somam o excedente do ano (régua congelada)",
           abs(_soma - _par["total"]) <= 0.01, True)
    checar("dossiê · trimestre sem barra só por falta de preço, nunca por piso",
           all(l["avaliavel"] or l["motivo"] for l in _ev["linhas"]), True)
    # o piso de volume vira RESSALVA, não portão: trimestre de volume baixo
    # continua com custo apurado e com barra (METODOLOGIA §5.4.1)
    checar("dossiê · volume baixo não esconde a barra do trimestre",
           all(l["avaliavel"] for l in _ev["linhas"] if l["volume_baixo"]), True)
checar("dossiê · em revisão só quem passa os três portões",
       all(l["sinalizado"] is False for l in dossie["procedimentos"]["linhas"]
           if l["excedente_itens"] is None), True)
checar("dossiê · proveniência presente", "proveniencia" in dossie, True)
codigo, corpo_404 = get("/api/cooperado/cooperado_inexistente")
checar("dossiê · cooperado desconhecido -> 404", codigo, 404)

print("\n7a. PAINEL DO PROCEDIMENTO NA ÁREA · RÉGUA IMÓVEL, ACHADO RECORTADO")
# O painel é metade régua e metade achado, como a tabela de onde ele abre. As
# checagens abaixo cobram exatamente essa divisão — é o único jeito de o bloco
# poder ser lido ao lado da linha sem que os dois somem populações diferentes.
_cd = procs["linhas"][0]["codigo"]
_, pnl = get(f"/api/area/{AREA_REF}/procedimento/{_cd}")
_, pnl_q = get(f"/api/area/{AREA_REF}/procedimento/{_cd}", recorte="qualificados")
checar("painel do exame · a distribuição é RÉGUA e não se move com o recorte",
       (pnl["distribuicao"]["referencia"]["valor_fmt"],
        pnl["distribuicao"]["n_pares"]),
       (pnl_q["distribuicao"]["referencia"]["valor_fmt"],
        pnl_q["distribuicao"]["n_pares"]))
checar("painel do exame · o achado SEGUE o recorte",
       pnl["acima"]["n"] >= pnl_q["acima"]["n"], True)
checar("painel do exame · declara o recorte em cena",
       pnl_q["recorte"]["n"] < pnl["recorte"]["n"], True)
# a mesma soma que a tabela: o painel não pode discordar da linha atrás dele
checar("painel do exame · volume == coluna Solicitações da tabela",
       pnl["peso"]["solicitacoes_fmt"], procs["linhas"][0]["n_solicitacoes_fmt"])
checar("painel do exame · quem está acima == coluna Acima do critério",
       pnl["acima"]["n"], procs["linhas"][0]["n_acima_do_criterio"])
# o núcleo é subconjunto de quem tem excedente, nunca maior
if pnl["nucleo"]:
    checar("painel do exame · núcleo <= quem tem excedente",
           pnl["nucleo"]["n_nucleo"] <= pnl["nucleo"]["n_com_excedente"], True)
checar("painel do exame · procedimento inexistente -> 404",
       get(f"/api/area/{AREA_REF}/procedimento/99999999")[0], 404)
# o fio entre a LISTA (ordenada por excedente) e o GRÁFICO (eixo da taxa): são
# grandezas diferentes, e a cor é o que faz as duas concordarem sobre quem
# importa. Se o ponto mais escuro não for o primeiro da lista, elas voltaram a
# se contradizer.
_esc = max(pnl["distribuicao"]["pontos"], key=lambda x: x["intensidade"] or 0)
checar("painel do exame · o ponto mais escuro é o primeiro da lista",
       _esc["id"], pnl["acima"]["linhas"][0]["id"])
# o corte da lista é o NÚCLEO dos 80%, e não um número fixo
checar("painel do exame · a lista corta no núcleo dos 80%",
       pnl["acima"]["n_visiveis"],
       min(max(pnl["nucleo"]["n_nucleo"], config.MIN_NOMES_PAINEL),
           config.MAX_NOMES_PAINEL, pnl["acima"]["n"]))
# a cauda é ADIADA, não escondida: o payload traz todos
checar("painel do exame · a cauda viaja no payload (revelada sob demanda)",
       len(pnl["acima"]["linhas"]), pnl["acima"]["n"])


print("\n7b. PRINCIPAIS OPORTUNIDADES · SÓ QUALIFICADOS, E CONCORDA COM O RESTO")
# O bloco não calcula nada: ele junta e ordena o que os outros já produziram.
# As checagens cobram exatamente isso — se alguma soma daqui divergir da do
# Pareto ou do painel do procedimento, é porque nasceu um segundo cálculo do
# mesmo número.
_opo = gin["oportunidades"]
checar("oportunidades · ordenado pelo custo excedente, do maior ao menor",
       [l["excedente_reais"] for l in _opo["linhas"]]
       == sorted((l["excedente_reais"] for l in _opo["linhas"]), reverse=True),
       True)
# a lista carrega um conjunto de trabalho, não a cauda inteira; o total continua
# declarado no cabeçalho, e é ele que impede o bloco de parecer exaustivo
# A LISTA LEVA TODOS os casos qualificados: cortá-la deixava o cabeçalho
# anunciando um total que a tela não conseguia mostrar.
checar("oportunidades · a lista leva todos os casos, e o total é declarado",
       (len(_opo["linhas"]) == _opo["n"],
        f"de {_opo['n']} casos qualificados" in _opo["resumo"]),
       (True, True))
checar("oportunidades · o corte visível é o do config",
       _opo["n_visiveis"], min(config.N_OPORTUNIDADES_VISIVEIS, _opo["n"]))
# SÓ QUALIFICADOS: é o degrau que dá a cada linha a defesa pronta. Uma lista de
# todos os que passam o critério poria em primeiro lugar quem tem fator de
# contexto verificado explicando o volume.
_qualif = next(d for d in gin["cascata"]["degraus"]
               if d["chave"] == CASCATA_DEGRAUS[-1][0])
checar("oportunidades · nenhum par além dos qualificados",
       _opo["n"] <= _qualif["n_pares"], True)
# AS TRÊS CÉLULAS DA MESMA LINHA FECHAM: frequência dividida pela referência é a
# razão impressa ao lado. É a checagem que pega formatador com casas de menos —
# "0,12" sobre "0,01" lê 12 onde a coluna diz 9,2×.
# A LEITURA DA RAZÃO carrega o que saiu das colunas: a frequência do cooperado,
# o denominador que a sustenta e a referência da área. É onde o denominador vive
# desde que a tabela deixou de ter coluna para ele, e o guia exige que ele esteja
# alcançável na leitura (§13), não que ocupe coluna.
_num_da_leitura = re.compile(r"([\d.,]+) solicitações por consulta, em "
                             r"([\d.,]+) consultas.*?referência[^:]*: ([\d.,]+)",
                             re.S | re.I)
_lidas = [(_num_da_leitura.search(l["leitura_razao"]), l) for l in _opo["linhas"]]
checar("oportunidades · a leitura da razão traz frequência, consultas e referência",
       all(m for m, _ in _lidas), True)
# e as três se dividem no que a coluna Razão imprime: é a checagem que pega
# formatador com casas de menos, como "0,004" para 0,0038, cuja divisão erra 6%.
# Tolerância RELATIVA: o arredondamento vale 0,3 num par de razão 36 e seria
# erro grosso num de razão 2.
checar("oportunidades · o texto lido fecha com a razão impressa",
       all(abs(num_ptbr(m.group(1)) / num_ptbr(m.group(3)) / l["razao"] - 1) < 0.05
           for m, l in _lidas if m and l["razao"]), True)
# A FATIA DE CADA CASO é o que o bloco acrescenta a uma lista ordenada: R$ 47 mil
# não diz se vale uma conversa, 1,1% do excedente da área diz. Somadas, as fatias
# do topo reproduzem a fração que o cabeçalho anuncia.
_soma_fatias = sum(l["fracao_area"] for l in _opo["linhas"][:_opo["n_visiveis"]])
checar("oportunidades · as fatias do topo somam a fração do cabeçalho",
       f"{round(_soma_fatias * 100):.0f}%" in _opo["resumo"], True)
# DOIS RESUMOS prontos, porque a lista tem dois tamanhos. O front alterna a
# frase; recalcular a soma no navegador seria um segundo lugar produzindo o
# mesmo número (Lei 1).
checar("oportunidades · o resumo expandido fala da lista inteira",
       (_opo["resumo"].startswith(f"{_opo['n_visiveis']} de "),
        _opo["resumo_todos"].startswith(f"{len(_opo['linhas'])} de "),
        bool(_opo["resumo_titulo"])), (True, True, True))
# CONCORDA COM O PAINEL DO PROCEDIMENTO: o mesmo par, o mesmo R$. São duas
# superfícies lendo a mesma soma, e divergir seria a tela contando duas
# histórias sobre um caso.
_l0 = _opo["linhas"][0]
_, _pnl0 = get(f"/api/area/{AREA_REF}/procedimento/{_l0['codigo']}")
checar("oportunidades · o R$ do par bate com o do painel do procedimento",
       next((c["reais_fmt"] for c in _pnl0["acima"]["linhas"]
             if c["id"] == _l0["id"]), None), _l0["excedente_reais_fmt"])
# SEGUE O RECORTE, como todo achado (Lei 0)
_, _ach_op = get(f"/api/area/{AREA_REF}/achados", perfil="opera")
checar("oportunidades · o recorte de perfil reduz o conjunto",
       _ach_op["oportunidades"]["n"] <= _opo["n"], True)
# A REGRA DA QUALIFICAÇÃO é dita UMA VEZ, no rodapé, e nomeia o gatilho ativo:
# ela vale para todas as linhas, e repeti-la em cada uma gastava três linhas de
# texto por caso sem separar um caso do outro.
checar("oportunidades · o rodapé declara a regra e nomeia o critério",
       (_opo["notas"][0].startswith("Casos qualificados:"),
        config.GATILHO_DEFAULT.upper() in _opo["notas"][0]), (True, True))
# A REFERÊNCIA DA FAIXA ETÁRIA só existe no nível do cooperado: no painel da
# área o sujeito da barra É a área, e o traço cairia em cima dela.
_, _pnl_area = get(f"/api/area/{AREA_REF}/procedimento/{_cd}")
checar("painel do exame · a faixa etária da área não desenha referência",
       all(x["area_pct"] is None and x["area_fmt"] is None
           for x in (_pnl_area.get("faixas") or {}).get("faixas", [])), True)
# e no dossiê ela existe, porque ali o sujeito é outro: o cooperado contra a
# área. É o mesmo bloco, e o que muda é quem está sendo descrito.
_cd_coop = next((l["codigo"] for l in dossie["procedimentos"]["linhas"]), None)
if _cd_coop:
    _, _pnl_coop = get(f"/api/cooperado/{alvo['id']}/procedimento/{_cd_coop}")
    _fx_coop = (_pnl_coop.get("faixas") or {}).get("faixas", [])
    checar("dossiê · a faixa etária do cooperado compara com a área",
           bool(_fx_coop) and all(x["area_fmt"] for x in _fx_coop), True)


# ÁREA SEM CRITÉRIO não produz o bloco: sem régua não há par acima do critério,
# e uma lista vazia sugeriria área sem variação em vez de área sem medida.
_, _mast = get("/api/area/mastologia")
checar("oportunidades · área sem critério não publica o bloco",
       _mast.get("oportunidades"), None)


print("\n7c. PANORAMA · JUNTA PESSOAS E VALORES, NUNCA RÉGUAS")
# O Panorama é o único lugar que soma as áreas. Ele não calcula nada: o
# catálogo é o mesmo de /api/meta e o excedente de cada área é o da cascata
# daquela área. As checagens cobram essa identidade — se algum número daqui
# divergir do da tela de Área, nasceu um segundo lugar produzindo o mesmo
# número, que é o defeito que a Lei 1 existe para impedir.
_, pano = get("/api/panorama")
_cartoes = {c["id"]: c for c in pano["areas"]["cartoes"]}
_com_regua = {k: c for k, c in _cartoes.items() if c["comparavel"]}
# TODA ÁREA VIRA CARTÃO, com régua ou sem. A tela é o catálogo da especialidade,
# e área que não aparece é área que ninguém lembra de classificar. O que separa
# as duas famílias é o CONTEÚDO do cartão, não a presença.
_, _meta_areas = get("/api/meta")
checar("panorama · toda área de atuação vira cartão",
       sorted(_cartoes),
       sorted(a["id"] for a in _meta_areas["areas"]
              if a["id"] != blocos.slug(config.AREA_INDEFINIDA)))
checar("panorama · e só as com régua trazem excedente",
       sorted(_com_regua), ["endoscopia-ginecologica", "ginecologia-geral", "obstetricia"])
# TODO CARTÃO DIZ AS MESMAS TRÊS COISAS, na mesma ordem: cartão que muda de
# campos conforme a área obriga a reaprender o desenho a cada um, e some com a
# comparação, que é a razão de eles estarem lado a lado.
checar("panorama · todo cartão traz as mesmas medidas, na mesma ordem",
       {tuple(l["rotulo"] for l in c["linhas"]) for c in _cartoes.values()},
       {("Custo total", "Custo excedente")})
# O CUSTO TOTAL é dado REAL e existe em toda área, com régua ou sem: ele não
# depende de norma, é o que a área solicitou. Só o excesso depende.
# ...exceto onde NINGUÉM passa o volume mínimo (v2: Ultrassonografia, 0 de 3):
# aí a ausência é declarada com o motivo, nunca zero
checar("panorama · o custo total aparece em toda área com comparáveis",
       [c["nome"] for c in _cartoes.values()
        if c["linhas"][0]["valor_fmt"] == config.SEM_MEDIDA
        and not c["populacao"].startswith("0 compar")], [])
checar("panorama · área sem comparáveis declara o motivo do custo ausente",
       all(c["linhas"][0]["motivo"] for c in _cartoes.values()
           if c["linhas"][0]["valor_fmt"] == config.SEM_MEDIDA), True)
# e onde a medida não existe, a ausência é DECLARADA com o motivo: nunca zero,
# que afirmaria ausência de variação, nem célula vazia, que manda o leitor
# procurar o número que não está lá (ajuste 4 do CLAUDE.md)
checar("panorama · sem régua, o excesso é ausência declarada e não zero",
       all(l["valor_fmt"] == config.SEM_MEDIDA and l["motivo"]
           for c in _cartoes.values() if not c["comparavel"]
           for l in c["linhas"][1:]), True)
# NINGUÉM DESAPARECE: os cartões e a classificação pendente somam a
# especialidade inteira. É a regra que impede a tela de esconder quem não pode
# ser medido, que é justamente quem mais precisa aparecer.
_pop = sum(int(num_ptbr(c["populacao"].split(" de ")[1])) for c in _cartoes.values())
checar("panorama · ninguém desaparece da especialidade",
       _pop + int(num_ptbr(pano["pendente"]["valor_fmt"])),
       pano["totais"]["cooperados"])
# O EXCEDENTE DE CADA ÁREA é o mesmo que a tela de Área imprime no destaque da
# Leitura, sob o recorte default. Duas telas, um número.
_linhas_gin = {l["rotulo"]: l["valor_fmt"]
               for l in _com_regua[AREA_REF]["linhas"]}
checar("panorama · o excedente da área bate com a tela de Área",
       _linhas_gin["Custo excedente"], gin["leitura"]["destaque"]["valor_fmt"])
# e o custo total, e a fração entre os dois: os três números do cartão são os
# mesmos que a Leitura da área imprime, palavra por palavra
checar("panorama · o custo total bate com a Leitura da área",
       _linhas_gin["Custo total"],
       linha_leitura(gin, "_custo_total")["valor_fmt"])
# o % ANDA COM O VALOR, e é o mesmo que o destaque da Leitura imprime
_apoio_gin = next(l["apoio"] for l in _com_regua[AREA_REF]["linhas"]
                  if l["rotulo"] == "Custo excedente")
checar("panorama · e o % excedente é o mesmo do destaque",
       _apoio_gin in gin["leitura"]["destaque"]["apoio"], True)
# as áreas COM RÉGUA vêm primeiro, e entre elas manda o excedente: sem ordem,
# um cartão de uma pessoa se intercalaria com o que carrega R$ 2,9 mi
_ordem = [c["comparavel"] for c in pano["areas"]["cartoes"]]
checar("panorama · áreas com régua vêm primeiro",
       _ordem == sorted(_ordem, reverse=True), True)
# A RÉGUA NÃO É SOMADA. Percentil comparando médicos de áreas diferentes é o
# pecado capital do método, e a prova é estrutural: nenhuma chave de posição
# atravessa o payload desta tela.
_proibidas = {"percentil", "posicao", "posto", "razao_vs_mediana", "razao_vs_alvo"}
def _chaves(no):
    if isinstance(no, dict):
        for k, v in no.items():
            yield k
            yield from _chaves(v)
    elif isinstance(no, list):
        for v in no:
            yield from _chaves(v)
checar("panorama · nenhuma medida de posição atravessa as áreas",
       sorted(_proibidas & set(_chaves(pano))), [])
# OS DOIS PARETOS somam o MESMO total da especialidade, por eixos diferentes:
# se divergirem, um dos dois está somando outra população.
# DUAS AGREGAÇÕES do mesmo total: por área diz onde alocar auditoria, por
# cooperado diz quantas conversas resolvem quanto. Trocar entre elas é LEITURA,
# não recorte, e por isso as duas viajam prontas no mesmo payload.
checar("panorama · a concentração agrupa por área e por cooperado",
       ([o["chave"] for o in pano["concentracao"]["ordens"]],
        pano["concentracao"]["rotulo_controle"]),
       (["area", "cooperado"], "Agrupar por"))
checar("panorama · as duas agregações somam o mesmo total",
       {b["total_fmt"] for b in pano["concentracao"]["dados"].values()},
       {fmt_reais(pano["totais"]["excedente_reais"])})
_conc = pano["concentracao"]["dados"]["cooperado"]
_trans = pano["transversais"]["dados"]["excedente"]
checar("panorama · os dois Paretos somam o mesmo excedente",
       (_conc["total_fmt"], _trans["total_fmt"]),
       (fmt_reais(pano["totais"]["excedente_reais"]),) * 2)
# e cada um se chama pelo que responde: com o mesmo total nos dois cabeçalhos, o
# título genérico do Pareto era a mesma frase dita duas vezes lado a lado
checar("panorama · cada Pareto tem nome próprio",
       (_conc["titulo"], _trans["titulo"]),
       ("Onde o excesso se concentra", "Procedimentos transversais"))
# a leitura de cada linha diz de que régua ela veio: numa tela que cruza áreas,
# a barra sozinha não diz contra o que a pessoa foi medida
checar("panorama · a linha do cooperado declara a área dele",
       _conc["linhas"][0]["detalhes"][0].startswith("Área de atuação:"), True)
checar("panorama · e a do procedimento, em quantas áreas ele aparece",
       _trans["linhas"][0]["detalhes"][0].startswith("Aparece em "), True)
# O SELETOR DE ÁREA RECORTA a tela, não navega para fora dela: o Panorama existe
# para comparar as áreas, e sair dele ao escolher uma é o oposto do que o
# controle promete. A chave é `areas` porque `area` na raiz é rota legada, que o
# servidor redireciona para /area/{id}.
_, _pano_go = get("/api/panorama", areas="obstetricia")
checar("panorama · o filtro de áreas recorta a tela",
       (len(_pano_go["areas"]["cartoes"]),
        _pano_go["totais"]["areas_com_referencia"]), (1, 1))
# ESCOLHA MÚLTIPLA: comparar duas áreas de sete é a leitura que esta tela
# existe para dar, e a escolha única não a expressa.
_, _pano_duas = get("/api/panorama", areas=f"{AREA_REF},obstetricia")
checar("panorama · o filtro aceita várias áreas",
       len(_pano_duas["areas"]["cartoes"]), 2)
# slug desconhecido é ignorado em vez de esvaziar a tela; seleção que não
# alcança área nenhuma cai em todas, o estado que a página sempre desenha
_, _pano_ruim = get("/api/panorama", areas="nao-existe")
checar("panorama · seleção que não alcança nada cai em todas",
       len(_pano_ruim["areas"]["cartoes"]), len(_cartoes))
checar("panorama · e a soma acompanha o recorte",
       _pano_go["totais"]["excedente_reais"] < pano["totais"]["excedente_reais"],
       True)
# com uma área só em cena, a coluna que diz de qual régua o caso veio some: ela
# repetiria a mesma palavra em todas as linhas
checar("panorama · com uma área só, a coluna da área não aparece",
       _pano_go["oportunidades"]["mostrar_area"], False)
# ETAPA 1: a tela declara o que ainda não tem. Quando a etapa 4 fechar, esta
# chave passa a existir e a checagem inverte.
checar("panorama · o funil ainda não foi publicado", "funil" in pano, False)


print("\n8. TEXTO DE TELA  (LEXICO_PRODUTO.md, PADRÃO DE REDAÇÃO)")
# As regras MECÂNICAS do padrão, cobradas onde elas se repetiram: rodapés de
# método, subtítulos, leituras e notas. As regras de julgamento (uma frase um
# fato, não explicar mecânica, voz impessoal) ficam com a revisão humana — mas
# estas quatro não dependem de julgamento nenhum e por isso não deviam depender
# de alguém lembrar delas.
#
# Chaves varridas: as que carregam FRASE. Rótulo de dado é outra coisa (não leva
# ponto, pode começar em minúscula) e fica fora de propósito.
# CHAVES QUE CARREGAM FRASE. `motivo`, `titulo_longo`, `resumo` e `traducao`
# ficam FORA: eles são apostos telegráficos por desenho ("alerta de perfil
# (pacientes homens)", "cooperados da área com atividade no período"), completam
# um rótulo e não são sentenças. Cobrar maiúscula e ponto neles seria a prova
# exigindo o contrário do que o produto decidiu.
CHAVES_DE_FRASE = ("nota", "leitura", "frase", "detalhe", "resumo_detalhe",
                   "base", "tendencia", "ajuda", "tooltip")
# regra 1: a tela não se descreve; regra 9: estado de projeto não é atributo.
# "provisório" ficou fora da lista: ele é legítimo onde qualifica a REGRA da
# classificação ("Regra provisória da classificação v1.0, em validação
# clínica"), que é governança declarada, e não o estado do projeto colado num
# número. Varrer por ele reprovaria o texto certo.
PROIBIDOS = ("o gráfico", "este gráfico", "esta série", "série limitada",
             "este bloco", "nesta tela", "as barras", "a barra inteira",
             "quarentena", "estimativa de teto")


def _frases(no, caminho=""):
    """Toda string de frase do payload, com o caminho até ela."""
    if isinstance(no, dict):
        for k, v in no.items():
            if isinstance(v, str) and k in CHAVES_DE_FRASE:
                yield f"{caminho}.{k}", v
            else:
                yield from _frases(v, f"{caminho}.{k}")
    elif isinstance(no, list):
        for i, v in enumerate(no):
            yield from _frases(v, f"{caminho}[{i}]")


_payloads = {"area": gin, "dossiê": dossie, "meta": meta}
_faltas = {"travessão": [], "palavra proibida": []}
for _nome, _p in _payloads.items():
    for _cam, _txt in _frases(_p, _nome):
        t = _txt.strip()
        if not t:
            continue
        if "—" in t:
            _faltas["travessão"].append((_cam, t[:70]))
        baixo = t.lower()
        for _pal in PROIBIDOS:
            if _pal in baixo:
                _faltas["palavra proibida"].append((_cam, f"{_pal!r} em {t[:60]}"))
                break

for _regra, _casos in _faltas.items():
    checar(f"texto · {_regra}", len(_casos), 0)
    for _cam, _ex in _casos[:6]:
        print(f"         {_cam}: {_ex}")

# ── TOOLTIP começa em maiúscula e termina em ponto ───────────────────────────
# Aqui a regra 5 do padrão VALE sem ambiguidade, e é por isso que ela é cobrada
# nestas chaves e não nas outras: o que entra num `title` é sempre uma frase de
# explicação. Não há fragmento telegráfico entre elas.
CHAVES_DE_TOOLTIP = ("titulo_longo", "ajuda", "par_titulo", "detalhe", "tooltip",
                     "leitura_titulo", "resumo_detalhe")


def _tooltips(no, caminho=""):
    if isinstance(no, dict):
        for k, v in no.items():
            if isinstance(v, str) and k in CHAVES_DE_TOOLTIP:
                yield f"{caminho}.{k}", v
            else:
                yield from _tooltips(v, f"{caminho}.{k}")
    elif isinstance(no, list):
        for i, v in enumerate(no):
            yield from _tooltips(v, f"{caminho}[{i}]")


_tt = []
for _nome, _p in _payloads.items():
    for _cam, _txt in _tooltips(_p, _nome):
        t = _txt.strip()
        if not t:
            continue
        if (t[0].isalpha() and not t[0].isupper()) or t[-1] not in ".?!":
            _tt.append((_cam, t[:70]))
checar("texto · tooltip com maiúscula e ponto", len(_tt), 0)
for _cam, _ex in _tt[:6]:
    print(f"         {_cam}: {_ex}")

# ── o que esta prova NÃO cobre, e por quê ────────────────────────────────────
# Maiúscula inicial e ponto final (regra 5 do padrão) foram tentados aqui e
# saíram: o payload mistura, sob as MESMAS chaves, sentenças ("O custo por
# consulta cai 6% de T1 a T4.") e fragmentos telegráficos que completam um
# rótulo ("consultas eletivas (episódios de PS excluídos)", "mai/25–jul/25. …",
# "solicitações excedentes distribuídas em 38 procedimentos"). De 74 apontamentos
# medidos em set/2026, 3 de cada 4 eram fragmento legítimo. Uma prova que reprova
# o texto certo ensina a ignorá-la.
#
# As regras que dependem de julgamento (1 quando sutil, 2, 3, 4, 5, 6, 7, 10)
# são de revisão humana, e é por isso que estão ESCRITAS no LEXICO_PRODUTO.md:
# para não serem redescobertas a cada frase.

print("═" * 78)
print("RESULTADO:", "API REPRODUZ O SMOKE E OS BLOCOS CONCORDAM" if not falhas
      else f"{falhas} divergência(s)")
raise SystemExit(1 if falhas else 0)
