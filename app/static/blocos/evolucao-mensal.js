/* evolucao-mensal.js — a área no tempo, em duas unidades.
 *
 * Uma barra por MÊS: a altura é o custo das solicitações do mês. Abaixo, a
 * faixa de FECHAMENTO por trimestre, cada célula sob as três barras que ela
 * fecha, com o excedente apurado ali.
 *
 * A divisão é de método, não de desenho: custo é uma soma e desce a qualquer
 * granularidade; o excedente é apurado por trimestre (config.JANELA_MINIMA), e
 * um excedente mensal seria uma medida que a metodologia não fez. Por isso as
 * barras existem mesmo quando nenhum trimestre fecha, e a faixa diz o que falta.
 *
 * O ALINHAMENTO é estrutural: o grupo (o trimestre) contém as suas barras, e a
 * célula da faixa recebe o MESMO peso (o número de meses, que vem do motor).
 * Não há duas grades para manter em acordo.
 *
 * Nada é calculado aqui: alturas, marcas da régua, rótulos, variações e frases
 * vêm prontos de `blocos.evolucao_mensal_da_area`. As alturas e os pesos saem em
 * `style` porque são DADO, como `largura_pct` no Pareto.
 */
'use strict';

import { el } from '../lib/dom.js';
import { colapsavel } from '../lib/colapsar.js';

/**
 * @param {HTMLElement} destino
 * @param {object} d  bloco `evolucao` de /api/area/{id}
 */
export function montarEvolucaoMensal(destino, d) {
  if (!d?.grupos?.length) return;

  const cartao = el('div', 'tbl');
  const topo = el('div', 'tbl-hd');

  const titulo = el('div', 'stack g4');
  titulo.appendChild(el('span', 't', d.titulo));
  if (d.subtitulo) titulo.appendChild(el('span', 'sub', d.subtitulo));
  /* A leitura em UMA frase: primeiro mês contra o último. É a única conclusão
     que uma série sem modelo sustenta, e o motor redige só o que ela paga. */
  if (d.leitura) titulo.appendChild(el('span', 'sub', d.leitura));
  topo.appendChild(titulo);

  const rolo = el('div', 'evom-rolo');
  const dentro = el('div', 'evom-in');
  /* O NÚMERO DE MESES EM CENA é dado, e é dele que o CSS tira a largura do
     bloco (a medida de um mês é do CSS, não daqui). Mesma natureza do
     `--evo-cols` da grade de volume: contagem, não decisão visual. */
  dentro.style.setProperty('--evom-n', d.grupos.reduce((n, g) => n + g.meses.length, 0));

  const grafico = el('div', 'evom-graf');

  /* A GRADE é UMA camada atrás das colunas, e não uma linha por coluna: a régua
     atravessa o gráfico inteiro, senão vira doze traços soltos. Fica ancorada
     no topo porque a pista é o primeiro filho de cada mês e tem altura fixa. */
  if (d.grade?.length) {
    const eixo = el('div', 'evom-eixo');
    const linhas = el('div', 'evom-linhas');
    for (const g of d.grade) {
      const marca = el('span', 'evom-marca', g.rotulo);
      marca.style.bottom = `${g.pct}%`;
      eixo.appendChild(marca);
      const linha = el('i', g.valor === 0 ? 'evom-base' : null);
      linha.style.bottom = `${g.pct}%`;
      linhas.appendChild(linha);
    }
    dentro.appendChild(eixo);
    grafico.appendChild(linhas);
  }

  const faixa = el('div', 'evom-faixa');

  for (const g of d.grupos) {
    /* O PESO do grupo é o número de meses dele, e é o MESMO dos dois lados: é o
       que mantém a célula sob as suas próprias barras quando um trimestre é
       parcial. Vem do motor, e por isso sai em `style`. */
    const grupo = el('div', 'evom-grupo');
    grupo.style.flex = `${g.peso} 1 0`;
    for (const m of g.meses) {
      const col = el('div', 'evom-mes');
      const plot = el('div', 'evom-plot');
      if (m.topo_fmt) {
        const t = el('span', 'evom-topo', m.topo_fmt);
        t.style.bottom = `${m.altura_pct}%`;
        plot.appendChild(t);
      }
      const barra = el('i', 'evom-barra');
      barra.style.height = `${m.altura_pct}%`;
      /* A dica vem redigida do motor e entra em `title`: `lib/dica.js` o
         intercepta e devolve a ficha do app. Nenhum texto é montado aqui. */
      if (m.tooltip) barra.title = m.tooltip;
      plot.appendChild(barra);
      col.append(plot, el('span', 'evom-rot', m.rotulo));
      grupo.appendChild(col);
    }
    grafico.appendChild(grupo);

    if (!d.tem_faixa) continue;
    const cel = el('div', 'evom-cel');
    cel.style.flex = `${g.peso} 1 0`;
    montarCelula(cel, g.trimestre);
    faixa.appendChild(cel);
  }

  dentro.appendChild(grafico);
  if (d.tem_faixa) dentro.appendChild(faixa);
  rolo.appendChild(dentro);

  const corpo = el('div', 'evom');
  corpo.appendChild(rolo);
  cartao.append(topo, corpo);

  /* ── O RODAPÉ: LEGENDA E RESSALVA, NA FAIXA CINZA ────────────────────────
     Mesmo arranjo do Pareto, da distribuição e da dispersão
     (`.tbl-ft.tbl-ft-nota`): legenda em cima, ressalva de método embaixo, as
     duas dentro da faixa. A legenda saiu da direita do cabeçalho em set/2026:
     acima do gráfico ela obrigava a decorar as duas tintas antes de ver o
     desenho a que elas se referem, e depois dele é consulta, que é o que legenda
     é. O cabeçalho fica com o título e a leitura, que é o que se lê primeiro.

     A marca do excedente só existe se alguma célula tiver excedente desenhado:
     legenda para uma tinta ausente do gráfico faz o leitor procurá-la.

     A NOTA vem redigida do motor e só aparece quando tem o que dizer: ela é
     ressalva, não descrição do desenho. */
  const pe = el('div', 'tbl-ft tbl-ft-nota');
  if (d.tem_reais) {
    const legenda = el('div', 'legend');
    const marca = (classe, texto) => {
      const s = document.createElement('span');
      s.append(el('i', classe), document.createTextNode(texto));
      legenda.appendChild(s);
    };
    marca('bar-total', 'Custo total do mês');
    if (d.grupos.some((g) => g.trimestre?.exc_barra_pct != null)) {
      marca('bar-exc', 'Custo excedente do trimestre');
    }
    pe.appendChild(legenda);
  }
  if (d.nota) pe.appendChild(el('span', 'nota', d.nota));
  if (pe.childElementCount) cartao.appendChild(pe);

  destino.appendChild(cartao);
  colapsavel(cartao, 'evolucao-mensal');
}

/* A célula do fechamento. Sem trimestre, ela DIZ o que falta: célula vazia faz
   o leitor procurar o dado, e a ausência aqui tem motivo conhecido (a ponta de
   uma janela que não fecha mais um trimestre). */
function montarCelula(cel, q) {
  if (!q) {
    cel.appendChild(el('span', 'evom-na', 'sem trimestre fechado neste período'));
    return;
  }

  const cab = el('div', 'evom-cel-cab');
  cab.appendChild(el('b', null, q.rotulo));
  if (q.meses) cab.appendChild(el('span', null, q.meses));
  cel.appendChild(cab);

  for (const l of q.linhas_apoio ?? []) {
    const par = el('div', 'evom-par');
    const v = el('span', 'evom-v');
    if (l.variacao) v.appendChild(el('span', 'evom-var', l.variacao));
    v.appendChild(el('span', null, l.valor));
    par.append(el('span', 'evom-k', l.rotulo), v);
    cel.appendChild(par);
  }

  const exc = el('div', 'evom-exc');
  const linha = el('div', 'evom-par');
  linha.append(el('span', 'evom-k', 'excedente'),
               el('span', 'evom-exc-v', q.excedente_fmt ?? ''));
  exc.appendChild(linha);
  /* A FATIA só é desenhada quando existe fatia positiva do custo acima da
     referência. Trimestre abaixo dela não tem parcela para preencher, e uma
     barrinha zerada leria como "nada acima" em vez de "abaixo". */
  if (q.exc_barra_pct != null) {
    const trilho = el('span', 'evom-fatia');
    const preenche = el('i');
    preenche.style.width = `${q.exc_barra_pct}%`;
    trilho.appendChild(preenche);
    exc.appendChild(trilho);
  }
  /* A LINHA DE APOIO DO EXCEDENTE só existe se tiver o que dizer: sem fatia e
     sem trimestre anterior (área sem excedente apurado, primeiro trimestre da
     janela) ela sairia como uma linha em branco no pé da célula, que se lê como
     bloco que não carregou. */
  if (q.exc_pct_fmt || q.variacao_exc) {
    const rodape = el('div', 'evom-par');
    rodape.appendChild(el('span', 'evom-k', q.exc_pct_fmt ?? ''));
    if (q.variacao_exc) rodape.appendChild(el('span', 'evom-var', q.variacao_exc));
    exc.appendChild(rodape);
  }
  cel.appendChild(exc);

  /* o trimestre abaixo do zero DIZ o que é: um valor negativo sem rótulo faz o
     leitor procurar o erro em vez da leitura */
  if (q.exc_negativo) {
    cel.appendChild(el('span', 'evom-na', 'dentro da referência neste trimestre'));
  }
  /* a ressalva de volume vem DEPOIS dos números e qualifica as duas taxas da
     célula, nunca o custo */
  if (q.volume_baixo && q.motivo) cel.appendChild(el('span', 'evom-na', q.motivo));

  if (q.tooltip) cel.title = q.tooltip;
}
