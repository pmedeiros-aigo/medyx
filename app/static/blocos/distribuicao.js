/* distribuicao.js — o gráfico de distribuição da área, em três medidas.
 *
 * Um ponto por cooperado avaliável sobre um eixo só. É a leitura que a tabela
 * não dá: onde está a massa, onde está a cauda, e o quanto o extremo se afasta
 * dela.
 *
 * ── o controle de MEDIDA (2026-08-31) ───────────────────────────────────────
 *
 * O eixo era um só: exames por consulta. Quem pede POUCO e CARO ficava no meio
 * da nuvem, indistinguível de quem pede pouco e barato. O segmentado no
 * cabeçalho troca a grandeza do eixo entre três leituras do mesmo grupo:
 *
 *   Exames por consulta   quantidade solicitada
 *   Custo por consulta    R$ solicitados por consulta
 *   Excesso por consulta  variação excedente em R$ por consulta
 *
 * Trocar de medida é LEITURA, não recorte: o conjunto em cena não muda, a
 * escolha de um ponto e o recorte de perfil sobrevivem à troca. Por isso a
 * medida NÃO viaja na URL, pela mesma razão que as abas Concentração /
 * Distribuição / Quantidade × custo não viajam (ver `area.js`), e por isso as
 * três chegam no MESMO payload: uma ida ao servidor para mudar de eixo faria
 * parecer que o conjunto medido mudou junto.
 *
 * Lê `distribuicao.medidas` de /api/area/{id}. Não calcula nada, nem posição: a
 * API manda `pos_pct` já resolvido contra a escala de cada medida.
 *
 * ── por que CSS e não ECharts ───────────────────────────────────────────────
 *
 * O `CLAUDE.md` lista ECharts na tabela de stack. Mas o contrato visual traz um
 * componente de gráfico COMPLETO e pronto — `.plot`, `.iqrband`, `.refline`,
 * `.reflbl`, `.pt`/`.pt-read`/`.pt-crit`, `.axisline`/`.axislbl`, `.legend` e o
 * tooltip —, todo movido pelos tokens `--ch-*`, e a API manda `pos_pct` para
 * cada elemento, feita sob medida para ele.
 *
 * Usar ECharts aqui significaria reimplementar com uma segunda tecnologia um
 * componente que o guia já demonstra, e reconfigurá-la até parecer com ele: é
 * exatamente o segundo contrato visual não documentado que a Regra 2 existe para
 * impedir. Para 63 pontos sem zoom nem brush, a biblioteca não paga o próprio
 * peso. DECISÃO PENDENTE DE RATIFICAÇÃO — se ECharts for obrigatório, este
 * módulo é o que muda, e os tokens `--ch-*` continuam sendo a fonte.
 *
 * ── fronteira visual ────────────────────────────────────────────────────────
 *
 * Uma classe nova, `.hd-ctl`: o controle que mora na direita de um `.tbl-hd`.
 * O segmentado em si é o `.seg` do contrato, com a mesma marcação de rádio da
 * régua de critérios. As posições saem em `style` (`left`/`width` em %) porque
 * são DADO — vêm de `pos_pct`, calculado pelo motor. Mesmo critério da régua de
 * posição e da barra de composição.
 *
 * A única medida que nasce aqui é a dispersão VERTICAL dos pontos, e ela não é
 * dado: o eixo é unidimensional, e sem espalhar, cooperados de valor próximo se
 * sobrepõem e somem. O teto vem do token `--ch-jitter`. É determinística (sai do
 * empacotamento, não de sorteio) para que o mesmo cooperado caia sempre no mesmo
 * lugar — ponto que pula a cada carga destrói a comparação entre duas leituras
 * da mesma tela.
 */
'use strict';

import { el, posicionado } from '../lib/dom.js';
import { colapsavel } from '../lib/colapsar.js';
import { cartaoVazio } from '../lib/vazio.js';
/* O empacotador do enxame mora em lib/ desde 2026-09-07: o painel do
   procedimento na área desenha o mesmo enxame, e duas cópias da geometria
   é como os mesmos pontos passam a cair em lugares diferentes. */
import { posicionarEmEnxame } from '../lib/enxame.js';

/** Um ponto: o cooperado, o valor e a leitura em linguagem comum. */
function ponto(p, altura, aoClicar) {
  /* DOIS ESTADOS (variante E do artboard "Medyx Escala de Cor", set/2026):
     cinza para quem está dentro do padrão da área, verde para quem passou o
     critério da MEDIDA em cena. `acima` vem do motor, comparado contra a mesma
     linha que o gráfico desenha — ponto verde à esquerda da régua seria o
     desenho contradizendo a si mesmo.
     A rampa por excedente em R$ saiu junto: ela pintava dinheiro num eixo de
     frequência e exigia uma legenda de três valores para ser decodificada. */
  const s = posicionado('span', `pt${p.acima ? ' pt-acima' : ''}`, p.pos_pct);
  s.style.bottom = `${altura}px`;
  s.tabIndex = 0;

  /* FICHA: identidade no título, um `Rótulo: valor` por linha. As linhas vêm
     redigidas do motor (`p.dica`), e é lá que está a razão de cada uma:
     o percentil nunca viaja sem tradução (ajuste 2 do CLAUDE.md), o
     denominador acompanha toda taxa (rigor §1) e o excedente responde "quanto",
     que a tinta deixou de codificar. Aqui só se monta. */
  const dica = el('span', 'tip');
  dica.appendChild(el('b', null, p.id));
  for (const linha of p.dica ?? []) dica.appendChild(el('em', null, linha));
  s.appendChild(dica);

  const acionar = () => aoClicar?.(p.id);
  s.addEventListener('click', acionar);
  s.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Enter' && ev.key !== ' ') return;
    ev.preventDefault();
    acionar();
  });
  return s;
}


/**
 * O segmentado que troca a medida, na marcação de rádio do contrato (`.seg` +
 * `input` + `.seg-o`), a mesma da régua de critérios: um grupo de rádio é o que
 * um leitor de tela precisa ouvir aqui, e é o que dá navegação por setas de
 * graça.
 */
function seletorDeMedida(medidas, ativa, aoTrocar) {
  const seg = el('div', 'seg hd-ctl');
  seg.setAttribute('aria-label', 'Medida do eixo');
  for (const m of medidas) {
    const id = `dist-medida-${m.chave}`;
    const radio = document.createElement('input');
    radio.type = 'radio';
    radio.name = 'dist-medida';
    radio.id = id;
    radio.checked = m.chave === ativa;
    radio.addEventListener('change', () => aoTrocar(m.chave));
    const rot = el('label', 'seg-o', m.rotulo);
    rot.setAttribute('for', id);
    rot.tabIndex = 0;
    seg.append(radio, rot);
  }
  return seg;
}


/**
 * O cartão que OCUPA O LUGAR do gráfico onde ele não pode existir.
 *
 * Áreas sem grupo de pares e áreas sem nenhum formador da referência não têm
 * distribuição: sem referência não há eixo contra o que distribuir. Até
 * 2026-09-11 o bloco simplesmente não era montado, e como a aba Distribuição
 * continua na faixa — ela é a mesma para todas as áreas —, clicar nela abria um
 * painel de 516px em branco. A pergunta "por que esta área não tem gráfico?"
 * não tinha resposta em canto nenhum da página.
 *
 * A alternativa era esconder a aba. Foi descartada porque esconder não
 * responde: some o sintoma e some a explicação junto.
 *
 * Nenhuma frase nasce aqui. `sem_distribuicao` é a frase do MÉTODO, redigida
 * pelo motor (`blocos.estado_area`) para os dois estados que estruturalmente
 * não têm gráfico; `descricao` é a rede, para qualquer outro caminho até aqui
 * (uma janela sem ninguém, uma medida que não sobrou). Sem nenhuma das duas —
 * só no estado pleno, onde o gráfico sempre existe — não há cartão a montar.
 */
function semDistribuicao(destino, estado) {
  cartaoVazio(destino, 'Distribuição', estado?.titulo,
              estado?.sem_distribuicao ?? estado?.descricao);
}


/**
 * Monta o gráfico dentro de `destino`.
 *
 * Não renderiza — e devolve `null` — quando o estado da área não tem referência
 * plena. Não é falha: uma área sem norma não tem contra o que distribuir, e
 * desenhar um eixo vazio sugeriria que o dado existe e está zerado. No lugar do
 * gráfico entra o cartão de `semDistribuicao`, que diz isso com todas as letras.
 *
 * @param {HTMLElement} destino
 * @param {object} dados  resposta de /api/area/{id}
 * @param {(id: string|null) => void} [aoEscolher]  id escolhido, ou `null` ao
 *        desfazer a escolha
 * @returns {{cartao: HTMLElement, marcar: (id: string|null) => void} | null}
 */
export function montarDistribuicao(destino, dados, aoEscolher) {
  const d = dados.distribuicao;
  /* O PORTÃO É O DADO. `dados.estado.tem_distribuicao === false` também estava
     aqui e era uma segunda autoridade sobre a mesma pergunta: quando o motor
     passou a servir distribuição descritiva nas áreas abaixo do mínimo
     (2026-09-11), a flag e o payload discordaram e a flag venceu — o bloco
     chegava pronto e a tela não o desenhava. Quem sabe se há o que desenhar são
     as medidas que vieram. */
  if (!d?.medidas?.length) {
    semDistribuicao(destino, dados.estado);
    return null;
  }

  /* Mesma moldura e mesmo cabeçalho da tabela: o gráfico e a lista são dois
     blocos da mesma família, e o título do guia (`font-size:14px;weight:600`,
     escrito inline lá) é exatamente `.tbl-hd .t`. O corpo entra numa `.tbl-band`
     porque `.plot` não traz respiro próprio. */
  const cartao = el('div', 'tbl');
  const topo = el('div', 'tbl-hd');
  const titulo = el('div', 'stack g4');
  /* O TÍTULO e o subtítulo são DA MEDIDA, e trocam com ela: chamar de "índice
     de solicitação" um eixo que está em R$ diria ao leitor que ele está vendo
     quantidade quando está vendo dinheiro. */
  const rotuloTitulo = el('span', 't');
  const rotuloSub = el('span', 'sub');
  titulo.append(rotuloTitulo, rotuloSub);
  /* Sem "passe o cursor sobre um ponto": instrução de uso não é conteúdo, e o
     ponteiro sobre o ponto já muda de forma. */
  topo.appendChild(titulo);

  let medida = d.medidas.find((m) => m.chave === d.medida_padrao) ?? d.medidas[0];
  /* Um só segmento não é escolha: com uma medida disponível, o controle some e
     o cartão volta a ser o gráfico de sempre. */
  if (d.medidas.length > 1) {
    topo.appendChild(seletorDeMedida(d.medidas, medida.chave, trocar));
  }
  cartao.appendChild(topo);

  const corpo = el('div', 'tbl-band');
  const plot = el('div', 'plot plot-area');
  /* A GEOMETRIA VEM DA PLOTAGEM, não da raiz (2026-09-07). A altura deste
     gráfico deixou de ser o token `--ch-h`: dentro da faixa de gráficos ele
     estica para preencher a vista, e a altura real só existe depois de o cartão
     entrar no documento. Ler da raiz devolvia 110px enquanto a plotagem media
     269, e os pontos caíam 159px abaixo da caixa que deveriam ocupar.

     `--ch-jitter` e `--ch-base-pct` saem do MESMO elemento pelo mesmo motivo: o
     CSS os declara em `.plot-area`, e o painel lateral do exame, que é `.plot`
     também, continua com os valores da raiz. Um token lido do lugar errado é um
     desenho que discorda de si mesmo sem avisar. */
  const medirPlot = () => {
    const est = getComputedStyle(plot);
    const eixo = parseFloat(est.getPropertyValue('--ch-eixo')) || 16;
    const frac = parseFloat(est.getPropertyValue('--ch-base-frac')) || 0.521;
    return {
      jitter: parseFloat(est.getPropertyValue('--ch-jitter')) || 26,
      diametro: parseFloat(est.getPropertyValue('--ch-dot')) || 7,
      /* o EIXO DO ENXAME, em px do rodapé da plotagem: a linha em que fica quem
         não tem vizinho para desviar, e a mesma altura em que o CSS desenha a
         haste. A conta é a do CSS, sobre a faixa acima da linha do eixo. */
      base: Math.round(eixo + frac * (plot.clientHeight - eixo)),
    };
  };
  corpo.appendChild(plot);

  cartao.appendChild(corpo);

  /* ── O RODAPÉ: LEGENDA E RESSALVA, NA FAIXA CINZA ────────────────────────
     A legenda ficava solta sobre o branco, encostada na plotagem, e a faixa
     cinza levava só a nota de método. Eram dois tratamentos para a mesma
     pergunta — "o que estou vendo, e o que este número é" — em dois gráficos
     irmãos que se alternam no MESMO cartão: trocar de vista mudava o desenho do
     rodapé junto com o gráfico.
     Agora é o arranjo do Pareto, que já era esse: `.tbl-ft.tbl-ft-nota`,
     legenda em cima, ressalva embaixo, as duas dentro da faixa. Um cartão, um
     rodapé (2026-09-11).

     A LEGENDA é do BLOCO, não da medida: as marcas valem para as três, e
     redesenhá-la a cada troca sugeriria que a leitura muda com a medida. A
     NOTA é da medida, e por isso é ela que `desenhar()` reescreve. */
  const rodape = el('div', 'tbl-ft tbl-ft-nota');
  const legenda = el('div', 'legend');
  /* A marca da CAIXA, guardada: o hover dela carrega o n sobre o qual a caixa
     se apoia, e esse n muda com a medida (as de dinheiro se apoiam em quem TEM
     a medida). A frase vem redigida do motor; aqui só se troca o `title`. */
  let marcaDaCaixa = null;
  for (const item of d.legenda ?? []) {
    const s = document.createElement('span');
    s.append(el('i', item.classe), document.createTextNode(item.rotulo));
    if (item.classe === 'mk-iqr') marcaDaCaixa = s;
    legenda.appendChild(s);
  }
  /* A NOTA DA MEDIDA ENTRA NA PRÓPRIA LEGENDA, como último item e sem marca —
     o mesmo lugar em que o Pareto põe "linha tracejada = corte de 80%".
     Era uma SEGUNDA LINHA do rodapé, e isso deixava a faixa da distribuição
     mais alta que a do Pareto ao lado: dois gráficos que se alternam no mesmo
     cartão, com rodapés de espessuras diferentes. Uma linha, sempre.
     Fica VAZIA na maioria das medidas, de propósito: ela só fala quando há
     exceção (grupo sem caixa, gente fora do desenho). `hidden` e não texto
     vazio, senão o `gap:16px` da legenda abriria um vão sem conteúdo. */
  const notaMedida = document.createElement('span');
  legenda.appendChild(notaMedida);
  rodape.appendChild(legenda);
  cartao.appendChild(rodape);

  destino.appendChild(cartao);

  let escolhido = null;
  let recorte = null;      // Set dos ids em cena; null = sem recorte
  let porId = new Map();
  let naTela = [];         // [{dado, elemento}] na ordem do payload

  /**
   * Redesenha a PLOTAGEM para a medida em cena, e só ela: cabeçalho, legenda e
   * rodapé são reescritos no lugar, e o cartão nunca é recriado.
   *
   * O cartão não pode ser recriado porque a faixa de abas dos três gráficos
   * mora DENTRO dele (`area.js` a insere como primeiro filho), e o botão de
   * recolher também. Trocar o cartão levaria os dois embora.
   *
   * Os pontos entram DEPOIS de o cartão estar no documento: o enxame precisa da
   * largura real da plotagem em pixels para saber o que é "vizinho" — a API
   * manda posição em porcentagem, e porcentagem não diz quantos pontos cabem
   * lado a lado.
   */
  function desenhar() {
    rotuloTitulo.textContent = medida.titulo;
    rotuloSub.textContent = medida.subtitulo ?? '';
    notaMedida.textContent = medida.nota ?? '';
    notaMedida.hidden = !notaMedida.textContent;
    if (marcaDaCaixa) marcaDaCaixa.title = medida.caixa_titulo ?? '';

    plot.replaceChildren();

    /* HASTE do menor ao maior valor observado, com tampa nas pontas: é o que dá
       o alcance total da distribuição, que a caixa sozinha não mostra. */
    if (medida.haste) {
      plot.appendChild(posicionado('div', 'haste', medida.haste.pos_pct,
                                   medida.haste.largura_pct));
      const tampa = (pos) => plot.appendChild(posicionado('div', 'tampa', pos));
      tampa(medida.haste.pos_pct);
      tampa(medida.haste.pos_pct + medida.haste.largura_pct);
    }
    if (medida.faixa_iqr) {
      plot.appendChild(posicionado('div', 'iqrband', medida.faixa_iqr.pos_pct,
                                   medida.faixa_iqr.largura_pct));
    }
    for (const r of medida.referencias ?? []) {
      plot.appendChild(posicionado('div', `refline ${r.classe}`, r.pos_pct));
      const lbl = posicionado('div', `reflbl ${r.classe}`, r.pos_pct, null, r.rotulo);
      /* o hover diz o que a linha é e, quando o critério foi ajustado ao
         tamanho do grupo, por quê — o rótulo só tem espaço para "· ajustado" */
      if (r.titulo) lbl.title = r.titulo;
      plot.appendChild(lbl);
    }

    plot.appendChild(el('div', 'axisline'));
    for (const t of medida.eixo ?? []) {
      plot.appendChild(posicionado('span', 'axislbl', t.pos_pct, null, t.valor_fmt));
    }

    naTela = (medida.pontos ?? []).map((p) => {
      const s = ponto(p, 0, escolher);
      plot.appendChild(s);
      return { dado: p, elemento: s };
    });
    porId = new Map(naTela.map(({ dado, elemento }) => [dado.id, elemento]));
    posicionarPontos();

    aplicarRecorte();
    aplicarEscolha();
  }

  /**
   * Reparte os pontos em altura, para a plotagem que existe AGORA.
   *
   * Separado de `desenhar` porque a plotagem deixou de ter altura fixa: ela
   * cresce para preencher a vista, e a altura final só existe depois de o
   * layout assentar. Na primeira montagem o enxame media 300px e desenhava o
   * eixo 15px acima de onde a caixa acabava ficando, e redimensionar a janela
   * repetia o desvio sem nunca corrigi-lo.
   *
   * Repor a altura é barato — mexe em `style.bottom` e mais nada —, então o
   * observador pode chamar sem cerimônia. O que NÃO se refaz aqui é o DOM: o
   * ponto escolhido, o recorte e o foco continuam onde estavam.
   */
  function posicionarPontos() {
    if (!naTela.length || !plot.clientWidth) return;
    const { jitter, diametro, base } = medirPlot();
    const alturas = posicionarEmEnxame(naTela.map((x) => x.dado), plot.clientWidth,
                                       jitter, diametro, base);
    naTela.forEach(({ elemento }, i) => { elemento.style.bottom = `${alturas[i]}px`; });
  }

  /**
   * Troca a medida do eixo. Quem está em cena não muda: a escolha de um ponto e
   * o recorte de perfil atravessam a troca.
   *
   * A exceção é o cooperado escolhido que NÃO tem a nova medida (sem preço nas
   * contas, ou sem nenhum procedimento acima do critério): ele não vira ponto
   * no zero, então a escolha é desfeita e a tabela avisada. Manter a linha
   * destacada apontando para um ponto que não existe seria pior.
   */
  function trocar(chave) {
    const nova = d.medidas.find((m) => m.chave === chave);
    if (!nova || nova.chave === medida.chave) return;
    medida = nova;
    if (escolhido && !medida.pontos.some((p) => p.id === escolhido)) {
      escolhido = null;
      aoEscolher?.(null);
    }
    desenhar();
  }

  /* Um só ponto escolhido por vez. Clicar no mesmo desfaz; clicar no vazio do
     gráfico também — sem isso, sair da seleção exigiria adivinhar onde clicar. */
  function escolher(id) {
    // ponto fora do recorte não responde: ele recuou de cena, e escolhê-lo
    // destacaria uma linha que a tabela não mostra
    if (id && recorte && !recorte.has(id)) return;
    escolhido = id === escolhido ? null : id;
    aplicarEscolha();
    aoEscolher?.(escolhido);
  }

  function aplicarEscolha() {
    for (const [k, s] of porId) s.classList.toggle('pt-escolhido', k === escolhido);
    plot.classList.toggle('com-selecao', Boolean(escolhido) && porId.has(escolhido));
  }

  function aplicarRecorte() {
    plot.classList.toggle('com-recorte', Boolean(recorte));
    for (const [k, s] of porId) {
      const emCena = Boolean(recorte?.has(k));
      s.classList.toggle('pt-no-recorte', emCena);
      // quem recuou sai também do alcance do teclado: Tab percorre só a cena
      s.tabIndex = recorte && !emCena ? -1 : 0;
    }
  }

  plot.addEventListener('click', (ev) => {
    if (!ev.target.closest('.pt')) escolher(null);
  });

  desenhar();

  /* O enxame acompanha a plotagem. Largura já era motivo (quem é "vizinho"
     depende de quantos pontos cabem lado a lado); altura passou a ser, porque o
     gráfico agora estica para preencher a vista. O observador dispara na
     montagem e a cada mudança de caixa, e repor altura não muda a caixa — não
     há laço. */
  new ResizeObserver(() => posicionarPontos()).observe(plot);

  /* Recolhível DEPOIS de montado: o enxame já leu a largura real da plotagem,
     e fechar agora não a zera para a próxima abertura. */
  colapsavel(cartao, 'distribuicao');

  return {
    cartao,
    /** Reflete no gráfico uma escolha feita fora dele. */
    marcar: (id) => { if (id !== escolhido) escolher(id); },
    /**
     * Realça um SUBCONJUNTO (os portadores de um sub-perfil) e recua o resto.
     *
     * `null` volta todos ao normal. Não toca na `.iqrband` nem no eixo, de
     * propósito: a régua é da área inteira, e mediana e critério parados são o
     * que garante que o perfil filtra quem aparece, não contra quem se mede.
     */
    realcar: (ids) => {
      recorte = ids && ids.length ? new Set(ids) : null;
      aplicarRecorte();
    },
  };
}
