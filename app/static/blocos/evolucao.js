/* evolucao.js — o caso ao longo do tempo, trimestre a trimestre.
 *
 * Uma barra por trimestre: a barra INTEIRA é o custo efetivo do período, o
 * trecho preenchido é o excedente dentro dele. É a mesma gramática do Pareto,
 * no eixo do tempo, e é de propósito — duas leituras do mesmo dinheiro com
 * desenhos diferentes obrigariam o leitor a reaprender a barra em cada bloco.
 *
 * A pergunta que só ela responde: o caso é ESTÁVEL ou está PIORANDO. A coluna
 * de consistência da tabela diz em quantos trimestres ele passou do critério;
 * ela não diz se o excedente cresce.
 *
 * A GRADE (régua horizontal com as marcas à esquerda) vem pronta do motor,
 * porque escala é número: teto, passo e posição de cada marca são calculados em
 * `_escala_grade`. O valor escrito em cima de cada barra continua sendo a
 * leitura exata; a grade dá a comparação de altura entre trimestres, que é o
 * que o olho faz antes de ler qualquer número.
 *
 * Nada é calculado aqui: alturas, percentuais, marcas, rótulos de mês e a frase
 * de leitura vêm prontos de `blocos.evolucao_trimestral`. As alturas saem em
 * `style` porque são DADO, como `largura_pct` no Pareto.
 */
'use strict';

import { el } from '../lib/dom.js';
import { colapsavel } from '../lib/colapsar.js';

/**
 * @param {HTMLElement} destino
 * @param {object} d  bloco `evolucao` de /api/cooperado/{id} ou do painel
 * @param {{semCartao?: boolean}} [opcoes]  `semCartao` para dentro do painel
 *   lateral, que é UMA superfície: cartão dentro de painel é moldura sobre
 *   moldura, a mesma decisão que as seções do painel já tomaram.
 */
export function montarEvolucao(destino, d, opcoes = {}) {
  if (!d?.linhas?.length) return;

  const nu = opcoes.semCartao === true;
  const cartao = nu ? destino : el('div', 'tbl');
  const topo = el('div', nu ? 'stack g8' : 'tbl-hd');

  const titulo = el('div', 'stack g4');
  /* Sem título dentro do painel: a seção já se chama "Custo por trimestre", e
     repetir o nome logo abaixo dele é moldura sobre moldura em texto. */
  if (!nu) titulo.appendChild(el('span', 't', d.titulo));
  if (d.subtitulo) titulo.appendChild(el('span', 'sub', d.subtitulo));
  /* A leitura em UMA frase: primeiro trimestre contra o último. Quatro pontos
     não sustentam tendência, e o motor redige só o que eles pagam. */
  if (d.leitura) titulo.appendChild(el('span', 'sub', d.leitura));
  topo.appendChild(titulo);

  /* LEGENDA: na direita do cabeçalho no cartão; ABAIXO do gráfico no painel.
     Numa coluna estreita ela não cabe ao lado do título, e acima das barras
     obrigava o leitor a decorar as duas tintas antes de ver o desenho a que
     elas se referem. Depois do gráfico, ela é consulta, que é o que legenda é. */
  let legenda = null;
  if (d.tem_reais) {
    legenda = el('div', nu ? 'legend' : 'legend hd-ctl');
    const marca = (classe, texto) => {
      const s = document.createElement('span');
      s.append(el('i', classe), document.createTextNode(texto));
      legenda.appendChild(s);
    };
    marca('bar-total', 'Custo total');
    /* A marca do excedente só existe se houver excedente. Sem isso, o exame sem
       variação apurada exibia uma legenda para uma cor que não está no gráfico. */
    if (d.linhas.some((l) => l.excedente_reais != null)) {
      marca('bar-exc', 'Custo excedente');
    }
    if (!nu) topo.appendChild(legenda);
  }

  const grafico = el('div', 'evo');

  /* A grade é UMA camada atrás das colunas, e não uma linha por coluna: a régua
     atravessa o gráfico inteiro, senão ela vira quatro traços soltos. Fica
     ancorada no topo porque a pista da barra é o primeiro filho de cada coluna
     e tem altura fixa. */
  if (d.grade?.length) {
    const eixo = el('div', 'evo-eixo');
    const linhas = el('div', 'evo-linhas');
    for (const g of d.grade) {
      const marca = el('span', 'evo-marca', g.rotulo);
      marca.style.bottom = `${g.pct}%`;
      eixo.appendChild(marca);
      const linha = el('i', g.valor === 0 ? 'evo-base' : null);
      linha.style.bottom = `${g.pct}%`;
      linhas.appendChild(linha);
    }
    grafico.append(eixo, linhas);
  }

  for (const l of d.linhas) {
    const col = el('div', 'evo-col');
    const plot = el('div', 'evo-plot');

    /* SEM CUSTO APURADO ocupa a vaga dele, vazia e tracejada. Só acontece
       quando não há preço para valorar as solicitações do trimestre: zero seria
       uma afirmação sobre o custo, e aqui não há custo apurado.
       VOLUME BAIXO não cai aqui: o piso decide se uma TAXA é comparável, não se
       o custo existe, e o trimestre segue com barra e com ressalva. */
    if (!l.avaliavel) {
      const vaga = el('i', 'evo-vaga');
      if (l.tooltip) vaga.title = l.tooltip;
      plot.appendChild(vaga);
      col.appendChild(plot);
      col.appendChild(el('span', 'evo-rot evo-rot-na', l.rotulo));
      grafico.appendChild(col);
      continue;
    }

    /* TUDO SE MEDE A PARTIR DA LINHA DO ZERO, que pode não estar no fundo da
       pista: quando algum trimestre tem excedente negativo, a régua desce
       abaixo de zero e o chão do gráfico deixa de ser o zero. */
    const zero = d.zero_pct ?? 0;

    /* O VALOR NO TOPO DA BARRA só no cartão do dossiê. No painel a coluna é
       estreita e todo número escrito sobre o desenho ou é cortado pela largura
       da barra, ou invade a coluna vizinha: os quatro rótulos ficam na grade
       logo abaixo, cada um sob a sua barra, onde têm largura e alinhamento.
       O gráfico do painel passa a carregar só a FORMA (comparação de alturas),
       e a grade carrega o NÚMERO. */
    if (!nu) {
      const topoTxt = el('span', 'evo-topo', l.topo_fmt ?? '');
      topoTxt.style.bottom = `${zero + l.altura_pct}%`;
      plot.appendChild(topoTxt);
    }

    const barra = el('i', 'evo-barra');
    barra.style.bottom = `${zero}%`;
    barra.style.height = `${l.altura_pct}%`;
    plot.appendChild(barra);

    if (d.tem_reais && l.altura_exc_pct > 0) {
      /* O excedente é irmão da barra, não filho: positivo ele preenche a base
         do custo; NEGATIVO ele desce abaixo do zero, onde não existe custo para
         preencher. Aninhado, o caso negativo não teria onde ser desenhado. */
      const dentro = el('i', `evo-exc${l.exc_negativo ? ' evo-exc-neg' : ''}`);
      dentro.style.height = `${l.altura_exc_pct}%`;
      dentro.style.bottom = l.exc_negativo
        ? `calc(${zero}% - ${l.altura_exc_pct}%)` : `${zero}%`;
      /* O MESMO hover da barra: o trecho verde cobre a base do custo, e sem o
         título aqui metade da área da coluna ficaria sem dica. */
      if (l.tooltip) dentro.title = l.tooltip;
      /* O valor do excedente DENTRO do próprio trecho, quando ele comporta uma
         linha de texto: o motor decide pela ALTURA (`exc_fmt_dentro`) e aqui se
         decide pela LARGURA, que ele não tem como conhecer.
         No painel a barra tem 48px e "R$ 28" não cabe: o texto saía cortado
         pelas bordas do trecho, em branco sobre verde. Lá o número vai para a
         grade de volume logo abaixo, alinhado à mesma coluna, onde ele tem a
         largura da coluna inteira e o contraste do corpo de texto. */
      if (l.exc_fmt_dentro && !nu) dentro.appendChild(el('b', null, l.exc_fmt_dentro));
      plot.appendChild(dentro);
    }
    /* A frase vem redigida do motor e entra em `title`: `lib/dica.js` o
       intercepta e devolve a bolha do app, a mesma dos cabeçalhos da tabela.
       Nenhum texto é montado aqui. */
    if (l.tooltip) barra.title = l.tooltip;

    col.appendChild(plot);
    col.appendChild(el('span', 'evo-rot', l.rotulo));
    grafico.appendChild(col);
  }

  const cartoes = el('div', 'evo-cards');
  for (const l of d.linhas) {
    const c = el('div', 'evo-card');
    const cab = el('div', 'row g6');
    cab.appendChild(el('b', null, l.rotulo));
    if (l.meses) cab.appendChild(el('span', 'evo-meses', l.meses));
    c.appendChild(cab);
    /* A SETA compara com o trimestre ANTERIOR e só aparece acima do piso de
       variação; abaixo dele o movimento existe mas não é afirmado, e continua
       no hover em número.
       Cor semântica só onde subir é PIOR (índice e custo por consulta). Volume
       (consultas, pacientes) leva seta neutra: mais gente atendida não é achado,
       e pintar de vermelho afirmaria que é. */
    const SEMANTICA = new Set(['indice', 'custo_por_consulta']);
    const par = (rot, val, chave) => {
      if (!val) return;
      const r = el('div', 'row row-between');
      const v = el('span', 'evo-v', val);
      const mov = l.variacao?.[chave];
      if (mov && mov.dir !== 'estavel') {
        const seta = el('span',
          `evo-seta ${SEMANTICA.has(chave) ? (mov.dir === 'sobe' ? 'dir-up' : 'dir-down') : ''}`,
          mov.dir === 'sobe' ? '↑' : '↓');
        seta.title = `${mov.pct_fmt} ${mov.dir === 'sobe' ? 'acima' : 'abaixo'} do trimestre anterior`;
        v.appendChild(seta);
      } else if (mov) {
        v.title = `${mov.pct_fmt} de variação sobre o trimestre anterior`;
      }
      r.append(el('span', 'evo-k', rot), v);
      c.appendChild(r);
    };
    if (l.avaliavel) {
      par('consultas', l.consultas_fmt, 'consultas');
      par('pacientes', l.pacientes_fmt, 'pacientes');
      par('SADT/consulta', l.indice_fmt, 'indice');
      par('custo/consulta', l.custo_por_consulta_fmt, 'custo_por_consulta');
      /* o trimestre abaixo do zero DIZ o que é, no cartão: uma barra que desce
         sem rótulo faz o leitor procurar o erro em vez da leitura */
      if (l.exc_negativo) {
        c.appendChild(el('span', 'evo-na', 'dentro da referência neste trimestre'));
      }
      /* a ressalva de volume vem DEPOIS dos números, não no lugar deles: ela
         qualifica as duas taxas do cartão, e não o custo */
      if (l.volume_baixo && l.motivo) c.appendChild(el('span', 'evo-na', l.motivo));
    } else {
      /* o cartão sem custo carrega o MOTIVO, não três traços: célula vazia faz
         o leitor procurar o dado que faltou */
      c.appendChild(el('span', 'evo-na', l.motivo ?? 'sem custo apurado'));
    }
    cartoes.appendChild(c);
  }

  const corpo = el('div', nu ? 'evo-corpo evo-corpo-nu' : 'evo-corpo');
  corpo.append(grafico);
  if (nu) { if (legenda) corpo.appendChild(legenda); } else { corpo.appendChild(cartoes); }
  cartao.append(topo, corpo);

  /* A NOTA DE MÉTODO no rodapé, na faixa de apoio: ela explica por que os
     quatro trimestres somam o número do resumo e por que um deles pode ficar
     abaixo do zero. Vem redigida do motor, como toda ressalva que carrega
     afirmação sobre o número. */
  if (d.nota) {
    if (nu) {
      cartao.appendChild(el('span', 'sub', d.nota));
    } else {
      const pe = el('div', 'tbl-ft tbl-ft-nota');
      pe.appendChild(el('span', 'nota', d.nota));
      cartao.appendChild(pe);
    }
  }

  if (nu) return;
  destino.appendChild(cartao);
  colapsavel(cartao, 'evolucao');
}
