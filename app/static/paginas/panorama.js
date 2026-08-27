/* panorama.js — o Panorama de oportunidades, a porta de entrada (espec §1).
 *
 * A pergunta da página: "onde está o dinheiro, por grupo, e o que eu olho
 * hoje?" É a tela que precede a Área: primeiro se escolhe ONDE olhar, depois
 * se olha.
 *
 * ── estado atual: ESQUELETO ─────────────────────────────────────────────────
 *
 * A tela existe para travar a navegação e a URL (`/` é o Panorama, não a
 * Área). O conteúdo especificado ainda não foi construído:
 *
 *   · síntese executiva (faixa qualificada + piso de confiança)
 *   · cards por especialidade (n, mediana, acima do critério, excedente)
 *   · cascata de qualificação, degrau a degrau
 *   · ranking qualificado, a fila de trabalho
 *
 * Enquanto isso, a página faz a única coisa honesta: declara o estado e leva
 * às áreas, que é para onde o analista ia de qualquer forma. Tela em branco
 * não é opção — é o único estado que este produto não admite.
 */
'use strict';

import { buscar } from '../lib/api.js';
import { el } from '../lib/dom.js';
import { abrirPagina } from '../lib/pagina.js';
import { TELAS, comRegua } from '../lib/rotas.js';

await abrirPagina({
  titulo: 'Panorama',
  aoTrocarArea: (id) => TELAS.area.caminho(id),
  montar: async ({ conteudo }) => {
    const topo = el('div', 'stack g6');
    topo.appendChild(el('h2', null, 'Panorama de oportunidades'));
    topo.appendChild(el('span', 'sub',
      'onde está a oportunidade, por área de atuação'));
    conteudo.appendChild(topo);

    const meta = await buscar('/api/meta',
                              { anunciarEm: conteudo, rotulo: 'carregando as áreas…' });

    const cartao = el('div', 'tbl');
    const cab = el('div', 'tbl-hd');
    const tt = el('div', 'stack g4');
    tt.appendChild(el('span', 't', 'Áreas de atuação'));
    tt.appendChild(el('span', 'sub',
      'a comparação acontece sempre dentro de uma área; escolha por onde começar'));
    cab.appendChild(tt);
    cartao.appendChild(cab);

    const corpo = el('div', 'tbl-band');
    const faixa = el('div', 'row flexwrap');
    for (const a of meta.areas ?? []) {
      const link = document.createElement('a');
      link.className = 'pill';
      link.href = comRegua(TELAS.area.caminho(a.id));
      link.textContent = a.titulo;
      if (a.perfil) link.title = a.perfil;
      faixa.appendChild(link);
    }
    corpo.appendChild(faixa);
    cartao.appendChild(corpo);

    const pe = el('div', 'tbl-ft');
    pe.appendChild(el('span', null,
      'síntese executiva, cards por área e fila de trabalho ainda não '
      + 'construídos; por ora esta tela leva às áreas'));
    cartao.appendChild(pe);
    conteudo.appendChild(cartao);

    if (meta.proveniencia?.carimbo) {
      conteudo.appendChild(el('span', 'note', meta.proveniencia.carimbo));
    }
  },
});
