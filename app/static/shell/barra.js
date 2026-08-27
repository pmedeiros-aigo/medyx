/* shell/barra.js — a barra superior (migalha + vigência) e a navegação lateral.
 *
 * A migalha NAVEGA e é montada da ROTA (a marcação do shell.html é só o
 * esqueleto). Duas regras:
 *
 *   · só vira LINK o que leva a um lugar diferente da página atual — migalha
 *     que não navega é promessa quebrada, link que recarrega a mesma tela é
 *     ruído;
 *   · a régua acompanha todo link, como na navegação lateral: trocar de tela
 *     não devolve o analista ao padrão sem ele ter pedido.
 *
 * "SADT" nunca é link: módulo não é destino, é a regra do guia.
 */
'use strict';

import { TELAS, comRegua, rotaAtual } from '../lib/rotas.js';

/**
 * A migalha da tela atual: o rastro, do módulo até a folha.
 *
 * @param {object} meta   /api/meta (para o rótulo da área e a vigência)
 * @param {string} area   id da área em cena, quando houver
 */
export function montarBarraSuperior(meta, area) {
  const { tela, cooperado } = rotaAtual();
  const escolhida = meta.areas?.find((a) => a.id === area);

  const caixa = document.querySelector('.crumbs');
  if (caixa) {
    const partes = [{ txt: 'SADT' }];
    if (tela === 'panorama') {
      partes.push({ txt: TELAS.panorama.rotulo });
    } else if (tela === 'metodologia') {
      partes.push({ txt: TELAS.metodologia.rotulo });
    } else if (tela === 'cooperados') {
      partes.push({ txt: TELAS.cooperados.rotulo });
    } else if (tela === 'area') {
      partes.push({ txt: TELAS.area.rotulo });
      partes.push({ txt: escolhida?.titulo ?? '' });
    } else if (tela === 'cooperado') {
      /* No dossiê, a ÁREA é destino de verdade: é o grupo inteiro contra o
         qual o caso é medido, e é para onde se volta depois de olhar um. */
      partes.push({ txt: TELAS.cooperado.rotulo });
      partes.push({ txt: escolhida?.titulo ?? '',
                    href: area ? comRegua(TELAS.area.caminho(area)) : null });
      partes.push({ txt: cooperado ?? '' });
    }

    const cheias = partes.filter((p) => p.txt);
    caixa.replaceChildren();
    cheias.forEach((p, i) => {
      if (i) {
        const sep = document.createElement('i');
        sep.textContent = '/';
        caixa.appendChild(sep);
      }
      const folha = i === cheias.length - 1;
      const e = document.createElement(folha ? 'b' : p.href ? 'a' : 'span');
      if (!folha && p.href) e.href = p.href;
      e.textContent = p.txt;
      caixa.appendChild(e);
    });
  }

  /* A vigência dos dados NÃO é escrita aqui. Ela vive no seletor de Período,
     que é onde ela pode ser mudada; repeti-la no canto da barra dava ao leitor
     duas janelas para conferir e só uma para editar. */
}

/**
 * Navegação lateral: o item ativo vem da ROTA, e a régua viaja nos links.
 *
 * O Dossiê não está na lateral, mas COOPERADOS está (27/ago): a regra é que a
 * lateral lista pontos de PARTIDA, e uma lista de cooperados é um deles. O
 * dossiê de UM continua sendo destino, alcançado pela lista, pelo Panorama ou
 * pela tabela da Área.
 *
 * E o item que acende num dossiê continua sendo Área de Atuação, não
 * Cooperados: a lateral mostra onde o caso MORA (o peer group contra o qual ele
 * é medido), não por qual porta se entrou. Duas portas, um dossiê, uma
 * identidade.
 *
 * @param {string} area  a área em cena, para o link da Área de atuação
 */
export function montarNavegacao(area) {
  const { tela } = rotaAtual();
  for (const a of document.querySelectorAll('.navitem[data-tela]')) {
    const alvo = a.dataset.tela;
    a.classList.toggle('on', alvo === tela
      // o dossiê é filho da Área: a lateral destaca de onde ele veio
      || (tela === 'cooperado' && alvo === 'area'));
    const caminho = alvo === 'area' && area
      ? TELAS.area.caminho(area)
      : TELAS[alvo]?.caminho();
    if (caminho) a.href = comRegua(caminho);
  }
}
