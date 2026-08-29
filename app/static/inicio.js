/* inicio.js — a porta de entrada: que tela a rota pede?
 *
 * O servidor devolve o mesmo `index.html` em toda rota de página; quem decide
 * o que montar é este arquivo, pelo caminho. Não é um roteador de SPA: cada
 * navegação continua sendo uma carga de página do servidor, e a URL continua
 * sendo a verdade. Aqui só se escolhe QUAL módulo importar.
 *
 * `import()` dinâmico e não estático: a tela de Área não paga o código do
 * Dossiê, nem o contrário.
 *
 * Uma tela nova = um arquivo em `paginas/` + uma entrada em `lib/rotas.js` +
 * uma linha aqui + a rota no `api.py`. Nada de HTML novo.
 */
'use strict';

import { rotaAtual } from './lib/rotas.js';

const PAGINAS = {
  panorama: () => import('./paginas/panorama.js'),
  area: () => import('./paginas/area.js'),
  cooperados: () => import('./paginas/cooperados.js'),
  cooperado: () => import('./paginas/cooperado.js'),
  metodologia: () => import('./paginas/metodologia.js'),
  conta: () => import('./paginas/conta.js'),
};

const { tela } = rotaAtual();

if (PAGINAS[tela]) {
  await PAGINAS[tela]();
} else {
  /* Rota sem tela é erro de programação (o servidor não devolveria o shell),
     mas falhar em silêncio deixaria a página em branco — e tela branca é o
     único estado que o produto não admite. */
  const { mostrarFalha } = await import('./shell/shell.js');
  mostrarFalha(new Error(`sem tela para a rota ${location.pathname}`));
}
