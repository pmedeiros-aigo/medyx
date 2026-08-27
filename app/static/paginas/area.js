/* area.js — a tela "Área de atuação".
 *
 * A página pede o chassi (navegação, contexto e régua vivem na barra lateral) e
 * escreve os SEUS blocos dentro de `conteudo`. Nenhum número nasce aqui: cada
 * bloco é desenhado a partir de /api/area/{id}.
 *
 * Blocos na tela, na ordem em que a pergunta se faz:
 *   · cabeçalho da página — título e a linha de contexto fixa da área
 *   · chips de recorte + perfis — o eixo aninhado da cascata
 *   · três cards — o tamanho do que está em cena, seguindo o recorte
 *   · abas Cooperados | Procedimentos — o conteúdo de trabalho, e dentro de
 *     cada uma: o Pareto do eixo, a tabela e (na de Cooperados) os gráficos
 *   · painel de excluídos, aberto pelo link da linha de contexto
 *
 * ── quem é dono do quê ──────────────────────────────────────────────────────
 *
 * ESTA PÁGINA é dona do ESTADO DA VISTA (recorte, perfil, aba, ordenação) e de
 * decidir QUEM ESTÁ EM CENA. Os blocos desenham o que recebem e avisam quando
 * são acionados — nenhum bloco comanda outro.
 *
 * Foi assim que se desfez o nó anterior: a tabela guardava o estado, o bloco de
 * perfis tinha de pedir a ela para trocar de perfil, e a tabela é que avisava o
 * gráfico. Três blocos amarrados para uma decisão que é da página.
 */
'use strict';

import { el } from '../lib/dom.js';
import { buscar } from '../lib/api.js';
import { abrirPagina } from '../lib/pagina.js';
import { TELAS } from '../lib/rotas.js';
import { criarVista } from '../lib/vista.js';
import { ordenar, ordemDaURL, proximaOrdem, casa } from '../lib/tabelas.js';
import { montarCabecalho } from '../blocos/cabecalho.js';
import { montarExcluidos } from '../blocos/excluidos.js';
import { montarPerfis } from '../blocos/perfis.js';
import { montarRecorte, recortePorChave } from '../blocos/recorte.js';
import { montarAbas } from '../blocos/abas.js';
import { montarTabela, COLUNAS } from '../blocos/tabela.js';
import { montarProcedimentos } from '../blocos/procedimentos.js';
import { montarDistribuicao } from '../blocos/distribuicao.js';
import { montarPareto } from '../blocos/pareto.js';
import { montarCards } from '../blocos/cards.js';
import { montarDispersao } from '../blocos/dispersao.js';

await abrirPagina({
  titulo: 'Área de atuação',
  // trocar de área continua na tela de Área, com a outra área
  aoTrocarArea: (id) => TELAS.area.caminho(id),
  montar: async ({ conteudo, area }) => {
  /* A área vem do CAMINHO; o chassi já a resolveu (e caiu na primeira se a
     rota não trouxe uma válida). */
  const escolhida = area;

  /* Default do recorte: COMPARÁVEIS (ajuste 6 do CLAUDE.md). Mora aqui, e não
     dentro de `criarVista`, porque a CARGA INICIAL também precisa dele: os
     blocos de achado vêm recortados do servidor, e pedi-los sem recorte traria
     a área inteira para uma tela que já abre em Comparáveis. */
  const RECORTE_PADRAO = 'comparaveis';

  function recorteInicial() {
    const q = new URLSearchParams(location.search);
    return { recorte: q.get('recorte') || RECORTE_PADRAO,
             perfil: q.get('perfil') || null,
             q: q.get('q') || null };
  }

  /* A primeira carga após o servidor subir paga o parquet e os motores, e uma
     tela em branco nesse intervalo lê como falha: `buscar` anuncia e limpa. */
  const dados = await buscar(`/api/area/${encodeURIComponent(escolhida)}`,
                             { anunciarEm: conteudo, rotulo: 'carregando a área…',
                               extra: recorteInicial() });

  const excluidos = montarExcluidos(conteudo, dados.composicao);
  montarCabecalho(conteudo, dados, () => excluidos.abrir());

  /* Recorte e perfil na MESMA faixa, acima do gráfico e da tabela: são a mesma
     pergunta ("quem aparece") e recortam os dois blocos. O perfil era um cartão
     à parte, com título e subtítulo, ocupando a dobra do conteúdo. */
  const faixaChips = document.createElement('div');
  faixaChips.className = 'row flexwrap';
  conteudo.appendChild(faixaChips);
  const chips = montarRecorte(faixaChips, dados,
    (chave) => definir({ recorte: chave }));
  /* Perfis são MÚLTIPLOS e viajam na URL separados por vírgula
     (?perfil=opera,alto-risco). `null` limpa tudo. */
  const perfis = montarPerfis(faixaChips, dados, (chave) => {
    if (chave === null) { definir({ perfil: null }); return; }
    const atuais = new Set(perfisEscolhidos());
    if (atuais.has(chave)) atuais.delete(chave); else atuais.add(chave);
    definir({ perfil: [...atuais].join(',') || null });
  });

  /* Os três cards ficam ABAIXO dos chips e seguem o recorte: são o tamanho do
     que está em cena. O contexto fixo da área é a linha sob o título, acima
     dos chips (CLAUDE.md, lei 0). */
  const cards = montarCards(conteudo, dados.cards);

  /* ── as duas unidades de análise, LOGO ABAIXO DOS CARDS ──────────────────
     As abas subiram em 2026-08-20, para o lugar que era da distribuição. O que
     a página responde primeiro é "quem" ou "o quê" — a lista de trabalho —, e
     ela vinha depois de dois gráficos altos: quem abria a tela para trabalhar
     rolava por eles toda vez.
     A régua continua a mesma nas duas abas (janela, critério, recorte, perfil),
     e por isso a faixa de filtros e os cards ficam ACIMA delas. */
  const abas = montarAbas(conteudo, [
    { chave: 'cooperados', rotulo: 'Cooperados', n: dados.cooperados.total },
    { chave: 'procedimentos', rotulo: 'Procedimentos', n: dados.area?.n_procedimentos },
  ], (aba) => definir({ aba }));

  /* O painel de Cooperados entra VISÍVEL para a montagem: o enxame da
     distribuição lê a largura real da plotagem em pixels, e dentro de um painel
     com `display:none` essa largura é 0 — todos os pontos empilhariam no mesmo
     lugar. `aplicar()` corrige a aba logo em seguida, inclusive quando a URL
     pede Procedimentos. */
  abas.paineis.cooperados.classList.add('on');

  /* ── OS TRÊS GRÁFICOS NUM CONTAINER SÓ, com abas (2026-08-27) ────────────
     Eram três blocos empilhados: o Pareto acima da tabela, distribuição e
     dispersão abaixo dela. Três leituras do MESMO conjunto de cooperados, e
     empilhadas custavam três alturas de rolagem para quem só queria uma.
     Agora dividem um container e se alternam por aba, com o Pareto por padrão.

     As abas são de LEITURA, não de recorte: as três desenham o mesmo recorte
     em cena, e trocar de aba não muda quem está sendo medido. Por isso não vão
     para a URL, ao contrário da aba Cooperados/Procedimentos, que troca a
     unidade de análise. */
  const graficos = montarAbas(abas.paineis.cooperados, [
    { chave: 'pareto', rotulo: 'Concentração' },
    { chave: 'distribuicao', rotulo: 'Distribuição' },
    { chave: 'dispersao', rotulo: 'Quantidade × custo' },
  ], (k) => { graficos.marcar(k); encaixar(k); });

  /* A faixa de abas mora DENTRO do cartão do gráfico em cena, não acima dele:
     fora das bordas ela parecia uma segunda navegação de página, irmã da de
     Cooperados/Procedimentos logo acima, quando é controle de um bloco só.

     Como um painel só está visível por vez, a faixa é UMA e se muda de cartão a
     cada troca, em vez de haver três cópias sincronizadas. Vai dentro de um
     `.tbl-hd` para herdar o respiro das bordas do contrato, e como primeiro
     filho para pegar o arredondamento de topo (`.tbl>:first-child`). */
  const faixaGraficos = abas.paineis.cooperados.querySelector('.vistas');
  const capaAbas = el('div', 'tbl-hd');
  capaAbas.appendChild(faixaGraficos);

  /* Qual aba está de pé. Guardado aqui porque `reencaixar()` precisa saber para
     onde devolver a faixa depois de um redesenho, e o `montarAbas` não guarda
     a escolha. */
  let graficoEmCena = 'pareto';

  function encaixar(chave) {
    graficoEmCena = chave;
    const cartao = graficos.paineis[chave]?.querySelector('.tbl');
    if (cartao && capaAbas.parentElement !== cartao) {
      cartao.insertBefore(capaAbas, cartao.firstChild);
    }
  }
  /* Devolve a faixa ao cartão em cena. Idempotente: se ela já está lá,
     `encaixar` não mexe. */
  graficos.reencaixar = () => encaixar(graficoEmCena);

  /* Todos os painéis VISÍVEIS durante a montagem, pela mesma razão que o painel
     de Cooperados já entra com `.on`: a distribuição e a dispersão leem a
     largura real da plotagem em pixels, e dentro de `display:none` ela é 0 —
     os pontos empilhariam todos no mesmo lugar. `marcar()` logo abaixo deixa só
     o Pareto de pé. */
  for (const painel of Object.values(graficos.paineis)) painel.classList.add('on');

  const pareto = montarPareto(graficos.paineis.pareto, dados.pareto_cooperados,
    (id) => grafico?.marcar(id), 'pareto-cooperados');
  const grafico = montarDistribuicao(graficos.paineis.distribuicao, dados, (id) => {
    if (!id) { tabela.destacar(null); return; }
    if (!tabela.destacar(id)) {
      definir({ recorte: 'todos' });
      tabela.destacar(id);
    }
  });
  /* Bloco EXPERIMENTAL: quantidade no X, custo no Y, porte no tamanho, cor no
     excedente. Serve para decidir se o custo entra como eixo próprio. */
  const bolhas = montarDispersao(graficos.paineis.dispersao, dados,
                                 (id) => grafico?.marcar(id));

  graficos.marcar('pareto');
  encaixar('pareto');

  const tabela = montarTabela(abas.paineis.cooperados, dados, {
    aoEscolherLinha: (id) => { grafico?.marcar(id); tabela.destacar(id); },
    aoOrdenar: (chave) => definir(proximaOrdemDaVista(chave)),
    /* Da URL e não de `estado`: a tabela é montada ANTES de `criarVista`, e
       ler o estado aqui estourava a tela inteira. Os callbacks podem, porque
       só rodam depois. */
    busca: new URLSearchParams(location.search).get('q') || '',
    aoBuscar: (q) => definir({ q: q || null }),
  });

  const paretoProc = montarPareto(abas.paineis.procedimentos,
                                  dados.pareto_procedimentos, null,
                                  'pareto-procedimentos');
  const procedimentos = montarProcedimentos(abas.paineis.procedimentos,
                                            dados.area?.id ?? '');

  /* ── o estado da vista, e o que ele governa ──────────────────────────────
   * "Todos" inclui quem está abaixo do volume mínimo, que entra sem posição,
   * sem consistência e sem excedente — abrir a tela nele põe em cena linhas
   * que não sustentam comparação. Por isso o default é COMPARÁVEIS (ajuste 6
   * do CLAUDE.md); "Todos" fica a um clique, e é lá que essas linhas são
   * vistas de propósito. */
  const { estado, definir } = criarVista(
    { recorte: RECORTE_PADRAO, perfil: null, aba: 'cooperados', q: null,
      ...ordemInicial() },
    aplicar);

  function ordemInicial() {
    const { chave, direcao } = ordemDaURL(COLUNAS);
    return { ord: chave, dir: direcao };
  }

  /** Três estados em ciclo: decrescente, crescente, padrão. */
  function proximaOrdemDaVista(chave) {
    const p = proximaOrdem(estado.ord, estado.dir, chave);
    return { ord: p.chave, dir: p.direcao };
  }

  /**
   * QUEM ESTÁ EM CENA — a única função que decide isso, e ela é da página.
   *
   * Não calcula nada: filtra o que a API já entregou, por campos que o motor
   * marcou (`grupos`, `avaliavel`, `sub_perfis`). Ordenar também não é
   * calcular — é reordenar o que já veio, e por isso não custa ida ao servidor.
   */
  /** As chaves de perfil da URL, já sem os vazios. */
  function perfisEscolhidos() {
    return (estado.perfil ?? '').split(',').filter(Boolean);
  }

  function emCena() {
    const r = recortePorChave(estado.recorte);
    let linhas = r.filtro ? dados.cooperados.linhas.filter(r.filtro)
                          : dados.cooperados.linhas;
    const chaves = new Set(perfisEscolhidos());
    const escolhidos = (dados.cooperados.perfis ?? [])
      .filter((p) => chaves.has(p.chave) && p.selecionavel);
    /* O perfil recorta por cima do recorte da cascata: quem aparece é quem
       CARREGA algum dos perfis marcados (UNIÃO, não interseção — identidades
       se acumulam, e ninguém procura "quem opera E é de alto risco"). A régua
       não muda: sub-perfil é identidade. */
    /* A BUSCA é o último filtro e o mais fraco: ela LOCALIZA dentro do que o
       recorte e o perfil deixaram em cena, e não muda nenhum agregado. Por
       isso não entra em `recorteAtivo()`, que é o que o servidor reagrega. */
    if (estado.q) linhas = linhas.filter((l) => casa(l.id, estado.q));
    if (escolhidos.length) {
      const flags = new Set(escolhidos.map((p) => p.flag));
      linhas = linhas.filter(
        (l) => l.sub_perfis?.some((sp) => flags.has(sp.chave)));
    }
    return { recorte: r, perfis: escolhidos, linhas };
  }

  /** Redistribui a vista para todos os blocos. */
  function aplicar() {
    const { recorte, perfis: escolhidos, linhas } = emCena();
    chips.marcar(recorte.chave);
    perfis?.marcar(escolhidos.map((p) => p.chave));

    /* O contador da aba conta QUEM ESTÁ EM CENA, não o total da área: ele fica
       encostado no rótulo que nomeia a lista logo abaixo, e um número parado
       enquanto a lista encolhe é contradição na mesma faixa da tela. A aba de
       Procedimentos não acompanha porque o recorte é de COOPERADOS: a lista
       dela é da área inteira, e recortá-la por aqui seria afirmar um filtro que
       não foi aplicado. */
    abas.contar('cooperados', linhas.length);

    /* O gráfico acompanha o que está em cena; "Todos" e "Comparáveis" não
       recuam ninguém, porque o gráfico só desenha avaliáveis e mandar o
       conjunto inteiro derrubaria o esmaecimento da escolha de um ponto. */
    const recorta = escolhidos.length > 0
      || !['todos', 'comparaveis'].includes(recorte.chave);
    const ids = recorta ? linhas.map((l) => l.id) : null;
    grafico?.realcar(ids);
    bolhas?.realcar(ids);
    buscarAchados();

    abas.marcar(estado.aba);
    if (estado.aba !== 'cooperados') {
      procedimentos.render(recorteAtivo()).catch(() => {});
      return;
    }

    const coluna = COLUNAS.find((c) => c.ordem === estado.ord);
    const visiveis = ordenar(linhas, coluna, estado.dir);
    tabela.atualizar({
      linhas: visiveis,
      /* A coluna do posto só entra com UM perfil: posto é a posição dentro de
         um perfil, e entre dois não há definição honesta. */
      perfilFlag: escolhidos.length === 1 ? escolhidos[0].flag : null,
      ordem: estado.ord,
      direcao: estado.dir,
      rodape: rodape(recorte, escolhidos, visiveis, coluna),
    });
  }

  /** O recorte ativo, na forma em que a API o recebe. */
  function recorteAtivo() {
    return { recorte: estado.recorte, perfil: estado.perfil || null };
  }

  /* ── os blocos de ACHADO, que o servidor reagrega ─────────────────────────
   * Os dois Paretos somam excedente, e somar é cálculo: não dá para recortá-los
   * aqui. Antes o bloco só esmaecia as linhas fora de cena, e o total do
   * título, a ordem e o % acumulado continuavam sendo os da área — a barra
   * dizia "12% do total" sobre um total que a lista visível já não somava.
   *
   * Uma busca por recorte, e só do que muda: régua, distribuição, estatísticas
   * do topo e a lista de cooperados não vêm de novo porque não se movem.
   *
   * `sequencia` descarta resposta atrasada: clicar Persistentes e Qualificados
   * em seguida pode devolver as duas fora de ordem, e a última a chegar venceria
   * a última pedida. */
  let sequencia = 0;
  /* O que os Paretos em cena já representam. Começa no recorte da carga
     inicial, que veio com a página — sem isso, abrir a tela dispararia uma
     busca para pedir de novo exatamente o que acabou de chegar. E como
     `aplicar()` roda a cada mudança de vista, inclusive trocar de aba ou de
     ordenação, a comparação é o que impede a ordenação da tabela de ir buscar
     Pareto no servidor. */
  let achadoEmCena = chaveDoRecorte(recorteInicial());

  function chaveDoRecorte({ recorte, perfil }) {
    return `${recorte ?? ''}|${perfil ?? ''}`;
  }

  async function buscarAchados() {
    const alvo = recorteAtivo();
    if (chaveDoRecorte(alvo) === achadoEmCena) return;
    achadoEmCena = chaveDoRecorte(alvo);
    const meu = ++sequencia;
    const a = await buscar(`/api/area/${encodeURIComponent(escolhida)}/achados`,
                           { extra: alvo });
    if (meu !== sequencia) return;
    cards.atualizar(a.cards);
    pareto?.atualizar(a.pareto_cooperados);
    paretoProc?.atualizar(a.pareto_procedimentos);
    /* O Pareto redesenha com `cartao.replaceChildren`, e isso leva junto a
       faixa de abas que mora DENTRO do cartão. Reencaixar depois de cada
       atualização, como o próprio `pareto.js` já faz com o botão de recolher.
       Sem isto, trocar o recorte deixava o gráfico de Concentração sozinho, sem
       caminho de volta para Distribuição e Dispersão. */
    graficos?.reencaixar();
  }

  /** O estado da vista em uma frase: o que está em cena e sob que ordem. */
  function rodape(recorte, escolhidos, visiveis, coluna) {
    let diz = `${visiveis.length} de ${dados.cooperados.total} · `
            + `recorte: ${recorte.rotulo.toLowerCase()}`;
    if (escolhidos.length) {
      diz += ` · ${escolhidos.length === 1 ? 'perfil' : 'perfis'}: `
           + escolhidos.map((p) => p.rotulo).join(', ');
    }
    /* A busca entra no rodapé como os outros filtros: o estado da vista é uma
       frase só, e um filtro que não aparece nela é um filtro que o leitor
       esquece que ligou. */
    if (estado.q) diz += ` · busca: "${estado.q}"`;
    const ordem = coluna
      ? `${coluna.nome.toLowerCase()}, ${estado.dir === 'asc' ? 'crescente' : 'decrescente'}`
      : `${dados.cooperados.ordenado_por} (padrão)`;
    return `${diz} · ordenado por ${ordem}`;
  }

  aplicar();
  },
});
