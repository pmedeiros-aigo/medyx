/* lib/dom.js — as primitivas de marcação, num lugar só.
 *
 * Existiam cinco cópias de `el()` (cabecalho, excluidos, distribuicao, pareto,
 * perfis) e duas de `posicionado()`. Eram idênticas, e é assim que começa a
 * divergência silenciosa: alguém melhora uma e as outras quatro ficam.
 *
 * Aqui não há decisão visual nenhuma. Estas funções só criam elemento e
 * aplicam CLASSES DO CONTRATO — o que é permitido ao JavaScript pela fronteira
 * do CLAUDE.md. A única exceção é `posicionado()`, e ela é DADO: posição em
 * porcentagem vem do motor (`pos_pct`), não é escolha de layout.
 */
'use strict';

/** Elemento com classe (do contrato) e texto. */
export function el(tag, classe, texto) {
  const e = document.createElement(tag);
  if (classe) e.className = classe;
  if (texto != null) e.textContent = texto;
  return e;
}

/**
 * Elemento posicionado por PORCENTAGEM, que aqui é dado, não estilo: `esquerda`
 * e `largura` vêm calculados do motor (a régua de posição, a faixa IQR, as
 * linhas de referência do gráfico). Mesmo critério da barra de composição.
 */
export function posicionado(tag, classe, esquerda, largura, texto) {
  const e = el(tag, classe, texto);
  e.style.left = `${esquerda}%`;
  if (largura != null) e.style.width = `${largura}%`;
  return e;
}
