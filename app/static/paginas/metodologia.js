/* metodologia.js — a Nota Metodológica (espec §4).
 *
 * O lugar onde o método é escrito por extenso, para que as telas não precisem
 * carregá-lo. É a contraparte de uma decisão do produto: vocabulário interno e
 * justificativa de método NÃO aparecem nas telas de trabalho; eles moram aqui
 * e nos hovers.
 *
 * ── estado atual: ESQUELETO ─────────────────────────────────────────────────
 *
 * Falta renderizar o METODOLOGIA_ANALITICA.md e o glossário do léxico, mais as
 * defesas escritas: mediana e robustez, percentis e não p-valor, critério ≠
 * referência, critério degradado por n, fronteira GO/Ginecologia, regra do PS,
 * quarentena do preço, premissa da autorreferência.
 *
 * A tela existe agora para travar a rota e o item de navegação; enquanto o
 * conteúdo não chega, ela declara o estado em vez de fingir que está pronta.
 */
'use strict';

import { el } from '../lib/dom.js';
import { abrirPagina } from '../lib/pagina.js';
import { TELAS } from '../lib/rotas.js';

/* Os assuntos que a nota vai cobrir, na ordem em que serão escritos. Estão
   aqui porque anunciar o que falta é mais útil que uma página vazia: quem
   abrir sabe o que esperar e o que ainda não pode citar. */
const ASSUNTOS = [
  ['Como a comparação é construída',
   'peer group por área de atuação, quem forma a referência e quem é apenas medido'],
  ['Critério de revisão e referência de adequação',
   'por que sinalizar e medir usam réguas diferentes'],
  ['Robustez',
   'mediana e IQR em distribuição de cauda longa; por que o outlier não é removido'],
  ['Volume mínimo e n mínimo',
   'por que denominador pequeno não sustenta comparação'],
  ['Consistência entre trimestres',
   'norma recalculada por período, e o que a persistência prova'],
  ['Piso de confiança',
   'reamostragem por paciente, e quando o intervalo não é calculável'],
  ['Fatores de contexto',
   'urgência, regime e autorreferência: leituras, nunca vereditos'],
  ['Preço e valores em R$',
   'preço interno derivado das contas, em quarentena até a tabela oficial'],
];

await abrirPagina({
  titulo: 'Nota Metodológica',
  aoTrocarArea: (id) => TELAS.area.caminho(id),
  montar: async ({ conteudo }) => {
    const topo = el('div', 'stack g6');
    topo.appendChild(el('h2', null, 'Nota metodológica'));
    topo.appendChild(el('span', 'sub',
      'como cada número desta plataforma é construído, e o que ele não afirma'));
    conteudo.appendChild(topo);

    const cartao = el('div', 'tbl');
    const cab = el('div', 'tbl-hd');
    const tt = el('div', 'stack g4');
    tt.appendChild(el('span', 't', 'Em construção'));
    tt.appendChild(el('span', 'sub',
      'o método está escrito e versionado no repositório; a publicação nesta '
      + 'tela ainda não foi feita'));
    cab.appendChild(tt);
    cartao.appendChild(cab);

    const corpo = el('div', 'tbl-band');
    const pilha = el('div', 'stack g10');
    for (const [titulo, resumo] of ASSUNTOS) {
      const item = el('div', 'stack g4');
      item.appendChild(el('span', 'micro', titulo));
      item.appendChild(el('span', 'sub', resumo));
      pilha.appendChild(item);
    }
    corpo.appendChild(pilha);
    cartao.appendChild(corpo);
    conteudo.appendChild(cartao);
  },
});
