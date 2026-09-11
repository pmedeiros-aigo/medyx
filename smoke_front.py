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
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path[:0] = [str(Path(__file__).resolve().parent)]
import config  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8770"


def caminho_de(url: str) -> str:
    """O caminho da URL, sem o servidor.

    Era `url.split("8770")[-1]`, com a porta cravada em quatro asserções: rodar
    a prova contra outra porta (um segundo servidor no ar, o de sempre ocupado)
    reprovava quatro checagens de rota que não tinham nada de errado.
    """
    return url[len(BASE):] if url.startswith(BASE) else url
falhas = 0

# A área agora é CAMINHO (`/area/{id}`), não query: o caminho diz o que se
# olha, a query diz como. A régua (janela, critério, piso) continua na query.
AREA = "/area/ginecologia-geral"   # a área de referência da classificação v2


def checar(nome: str, obtido, esperado):
    global falhas
    ok = obtido == esperado
    falhas += 0 if ok else 1
    print(f"  [{'ok' if ok else 'FALHA'}] {nome}: {obtido}"
          + ("" if ok else f"   (esperado {esperado})"))


# A faixa de recorte e o bloco de perfis usam a MESMA linguagem (chips), e os
# dois têm um chip "todos" — escopar é obrigatório, senão o teste clica no
# primeiro do DOM (o de perfis, que vem acima) e mede outra coisa.


def chip(pg, chave: str):
    """Escolhe um degrau no controle de Recorte, pela CHAVE do método.

    O controle era um segmentado de chips e virou um menu suspenso quando os
    degraus passaram a viajar com a queda e a contagem de cada um: sete opções
    lado a lado não cabiam na faixa. Abrir e escolher são dois gestos, e o
    `for`/checkbox que o abre é o mesmo padrão do filtro de perfil.

    Pela CHAVE e não pelo rótulo: o texto da opção vem do motor e acompanha o
    vocabulário do produto, então uma prova presa a ele reprova toda vez que
    uma palavra melhora.
    """
    pg.locator(".pf-trig", has_text="Recorte").first.click()
    pg.wait_for_selector(".pf-pop .pf-opt", state="visible", timeout=15_000)
    return pg.locator(f'.pf-pop .pf-opt[data-chave="{chave}"]').first


def vista_grafico(pg, rotulo: str):
    """Troca a vista do container de gráficos (Concentração · Distribuição ·
    Quantidade × custo).

    Os três eram blocos empilhados e passaram a dividir um container com abas em
    set/2026: são três leituras do MESMO conjunto, e empilhadas custavam três
    alturas de rolagem para quem só queria uma. Trocar de vista é LEITURA e não
    recorte, então nada vai para a URL e a prova precisa clicar.
    """
    pg.locator(".graficos-vistas .segfilt-o", has_text=rotulo).first.click()
    pg.wait_for_timeout(300)


def abrir(pg, caminho: str, espera_tabela: bool = True):
    """Vai à tela e espera ela estar MONTADA, não só respondida.

    O arranque frio do servidor carrega parquet e roda os motores; esperar por
    um seletor (e não por tempo) é o que faz a suite ser determinística tanto
    no primeiro acesso quanto no cache quente.
    """
    pg.goto(f"{BASE}{caminho}")
    # A TABELA PRINCIPAL da tela, e não a primeira que aparecer: a de
    # Principais oportunidades monta antes e devolveria a página com a lista de
    # cooperados ainda vazia. Ela vive fora das abas, então basta nomear as
    # abas. No dossiê, que não tem abas de vista, a espera segue genérica.
    seletor = ("tbody tr:not(.tbl-oportunidades tbody tr)" if espera_tabela
               else "[data-slot='conteudo'] h2")
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
        # A FAIXA DE KPIs SAIU (set/2026) e o bloco "Leitura da área" ocupou o
        # lugar dela: os mesmos números, agrupados pela pergunta que respondem,
        # com o excedente em destaque. A prova segue o bloco que existe.
        checar("Leitura da área com os grupos de números",
               pg.locator(".res-grupo").count() >= 3, True)
        # O bloco que responde "o que eu faço agora", entre a Leitura e as abas
        checar("principais oportunidades com o corte do config",
               pg.locator(".tbl-oportunidades tbody tr:not([hidden])").count(),
               config.N_OPORTUNIDADES_VISIVEIS)
        # DOIS gatilhos na faixa desde que o Recorte virou menu suspenso: ele e
        # o Perfil usam o mesmo componente, e é isso que os torna irmãos na tela
        checar("Recorte e Perfil na faixa", pg.locator(".pf-trig").count(), 2)
        checar("gráfico de distribuição tem um ponto por comparável",
               pg.locator(".plot .pt").count(), 45)
        vista_grafico(pg, "Concentração")
        # O PARETO FOI PARA DENTRO DAS ABAS DE GRÁFICO (set/2026): Concentração,
        # Distribuição e Quantidade × custo dividem um container e se alternam,
        # com a Concentração por padrão. A prova pergunta pela vista ativa.
        checar("Concentração é a vista de gráfico padrão",
               pg.locator(".graficos-vistas .vista-painel.on .tbl-hd .t")
                 .inner_text().startswith("Concentração"), True)
        checar("tabela de cooperados", pg.locator(".vista-painel tbody tr").count(), 45)

        # A LATERAL RECOLHE, e recolhida sobra o essencial: a marca, o ícone de
        # cada tela e o avatar. Nenhum destino some — o que sai é a etiqueta, e
        # ela volta no `title`, senão o ícone sozinho é adivinhação.
        largura = "() => document.querySelector('.shell-side').getBoundingClientRect().width"
        aberta = pg.evaluate(largura)
        pg.locator("[data-lateral-btn]").click()
        pg.wait_for_timeout(250)
        checar("a lateral recolhe", pg.evaluate(largura) < aberta / 2, True)
        checar("e os destinos continuam todos lá",
               pg.locator(".shell-side .navitem").count(), 5)
        checar("com o rótulo no hover, já que o ícone fica sozinho",
               pg.locator(".shell-side .navitem").first.get_attribute("title"),
               "Panorama")
        pg.locator("[data-lateral-btn]").click()
        pg.wait_for_timeout(250)
        checar("e volta ao expandir", pg.evaluate(largura), aberta)

        print("\n2. CHIPS DE RECORTE FILTRAM A TABELA E O GRÁFICO")
        for chave, linhas in (("todos", 55), ("qualificados", 13),
                              ("persistente", 27), ("comparaveis", 45)):
            chip(pg, chave).click()
            pg.wait_for_function(
                "n => document.querySelectorAll('.vista-painel tbody tr').length === n", arg=linhas,
                timeout=15_000)
            checar(f"recorte {chave}", pg.locator(".vista-painel tbody tr").count(), linhas)
        chip(pg, "qualificados").click()
        pg.wait_for_timeout(300)
        vista_grafico(pg, "Distribuição")
        checar("gráfico recuado no recorte",
               pg.locator(".plot.com-recorte").count(), 1)
        checar("pontos em cena no gráfico = linhas da tabela",
               pg.locator(".pt-no-recorte").count(), 13)

        # TROCAR A ORDEM DO PARETO não pode levar a faixa de abas junto. Ela mora
        # DENTRO do cartão do gráfico em cena, e o Pareto se redesenha com
        # `replaceChildren`: sem devolvê-la, ordenar apagava o caminho para
        # Distribuição e Quantidade × custo, e o cartão encolhia a altura dela.
        vista_grafico(pg, "Concentração")
        pg.locator(".graficos-vistas .vista-painel.on .segfilt-o",
                   has_text="Custo total").click()
        pg.wait_for_timeout(400)
        # a faixa é o `.tbl-hd` de topo do cartão; o "Ordenar por" é outro
        # `.segfilt`, no cabeçalho de baixo, então a prova pergunta pelo nome de
        # uma das vistas em vez de contar controles
        checar("trocar a ordem do Pareto mantém as abas dos gráficos",
               pg.locator(".graficos-vistas .vista-painel.on .tbl .segfilt-o",
                          has_text="Quantidade × custo").count(), 1)
        # e o caminho continua servindo: a aba trocada depois da reordenação
        vista_grafico(pg, "Distribuição")
        checar("e as abas continuam trocando de gráfico depois de reordenar",
               pg.locator(".graficos-vistas .vista-painel.on .tbl-hd .t")
                 .inner_text().startswith("Distribuição"), True)

        print("\n3. PERFIL RECORTA E TRAZ O POSTO")
        abrir(pg, AREA)
        pg.locator(".pf-trig", has_text="Perfil").first.click()
        pg.wait_for_timeout(250)
        # v2: os badges são identidade da mistura (carteira, área secundária,
        # cirurgia, executa); "carteira jovem" tem 7 portadores na área de referência
        pg.locator(".pf-opt", has_text="carteira jovem").first.click()
        pg.wait_for_selector("th:has-text('Posto no perfil')", timeout=15_000)
        checar("coluna do posto entra em cena",
               pg.locator("th", has_text="Posto no perfil").count(), 1)
        checar("só os portadores na tabela", pg.locator(".vista-painel tbody tr").count(), 7)

        print("\n4. ESCOLHA NO GRÁFICO CONVERSA COM A TABELA")
        abrir(pg, AREA)
        # A distribuição é uma VISTA do container de gráficos desde set/2026, e
        # a padrão é a Concentração: sem trocar de vista o ponto existe no DOM e
        # não está em cena.
        vista_grafico(pg, "Distribuição")
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
               pg.locator(".vista-painel tbody tr:visible").count() > 100, True)
        # Cada aba leva o Pareto do PRÓPRIO eixo: o de cooperados fica na aba
        # Cooperados, o de procedimentos na aba Procedimentos. Os dois se chamam
        # "Concentração do custo excedente" porque a pergunta é a mesma; o que
        # muda é a unidade das linhas, e é ela que a prova pergunta.
        checar("e leva o Pareto do próprio eixo",
               pg.locator(".vista-painel.on .pareto-l").count() > 0, True)
        # A RÉGUA CONTINUA ACIMA DAS ABAS, e é a mesma nas duas: trocar de
        # unidade de análise não mexe em contra quem se mede. O controle era um
        # segmentado de chips e virou menu suspenso; o que a prova cobra é que
        # ele siga na tela e mantenha o recorte escolhido.
        checar("a régua continua acima das abas, com o recorte intacto",
               pg.locator(".pf-trig", has_text="Recorte")
                 .locator(".pf-tag").inner_text().startswith("Comparáveis"),
               True)
        pg.locator(".vista", has_text="Cooperados").click()
        pg.wait_for_selector("th:has-text('COOPERADO'), th:has-text('Cooperado')",
                             timeout=60_000)

        print("\n5a. UMA OPORTUNIDADE ABRE O PAINEL COM O PAR APONTADO")
        # Clicar numa linha de Principais oportunidades é escolher um PAR, e o
        # painel tem de abrir dizendo qual dos cooperados é o dele nos DOIS
        # desenhos: o ponto no enxame e a linha na lista. Sem isso o leitor
        # procura no gráfico o nome que acabou de clicar.
        abrir(pg, AREA)
        linha_opo = pg.locator(".tbl-oportunidades tbody tr").first
        coop = linha_opo.get_attribute("data-coop")
        linha_opo.click()
        pg.wait_for_selector(".painel-lateral .pnl-ent-alvo", timeout=60_000)
        checar("o painel abre com a linha do par apontada",
               pg.locator(".painel-lateral .pnl-ent-alvo")
                 .first.get_attribute("data-coop"), coop)
        checar("e com o ponto dele aceso no enxame",
               pg.locator(".painel-lateral .plot .pt.pt-escolhido")
                 .first.get_attribute("data-coop"), coop)
        # o realce dos demais RECUA, que é o que faz o ponto apontado se ler
        checar("os outros pontos recuam",
               pg.locator(".painel-lateral .plot.com-selecao").count(), 1)
        # e o hover EMPRESTA o destaque: sair dele devolve ao par apontado, em
        # vez de deixar a gaveta sem destaque nenhum
        pg.locator(".painel-lateral .plot .pt").last.hover()
        pg.locator(".painel-lateral .pnl-hd .t").hover()
        pg.wait_for_timeout(200)
        checar("sair do hover devolve o destaque ao par apontado",
               pg.locator(".painel-lateral .pnl-ent-alvo")
                 .first.get_attribute("data-coop"), coop)
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(300)

        print("\n6. NAVEGAÇÃO ATÉ O DOSSIÊ E DE VOLTA")
        abrir(pg, f"{AREA}?recorte=qualificados")
        pg.locator("tbody td a").first.click()
        pg.wait_for_selector("[data-slot='conteudo'] h2", timeout=120_000)
        checar("o dossiê abre no cooperado da linha",
               pg.locator("h2").first.inner_text().startswith("cooperado_"), True)
        checar("a URL nomeia a coisa, não a tela", "/cooperado/" in pg.url, True)
        checar("a área NÃO viaja na query do dossiê", "area=" in pg.url, False)
        # A FAIXA DE KPIs SAIU do dossiê junto com a da área (set/2026): os
        # mesmos números vivem na "Leitura do caso", agrupados pela pergunta que
        # respondem. O que a prova cobra continua sendo o mesmo: nenhum número do
        # cabeçalho anda sem o par da área ao lado.
        checar("Leitura do caso traz o par da área em todo número",
               pg.locator(".res-grupo").count() >= 3, True)
        checar("leitura do caso, seção a seção",
               pg.locator(".tbl", has_text="Leitura do caso").count(), 1)
        pg.wait_for_selector("tbody tr", timeout=60_000)
        checar("procedimentos do cooperado", pg.locator("tbody tr").count() > 0, True)
        checar("sem coluna de vocabulário interno",
               pg.locator("th", has_text="cascata").count(), 0)

        print("\n7. O RASTRO DO DOSSIÊ, E A VOLTA AO GRUPO")
        # A migalha é COLEÇÃO › ITEM (set/2026), a única hierarquia que a URL
        # tem: `/cooperados` -> `/cooperado/85`. Saíram dali o tipo ("Dossiê do
        # Cooperado", que não era lugar) e a área (que a URL não contém).
        checar("a migalha é coleção › item",
               pg.locator(".crumbs a", has_text="Cooperados").count(), 1)
        checar("e não nomeia mais o tipo do documento",
               pg.locator(".crumbs", has_text="Dossiê do Cooperado").count(), 0)
        checar("a lateral acende Cooperados, de onde o item veio",
               pg.locator(".navitem.on").inner_text(), "Cooperados")
        # A ÁREA continua a um clique, na linha de contexto do cabeçalho: ela é
        # fato analítico (contra quem o caso é medido), não degrau do rastro.
        # Sem este link o dossiê ficaria sem porta para o próprio grupo.
        pg.locator(".sub a", has_text="Ginecologia Geral").first.click()
        pg.wait_for_selector("tbody tr", timeout=60_000)
        checar("volta à área pelo link do contexto",
               caminho_de(pg.url).startswith("/area/ginecologia-geral"), True)

        print("\n8. PANORAMA É A PORTA DE ENTRADA")
        pg.locator(".navitem", has_text="Panorama").click()
        pg.wait_for_selector("[data-slot='conteudo'] h2", timeout=60_000)
        checar("a raiz é o Panorama", caminho_de(pg.url).split("?")[0], "/")
        checar("o item ativo da navegação segue a rota",
               pg.locator(".navitem.on").inner_text(), "Panorama")
        # espera o CONTEÚDO, não só o título: o h2 entra antes de a API
        # responder, e checar as áreas nesse intervalo é medir o meio da carga.
        # As pastilhas viraram CARTÕES em set/2026, quando o Panorama deixou de
        # ser esqueleto: cada área tem o seu, com régua ou sem.
        pg.wait_for_selector(".kpis-areas .kpi", timeout=60_000)
        checar("e mostra todas as áreas de atuação",
               pg.locator(".kpis-areas .kpi").count(), 8)
        # NINGUÉM DESAPARECE: as áreas sem régua continuam na tela, recuadas e
        # com o motivo no lugar dos números que não existem.
        checar("as áreas sem referência continuam na tela",
               pg.locator(".kpi-sem-regua").count(), 5)
        # O CARTÃO NÃO É LINK: ele descreve a área, e o gesto útil da tela é
        # comparar as áreas entre si, não entrar numa delas.
        checar("e o cartão de área não é link",
               pg.locator(".kpis-areas a.kpi").count(), 0)
        # as PRINCIPAIS OPORTUNIDADES da especialidade, o mesmo bloco da tela de
        # Área com o conjunto trocado, ganham a coluna que diz contra qual régua
        # cada caso foi medido
        checar("as principais oportunidades cruzam as áreas",
               pg.locator(".tbl-oportunidades th",
                          has_text="Área de atuação").count(), 1)
        # UMA GRADE, UM TAMANHO: houve uma versão com dois cartões grandes na
        # frente, e eles prometiam responder "onde o excesso está" — pergunta de
        # Pareto, que tem seção própria. Cartão grande sobre uma lista de áreas
        # afirma concentração onde o desenho só cataloga.
        #
        # A prova é ESTRUTURAL, e não a altura medida: numa janela estreita a
        # grade quebra em duas fileiras e as alturas divergem por largura, não
        # por desenho. O que se cobra é que exista UMA grade e que ela guarde
        # todos os cartões.
        checar("uma grade só, com todas as áreas",
               (pg.locator(".kpis-areas").count(),
                pg.locator(".kpis-areas > .kpi").count()), (1, 8))
        checar("e o título não promete concentração",
               pg.locator("h3").first.inner_text(), "Áreas de atuação")
        pg.locator(".navitem", has_text="Nota Metodológica").click()
        pg.wait_for_selector("[data-slot='conteudo'] h2", timeout=60_000)
        checar("a Nota Metodológica existe e se declara",
               pg.locator("h2").first.inner_text(), "Nota metodológica")

        print("\n8a. O ÍNDICE DE PROCEDIMENTOS TEM NÚMERO, E POR QUÊ")
        # A diferença para o índice de cooperados é o assunto desta seção. Lá a
        # lista atravessa peer groups e por isso NÃO tem coluna ordenável;
        # aqui a soma junta dinheiro já medido contra a régua de cada área, e a
        # tela seria inútil sem número.
        abrir(pg, "/procedimentos")
        checar("o índice abre com todos os procedimentos",
               pg.locator("tbody tr").count(), 883)
        checar("e a ordem de entrada é a variação excedente",
               pg.locator("tbody tr").first.locator("td").first.inner_text(),
               "Procedimento Diagnóstico Por Captura Híbrida")
        # A COLUNA QUE SÓ ESTA TELA DÁ: excedente em mais de uma área é conversa
        # de protocolo, e não conversa individual.
        checar("com a coluna de áreas com excedente",
               pg.locator("th", has_text="Áreas").count(), 1)
        checar("as colunas são ordenáveis, ao contrário do índice de cooperados",
               pg.locator("th.ord").count() > 0, True)
        # O SELETOR DE ÁREA SAI: a lista é da especialidade inteira, somada
        # entre as áreas. Controle que não governa nada não é inofensivo.
        checar("e o seletor de área sai, porque não governa a lista",
               pg.locator("[data-trig='area']").count(), 0)
        # A FAIXA DE CRITÉRIOS FICA: todo número desta tabela é número comparado,
        # e a faixa é o carimbo de sob qual régua ele foi calculado.
        checar("mas a faixa de critérios fica, porque há número comparado",
               pg.locator(".critbar").count(), 1)
        campo = pg.locator(".search input")
        campo.fill("captura")
        pg.wait_for_timeout(150)
        checar("a busca recorta a lista", pg.locator("tbody tr").count(), 1)
        campo.fill("")
        pg.wait_for_timeout(150)
        # E DE LÁ SE ABRE UM: a lista é a porta, como /cooperados é a porta do
        # dossiê. O link tem de levar à tela do procedimento, e não à gaveta de
        # uma área.
        pg.locator("tbody tr td a").first.click()
        pg.wait_for_selector(".res-grupo", timeout=60_000)
        checar("a lista abre o procedimento",
               caminho_de(pg.url).split("?")[0], "/procedimento/40601293")
        checar("com a leitura do procedimento",
               pg.locator("h2").first.inner_text(),
               "Procedimento Diagnóstico Por Captura Híbrida")
        # A SEÇÃO QUE SÓ ESTA TELA DÁ: as réguas lado a lado. Ela é o que impede
        # que o excedente somado seja lido como se houvesse uma régua única.
        checar("as réguas das áreas aparecem lado a lado",
               pg.locator(".tbl-hd .t", has_text="por área de atuação").count(), 1)
        # ÁREA SEM RÉGUA CONTINUA NA TELA, com o motivo no lugar do número
        checar("e a área sem referência não desaparece",
               pg.locator(".tag-caveat").count() > 0, True)
        checar("quem pede acima da referência traz a área de cada um",
               pg.locator("th", has_text="Área de atuação").count(), 2)
        # NENHUMA DAS DUAS TABELAS ORDENA: cabeçalho clicável sobre peer groups
        # convida a ranqueá-los, e réguas não se comparam entre si.
        checar("e nenhuma das duas tabelas convida a ranquear",
               pg.locator("th.ord").count(), 0)
        checar("o rastro é coleção › item",
               pg.locator(".crumbs a", has_text="Procedimentos").count(), 1)
        pg.goto(f"{BASE}/procedimento/00000000")
        pg.wait_for_selector(".banner-err", timeout=30_000)
        checar("procedimento desconhecido vira estado declarado",
               pg.locator(".banner-err").count(), 1)

        print("\n8b. LINKS ANTIGOS CONTINUAM VALENDO")
        pg.goto(f"{BASE}/?area=ginecologia-geral")
        pg.wait_for_selector("tbody tr", timeout=120_000)
        checar("/?area=x redireciona para /area/x",
               caminho_de(pg.url), "/area/ginecologia-geral")
        pg.goto(f"{BASE}/dossie/cooperado_85")
        pg.wait_for_selector("[data-slot=\'conteudo\'] h2", timeout=120_000)
        checar("/dossie/{id} redireciona para /cooperado/{id}",
               caminho_de(pg.url), "/cooperado/cooperado_85")

        print("\n9. ESTADOS DECLARADOS, NUNCA TELA MUDA")
        abrir(pg, "/area/mastologia")
        checar("área sem referência plena não desenha distribuição",
               pg.locator(".plot").count(), 0)
        checar("mas a lista continua", pg.locator(".vista-painel tbody tr").count(), 6)
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
               pg.locator(".sec-hd h3").first.inner_text(),
               "Sessão não autenticada")
        # A tela é de LEITURA, não de análise: sem cartão, sem moldura. Guarda
        # contra alguém reintroduzir `.tbl` aqui por hábito das outras telas.
        checar("sem cartão em volta da seção",
               pg.locator("[data-slot='conteudo'] .tbl").count(), 0)
        checar("nenhum banner de falha", pg.locator(".banner-err").count(), 0)
        # Tela sem número não carrega régua: a faixa de critérios declararia o
        # critério de um cálculo que não aconteceu.
        checar("faixa de critérios fora da tela",
               pg.locator(".critbar").count(), 0)

        print("\n11. NENHUM ERRO DE JAVASCRIPT EM TODA A SUITE")
        # Três ruídos que NÃO são defeito: o ícone da aba, que o navegador pede
        # sozinho, e os dois 404 que os passos 8a e 9 provocam de propósito para
        # provar o estado declarado. Qualquer outra linha vermelha é falha.
        ignorar = ("favicon", "cooperado_inexistente", "procedimento/00000000")
        reais = [e for e in erros if not any(t in e.lower() for t in ignorar)]
        checar("console limpo", reais or "nenhum", "nenhum")

        navegador.close()

    print("═" * 78)
    print("RESULTADO:", "AS TELAS MONTAM E RESPONDEM" if not falhas
          else f"{falhas} divergência(s)")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
