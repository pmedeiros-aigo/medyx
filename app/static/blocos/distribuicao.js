/* distribuicao.js — o gráfico de distribuição da área.
 *
 * Um ponto por cooperado avaliável, no eixo de solicitações por consulta. É a
 * leitura que a tabela não dá: onde está a massa, onde está a cauda, e o quanto
 * o extremo se afasta dela.
 *
 * Lê `distribuicao` de /api/area/{id}. Não calcula nada — nem posição: a API
 * manda `pos_pct` já resolvido contra a escala do grupo.
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
 * Nenhuma classe nova. As posições saem em `style` (`left`/`width` em %) porque
 * são DADO — vêm de `pos_pct`, calculado pelo motor. Mesmo critério da régua de
 * posição e da barra de composição.
 *
 * A única medida que nasce aqui é a dispersão VERTICAL dos pontos, e ela não é
 * dado: o eixo é unidimensional, e sem espalhar, cooperados de valor próximo se
 * sobrepõem e somem. O teto vem do token `--ch-jitter`. É determinística (sai do
 * id, não de sorteio) para que o mesmo cooperado caia sempre no mesmo lugar —
 * ponto que pula a cada carga destrói a comparação entre duas leituras da mesma
 * tela.
 */
'use strict';

import { el, posicionado } from '../lib/dom.js';
import { colapsavel } from '../lib/colapsar.js';

/* Enxame por empacotamento CONTÍNUO.
 *
 * Cada ponto procura a altura mais próxima do eixo em que não ENCOSTE em nenhum
 * vizinho já colocado. Não há faixas: a altura é um número real, resultado da
 * geometria, não de uma grade.
 *
 * Três tentativas até chegar aqui, e cada uma falhou por desenhar um padrão que
 * não existe no dado:
 *   · sorteio pelo id — vizinhos caíam na mesma altura por acaso e se sobrepunham;
 *   · faixas em ciclo — sem colisão, mas escadas diagonais regulares;
 *   · faixas por colisão — sem escadas, mas os pontos encaixavam em linhas e o
 *     resultado parecia uma grade.
 *
 * A geometria: dois círculos de diâmetro d não se sobrepõem se a distância entre
 * os centros for >= d. Fixado o afastamento horizontal dx, as alturas PROIBIDAS
 * por um vizinho são o intervalo y_vizinho +/- sqrt(d^2 - dx^2). Junta-se todos
 * os intervalos dos vizinhos e escolhe-se a altura livre de menor módulo — a mais
 * perto do eixo.
 *
 * O contorno que emerge É a densidade: onde há um cooperado sozinho ele fica no
 * eixo; onde se acumulam, o grupo incha. Diz o que um histograma diria sem
 * deixar de mostrar cada cooperado.
 *
 * Determinístico: mesma janela, mesmas alturas.
 */
function posicionarEmEnxame(pontos, larguraPx, jitter, diametro, base) {
  const limite = jitter / 2;
  const d = diametro + 1;                 // 1px de folga para não encostarem
  const ordem = pontos
    .map((p, i) => [i, (p.pos_pct / 100) * larguraPx])
    .sort((a, b) => a[1] - b[1]);

  const colocados = [];                   // {x, y} já resolvidos
  const alturas = new Array(pontos.length);

  for (const [indice, x] of ordem) {
    const proibidos = [];
    for (const q of colocados) {
      const dx = Math.abs(x - q.x);
      if (dx >= d) continue;
      const meia = Math.sqrt(d * d - dx * dx);
      proibidos.push([q.y - meia, q.y + meia]);
    }

    // candidatos: o eixo e as bordas de cada intervalo proibido — é onde a
    // primeira altura livre sempre está
    const candidatos = [0];
    for (const [de, ate] of proibidos) candidatos.push(de, ate);
    candidatos.sort((a, b) => Math.abs(a) - Math.abs(b));

    let y = null;
    for (const c of candidatos) {
      if (Math.abs(c) > limite) continue;
      const livre = proibidos.every(([de, ate]) => c <= de + 0.01 || c >= ate - 0.01);
      if (livre) { y = c; break; }
    }
    // enxame cheio até o teto: fica na borda, encostando, em vez de estourar a
    // área de plotagem
    if (y === null) y = colocados.length % 2 ? limite : -limite;

    colocados.push({ x, y });
    alturas[indice] = Math.round(base + y);
  }
  return alturas;
}


/** Um ponto: o cooperado, o valor e a leitura em linguagem comum. */
function ponto(p, altura, aoClicar) {
  /* A COR é o EXCEDENTE EM R$ (2026-08-20). `intensidade` (0–1) é dado do
     motor — posição do cooperado na ordem dos excedentes —, e o CSS a converte
     em tinta. A paleta de severidade (`pt-read`/`pt-crit`) saiu junto com as
     linhas de referência: ver a docstring de `distribuicao()` no motor. */
  const s = posicionado('span', 'pt', p.pos_pct);
  s.style.setProperty('--i', String(p.intensidade ?? 0));
  s.style.bottom = `${altura}px`;
  s.tabIndex = 0;

  const dica = el('span', 'tip');
  dica.appendChild(el('b', null, `${p.id} · ${p.valor_fmt}`));
  // ajuste 2 do CLAUDE.md: percentil nunca viaja sem tradução
  dica.appendChild(el('em', null, p.leitura));
  // o número que a cor representa, por extenso: tinta sozinha é sensação
  dica.appendChild(el('em', null, p.excedente_reais_fmt
    ? `Excedente: ${p.excedente_reais_fmt}` : 'Sem excedente valorado'));
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
 * Monta o gráfico dentro de `destino`.
 *
 * Não renderiza — e devolve `null` — quando o estado da área não tem referência
 * plena. Não é falha: uma área sem norma não tem contra o que distribuir, e
 * desenhar um eixo vazio sugeriria que o dado existe e está zerado.
 *
 * @param {HTMLElement} destino
 * @param {object} dados  resposta de /api/area/{id}
 * @param {(id: string|null) => void} [aoEscolher]  id escolhido, ou `null` ao
 *        desfazer a escolha
 * @returns {{cartao: HTMLElement, marcar: (id: string|null) => void} | null}
 */
export function montarDistribuicao(destino, dados, aoEscolher) {
  const d = dados.distribuicao;
  if (!d || dados.estado?.tem_distribuicao === false) return null;

  const estilo = getComputedStyle(document.documentElement);
  const jitter = parseFloat(estilo.getPropertyValue('--ch-jitter')) || 26;
  const diametro = parseFloat(estilo.getPropertyValue('--ch-dot')) || 7;
  /* CLEAN V3: os pontos caem DENTRO da caixa interquartil (topo em 27px,
     altura 29). O centro da faixa fica em 41px do topo, e como o CSS posiciona
     por `bottom`, a conta vira altura-do-plot menos isso. */
  const alturaPlot = parseFloat(estilo.getPropertyValue('--ch-h')) || 110;
  const base = Math.round(alturaPlot - 45);

  /* Mesma moldura e mesmo cabeçalho da tabela: o gráfico e a lista são dois
     blocos da mesma família, e o título do guia (`font-size:14px;weight:600`,
     escrito inline lá) é exatamente `.tbl-hd .t`. O corpo entra numa `.tbl-band`
     porque `.plot` não traz respiro próprio. */
  const cartao = el('div', 'tbl');
  const topo = el('div', 'tbl-hd');
  const titulo = el('div', 'stack g4');
  titulo.appendChild(el('span', 't', 'Distribuição do índice de solicitação'));
  if (d.subtitulo) titulo.appendChild(el('span', 'sub', d.subtitulo));
  /* Sem "passe o cursor sobre um ponto": instrução de uso não é conteúdo, e o
     ponteiro sobre o ponto já muda de forma. */
  topo.appendChild(titulo);
  cartao.appendChild(topo);

  const corpo = el('div', 'tbl-band');
  const plot = el('div', 'plot');

  /* HASTE do menor ao maior valor da área, com tampa nas pontas: é o que dá o
     alcance total da distribuição, que a caixa sozinha não mostra. */
  if (d.haste) {
    plot.appendChild(posicionado('div', 'haste', d.haste.pos_pct, d.haste.largura_pct));
    const tampa = (pos) => plot.appendChild(posicionado('div', 'tampa', pos));
    tampa(d.haste.pos_pct);
    tampa(d.haste.pos_pct + d.haste.largura_pct);
  }
  if (d.faixa_iqr) {
    plot.appendChild(posicionado('div', 'iqrband', d.faixa_iqr.pos_pct, d.faixa_iqr.largura_pct));
  }
  for (const r of d.referencias ?? []) {
    plot.appendChild(posicionado('div', `refline ${r.classe}`, r.pos_pct));
    plot.appendChild(posicionado('div', `reflbl ${r.classe}`, r.pos_pct, null, r.rotulo));
  }

  plot.appendChild(el('div', 'axisline'));
  for (const t of d.eixo ?? []) {
    plot.appendChild(posicionado('span', 'axislbl', t.pos_pct, null, t.valor_fmt));
  }
  corpo.appendChild(plot);

  if (d.rampa || d.legenda?.length) {
    const legenda = el('div', 'legend');
    /* A RAMPA com os valores nas pontas e no meio. "menor → maior" faria a cor
       virar sensação; e o método da escala vai declarado porque a tinta é por
       ORDEM, não por valor — o dobro de tinta não é o dobro de dinheiro. */
    if (d.rampa) {
      const faixa = el('span', 'rampa');
      faixa.appendChild(el('i', 'rampa-barra'));
      for (const m of d.rampa.marcas) faixa.appendChild(el('b', null, m.valor_fmt));
      faixa.title = `${d.rampa.rotulo} · ${d.rampa.metodo}`;
      legenda.appendChild(faixa);
    }
    for (const item of d.legenda) {
      const s = document.createElement('span');
      s.append(el('i', item.classe), document.createTextNode(item.rotulo));
      legenda.appendChild(s);
    }
    corpo.appendChild(legenda);
  }
  cartao.appendChild(corpo);

  destino.appendChild(cartao);

  /* Os pontos entram DEPOIS de o cartão estar no documento: o enxame precisa da
     largura real da plotagem em pixels para saber o que é "vizinho" — a API
     manda posição em porcentagem, e porcentagem não diz quantos pontos cabem
     lado a lado. */
  const pontos = d.pontos ?? [];
  const alturas = posicionarEmEnxame(pontos, plot.clientWidth, jitter, diametro, base);
  const porId = new Map();
  pontos.forEach((p, i) => {
    const s = ponto(p, alturas[i], escolher);
    porId.set(p.id, s);
    plot.appendChild(s);
  });

  let escolhido = null;
  let recorte = null;      // Set dos ids em cena; null = sem recorte

  /* Um só ponto escolhido por vez. Clicar no mesmo desfaz; clicar no vazio do
     gráfico também — sem isso, sair da seleção exigiria adivinhar onde clicar. */
  function escolher(id) {
    // ponto fora do recorte não responde: ele recuou de cena, e escolhê-lo
    // destacaria uma linha que a tabela não mostra
    if (id && recorte && !recorte.has(id)) return;
    escolhido = id === escolhido ? null : id;
    for (const [k, s] of porId) s.classList.toggle('pt-escolhido', k === escolhido);
    plot.classList.toggle('com-selecao', Boolean(escolhido));
    aoEscolher?.(escolhido);
  }
  plot.addEventListener('click', (ev) => {
    if (!ev.target.closest('.pt')) escolher(null);
  });

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
     * `null` volta todos ao normal. Não toca em `.refline`, `.iqrband` nem no
     * eixo, de propósito: a régua é da área inteira, e mediana e critério
     * parados são o que garante que o perfil filtra quem aparece, não contra
     * quem se mede.
     */
    realcar: (ids) => {
      recorte = ids && ids.length ? new Set(ids) : null;
      plot.classList.toggle('com-recorte', Boolean(recorte));
      for (const [k, s] of porId) {
        const emCena = Boolean(recorte?.has(k));
        s.classList.toggle('pt-no-recorte', emCena);
        // quem recuou sai também do alcance do teclado: Tab percorre só a cena
        s.tabIndex = recorte && !emCena ? -1 : 0;
      }
    },
  };
}
