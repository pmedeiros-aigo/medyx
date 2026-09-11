/* procedimentos.js — o ÍNDICE de procedimentos, em /procedimentos.
 *
 * A quarta dimensão do app, e a mais fina: Panorama (especialidade) → Área
 * (peer group) → Cooperado (pessoa) → PROCEDIMENTO (o que se pede).
 *
 * A pergunta da página: "qual procedimento está custando, na especialidade
 * inteira?". Até aqui o procedimento só existia DENTRO de uma área: a gaveta
 * que abre na tela de Área é sempre "este procedimento na Ginecologia", e quem
 * quisesse o procedimento inteiro somava as áreas de cabeça.
 *
 * ── por que esta lista TEM número, e a de cooperados não ────────────────────
 * O índice de cooperados é uma porta sem número nenhum, e por regra: ele
 * atravessa as áreas, e coluna ordenável ali convida a ler a lista como
 * ranking, que entre peer groups é a comparação proibida.
 *
 * Com procedimento a soma é legítima, e é essa diferença que torna esta tela
 * possível: o excedente de cada par já foi medido contra a referência da ÁREA
 * daquele cooperado. Soma-se dinheiro já comparado, nunca régua. Por isso aqui
 * há colunas ordenáveis, e por isso a faixa de critérios continua em cena (o
 * shell a mantém): todo número desta tabela é número comparado.
 *
 * ── fronteira visual ───────────────────────────────────────────────────────
 * Nenhuma classe nova: `moldura`, `cabecalho`, `campoDeBusca`, `casa`,
 * `ordenar` e a ordem na URL saem do `lib/tabelas.js`, o mesmo da tela de Área,
 * do Dossiê e do índice de cooperados.
 *
 * ── nenhum número calculado aqui ───────────────────────────────────────────
 * Contagens, somas e formatação vêm prontas de `blocos.indice_de_procedimentos`
 * (CLAUDE.md). O JavaScript filtra, ordena e desenha.
 */
'use strict';

import { el } from '../lib/dom.js';
import { buscar } from '../lib/api.js';
import { abrirPagina } from '../lib/pagina.js';
import { TELAS, comRegua } from '../lib/rotas.js';
import { cabecalho, moldura, campoDeBusca, casa, ordenar,
         ordemDaURL, proximaOrdem, gravarOrdem } from '../lib/tabelas.js';

/* As colunas respondem, nesta ordem: o que é · em quantos grupos dói · quem
   pede · quanto custa · quantos estão acima · quanto disso está acima.

   "% do custo" é a coluna que separa procedimentos de portes diferentes: R$ 460
   mil sobre um custo de R$ 894 mil é outra conversa que os mesmos R$ 460 mil
   sobre R$ 12 milhões. Sem ela a lista seria só um ranking de tamanho.

   A TABELA É DE LARGURA FIXA (`.tbl-fixa`), então toda coluna com medida tira
   espaço da que não tem. As numéricas declaram a sua e o nome do procedimento
   fica com o resto: ele é a coluna que se lê, e quebrar em três linhas fazia a
   grade inteira respirar errado.

   "Solicitações" saiu daqui e ficou na tela do procedimento. Volume sozinho não
   decide nada nesta lista, e o custo total já é volume vezes preço. */
const COLUNAS = [
  { nome: 'Procedimento' },
  { nome: 'Áreas', direita: true, classe: 'col-num',
    def: 'Em quantas áreas de atuação este procedimento tem custo acima da '
       + 'referência. Excedente em mais de uma área é conversa de protocolo, '
       + 'e não conversa individual.',
    ordem: 'areas', valor: (l) => l.n_areas },
  { nome: 'Solicitantes', direita: true, classe: 'col-num',
    def: 'Cooperados que solicitaram este procedimento no período, com volume '
       + 'suficiente para entrar na comparação.',
    ordem: 'solicitantes', valor: (l) => l.solicitantes },
  { nome: 'Custo total', direita: true, classe: 'col-num-md',
    def: 'Valor de tudo que foi solicitado deste procedimento no período.',
    ordem: 'custo', valor: (l) => l.custo },
  { nome: 'Acima do critério', direita: true, classe: 'col-num-lg',
    def: 'Cooperados que passaram o critério de revisão da própria área neste '
       + 'procedimento.',
    ordem: 'acima', valor: (l) => l.n_acima },
  { nome: 'Variação excedente', direita: true, classe: 'col-num-lg',
    def: 'Valor das solicitações acima da referência, cada área medida contra '
       + 'a própria.',
    ordem: 'excedente', valor: (l) => l.excedente_reais },
  { nome: '% do custo', direita: true, classe: 'col-num',
    def: 'Parte do custo deste procedimento que está acima da referência. É a '
       + 'coluna comparável entre procedimentos de portes diferentes.',
    ordem: 'fracao', valor: (l) => l.fracao },
];

await abrirPagina({
  titulo: 'Procedimentos',
  aoTrocarArea: (id) => TELAS.area.caminho(id),
  montar: async ({ conteudo }) => {
    const topo = el('div', 'stack g6');
    topo.appendChild(el('h2', null, 'Procedimentos'));
    const sub = el('span', 'sub', '');
    topo.appendChild(sub);
    conteudo.appendChild(topo);

    const d = await buscar('/api/procedimentos', {
      anunciarEm: conteudo, rotulo: 'Calculando',
    });
    const todos = d.linhas ?? [];
    sub.textContent = d.resumo ?? '';

    let termo = '';
    const caixa = campoDeBusca({
      placeholder: 'Buscar por nome ou código',
      aoDigitar: (t) => { termo = t; desenhar(); },
    });

    /* MESMA moldura das outras três tabelas (lib/tabelas.js). */
    const { quadro, topo: cabecalhoTabela, tabela, peEstado } = moldura();
    const tt = el('div', 'stack g4');
    tt.appendChild(el('span', 't', 'Todos os procedimentos'));
    cabecalhoTabela.append(tt, caixa);
    conteudo.appendChild(quadro);

    /* A ordem viaja na URL, como nas outras tabelas: um link levado a uma
       reunião tem de reabrir a mesma leitura. O padrão é a variação excedente,
       que é a pergunta com que se abre a tela, e é a ordem em que o motor já
       entrega — por isso o estado inicial pode ser "sem ordenação". */
    let { chave: ordem, direcao } = ordemDaURL(COLUNAS);

    /** Uma linha. O nome é o link; a linha inteira não é clicável porque as
     *  células têm valor selecionável (o analista copia número). */
    function linha(l) {
      const tr = document.createElement('tr');
      const nome = el('td');
      const a = document.createElement('a');
      a.href = comRegua(TELAS.procedimento.caminho(l.codigo));
      a.textContent = l.descricao;
      a.title = `${l.descricao} · código ${l.codigo}`;
      nome.appendChild(a);
      tr.appendChild(nome);

      for (const [classe, texto] of [
        ['col-num', l.areas_fmt], ['col-num', String(l.solicitantes)],
        ['col-num-md', l.custo_fmt], ['col-num-lg', l.n_acima_fmt],
        ['col-num-lg', l.excedente_fmt], ['col-num', l.fracao_fmt],
      ]) tr.appendChild(el('td', `rt num ${classe}`, texto));
      return tr;
    }

    function desenhar() {
      const filtradas = todos.filter(
        (l) => casa(l.descricao, termo) || casa(l.codigo, termo));
      const lista = ordenar(filtradas,
                            COLUNAS.find((c) => c.ordem === ordem), direcao);

      const corpo = document.createElement('tbody');
      if (!lista.length) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = COLUNAS.length;
        td.className = 'val-ressalva';
        td.textContent = 'nenhum procedimento com esse nome ou código';
        tr.appendChild(td);
        corpo.appendChild(tr);
      } else {
        for (const l of lista) corpo.appendChild(linha(l));
      }

      tabela.replaceChildren(
        cabecalho(COLUNAS, ordem, direcao, (chave) => {
          ({ chave: ordem, direcao } = proximaOrdem(ordem, direcao, chave));
          gravarOrdem(ordem, direcao);
          desenhar();
        }),
        corpo);

      /* O estado da vista no RODAPÉ, como nas outras tabelas. O total em R$ vem
         pronto do motor, e é do conjunto inteiro: recortar por busca não muda
         o dinheiro que está na especialidade. */
      peEstado.textContent = (termo
        ? `${lista.length} de ${todos.length} procedimentos`
        : `${todos.length} procedimentos`)
        + ` · ${d.excedente_total_fmt} de variação excedente`;
    }

    desenhar();
    caixa.querySelector('input').focus();
  },
});
