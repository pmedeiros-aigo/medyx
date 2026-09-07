/* blocos/resumo-caso.js — o caso em um bloco, no topo do dossiê.
 *
 * Substitui a faixa de sete cartões de KPI. A faixa dava aos sete números o
 * MESMO peso e nenhuma relação entre eles: sete caixas em linha, e o leitor
 * montava sozinho a leitura "ele atende muito, pede acima da referência, e o
 * dinheiro está no excesso". Aqui os mesmos números vêm agrupados pela pergunta
 * que respondem, e o bloco fecha com a carteira que ele atende.
 *
 * ── por que a carteira fecha o bloco ───────────────────────────────────────
 * Porque a primeira defesa de quem é sinalizado é "a minha carteira é
 * diferente", e às vezes ela está certa. A composição etária dele contra a da
 * área é a pergunta que se faz ANTES de concluir qualquer coisa sobre a
 * frequência. Ela não entra em cálculo nenhum, e o bloco diz isso na base.
 *
 * ── fronteira visual ───────────────────────────────────────────────────────
 * Reusa o `.tbl` do contrato (cabeçalho, faixa e rodapé), como todo bloco da
 * tela. As classes próprias são a grade de números (`.res-*`) e a barra dupla
 * da carteira (`.cart-*`), que não existiam. Nenhum número é calculado aqui:
 * larguras vêm em `largura_pct`/`area_pct` do motor, como no Pareto.
 */
'use strict';

import { el } from '../lib/dom.js';


/** Um grupo de números: rótulo pequeno em cima, pares rótulo/valor embaixo. */
function grupo(g) {
  const bloco = el('div', 'res-grupo');
  bloco.appendChild(el('span', 'micro res-grupo-t', g.rotulo));
  for (const l of g.linhas) {
    const linha = el('div', 'res-linha');
    /* DOIS hovers, cada um no elemento que ele explica: o do rótulo diz o que a
       métrica mede; o da referência diz como ela foi construída. O valor não
       tem hover próprio — o que ele mostrava era "referência: 5,13", que é
       exatamente o texto impresso na linha de baixo. */
    const k = el('span', 'res-k', l.rotulo);
    if (l.titulo_longo) k.title = l.titulo_longo;
    linha.appendChild(k);
    linha.appendChild(el('span', 'res-v', l.valor_fmt));
    const par = el('span', l.par_titulo ? 'res-p tem-hover' : 'res-p',
                   l.par_fmt ?? '');
    if (l.par_titulo) par.title = l.par_titulo;
    linha.appendChild(par);
    bloco.appendChild(linha);
  }
  return bloco;
}


/** A composição etária: uma linha por faixa, com a fatia dele e a da área. */
function carteira(c) {
  const bloco = el('div', 'cart');

  const topo = el('div', 'row row-between flexwrap');
  const esq = el('div', 'row g8 flexwrap');
  esq.appendChild(el('span', 'micro res-grupo-t', 'Carteira atendida'));
  topo.appendChild(esq);
  bloco.appendChild(topo);

  const cab = el('div', 'row g8 flexwrap cart-hd');
  cab.appendChild(el('span', 'cart-n', c.n_fmt));
  const apoio = ['beneficiários distintos'];
  if (c.por_beneficiario_fmt) apoio.push(`${c.por_beneficiario_fmt} consultas por beneficiário`);
  /* A referência entre PARÊNTESES, colada na medida que ela qualifica: solta
     depois de um "·" ela ficava a três itens de "idade mediana" e podia ser
     lida como referência de consultas por beneficiário. */
  if (c.idade_mediana_fmt) {
    apoio.push(`idade mediana ${c.idade_mediana_fmt} anos`
      + (c.idade_mediana_area_fmt
         ? ` (referência da área: ${c.idade_mediana_area_fmt})` : ''));
  }
  cab.appendChild(el('span', 'sub', apoio.join(' · ')));
  bloco.appendChild(cab);

  /* AUSÊNCIA DECLARADA: carteira pequena ou idade desconhecida na maioria dela
     não vira barra vazia, vira o motivo por extenso (o motor o redige). */
  if (c.motivo) {
    bloco.appendChild(el('span', 'sub', c.motivo));
    return bloco;
  }

  const grade = el('div', 'cart-faixas');
  for (const f of c.faixas) {
    const item = el('div', 'cart-f');
    const rot = el('div', 'row row-between');
    rot.appendChild(el('span', 'cart-f-k', f.rotulo));
    rot.appendChild(el('span', 'cart-f-v', f.fracao_fmt));
    item.appendChild(rot);

    /* A barra é a fatia DELE; o traço é a fatia da ÁREA na mesma faixa. Duas
       barras empilhadas diriam o mesmo e ocupariam o dobro; o traço deixa a
       comparação acontecer na mesma linha, que é onde o olho já está. */
    const trilho = el('div', 'cart-bar');
    const cheia = el('i', null);
    cheia.style.width = `${f.largura_pct}%`;
    trilho.appendChild(cheia);
    if (f.area_pct != null) {
      const marca = el('b', null);
      marca.style.left = `${f.area_pct}%`;
      trilho.appendChild(marca);
    }
    trilho.title = f.titulo;
    item.appendChild(trilho);
    /* A referência da faixa explica como foi construída, no MESMO hover e com
       o mesmo pontilhado dos números de cima: é a mesma pergunta ("referência
       do quê?") e não pode ter duas respostas de formatos diferentes. */
    const ref = el('span', 'cart-f-a tem-hover', f.area_fmt);
    ref.title = 'Fatia desta faixa etária entre todos os beneficiários '
      + 'atendidos na área de atuação no período, sob a mesma janela e o mesmo '
      + 'recorte de consultas.';
    item.appendChild(ref);
    grade.appendChild(item);
  }
  bloco.appendChild(grade);

  const legenda = el('div', 'legend');
  const marca = (classe, texto) => {
    const s = document.createElement('span');
    s.append(el('i', classe), document.createTextNode(texto));
    legenda.appendChild(s);
  };
  marca('cart-mk-eu', 'Esta carteira');
  marca('cart-mk-area', 'Referência da área');
  bloco.appendChild(legenda);
  return bloco;
}


/** Os fatores de contexto, na faixa de apoio que fecha o cartão. */
function fatores(itens) {
  const bloco = el('div', 'res-fatores');
  bloco.appendChild(el('span', 'micro res-grupo-t', 'Fatores de contexto'));

  const chips = el('div', 'row g8 flexwrap');
  for (const c of itens) {
    /* Contorno TRACEJADO, que neste app significa ressalva de método e não
       medida (a mesma gramática do quadrado sem trimestre medido): é exatamente
       o que um fator de contexto é. O ponto verde marca o que foi verificado
       na base, como no `.tag-ctx`. */
    const chip = el('span', 'tag tag-fator');
    chip.append(el('i', 'mk'),
                document.createTextNode(`${c.rotulo}: ${c.valor_fmt}`));
    if (c.ajuda) chip.title = c.ajuda;
    chips.appendChild(chip);
  }
  bloco.appendChild(chips);

  bloco.appendChild(el('span', 'sub',
    'Não alteram nenhum número desta tela: dizem com que lente investigar '
    + 'antes de concluir.'));
  return bloco;
}


/**
 * Monta o bloco dentro de `destino`.
 *
 * @param {HTMLElement} destino
 * @param {object} d  resposta de /api/cooperado/{id}
 */
export function montarResumoDoCaso(destino, d) {
  const r = d.resumo;
  if (!r?.grupos?.length) return;

  const cartao = el('div', 'tbl');
  const topo = el('div', 'tbl-hd');
  const titulo = el('div', 'stack g6');
  titulo.appendChild(el('span', 't', 'Leitura do caso'));
  /* UM ITEM POR AFIRMAÇÃO, com a mesma marca dos fatores de contexto. Antes as
     mesmas frases saíam como duas linhas de texto corrido separadas por "·", e
     liam como um parágrafo perdido sob o título: nada dizia onde uma afirmação
     terminava e a seguinte começava. */
  if (r.itens?.length) {
    const lista = el('div', 'res-itens');
    for (const i of r.itens) {
      const item = el('span', 'res-item');
      item.append(el('i', 'mk'), document.createTextNode(i));
      lista.appendChild(item);
    }
    titulo.appendChild(lista);
  }
  topo.appendChild(titulo);
  cartao.appendChild(topo);

  const nums = el('div', 'res-grade');
  for (const g of r.grupos) nums.appendChild(grupo(g));
  cartao.appendChild(nums);

  if (r.carteira) {
    const faixa = el('div', 'tbl-band res-carteira');
    faixa.appendChild(carteira(r.carteira));
    /* A descrição do que a seção mostra saiu (set/2026): o rótulo, os rótulos
       das faixas e a legenda já dizem tudo que ela dizia, e a ressalva de que
       nada aqui entra em cálculo é a mesma dos fatores de contexto, logo
       abaixo. `base` fica: ela só chega preenchida quando falta a idade de
       alguém, e aí é premissa do número, não descrição. */
    if (r.carteira.base) faixa.appendChild(el('span', 'sub', r.carteira.base));
    cartao.appendChild(faixa);
  }

  /* Os FATORES fecham o cartão, na faixa de apoio: eles são a última pergunta
     antes de concluir qualquer coisa sobre tudo que está acima. */
  if (d.contexto?.length) cartao.appendChild(fatores(d.contexto));

  destino.appendChild(cartao);
}
