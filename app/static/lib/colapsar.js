/* lib/colapsar.js — fechar e abrir o corpo de um cartão.
 *
 * A tela de Área acumulou quatro blocos altos (distribuição, dispersão e os dois
 * Paretos) acima do conteúdo de trabalho. Quem veio olhar a tabela rola por
 * todos eles; quem veio olhar um gráfico não precisa dos outros três. Fechar é
 * a saída barata: o bloco continua declarado no lugar, com título e subtítulo,
 * e só o corpo recolhe.
 *
 * ── o estado é PREFERÊNCIA, não vista ───────────────────────────────────────
 *
 * Recorte, perfil, aba e ordenação viajam na URL porque são o que a tela está
 * mostrando — um link precisa reabrir a mesma leitura. Bloco fechado é
 * preferência de quem lê, não conteúdo: vai para o `localStorage`, e um link
 * compartilhado não impõe ao outro os blocos que eu fechei.
 *
 * ── por que o cartão é montado ABERTO e fechado depois ──────────────────────
 *
 * O enxame da distribuição precisa da largura real da plotagem em pixels para
 * saber o que é vizinho. Com o corpo em `display:none` na montagem, essa largura
 * é 0 e todos os pontos empilham no mesmo lugar. Montar aberto e recolher em
 * seguida custa um quadro e evita o caso inteiro.
 */
'use strict';

import { el } from './dom.js';

const CHAVE = 'medyx:blocos-fechados';

function fechados() {
  try {
    return new Set(JSON.parse(localStorage.getItem(CHAVE) ?? '[]'));
  } catch {
    return new Set();          // storage corrompido não pode derrubar a tela
  }
}

function gravar(conjunto) {
  try {
    localStorage.setItem(CHAVE, JSON.stringify([...conjunto]));
  } catch {
    /* modo privado ou cota cheia: a tela funciona, só não lembra da próxima vez */
  }
}

/**
 * Torna um cartão `.tbl` recolhível. Idempotente — chamar de novo depois de um
 * `replaceChildren` reinstala o botão e reaplica o estado salvo.
 *
 * @param {HTMLElement} cartao  o `.tbl`
 * @param {string} chave        identificador do bloco no armazenamento
 */
export function colapsavel(cartao, chave) {
  const topo = cartao.querySelector(':scope > .tbl-hd');
  if (!topo || topo.querySelector(':scope > .tbl-toggle')) return;

  const botao = el('button', 'tbl-toggle');
  botao.type = 'button';
  botao.insertAdjacentHTML('beforeend',
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke-width="2" '
    + 'stroke-linecap="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>');
  topo.appendChild(botao);

  const aplicar = (fechado) => {
    cartao.classList.toggle('fechado', fechado);
    botao.setAttribute('aria-expanded', String(!fechado));
    botao.title = fechado ? 'Abrir este bloco' : 'Fechar este bloco';
  };

  botao.addEventListener('click', () => {
    const conjunto = fechados();
    const fechado = !cartao.classList.contains('fechado');
    if (fechado) conjunto.add(chave); else conjunto.delete(chave);
    gravar(conjunto);
    aplicar(fechado);
  });

  aplicar(fechados().has(chave));
}
