/* cards.js — os KPIs abaixo dos chips de recorte.
 *
 *   Cooperados no recorte · Excesso de solicitações · Excesso em R$
 *
 * Seguem o recorte ativo (CLAUDE.md, lei 0: acima dos chips é a área, fixo;
 * abaixo é a bancada, que segue o filtro). Nada é calculado aqui — rótulo,
 * número, apoio e hover vêm prontos de /api/area/{id}.
 *
 * ── fronteira visual ────────────────────────────────────────────────────────
 * `.kpis`/`.kpi` (`.k`/`.v`/`.h`), a grade sem moldura da página "Área de
 * Atuação" do Claude Design.
 */
'use strict';

import { el } from '../lib/dom.js';

/**
 * Monta a grade de KPIs em `destino`.
 *
 * @param {HTMLElement} destino
 * @param {object[]} cards  bloco `cards` de /api/area/{id}
 * @returns {{atualizar: (cards: object[]) => void}}
 */
export function montarCards(destino, cards) {
  const grade = el('div', 'kpis');
  destino.appendChild(grade);
  desenhar(cards);
  return { atualizar: desenhar };

  function desenhar(cards) {
    grade.replaceChildren(...(cards ?? []).map((c) => {
      const kpi = el('div', 'kpi');
      kpi.appendChild(el('span', 'k', c.rotulo));
      kpi.appendChild(el('span', 'v', c.valor_fmt));
      if (!c.apoio) return kpi;
      // o pontilhado só aparece onde há o que revelar: sublinhado sem hover
      // promete uma explicação que não existe
      const apoio = el('span', c.titulo_longo ? 'h tem-hover' : 'h', c.apoio);
      if (c.titulo_longo) apoio.title = c.titulo_longo;
      kpi.appendChild(apoio);
      return kpi;
    }));
  }
}
