/* dispersao.js — quantidade × custo por consulta (bloco experimental).
 *
 *   X  solicitações por consulta
 *   Y  custo médio por consulta
 *   r  valor total solicitado pelo cooperado na janela
 *
 * O rodapé é UMA linha: a legenda, e dentro dela a ressalva de quem ficou fora
 * do desenho. Mesma espessura da faixa do Pareto e da distribuição, que se
 * alternam neste mesmo cartão.
 *
 * TRÊS dimensões, e não quatro. Havia uma quarta — a tinta do ponto era o
 * excedente em R$ —, e ela saiu em 2026-09-11: punha dois dinheiros diferentes
 * no mesmo ponto (porte no tamanho, excesso na cor) sobre eixos que já falavam
 * de um terceiro, e exigia uma legenda de três valores para ser decodificada.
 * Mesma decisão que a distribuição tomou em set/2026. O excedente segue na
 * DICA, por extenso.
 *
 * A distribuição ao lado responde "quem pede muito"; esta responde "quem custa
 * muito", e as duas perguntas não têm a mesma resposta — quem pede pouco e caro
 * é invisível lá.
 *
 * SEM linha de referência e SEM cor de severidade: o método não define critério
 * para custo, e desenhar régua onde não há uma é o defeito que a distribuição
 * carregava. Este gráfico descreve, não julga.
 *
 * Nada é calculado aqui: posição em %, tamanho relativo, marcas de eixo e o
 * texto do tooltip vêm prontos de /api/area/{id}.
 *
 * ── fronteira visual ────────────────────────────────────────────────────────
 * Mesma moldura da distribuição (`.tbl` + `.tbl-hd` + `.tbl-band`). As classes
 * `.disp-*` são novas — é um gráfico que o guia ainda não tem. REPLICAR NO
 * DESIGN se o bloco for adotado.
 */
'use strict';

import { el } from '../lib/dom.js';
import { colapsavel } from '../lib/colapsar.js';
import { cartaoVazio } from '../lib/vazio.js';

/**
 * Monta o gráfico dentro de `destino`.
 *
 * SEM PONTOS, monta o cartão de ausência no lugar (`lib/vazio.js`) e devolve
 * `null`. Antes devolvia `null` e mais nada, e como a aba Quantidade × custo
 * continua na faixa de gráficos, o que ela abria em Ultrassonografia — 3
 * cooperados, nenhum acima do volume mínimo — era um painel de 516px em branco.
 * A frase do porquê vem no próprio bloco (`vazio`, do motor), como no Pareto.
 *
 * @param {HTMLElement} destino
 * @param {object} dados  resposta de /api/area/{id}
 * @param {(id: string) => void} [aoEscolher]
 * @returns {{cartao: HTMLElement} | null}
 */
export function montarDispersao(destino, dados, aoEscolher) {
  const d = dados.dispersao;
  if (!d?.pontos?.length) {
    cartaoVazio(destino, 'Solicitações × custo', dados.estado?.titulo,
                d?.vazio ?? dados.estado?.descricao);
    return null;
  }

  const cartao = el('div', 'tbl');
  const topo = el('div', 'tbl-hd');
  const titulo = el('div', 'stack g4');
  titulo.appendChild(el('span', 't', d.titulo));
  if (d.subtitulo) titulo.appendChild(el('span', 'sub', d.subtitulo));
  topo.appendChild(titulo);
  cartao.appendChild(topo);

  const corpo = el('div', 'tbl-band');
  const grade = el('div', 'disp');

  /* Rótulo do eixo Y na vertical, à esquerda das marcas: sem ele "R$ 260" solto
     não diz de que grandeza é. */
  grade.appendChild(el('span', 'disp-eixo-y', d.eixo_y.rotulo));

  const marcasY = el('div', 'disp-marcas-y');
  for (const m of d.eixo_y.marcas) {
    const s = el('span', null, m.valor_fmt);
    s.style.bottom = `${m.pos_pct}%`;
    marcasY.appendChild(s);
  }
  grade.appendChild(marcasY);

  const plot = el('div', 'disp-plot');
  const porId = new Map();
  for (const p of d.pontos) {
    const b = el('button', 'disp-pt');
    b.type = 'button';
    b.style.left = `${p.x_pct}%`;
    b.style.bottom = `${p.y_pct}%`;
    // `--t` é DADO (tamanho relativo, do motor); o CSS o converte em diâmetro.
    // É a única variável que o ponto carrega: a tinta é uma só, do CSS.
    b.style.setProperty('--t', String(p.tamanho));
    /* A ficha vem redigida do motor: cinco medidas do mesmo ponto são dado, e
       texto que carrega número nasce onde o número nasce. */
    if (p.tooltip) b.title = p.tooltip;
    if (aoEscolher) b.addEventListener('click', () => aoEscolher(p.id));
    plot.appendChild(b);
    porId.set(p.id, b);
  }
  grade.appendChild(plot);

  const marcasX = el('div', 'disp-marcas-x');
  for (const m of d.eixo_x.marcas) {
    const s = el('span', null, m.valor_fmt);
    s.style.left = `${m.pos_pct}%`;
    marcasX.appendChild(s);
  }
  grade.appendChild(marcasX);
  grade.appendChild(el('span', 'disp-eixo-x', d.eixo_x.rotulo));

  corpo.appendChild(grade);
  cartao.appendChild(corpo);

  /* ── O RODAPÉ: LEGENDA E RESSALVA, NA FAIXA CINZA ────────────────────────
     Mesmo arranjo do Pareto e da distribuição (`.tbl-ft.tbl-ft-nota`): legenda
     em cima, ressalva de método embaixo, as duas dentro da faixa. Os três
     gráficos se alternam no MESMO cartão, e cada um desenhar o próprio rodapé
     de um jeito fazia a moldura mudar junto com o conteúdo (2026-09-11).

     As marcas vêm do MOTOR (`d.legenda`), na mesma forma da distribuição, e
     nomeiam só o que está desenhado: a posição e o tamanho. A legenda da rampa
     saiu com a cor. */
  const pe = el('div', 'tbl-ft tbl-ft-nota');
  if (d.legenda?.length) {
    const legenda = el('div', 'legend');
    for (const item of d.legenda) {
      const s = document.createElement('span');
      /* Item SEM marca é texto puro — a ressalva de quem ficou fora do desenho.
         Mesmo arranjo do Pareto, que põe "linha tracejada = corte de 80%" como
         último item da própria legenda em vez de abrir uma segunda linha. */
      if (item.classe) s.appendChild(el('i', item.classe));
      s.appendChild(document.createTextNode(item.rotulo));
      legenda.appendChild(s);
    }
    pe.appendChild(legenda);
  }
  cartao.appendChild(pe);

  destino.appendChild(cartao);
  colapsavel(cartao, 'dispersao');

  return {
    cartao,
    /**
     * Recorta como a distribuição: quem sai de cena recua, quem fica mantém a
     * própria tinta. Os EIXOS não se movem — a escala é da área inteira, e
     * quem recuou continua desenhado como contexto (CLAUDE.md, lei 0).
     *
     * `null` volta todos ao normal.
     */
    realcar: (ids) => {
      const conjunto = ids && ids.length ? new Set(ids) : null;
      grade.classList.toggle('com-recorte', Boolean(conjunto));
      for (const [id, ponto] of porId) {
        const dentro = Boolean(conjunto?.has(id));
        ponto.classList.toggle('em-cena', dentro);
        // quem recuou sai do alcance do teclado: Tab percorre só a cena
        ponto.tabIndex = conjunto && !dentro ? -1 : 0;
      }
    },
  };
}
