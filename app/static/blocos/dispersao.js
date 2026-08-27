/* dispersao.js — quantidade × custo por consulta (bloco experimental).
 *
 *   X  exames solicitados por consulta
 *   Y  custo médio por consulta
 *   r  valor total solicitado pelo cooperado na janela
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

/**
 * Monta o gráfico dentro de `destino`.
 *
 * @param {HTMLElement} destino
 * @param {object} dados  resposta de /api/area/{id}
 * @param {(id: string) => void} [aoEscolher]
 * @returns {{cartao: HTMLElement} | null}
 */
export function montarDispersao(destino, dados, aoEscolher) {
  const d = dados.dispersao;
  if (!d?.pontos?.length) return null;

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
    // `--t` é DADO (tamanho relativo, do motor); o CSS o converte em diâmetro
    b.style.setProperty('--t', String(p.tamanho));
    /* `--i` é a mesma rampa da distribuição: tinta por ordem do excedente.
       Tamanho e cor são dinheiros DIFERENTES — porte e excesso —, e é o
       contraste entre os dois que este bloco existe para mostrar. */
    b.style.setProperty('--i', String(p.intensidade ?? 0));
    b.title = `${p.id} · ${p.valor_fmt} solicitados`
      + (p.excedente_reais_fmt ? ` · ${p.excedente_reais_fmt} de excedente` : '')
      + ` · ${p.leitura}`;
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

  /* A legenda da rampa, igual à da distribuição: os dois blocos usam a mesma
     tinta para a mesma grandeza, e uma legenda diferente em cada faria parecer
     que são escalas diferentes. */
  if (d.rampa) {
    const legenda = el('div', 'legend');
    const faixa = el('span', 'rampa');
    faixa.appendChild(el('i', 'rampa-barra'));
    for (const m of d.rampa.marcas) faixa.appendChild(el('b', null, m.valor_fmt));
    faixa.title = `${d.rampa.rotulo} · ${d.rampa.metodo}`;
    legenda.append(faixa, el('span', null, 'tamanho = valor total solicitado'));
    corpo.appendChild(legenda);
  }

  cartao.appendChild(corpo);

  /* A ressalva de método no rodapé, como no Pareto: o R$ é o mesmo preço
     interno, e o total é parcial — só entra procedimento com preço nas contas. */
  const pe = el('div', 'tbl-ft');
  pe.appendChild(el('span', null,
    d.n_sem_preco ? `${d.n_sem_preco} sem preço nas contas, fora do gráfico · ${d.metodo}`
                  : d.metodo));
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
