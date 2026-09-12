/* blocos/leitura-area.js — o que a tela de área produziu, num bloco.
 *
 * Mesma marcação do "Leitura do caso" do dossiê (`.res-*`), e é de propósito:
 * as duas telas respondem a mesma pergunta em escalas diferentes (a área e um
 * cooperado), e um desenho por escala obrigaria o leitor a reaprender o bloco
 * ao trocar de tela.
 *
 * ── o que ele acrescenta ao que já existe ──────────────────────────────────
 * A faixa de cards dava aos cinco números o mesmo peso: "cooperados no recorte"
 * e "custo excedente" lado a lado, do mesmo tamanho, sem nada dizendo qual
 * deles é o produto da tela. Aqui eles vêm agrupados pela GRANDEZA que medem, e
 * cada grupo repete o mesmo par de linhas — total em cima, excedente embaixo,
 * com a fração ao lado —, então "quanto disso está acima da referência" se lê na
 * vertical, dentro do grupo. Sem apoio sob os números: o que eles diziam ou já
 * está em outro bloco da página, ou virou hover da linha a que pertence. E sem
 * rodapé: o que sobrava nele era afirmação de método, que mora na definição da
 * coluna, no painel do procedimento e na Nota Metodológica.
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
    /* O APOIO só existe se houver o que dizer. Ele era criado SEMPRE, com texto
       vazio quando não havia apoio — e um `.res-p` vazio continua ocupando a
       própria linha da grade (`row-gap:2px` mais a altura do texto). Toda linha
       do bloco carregava um vão sob o número, inclusive as que nunca tiveram
       apoio nenhum. Hoje a Leitura da área não manda apoio em nenhuma linha; a
       guarda fica porque o bloco é o mesmo do dossiê, onde a referência do
       grupo ("referência: 3.497") mora aqui. */
    if (l.apoio) linha.appendChild(el('span', 'res-p', l.apoio));
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
  /* A FRASE COM A MARCA das afirmações, a mesma do "Leitura do caso" do dossiê
     (`.res-itens`/`.res-item`). Ela saía como `.sub`, indistinguível de um
     subtítulo que descreve o bloco — e ela não descreve o bloco, ela AFIRMA um
     fato apurado (onde o dinheiro se concentra). A marca é o que diz isso, e é
     a mesma dos fatores de contexto em toda a tela. */
  const itens = el('div', 'res-itens');
  const frase = el('span', 'res-item');
  frase.appendChild(el('i', 'mk'));
  const fraseTxt = document.createTextNode('');
  frase.appendChild(fraseTxt);
  itens.appendChild(frase);
  titulo.appendChild(itens);
  topo.appendChild(titulo);
  cartao.appendChild(topo);

  const nums = el('div', 'res-grade');
  cartao.appendChild(nums);

  /* A FAIXA DE DESTAQUE SAIU (2026-09-11). Ela levava o custo excedente
     sozinho, em corpo grande, numa faixa abaixo da grade — e com isso o número
     ficava longe do total de que ele é a parte, que morava num terceiro grupo
     lá em cima. Agora o par vive junto, no grupo "Custo": total em cima,
     excedente embaixo com a fração ao lado, e a comparação se faz na vertical
     sem o olho atravessar o cartão.

     O RODAPÉ SAIU DEPOIS (set/2026). Ele já tinha sido reduzido de dois
     parágrafos a uma linha, e a linha que restou era afirmação de MÉTODO (a
     unidade em que o excedente é medido), não número do recorte: um resumo de
     números não fecha com uma frase sobre como eles nascem. O fato continua na
     definição da coluna "Excesso em R$", no painel de cada procedimento e na
     Nota Metodológica. O cartão é o título, a afirmação e a grade. */
  destino.appendChild(cartao);

  function atualizar(L) {
    if (!L) return;
    fraseTxt.nodeValue = L.frase ?? '';
    itens.hidden = !L.frase;
    nums.replaceChildren(...L.grupos.map(grupo));
  }
  atualizar(dados.leitura);
  return { atualizar };
}
