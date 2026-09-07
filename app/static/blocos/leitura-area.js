/* blocos/leitura-area.js — o que a tela de área produziu, num bloco.
 *
 * Mesma marcação do "Leitura do caso" do dossiê (`.res-*`), e é de propósito:
 * as duas telas respondem a mesma pergunta em escalas diferentes (a área e um
 * cooperado), e um desenho por escala obrigaria o leitor a reaprender o bloco
 * ao trocar de tela.
 *
 * ── o que ele acrescenta ao que já existe ──────────────────────────────────
 * A faixa de cards dá aos cinco números o mesmo peso: "cooperados no recorte" e
 * "custo excedente" lado a lado, do mesmo tamanho, sem nada dizendo qual deles
 * é o produto da tela. Aqui os mesmos números vêm agrupados pela pergunta que
 * respondem, o excedente ganha o destaque que é dele, e duas linhas fecham com
 * o que o número não diz sozinho: quanto do total da área este recorte mostra,
 * e qual é a régua ativa.
 *
 * Nada é calculado aqui. Segue o recorte, como os cards e os Paretos.
 */
'use strict';

import { el } from '../lib/dom.js';


/** Um grupo de números: rótulo pequeno em cima, pares rótulo/valor embaixo. */
function grupo(g) {
  const bloco = el('div', 'res-grupo');
  bloco.appendChild(el('span', 'micro res-grupo-t', g.rotulo));
  for (const l of g.linhas) {
    const linha = el('div', 'res-linha');
    const k = el('span', 'res-k', l.rotulo);
    if (l.titulo_longo) k.title = l.titulo_longo;
    linha.appendChild(k);
    linha.appendChild(el('span', 'res-v', l.valor_fmt));
    /* O APOIO ocupa a mesma posição da referência no bloco do dossiê: sob o
       valor, à direita. Aqui ele declara a base do número quando ela é parcial
       ("em 528 de 685 procedimentos"), que é a ressalva de preço. */
    linha.appendChild(el('span', 'res-p', l.apoio ?? ''));
    bloco.appendChild(linha);
  }
  return bloco;
}


/**
 * Monta o bloco dentro de `destino` e devolve como atualizá-lo no recorte.
 *
 * @param {HTMLElement} destino
 * @param {object} dados  resposta de /api/area/{id}
 * @returns {{atualizar: (leitura: object) => void} | null}
 */
export function montarLeituraDaArea(destino, dados) {
  if (!dados?.leitura?.grupos?.length) return null;

  const cartao = el('div', 'tbl');
  const topo = el('div', 'tbl-hd');
  const titulo = el('div', 'stack g6');
  titulo.appendChild(el('span', 't', dados.leitura.titulo));
  const frase = el('span', 'sub');
  titulo.appendChild(frase);
  topo.appendChild(titulo);
  cartao.appendChild(topo);

  const nums = el('div', 'res-grade');
  cartao.appendChild(nums);

  /* O DESTAQUE numa faixa própria: ele é o produto da tela, e no meio da grade
     teria o peso de mais um número entre seis. */
  const faixa = el('div', 'tbl-band res-destaque');
  const valor = el('span', 'la-destaque');
  const apoio = el('span', 'sub');
  faixa.append(valor, apoio);
  cartao.appendChild(faixa);

  const pe = el('div', 'tbl-ft res-notas-ft');
  cartao.appendChild(pe);
  destino.appendChild(cartao);

  function atualizar(L) {
    if (!L) return;
    frase.textContent = L.frase ?? '';
    frase.hidden = !L.frase;
    nums.replaceChildren(...L.grupos.map(grupo));
    valor.textContent = L.destaque?.valor_fmt ?? '';
    apoio.textContent = L.destaque?.apoio ?? '';
    pe.replaceChildren(...(L.notas ?? []).map((n) => el('span', null, n)));
    pe.hidden = !(L.notas ?? []).length;
  }
  atualizar(dados.leitura);
  return { atualizar };
}
