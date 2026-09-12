/* lib/vazio.js — o cartão que OCUPA O LUGAR de um gráfico que não existe.
 *
 * Nasceu de um defeito repetido: a faixa de gráficos da tela de Área reserva a
 * altura da vista mais alta, as três abas ficam sempre na faixa, e um bloco que
 * não é montado deixava ali um painel de 516px em BRANCO. Aconteceu na
 * Distribuição (áreas sem referência) e na Quantidade × custo (Ultrassonografia,
 * onde nenhum cooperado alcança o volume mínimo).
 *
 * Ausência por método não se lê como ausência: lê-se como tela que não
 * carregou. E esconder a aba não resolve — some o sintoma e a explicação junto,
 * e quem vem de uma área com três vistas para outra com duas não tem como saber
 * o que aconteceu.
 *
 * Este módulo existe para os dois blocos não terem cada um a sua versão do
 * mesmo cartão: era assim que começava a divergência silenciosa que `lib/dom.js`
 * já descreve no topo dele.
 *
 * NENHUMA FRASE NASCE AQUI. Título e motivo chegam prontos de quem chama, e de
 * lá vêm do motor: por que um bloco não tem o que desenhar é método, e método
 * mora com o número.
 *
 * ── fronteira visual ────────────────────────────────────────────────────────
 * Só classes do contrato: `.tbl` + `.tbl-hd` (a moldura de todo cartão),
 * `.tbl-band.tbl-vazio` (o corpo que centra o que tem dentro) e `.caveat-box`
 * (§07), que é a cor que o app já usa para ressalva de método.
 */
'use strict';

import { el } from './dom.js';

/**
 * Monta o cartão de ausência dentro de `destino`.
 *
 * SEM SETA DE RECOLHER, ao contrário dos cartões de gráfico vizinhos: recolher
 * esconde o corpo, e aqui o corpo é a explicação — o gesto devolveria
 * exatamente o painel em branco que este cartão veio desfazer.
 *
 * @param {HTMLElement} destino
 * @param {string} titulo  o nome do bloco ausente, o mesmo da aba que o abre
 * @param {string} rotulo  o título da ressalva (o estado da área, em geral)
 * @param {string} motivo  a frase do motor: por que não há o que desenhar
 * @returns {HTMLElement|null} o cartão, ou `null` se não houver motivo a dizer
 */
export function cartaoVazio(destino, titulo, rotulo, motivo) {
  /* Sem frase não há cartão: uma moldura com um retângulo pastel vazio dentro
     seria o painel em branco com mais passos. */
  if (!motivo) return null;

  const cartao = el('div', 'tbl');
  const topo = el('div', 'tbl-hd');
  const cabeca = el('div', 'stack g4');
  cabeca.appendChild(el('span', 't', titulo));
  topo.appendChild(cabeca);
  cartao.appendChild(topo);

  const corpo = el('div', 'tbl-band tbl-vazio');
  const caixa = el('div', 'caveat-box');
  if (rotulo) caixa.appendChild(el('div', 't', rotulo));
  caixa.appendChild(el('div', 'd', motivo));
  corpo.appendChild(caixa);
  cartao.appendChild(corpo);

  destino.appendChild(cartao);
  return cartao;
}
