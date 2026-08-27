/* abas.js — as duas unidades de análise da tela de Área.
 *
 *   Cooperados     quem está fora do padrão
 *   Procedimentos  em que a área varia
 *
 * A mesma pergunta ("onde está a oportunidade") por dois eixos. A RÉGUA é a
 * mesma nos dois: janela, critério, referência, recorte e perfil continuam
 * valendo, e por isso a faixa de filtros e a distribuição ficam ACIMA das abas,
 * fora delas. O que a aba troca é a unidade de análise, não a regra.
 *
 * As abas eram internas ao cartão da tabela e trocavam só a tabela. Subiram
 * para a página (Clean v3) quando cada eixo ganhou o próprio Pareto: o de
 * cooperados pertence à leitura de quem, o de procedimentos à de quê, e
 * mantê-los empilhados obrigava a rolar por um gráfico que não era da pergunta
 * em cena.
 *
 * Este bloco não sabe o que há dentro de cada painel: recebe os destinos e
 * alterna. A página é quem monta o conteúdo e guarda a aba na URL.
 */
'use strict';

import { el } from '../lib/dom.js';

/**
 * Monta a faixa de abas e devolve o painel de cada uma.
 *
 * @param {HTMLElement} destino
 * @param {{chave: string, rotulo: string, n?: number|string}[]} abas
 * @param {(chave: string) => void} aoTrocar
 * @returns {{paineis: Record<string, HTMLElement>, marcar: (chave: string) => void}}
 */
export function montarAbas(destino, abas, aoTrocar) {
  const faixa = el('div', 'vistas');
  const botoes = new Map();
  const contadores = new Map();
  const paineis = {};

  for (const a of abas) {
    const b = el('button', 'vista', a.rotulo);
    b.type = 'button';
    if (a.n != null) {
      const cnt = el('span', 'cnt', String(a.n));
      b.appendChild(cnt);
      contadores.set(a.chave, cnt);
    }
    b.addEventListener('click', () => aoTrocar(a.chave));
    faixa.appendChild(b);
    botoes.set(a.chave, b);
    paineis[a.chave] = el('div', 'vista-painel');
  }

  destino.appendChild(faixa);
  for (const a of abas) destino.appendChild(paineis[a.chave]);

  return {
    paineis,
    /**
     * Reescreve o contador de uma aba. Existe porque o número ao lado do rótulo
     * anuncia o TAMANHO DA LISTA que a aba abre, e essa lista é recortada: fixo
     * no total da área, ele contradizia a própria tabela logo abaixo (64 na
     * aba, 21 linhas na lista). Quem sabe quantos estão em cena é a página, que
     * é dona do estado da vista — daí vir de fora, e não de um cálculo aqui.
     */
    contar: (chave, n) => {
      const cnt = contadores.get(chave);
      if (cnt) cnt.textContent = String(n);
    },
    marcar: (chave) => {
      for (const [k, b] of botoes) b.classList.toggle('on', k === chave);
      /* Painel fora de cena sai do FLUXO (`display:none`), não fica escondido:
         conteúdo oculto que continua ocupando altura deixa a página com um
         vazio que ninguém explica. */
      for (const [k, painel] of Object.entries(paineis)) {
        painel.classList.toggle('on', k === chave);
      }
    },
  };
}
