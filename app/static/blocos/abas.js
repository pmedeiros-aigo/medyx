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
 * DUAS FORMAS, porque são dois níveis diferentes de escolha:
 *
 *   'abas'  sublinhado no ativo, sem moldura (`.vistas`). É o corte da PÁGINA:
 *           Cooperados / Procedimentos trocam a unidade de análise, e por isso
 *           viajam na URL.
 *   'seg'   trilho cinza com pastilha branca (`.segfilt`). É controle de UM
 *           bloco: Concentração / Distribuição / Quantidade × custo trocam a
 *           leitura do mesmo recorte, dentro do cartão do gráfico.
 *
 * A distinção não é decorativa. As duas faixas ficam a poucos pixels uma da
 * outra, e desenhadas iguais a de dentro do cartão lia como uma segunda
 * navegação de página. O segmentado é fechado, cabe num cabeçalho e se anuncia
 * como controle local.
 *
 * @param {HTMLElement} destino
 * @param {{chave: string, rotulo: string, n?: number|string}[]} abas
 * @param {(chave: string) => void} aoTrocar
 * @param {{forma?: 'abas'|'seg'}} [opcoes]
 * @returns {{faixa: HTMLElement, paineis: Record<string, HTMLElement>,
 *            contar: (chave: string, n: number|string) => void,
 *            marcar: (chave: string) => void}}
 */
export function montarAbas(destino, abas, aoTrocar, opcoes = {}) {
  const seg = opcoes.forma === 'seg';
  const faixa = el('div', seg ? 'segfilt' : 'vistas');
  const botoes = new Map();
  const contadores = new Map();
  const paineis = {};

  for (const a of abas) {
    const b = el('button', seg ? 'segfilt-o' : 'vista', a.rotulo);
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
    /* A faixa sai junto porque a página de Área a REMANEJA: ela mora dentro do
       cartão do gráfico em cena, e muda de cartão a cada troca. Procurá-la de
       volta por classe amarrava quem chama à forma escolhida aqui. */
    faixa,
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
