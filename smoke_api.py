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
gin_meta = next(a for a in meta["areas"] if a["id"] == "ginecologia")
checar("meta · elegíveis Ginecologia", gin_meta["n_formam_referencia"],
       config.SMOKE_N_NA_NORMA_GINECOLOGIA)
checar("meta · total Ginecologia", gin_meta["n_total"], config.SMOKE_N_TOTAL_GINECOLOGIA)
checar("meta · gatilho efetivo", gin_meta["gatilho_usado"], config.GATILHO_DEFAULT)
checar("meta · avaliáveis (todas as áreas)",
       sum(a["n_avaliaveis"] for a in meta["areas"]), config.SMOKE_N_AVALIAVEIS)

_, gin = get("/api/area/ginecologia")
# A distribuição NÃO desenha mais linha de referência nem de critério
# (blocos.py, 2026-08-20): régua desenhada que não mede era o defeito do bloco,
# e `referencias` passou a sair vazia POR DECISÃO. O smoke ainda exigia a linha
# e morria com StopIteration antes de checar qualquer outra coisa — checagem
# obsoleta, removida em ago/2026. A mediana continua provada pelo rodapé da
# tabela, logo abaixo, que é onde ela aparece para o usuário.
# TRÊS MEDIDAS desde 2026-08-31 (exames, custo, excesso por consulta): o bloco
# deixou de ter uma geometria só e passou a ter uma por medida, todas no mesmo
# payload. As checagens abaixo valem para as três.
_medidas_gin = {m["chave"]: m for m in gin["distribuicao"]["medidas"]}
checar("area · distribuição serve as três medidas",
       sorted(_medidas_gin), ["custo", "exames", "excesso"])
checar("area · nenhuma medida desenha régua de referência",
       [m["referencias"] for m in _medidas_gin.values()], [[], [], []])
checar("area · mediana também no rodapé da tabela",
       f"mediana {config.SMOKE_MEDIANA_GINECOLOGIA:.2f}".replace(".", ",")
       in gin["cooperados"]["rodape"]["direita"], True)
# COMPARÁVEIS, não "elegíveis": a linha do bloco, o chip de recorte e a
# estatística do cabeçalho falam do MESMO conjunto e com a MESMA palavra
# (31/jul/2026). Antes o 58 aparecia como "elegíveis" ao lado de um chip
# "Comparáveis 63", e nada dizia se eram dois recortes ou dois nomes para um.
checar("area · n na justificativa",
       f"n={gin['area']['n_avaliaveis']} comparáveis" in gin["justificativa"]["resumo"], True)
checar("justificativa não fala em elegíveis",
       "elegíveis" in gin["justificativa"]["resumo"], False)

linhas = {linha["id"]: linha for linha in gin["cooperados"]["linhas"]}
for coop, esperado in config.SMOKE_SINALIZADOS_ESPERADOS.items():
    checar(f"area · {coop} procedimentos em revisão",
           linhas[coop]["procedimentos_em_revisao"], esperado)
checar("area · topo por razão vs mediana",
       tuple(linha["id"] for linha in
             sorted((l for l in gin["cooperados"]["linhas"] if l["razao_vs_mediana"]),
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
       all("caixa" in m["nota"] for m in _medidas_gin.values()), True)
checar("tabela · linhas == total da área",
       len(gin["cooperados"]["linhas"]), gin["area"]["n_total"])
checar("gatilho_usado presente em toda linha avaliável",
       all(linha["gatilho_usado"] for linha in gin["cooperados"]["linhas"]
           if linha["avaliavel"]), True)
checar("percentil sempre com tradução (ajuste 2)",
       all(linha["posicao"]["traducao"] for linha in gin["cooperados"]["linhas"]
           if linha["posicao"]["tipo"] == "percentil"), True)

_, procs = get("/api/area/ginecologia/procedimentos")
exc_stat = parte(gin, "excedente")["valor"]
checar("excedente · linha de contexto == soma da aba Procedimentos",
       round(exc_stat), round(procs["resumo"]["excedente_total"]))
checar("procedimentos · % acumulado termina em 100%",
       procs["linhas"][-1]["pct_acumulado_fmt"], "100%")

print("\n2a. LINHA DE CONTEXTO — o que o gráfico NÃO mostra (ajuste 5)")
chaves_stats = [x["chave"] for x in gin["contexto"]["partes"]]
checar("contexto · não duplica o gráfico (sem mediana/IQR/P90)",
       [k for k in ("mediana", "iqr", "criterio") if k in chaves_stats], [])
# a ordem nomeia os DOIS níveis: o achado (par cooperado×procedimento) antes da
# leitura sobre o índice agregado, que é adicional
checar("contexto · as partes, nesta ordem", chaves_stats,
       ["na_area", "comparaveis", "com_excedente", "em_revisao", "excedente",
        "excedente_reais"])
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
       comparaveis["valor"] != config.SMOKE_N_NA_NORMA_GINECOLOGIA, True)
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
       "volume suficiente para comparação" in comparaveis["titulo_longo"], True)
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
exc = parte(gin, "excedente_reais")
# LÉXICO DO R$ (decisão 2026-08-14): rótulo único em todas as telas,
# "(em quarentena)" — o preço interno não é reportável até a tabela oficial.
# Vira número pleno quando ela for injetada no pipeline.
checar("o R$ tem parte própria na linha", "R$ " in exc["texto"], True)
checar("rotulado em quarentena", "(em quarentena)" in exc["texto"], True)
checar("sem o rótulo 'estimativa'", "estimad" in exc["texto"], False)
# guia, tabela de formatos: "R$ abreviado, 1 casa · R$ 1,2 mi". Sete dígitos numa
# linha de contexto não se leem; o valor exato pertence ao dossiê.
checar("R$ abreviado na linha de contexto",
       bool(re.search(r"R\$ [\d.,]+ (mi|mil)\b", exc["texto"])), True)

# Pareto do custo evitável potencial: ordem e acumulado nascem no motor e têm
# de concordar com a faixa (mesma fonte, casc["excedente_reais*"]).
par = gin["pareto_cooperados"]
checar("pareto · presente na área com referência", par is not None, True)
# cada barra é arredondada a 2 casas antes de somar; tolerância = 1 centavo/linha
checar("pareto · soma das barras é o total (tolerância de arredondamento)",
       abs(sum(l["reais"] for l in par["linhas"]) - par["total"])
       <= 0.01 * len(par["linhas"]), True)
checar("pareto · ordenado decrescente",
       all(a["reais"] >= b["reais"] for a, b in zip(par["linhas"], par["linhas"][1:])),
       True)
checar("pareto · acumulado fecha em 100%",
       par["linhas"][-1]["pct_acumulado"], 1.0)
checar("pareto · método declarado (teto, não economia)",
       "teto" in par["metodo"].lower(), True)
# o Pareto de procedimentos agrega a MESMA fonte pelo outro eixo: os totais
# têm de ser idênticos (concordância entre blocos)
parp = gin["pareto_procedimentos"]
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
checar("classificação em revisão sai no degrau de artefato",
       [linha["id"] for linha in gin["cooperados"]["linhas"]
        if "material" in linha["grupos"] and "classificacao_firme" not in linha["grupos"]],
       ["cooperado_61"])

print("\n3. TROCA DE CRITÉRIO P90 -> P75 (aceite 5)")
_, gin75 = get("/api/area/ginecologia", criterio="p75")
n75_stat = parte(gin75, "em_revisao")["valor"]
n75_tab = sum(1 for linha in gin75["cooperados"]["linhas"] if linha["acima_do_criterio"])
print(f"      P90: {n_stat} acima do critério   ->   P75: {n75_stat}")
# Sem o gráfico: ver a nota da checagem equivalente no P90, acima — o ponto não
# carrega mais flag de critério, e a distribuição não desenha régua de critério.
checar("P75 · estatística == tabela", (n75_stat, n75_tab), (n75_stat, n75_stat))
checar("P75 sinaliza mais que P90", n75_stat > n_stat, True)
checar("P75 · carimbo de proveniência acompanha",
       "gatilho p75" in gin75["proveniencia"]["carimbo"], True)

print("\n4. ESTADOS DE BORDA — sem terceiro componente")
for area_id, estado_esperado, variante, tem_grafico in (
        ("mastologia", "grupo_insuficiente", "grupo_pequeno", False),
        ("reproducao", "grupo_insuficiente", "sem_formadores", False),
        ("ultrassonografista", "grupo_insuficiente", "sem_formadores", False),
        ("indefinido", "sem_peer_group", None, False),
        ("go", "plena", None, True)):
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
_, repro = get("/api/area/reproducao")
_, ultra = get("/api/area/ultrassonografista")
checar("Mastologia · frase de apoio",
       mast["estado"]["frase_apoio"],
       "grupo de pares insuficiente para análise comparativa")
checar("Reprodução · frase de apoio", repro["estado"]["frase_apoio"],
       "sem referência: nenhum cooperado desta área forma a norma, motivos abaixo")
seg_repro = {s["chave"]: s["n"] for s in repro["composicao"]["segmentos"]}
checar("Reprodução · composição 0 / 0 / 2",
       (seg_repro["formam_norma"], seg_repro["abaixo_volume_minimo"],
        seg_repro["fora_da_construcao"]), (0, 0, 2))
checar("Reprodução · todo excluído tem motivo",
       all(e["motivos"] for e in repro["composicao"]["excluidos"]), True)

cods_repro = {m["codigo"] for e in repro["composicao"]["excluidos"] for m in e["motivos"]}
checar("Reprodução · motivo é o alerta de perfil masculino",
       cods_repro, {"alerta_perfil_masculino"})
checar("Reprodução · natureza PROVISÓRIA",
       {e["natureza"] for e in repro["composicao"]["excluidos"]}, {"provisoria"})
checar("Reprodução · falso positivo previsível declarado",
       all(m["revisao"]["falso_positivo_previsivel"]
           for e in repro["composicao"]["excluidos"] for m in e["motivos"]), True)
checar("Reprodução · status de triagem clínica pendente",
       {m["revisao"]["rotulo"] for e in repro["composicao"]["excluidos"]
        for m in e["motivos"]}, {"triagem clínica pendente"})
checar("Reprodução · revisão pendente contabilizada",
       repro["composicao"]["revisao_pendente"], 2)

cods_ultra = {m["codigo"] for e in ultra["composicao"]["excluidos"] for m in e["motivos"]}
checar("Ultrassonografista · motivo é o perfil de execução",
       cods_ultra, {"perfil_ultrassonografista"})
checar("Ultrassonografista · natureza DEFINITIVA",
       {e["natureza"] for e in ultra["composicao"]["excluidos"]}, {"definitiva"})
checar("Ultrassonografista · sem revisão pendente",
       ultra["composicao"]["revisao_pendente"], 0)
checar("Ultrassonografista · rótulo 'não solicita'",
       "não solicita" in ultra["composicao"]["excluidos"][0]["motivo"], True)
checar("naturezas são opostas entre as duas áreas",
       ultra["composicao"]["excluidos"][0]["natureza"]
       != repro["composicao"]["excluidos"][0]["natureza"], True)

print("\n4c. FILA DE CLASSIFICAÇÃO PENDENTE (INDEFINIDO)")
_, indef = get("/api/area/indefinido")
fila = indef["fila_classificacao_pendente"]
checar("INDEFINIDO · fila real = quem passa o piso", fila["n_fila"], 5)
checar("INDEFINIDO · baixo volume fora da fila", fila["n_baixo_volume"], 67)
checar("INDEFINIDO · fila + baixo volume == total",
       fila["n_fila"] + fila["n_baixo_volume"], fila["n_total"])
checar("INDEFINIDO · nomes da fila listados", len(fila["ids_fila"]), fila["n_fila"])
checar("áreas comparáveis não trazem fila",
       get("/api/area/ginecologia")[1]["fila_classificacao_pendente"], None)

print("\n5. REGRAS ESTRUTURAIS E ERROS")
codigo, corpo = get("/api/area/ginecologia", criterio="p75", referencia="p90")
checar("referência > critério recusada com 422", codigo, 422)
checar("422 explica o porquê", "condenaria o quartil superior" in corpo["detail"], True)
codigo, _ = get("/api/area/nao-existe")
checar("área inexistente -> 404", codigo, 404)
codigo, _ = get("/api/meta", janela="7m")
checar("janela inválida -> 422", codigo, 422)

_, gin3m = get("/api/area/ginecologia", janela="3m")
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
_, gin_12m = get("/api/area/ginecologia", janela="12m")
_, gin_int = get("/api/area/ginecologia", ini="2025-05", fim="2026-04")
for chave in ("comparaveis", "em_revisao", "excedente"):
    a = parte(gin_12m, chave)["valor"]
    b = parte(gin_int, chave)["valor"]
    checar(f"intervalo equivalente ao atalho reproduz {chave}", b, a)
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
codigo, _ = get("/api/area/ginecologia", ini="2025-05", fim="2025-06")
checar("abaixo do mínimo trimestral -> 422", codigo, 422)
codigo, _ = get("/api/area/ginecologia", ini="2024-01", fim="2026-04")
checar("fora da base disponível -> 422", codigo, 422)
codigo, _ = get("/api/area/ginecologia", ini="2026-01", fim="2025-05")
checar("janela invertida -> 422", codigo, 422)
checar("o intervalo disponível é publicado",
       m6["periodo"]["disponivel"]["primeiro"] <= "2025-05", True)

print("\n6. PROVENIÊNCIA EM TODA RESPOSTA")
# decisão 2026-08-14: o status de homologação NÃO aparece para o usuário — o
# carimbo diz a versão e só; o status vive na documentação
for rotulo, corpo in (("meta", meta), ("area", gin), ("procedimentos", procs)):
    checar(f"{rotulo} · bloco de proveniência", "proveniencia" in corpo, True)
    checar(f"{rotulo} · carimbo com a versão da classificação",
           "classificação v1.0" in corpo["proveniencia"]["carimbo"], True)
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
checar("dossiê · soma dos procedimentos devolve o excedente do cooperado",
       soma_procs, round(alvo["excedente_itens"], 1))
checar("dossiê · cabeçalho com o par da área em todo número",
       all("referência" in c["par_fmt"] for c in dossie["cabecalho"]), True)
checar("dossiê · em revisão só quem passa os três portões",
       all(l["sinalizado"] is False for l in dossie["procedimentos"]["linhas"]
           if l["excedente_itens"] is None), True)
checar("dossiê · proveniência presente", "proveniencia" in dossie, True)
codigo, corpo_404 = get("/api/cooperado/cooperado_inexistente")
checar("dossiê · cooperado desconhecido -> 404", codigo, 404)

print("═" * 78)
print("RESULTADO:", "API REPRODUZ O SMOKE E OS BLOCOS CONCORDAM" if not falhas
      else f"{falhas} divergência(s)")
raise SystemExit(1 if falhas else 0)
