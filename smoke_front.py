"""smoke_front — as telas montam, não quebram e as interações-chave respondem.

O que ele protege, e por que existe: os defeitos que apareceram na sessão de
13/ago não eram de cálculo, eram de MONTAGEM — uma função usada e nunca
declarada derrubava a tela inteira (`ReferenceError` em módulo ES), chips que
não filtravam nada, um bloco que prometia recorte e não avisava o gráfico.
Nenhum smoke de API pega isso: o JSON estava certo, a tela é que não subia.

A regra desta suite: **erro de console é falha**. Um `pageerror` significa que
alguma parte da tela não montou, e numa página de evidência isso é pior que um
número errado — o número errado se discute, a tela em branco não se vê.

Uso:
    uvicorn app.api:app --port 8770 &
    python smoke_front.py [http://127.0.0.1:8770]

Depende de playwright (já no ambiente global-env do projeto).
"""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8770"
falhas = 0

# A área agora é CAMINHO (`/area/{id}`), não query: o caminho diz o que se
# olha, a query diz como. A régua (janela, critério, piso) continua na query.
AREA = "/area/ginecologia"


def checar(nome: str, obtido, esperado):
    global falhas
    ok = obtido == esperado
    falhas += 0 if ok else 1
    print(f"  [{'ok' if ok else 'FALHA'}] {nome}: {obtido}"
          + ("" if ok else f"   (esperado {esperado})"))


# A faixa de recorte e o bloco de perfis usam a MESMA linguagem (chips), e os
# dois têm um chip "todos" — escopar é obrigatório, senão o teste clica no
# primeiro do DOM (o de perfis, que vem acima) e mede outra coisa.
FAIXA_RECORTE = "div.row:has(> span.micro:text-is('Recorte'))"


def chip(pg, rotulo: str):
    return pg.locator(FAIXA_RECORTE).locator(".segfilt-o", has_text=rotulo).first


def abrir(pg, caminho: str, espera_tabela: bool = True):
    """Vai à tela e espera ela estar MONTADA, não só respondida.

    O arranque frio do servidor carrega parquet e roda os motores; esperar por
    um seletor (e não por tempo) é o que faz a suite ser determinística tanto
    no primeiro acesso quanto no cache quente.
    """
    pg.goto(f"{BASE}{caminho}")
    seletor = "tbody tr" if espera_tabela else "[data-slot='conteudo'] h2"
    pg.wait_for_selector(seletor, timeout=120_000)


def main() -> int:
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pg = navegador.new_page(viewport={"width": 1440, "height": 1000})

        # erro de console é falha, em TODA a suite: coletado aqui, cobrado no
        # fim. A URL do recurso viaja junto — sem ela, "404" não diz se é a
        # aplicação ou o ícone da aba que o navegador pede sozinho.
        erros: list[str] = []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.on("console", lambda m: erros.append(
            f"{m.text} [{(m.location or {}).get('url', '')}]")
            if m.type == "error" else None)

        print("1. TELA DE ÁREA MONTA E OS BLOCOS APARECEM")
        abrir(pg, AREA)
        checar("faixa de estatísticas", pg.locator(".stats > div").count() >= 3, True)
        checar("filtro de perfil na faixa", pg.locator(".pf-trig").count(), 1)
        checar("gráfico de distribuição tem um ponto por comparável",
               pg.locator(".plot .pt").count(), 63)
        # os dois Paretos existem, um por aba: só o da aba em cena fica visível
        checar("Pareto de cooperados na aba Cooperados",
               pg.locator(".vista-painel.on .tbl",
                          has_text="por cooperado").count(), 1)
        checar("tabela de cooperados", pg.locator("tbody tr").count(), 63)

        print("\n2. CHIPS DE RECORTE FILTRAM A TABELA E O GRÁFICO")
        for rotulo, linhas in (("Todos", 64), ("Qualificados", 21),
                               ("Persistentes", 39), ("Comparáveis", 63)):
            chip(pg, rotulo).click()
            pg.wait_for_function(
                "n => document.querySelectorAll('tbody tr').length === n", arg=linhas,
                timeout=15_000)
            checar(f"chip {rotulo}", pg.locator("tbody tr").count(), linhas)
        chip(pg, "Qualificados").click()
        pg.wait_for_timeout(300)
        checar("gráfico recuado no recorte",
               pg.locator(".plot.com-recorte").count(), 1)
        checar("pontos em cena no gráfico = linhas da tabela",
               pg.locator(".pt-no-recorte").count(), 21)

        print("\n3. PERFIL RECORTA E TRAZ O POSTO")
        abrir(pg, AREA)
        pg.locator(".pf-trig").click()
        pg.wait_for_timeout(250)
        pg.locator(".pf-opt", has_text="opera").click()
        pg.wait_for_selector("th:has-text('Posto no perfil')", timeout=15_000)
        checar("coluna do posto entra em cena",
               pg.locator("th", has_text="Posto no perfil").count(), 1)
        checar("só os portadores na tabela", pg.locator("tbody tr").count(), 3)

        print("\n4. ESCOLHA NO GRÁFICO CONVERSA COM A TABELA")
        abrir(pg, AREA)
        pg.locator(".plot .pt").first.click()
        pg.wait_for_selector("tbody tr.selected", timeout=15_000)
        checar("clique no ponto destaca a linha",
               pg.locator("tbody tr.selected").count(), 1)
        # REGRA DOS PONTOS (2026-08-19): selecionado fica na COR NORMAL — não em
        # cor cheia, e sem anel. O que marca a escolha é o recuo dos outros.
        # Cobrava "opacity 1", que só o cinza tinha folga para obedecer: ele
        # escurecia além do próprio normal e âmbar e vermelho não mudavam nada.
        # A prova agora é a RELAÇÃO, não o valor absoluto, e vale para as três
        # cores: o escolhido é mais opaco que os demais, e nenhum tem anel.
        escolhido, outro = pg.evaluate("""() => {
            const p = document.querySelector('.plot');
            const g = (s) => getComputedStyle(p.querySelector(s));
            return [parseFloat(g('.pt-escolhido').opacity),
                    parseFloat(g('.pt:not(.pt-escolhido)').opacity)];
        }""")
        checar("o ponto escolhido fica mais opaco que os demais",
               escolhido > outro, True)
        checar("e sem anel: o recuo dos outros é que marca a escolha",
               pg.eval_on_selector(".pt-escolhido",
                                   "e => getComputedStyle(e).boxShadow"),
               "none")

        print("\n5. ABA PROCEDIMENTOS")
        pg.locator(".vista", has_text="Procedimentos").click()
        pg.wait_for_selector("th:has-text('PREVALÊNCIA'), th:has-text('Prevalência')",
                             timeout=60_000)
        checar("a aba troca a unidade de análise",
               pg.locator("tbody tr:visible").count() > 100, True)
        checar("e leva o Pareto do próprio eixo",
               pg.locator(".vista-painel.on .tbl",
                          has_text="por procedimento").count(), 1)
        checar("a régua continua acima das abas",
               pg.locator(".segfilt-o").count(), 4)
        pg.locator(".vista", has_text="Cooperados").click()
        pg.wait_for_selector("th:has-text('COOPERADO'), th:has-text('Cooperado')",
                             timeout=60_000)

        print("\n6. NAVEGAÇÃO ATÉ O DOSSIÊ E DE VOLTA")
        abrir(pg, f"{AREA}?recorte=qualificados")
        pg.locator("tbody td a").first.click()
        pg.wait_for_selector("[data-slot='conteudo'] h2", timeout=120_000)
        checar("o dossiê abre no cooperado da linha",
               pg.locator("h2").first.inner_text().startswith("cooperado_"), True)
        checar("a URL nomeia a coisa, não a tela", "/cooperado/" in pg.url, True)
        checar("a área NÃO viaja na query do dossiê", "area=" in pg.url, False)
        checar("cabeçalho traz o par da área em todo número",
               pg.locator(".stats > div").count(), 4)
        checar("leitura do caso, seção a seção",
               pg.locator(".tbl", has_text="Leitura do caso").count(), 1)
        pg.wait_for_selector("tbody tr", timeout=60_000)
        checar("procedimentos do cooperado", pg.locator("tbody tr").count() > 0, True)
        checar("sem coluna de vocabulário interno",
               pg.locator("th", has_text="cascata").count(), 0)

        print("\n7. MIGALHA NAVEGA")
        pg.locator(".crumbs a", has_text="Ginecologia").click()
        pg.wait_for_selector("tbody tr", timeout=60_000)
        checar("volta à área pelo caminho da migalha",
               pg.url.split("8770")[-1].startswith("/area/ginecologia"), True)

        print("\n8. PANORAMA É A PORTA DE ENTRADA")
        pg.locator(".navitem", has_text="Panorama").click()
        pg.wait_for_selector("[data-slot='conteudo'] h2", timeout=60_000)
        checar("a raiz é o Panorama", pg.url.split("8770")[-1].split("?")[0], "/")
        checar("o item ativo da navegação segue a rota",
               pg.locator(".navitem.on").inner_text(), "Panorama")
        # espera o CONTEÚDO, não só o título: o h2 entra antes de /api/meta
        # responder, e checar as áreas nesse intervalo é medir o meio da carga
        pg.wait_for_selector("a.pill", timeout=60_000)
        checar("e leva às áreas",
               pg.locator("a.pill", has_text="Ginecologia").count() >= 1, True)
        pg.locator(".navitem", has_text="Nota Metodológica").click()
        pg.wait_for_selector("[data-slot='conteudo'] h2", timeout=60_000)
        checar("a Nota Metodológica existe e se declara",
               pg.locator("h2").first.inner_text(), "Nota metodológica")

        print("\n8b. LINKS ANTIGOS CONTINUAM VALENDO")
        pg.goto(f"{BASE}/?area=ginecologia")
        pg.wait_for_selector("tbody tr", timeout=120_000)
        checar("/?area=x redireciona para /area/x",
               pg.url.split("8770")[-1], "/area/ginecologia")
        pg.goto(f"{BASE}/dossie/cooperado_85")
        pg.wait_for_selector("[data-slot=\'conteudo\'] h2", timeout=120_000)
        checar("/dossie/{id} redireciona para /cooperado/{id}",
               pg.url.split("8770")[-1], "/cooperado/cooperado_85")

        print("\n9. ESTADOS DECLARADOS, NUNCA TELA MUDA")
        abrir(pg, "/area/mastologia")
        checar("área sem referência plena não desenha distribuição",
               pg.locator(".plot").count(), 0)
        checar("mas a lista continua", pg.locator("tbody tr").count(), 4)
        pg.goto(f"{BASE}/cooperado/cooperado_inexistente")
        pg.wait_for_selector(".banner-err", timeout=30_000)
        checar("cooperado desconhecido vira estado declarado",
               pg.locator(".banner-err").count(), 1)

        print("\n10. MINHA CONTA: A TELA DO ENTORNO, E OS SEUS DOIS ESTADOS")
        # Esta suíte roda SEM sessão (nada exporta MEDYX_SESSAO_DEV), então o
        # que ela prova aqui é o estado honesto: a tela monta, declara que não
        # há sessão, e o bloco de conta NÃO aparece na lateral. É a regra que
        # manteve o bloco fora do chassi até existir login, e ela precisa de
        # guarda: um nome de exemplo aparecendo por engano é exatamente o tipo
        # de defeito que ninguém repara até estar em produção.
        pg.goto(f"{BASE}/conta")
        pg.wait_for_selector("[data-slot='conteudo'] h2", timeout=120_000)
        checar("a tela monta", pg.locator("h2").inner_text(), "Minha conta")
        checar("sem sessão, sem bloco de conta na lateral",
               pg.locator(".side-user").count(), 0)
        checar("o rodapé da lateral fica escondido, não vazio",
               pg.locator("[data-slot='conta']").is_hidden(), True)
        checar("o estado é declarado, não é banner de erro",
               pg.locator(".tbl-hd .t").first.inner_text(),
               "Nenhuma sessão autenticada")
        checar("nenhum banner de falha", pg.locator(".banner-err").count(), 0)
        # Tela sem número não carrega régua: a faixa de critérios declararia o
        # critério de um cálculo que não aconteceu.
        checar("faixa de critérios fora da tela",
               pg.locator(".critbar").count(), 0)

        print("\n11. NENHUM ERRO DE JAVASCRIPT EM TODA A SUITE")
        # Dois ruídos que NÃO são defeito: o ícone da aba, que o navegador pede
        # sozinho, e o 404 que o próprio passo 9 provoca de propósito. Qualquer
        # outra linha de console vermelha é falha.
        ignorar = ("favicon", "cooperado_inexistente")
        reais = [e for e in erros if not any(t in e.lower() for t in ignorar)]
        checar("console limpo", reais or "nenhum", "nenhum")

        navegador.close()

    print("═" * 78)
    print("RESULTADO:", "AS TELAS MONTAM E RESPONDEM" if not falhas
          else f"{falhas} divergência(s)")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
