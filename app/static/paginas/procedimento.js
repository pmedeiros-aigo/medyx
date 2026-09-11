/* procedimento.js — UM procedimento, visto da especialidade inteira.
 *
 * O irmão do dossiê com a unidade trocada: lá uma PESSOA contra a régua da área
 * dela, aqui um PROCEDIMENTO contra as réguas de todas as áreas em que ele é
 * pedido. A pergunta que só esta tela responde: isto é hábito de alguns, ou é
 * padrão da especialidade?
 *
 * Três blocos, três perguntas:
 *
 *   LEITURA     quanto se pede, quanto custa, quanto está acima. Mesmo bloco da
 *               Leitura da área, com a unidade trocada (blocos/leitura-area.js).
 *   POR ÁREA    as réguas lado a lado. A seção que só esta tela dá.
 *   QUEM PEDE   os cooperados acima do critério, cada um medido contra a régua
 *               da PRÓPRIA área, com a área declarada na linha.
 *
 * ── nenhuma das duas tabelas ordena, e é decisão ───────────────────────────
 * A de áreas porque cabeçalho clicável sobre uma lista de peer groups convida a
 * ranqueá-los, e réguas não se comparam entre si. A de cooperados porque a
 * ordem dela É o achado: variação excedente decrescente, a mesma fila do resto
 * do app.
 *
 * Nada é calculado aqui: contagem, soma e formato vêm de
 * `blocos.retrato_do_procedimento` (CLAUDE.md).
 */
'use strict';

import { el } from '../lib/dom.js';
import { buscar } from '../lib/api.js';
import { abrirPagina } from '../lib/pagina.js';
import { TELAS, comRegua, rotaAtual } from '../lib/rotas.js';
import { moldura, cabecalho } from '../lib/tabelas.js';
import { montarLeituraDaArea } from '../blocos/leitura-area.js';

/* Mesma disciplina de largura do índice: as numéricas declaram a sua, e a
   coluna que se lê fica com o resto (`.tbl-fixa`). */
const COLUNAS_AREA = [
  { nome: 'Área de atuação' },
  { nome: 'Solicitantes', direita: true, classe: 'col-num',
    def: 'Cooperados da área que pediram este procedimento e têm volume de '
       + 'consultas para entrar na comparação.' },
  { nome: 'Prevalência', direita: true, classe: 'col-num',
    def: 'Parte dos cooperados que formam a referência da área e pedem este '
       + 'procedimento.' },
  { nome: 'Referência', direita: true, classe: 'col-num',
    def: 'Frequência de referência da área para este procedimento, em '
       + 'solicitações por consulta.' },
  { nome: 'Critério', direita: true, classe: 'col-num',
    def: 'Frequência a partir da qual o par entra em revisão, na régua desta '
       + 'área.' },
  { nome: 'Acima do critério', direita: true, classe: 'col-num-lg',
    def: 'Cooperados da área que passaram o critério neste procedimento.' },
  { nome: 'Custo', direita: true, classe: 'col-num-md',
    def: 'Valor solicitado deste procedimento pelos cooperados da área.' },
  { nome: 'Variação excedente', direita: true, classe: 'col-num-lg',
    def: 'Valor acima da referência da própria área.' },
];

const COLUNAS_QUEM = [
  { nome: 'Cooperado', classe: 'col-id' },
  { nome: 'Área de atuação', classe: 'col-txt',
    def: 'A área contra cuja referência este cooperado foi medido.' },
  { nome: 'Frequência', direita: true, classe: 'col-num',
    def: 'Solicitações deste procedimento por consulta do cooperado.' },
  { nome: 'Referência', direita: true, classe: 'col-num',
    def: 'Frequência de referência da área dele para este procedimento.' },
  { nome: 'Razão', direita: true, classe: 'col-num',
    def: 'Quantas vezes a frequência dele supera a referência da própria área.' },
  { nome: 'Consultas', direita: true, classe: 'col-num',
    def: 'Consultas do cooperado no período, o denominador da frequência.' },
  { nome: 'Excesso de solicitações', direita: true, classe: 'col-num-lg',
    def: 'Solicitações acima do que a referência da área dele previa.' },
  { nome: 'Variação excedente', direita: true, classe: 'col-num-lg',
    def: 'Valor das solicitações acima da referência da área dele.' },
];


/** Uma tabela fechada: cabeçalho, corpo e a nota da seção no rodapé. */
function tabela(destino, { titulo, nota, colunas, linhas, vazio, montarLinha }) {
  const { quadro, topo, tabela: tbl, peEstado } = moldura();
  const tt = el('div', 'stack g4');
  tt.appendChild(el('span', 't', titulo));
  topo.appendChild(tt);

  const corpo = document.createElement('tbody');
  if (!linhas.length) {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = colunas.length;
    td.className = 'val-ressalva';
    td.textContent = vazio;
    tr.appendChild(td);
    corpo.appendChild(tr);
  } else {
    for (const l of linhas) corpo.appendChild(montarLinha(l));
  }
  tbl.replaceChildren(cabecalho(colunas, null, null, null), corpo);
  peEstado.textContent = nota;
  destino.appendChild(quadro);
}


await abrirPagina({
  titulo: 'Procedimento',
  aoTrocarArea: (id) => TELAS.area.caminho(id),
  montar: async ({ conteudo }) => {
    const codigo = rotaAtual().procedimento;
    const topo = el('div', 'stack g6');
    const h = el('h2', null, '');
    const sub = el('span', 'sub', '');
    topo.append(h, sub);
    conteudo.appendChild(topo);

    const d = await buscar(`/api/procedimento/${encodeURIComponent(codigo)}`,
                           { anunciarEm: conteudo, rotulo: 'Calculando' });
    h.textContent = d.descricao;
    sub.textContent = `Código ${d.codigo}`;

    montarLeituraDaArea(conteudo, d);

    // ── as réguas lado a lado ────────────────────────────────────────────
    tabela(conteudo, {
      titulo: d.areas.titulo,
      nota: d.areas.nota,
      colunas: COLUNAS_AREA,
      linhas: d.areas.linhas,
      vazio: 'nenhuma área pediu este procedimento no período',
      montarLinha: (l) => {
        const tr = document.createElement('tr');
        const nome = el('td', null, l.area);
        /* O MOTIVO vira etiqueta, e não coluna: seria uma coluna vazia em quase
           toda linha. `.tag-caveat` é a mesma ressalva do resto do app. */
        if (l.motivo) {
          const t = el('span', 'tag tag-caveat', l.motivo);
          nome.appendChild(t);
        }
        tr.appendChild(nome);
        for (const [classe, texto] of [
          ['col-num', String(l.solicitantes)], ['col-num', l.prevalencia_fmt],
          ['col-num', l.referencia_fmt], ['col-num', l.criterio_fmt],
          ['col-num-lg', l.n_acima_fmt], ['col-num-md', l.custo_fmt],
          ['col-num-lg', l.excedente_fmt],
        ]) tr.appendChild(el('td', `rt num ${classe}`, texto));
        return tr;
      },
    });

    // ── quem pede acima da referência ────────────────────────────────────
    tabela(conteudo, {
      titulo: d.solicitantes.titulo,
      nota: d.solicitantes.nota,
      colunas: COLUNAS_QUEM,
      linhas: d.solicitantes.linhas,
      vazio: d.solicitantes.vazio,
      montarLinha: (l) => {
        const tr = document.createElement('tr');
        const id = el('td', 'col-id');
        const a = document.createElement('a');
        a.href = comRegua(TELAS.cooperado.caminho(l.id));
        a.textContent = l.id;
        id.appendChild(a);
        tr.appendChild(id);
        tr.appendChild(el('td', 'col-txt', l.area));
        for (const [classe, texto] of [
          ['col-num', l.taxa_fmt], ['col-num', l.referencia_fmt],
          ['col-num', l.razao_fmt], ['col-num', l.consultas_fmt],
          ['col-num-lg', l.excedente_itens_fmt], ['col-num-lg', l.excedente_fmt],
        ]) tr.appendChild(el('td', `rt num ${classe}`, texto));
        return tr;
      },
    });
  },
});
