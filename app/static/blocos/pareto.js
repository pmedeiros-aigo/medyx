/* pareto.js — a concentração do excesso em R$.
 *
 * A leitura que a distribuição não dá: ONDE ESTÁ O DINHEIRO. Uma linha por
 * cooperado (ou procedimento), em ordem decrescente, com a barra proporcional
 * ao maior valor, o valor em R$ e a participação acumulada.
 *
 * Lê `pareto_cooperados` / `pareto_procedimentos` de /api/area/{id}. Nada é
 * calculado aqui: ordem, somas, acumulado, largura da barra e o texto do
 * tooltip vêm prontos do motor — até a ressalva de método vem redigida, porque
 * ela é parte do número.
 *
 * ── por que deixou de ser um gráfico ────────────────────────────────────────
 *
 * Era um gráfico de barras verticais em ECharts, com régua de deslize para
 * alcançar a cauda. Três problemas que a lista horizontal resolve de graça:
 *
 *   · o NOME não cabia no eixo vertical, então a barra mais alta era anônima
 *     até o hover — e num Pareto, saber QUEM é a leitura inteira;
 *   · o valor exato também só existia no hover;
 *   · e uma biblioteca inteira (~1 MB de CDN) existia para desenhar retângulos.
 *
 * A curva do acumulado virou uma COLUNA de acumulado, que se lê sem cruzar o
 * olho com um segundo eixo. E o corte de 80% virou uma régua tracejada entre
 * duas linhas: onde ela está é exatamente onde o núcleo termina.
 *
 * ── fronteira visual ────────────────────────────────────────────────────────
 * Nenhuma classe nova fora das declaradas para este bloco em components.css.
 * As larguras saem em `style` porque são DADO (`largura_pct`, do motor).
 */
'use strict';

import { el } from '../lib/dom.js';
import { colapsavel } from '../lib/colapsar.js';

/**
 * Monta UM Pareto dentro de `destino`. Genérico: cooperados e procedimentos
 * usam o mesmo bloco — título, leitura de concentração e o conteúdo do
 * tooltip (`rotulo_tooltip` + `detalhes`) vêm redigidos do motor.
 *
 * @param {HTMLElement} destino
 * @param {object} d  um bloco `pareto_*` de /api/area/{id}
 * @param {(id: string) => void} [aoEscolher]  clique numa linha (opcional)
 * @returns {{recortar: (ids: string[]|null) => void} | null}
 */
export function montarPareto(destino, d, aoEscolher, chave = 'pareto') {
  if (!d) return null;

  const cartao = el('div', 'tbl');
  destino.appendChild(cartao);
  desenhar(d);

  return {
    /**
     * Redesenha o bloco com os números de OUTRO recorte.
     *
     * Substituiu `recortar(ids)`, que apenas esmaecia as linhas fora de cena.
     * Esmaecer não bastava: sob recorte, total, ordem, % acumulado e o número
     * do título mudam todos, e nenhum deles pode ser recalculado aqui — o
     * front não calcula. Então quem muda é o dado, e o bloco só redesenha.
     * `null` (recorte sem nada a distribuir vindo como bloco vazio já vem
     * tratado do motor) mantém o cartão e mostra o estado vazio.
     */
    atualizar: (novo) => desenhar(novo ?? d),
  };

  function desenhar(d) {
  const partes = [];
  const topo = el('div', 'tbl-hd');
  const titulo = el('div', 'stack g4');
  titulo.appendChild(el('span', 't', d.titulo));
  /* DUAS linhas sob o título, e só: a população que o bloco soma, e a leitura
     de concentração. De quem é o denominador — que não é o dos comparáveis da
     área — fica no hover da segunda; a frase inteira no cabeçalho empurrava o
     Pareto para baixo da dobra. */
  if (d.subtitulo) titulo.appendChild(el('span', 'sub', d.subtitulo));
  if (d.leitura_concentracao) {
    const l = el('span', 'sub', d.leitura_concentracao);
    if (d.leitura_titulo) l.title = d.leitura_titulo;
    titulo.appendChild(l);
  }
  topo.appendChild(titulo);
  partes.push(topo);

  /* Recorte que não alcança ninguém com excedente valorado: o bloco fica, com
     a frase do motor. Sumir faria o leitor achar que o filtro quebrou a tela. */
  if (!d.linhas?.length) {
    partes.push(el('div', 'tbl-band', d.vazio ?? ''));
    cartao.replaceChildren(...partes);
    return;
  }

  /* A lista ROLA dentro do cartão com a lista INTEIRA. Foi tentada uma dobra
     em 10 linhas com "ver todos": a cauda é parte do Pareto, e esconder o que
     já foi calculado para reexibi-lo num clique é interação sem pergunta por
     trás. */
  /* Cabeçalho das colunas: sem ele, "R$ 736 mil" e "26%" são dois números
     soltos à direita de uma barra e o leitor precisa deduzir o que cada um é.
     Os rótulos vêm do motor porque o primeiro muda com o eixo (Cooperado /
     Procedimento). */
  const col = d.colunas ?? {};
  const cab = el('div', 'pareto-cab');
  cab.append(el('span', 'rot', col.rotulo ?? ''),
             el('span', 'trilho'),
             el('span', 'val', col.valor ?? ''),
             el('span', 'cum-rs', col.acumulado_reais ?? ''),
             el('span', 'cum', col.acumulado ?? ''));
  partes.push(cab);

  const lista = el('div', 'pareto');
  const limiar = d.limiar_concentracao ?? 0.8;

  d.linhas.forEach((l, i) => {
    const linha = el('div', 'pareto-l');
    if (l.no_nucleo) linha.classList.add('nucleo');
    // a régua tracejada fecha a última linha do núcleo
    if (l.no_nucleo && !d.linhas[i + 1]?.no_nucleo) linha.classList.add('corte');

    const barra = document.createElement('i');
    barra.style.width = `${l.largura_pct}%`;
    const trilho = el('span', 'trilho');
    trilho.appendChild(barra);

    const tip = el('span', 'tip');
    tip.appendChild(el('b', null, l.rotulo_tooltip ?? l.id));
    for (const det of l.detalhes ?? []) tip.appendChild(el('em', null, det));
    if (l.pct_acumulado_fmt) {
      tip.appendChild(el('em', null, `Participação acumulada: ${l.pct_acumulado_fmt}`));
    }

    /* Na linha, o rótulo CURTO (id do cooperado, descrição do procedimento);
       a frase inteira fica no tooltip, que tem espaço para ela. */
    const rot = el('span', 'rot', l.rotulo_linha ?? l.id);
    rot.title = l.rotulo_tooltip ?? l.id;
    /* Duas colunas de acumulado, e não uma célula com os dois valores: o R$ diz
       QUANTO vale parar nesta linha, o % diz que FRAÇÃO do total é isso. São
       leituras diferentes, e juntas num campo só viram um par de números
       separados por ponto que ninguém decifra — o defeito que a coluna
       "Variação excedente" da tabela tinha. */
    linha.append(rot, trilho, el('span', 'val', l.reais_fmt),
                 el('span', 'cum-rs', l.reais_acumulado_fmt ?? ''),
                 el('span', 'cum', l.pct_acumulado_fmt), tip);

    if (aoEscolher) {
      linha.classList.add('clicavel');
      linha.tabIndex = 0;
      const acionar = () => aoEscolher(l.id);
      linha.addEventListener('click', acionar);
      linha.addEventListener('keydown', (ev) => {
        if (ev.key !== 'Enter' && ev.key !== ' ') return;
        ev.preventDefault();
        acionar();
      });
    }
    lista.appendChild(linha);
  });
  partes.push(lista);

  /* A LISTA ABRE NO TOPO, sempre. Foi tentado abri-la rolada até a régua do
     corte, que em Ginecologia nasce 21px abaixo da dobra: funcionou, e custou
     os dois maiores da lista (R$ 736 mil e R$ 465 mil saíam de cena). Na aba
     de Procedimentos custava 663px de topo. A cabeça do Pareto é a leitura
     inteira; nenhuma marca vale escondê-la. */

  const legenda = el('div', 'legend');
  const marca = (classe, texto) => {
    const s = document.createElement('span');
    s.append(el('i', classe), document.createTextNode(texto));
    legenda.appendChild(s);
  };
  const pct = Math.round(limiar * 100);
  marca('bar-nucleo', `concentram ${pct}% do excesso`);
  marca('bar-cauda', 'demais');
  legenda.appendChild(el('span', null, `linha tracejada = corte de ${pct}%`));
  partes.push(legenda);

  // a ressalva é parte do número: método no rodapé, visível sem hover
  const pe = el('div', 'tbl-ft');
  pe.appendChild(el('span', null, d.metodo ?? ''));
  partes.push(pe);

  cartao.replaceChildren(...partes);
  /* Reinstala o botão: `replaceChildren` levou o `.tbl-hd` anterior junto. O
     helper é idempotente e relê o estado salvo, então o bloco não reabre
     sozinho a cada troca de recorte. */
  colapsavel(cartao, chave);
  }
}
