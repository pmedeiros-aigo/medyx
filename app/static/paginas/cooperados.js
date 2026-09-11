/* cooperados.js — o ÍNDICE de cooperados, em /cooperados.
 *
 * A pergunta da página: "quero olhar um médico específico, e não sei a área
 * dele". Até aqui só se chegava à página de um cooperado descobrindo antes a
 * área e achando a linha na tabela; errar a área fazia concluir que ele não
 * estava na base.
 *
 * É uma PORTA, com três números ABSOLUTOS por cooperado (decisão de produto,
 * set/2026): consultas, solicitações e custo total no período. São volumes,
 * não comparações — nenhum passa por régua de área, e por isso podem atravessar
 * as áreas numa lista só e ser ordenados. O que continua fora daqui é tudo que
 * depende de referência (excedente, percentil, posição): isso vive na página
 * do cooperado e na tela de Área, onde há régua. Ordenar por custo total não é
 * ranquear contra os pares; é ordenar uma lista pelo tamanho.
 *
 * Os seletores de Especialidade e Área FILTRAM esta lista, e não navegam: abrem
 * em "Todas" e recortam o que está em cena. É a diferença entre um filtro e uma
 * navegação disfarçada, e aqui eles são filtro de verdade (ver `escopo` em
 * lib/pagina.js).
 *
 * ── fronteira visual ────────────────────────────────────────────────────────
 * Nenhuma classe nova. `.tbl`/`.tbl-hd`/`.tbl-scroll` são a moldura de sempre,
 * `.search` é o campo do contrato (o desvio autorizado do `<input>`), e a
 * tabela sai pelo `lib/tabelas.js`, o mesmo da tela de Área — inclusive o
 * cabeçalho ordenável e o ciclo desc → asc → nome.
 */
'use strict';

import { el } from '../lib/dom.js';
import { buscar } from '../lib/api.js';
import { abrirPagina } from '../lib/pagina.js';
import { TELAS, comRegua } from '../lib/rotas.js';
import {
  cabecalho, moldura, campoDeBusca, casa, ordenar, ordemDaURL, gravarOrdem,
  proximaOrdem,
} from '../lib/tabelas.js';

/* As duas primeiras não ordenam: a ordem padrão é o nome, e ela não muda. As
   três numéricas ordenam pelo valor bruto (`valor`), nunca pelo texto
   formatado; quem não tem o número vai para o fim nas duas direções. */
const COLUNAS = [
  { nome: 'Cooperado', classe: 'col-id' },
  { nome: 'Área de atuação', classe: 'col-txt' },
  { nome: 'Consultas', classe: 'col-num', direita: true, ordem: 'consultas',
    def: 'Consultas com pedido de exame no período.',
    valor: (c) => c.consultas },
  { nome: 'Solicitações', classe: 'col-num-md', direita: true, ordem: 'solicitacoes',
    def: 'Itens solicitados no período.',
    valor: (c) => c.solicitacoes },
  { nome: 'Custo total', classe: 'col-num-md', direita: true, ordem: 'custo',
    def: 'Valor de tudo que foi solicitado no período, a preços de referência '
       + 'internos derivados das contas.',
    valor: (c) => c.custo_total },
];

/* O escopo escolhido nos seletores do chassi. `null` = "Todas". Vive fora do
   `montar` porque o callback do chassi é registrado antes de a lista existir. */
const escopoAtivo = { esp: null, area: null };
let aplicarEscopo = () => {};

await abrirPagina({
  titulo: 'Cooperados',
  aoTrocarArea: (id) => TELAS.area.caminho(id),
  /* FILTRA, não navega: nesta tela o seletor recorta a lista em cena. Abrir em
     "Todas" é o que faz dela uma porta para os 202, e não para uma área. */
  escopo: {
    todas: true,
    aoFiltrar: (campo, id) => { escopoAtivo[campo] = id; aplicarEscopo(); },
  },
  montar: async ({ conteudo }) => {
    const topo = el('div', 'stack g6');
    topo.appendChild(el('h2', null, 'Cooperados'));
    const sub = el('span', 'sub', 'carregando…');
    topo.appendChild(sub);
    conteudo.appendChild(topo);

    const dados = await buscar('/api/cooperados', {
      anunciarEm: conteudo, rotulo: 'Calculando', soMotor: true,
    });
    const todos = dados.cooperados ?? [];
    sub.textContent = `${dados.total} cooperados na classificação · `
      + `${dados.n_disponiveis} com atividade no período`;

    let termo = '';
    const caixa = campoDeBusca({
      placeholder: 'Buscar por nome ou área',
      aoDigitar: (t) => { termo = t; desenhar(); },
    });

    /* A ordenação viaja na URL (`ord`/`dir`), como na tela de Área: um link
       compartilhado abre na mesma ordem. Sem `ord`, a ordem é o nome. */
    const ordem = ordemDaURL(COLUNAS);

    /* MESMA moldura das tabelas da Área e do Cooperado (lib/tabelas.js). */
    const { quadro, topo: cabecalhoTabela, tabela, peEstado } = moldura();
    const tt = el('div', 'stack g4');
    tt.appendChild(el('span', 't', 'Todos os cooperados'));
    cabecalhoTabela.append(tt, caixa);
    conteudo.appendChild(quadro);

    /** Célula numérica: o texto já vem formatado do motor; vazia quando não há
     *  medida (nunca zero, que leria como "não custa nada"). */
    function celulaNum(texto, classe) {
      const td = el('td', `${classe} rt num`, texto ?? '');
      return td;
    }

    /** Uma linha. Quem não tem atividade no período fica esmaecido e sem link:
     *  a página dele não renderiza nesta janela. Continua LISTADO, porque
     *  sumir devolveria "não encontrado" para alguém que existe. */
    function linha(c) {
      const tr = document.createElement('tr');
      const id = document.createElement('td');
      id.className = 'col-id';
      if (c.disponivel) {
        const a = document.createElement('a');
        a.href = comRegua(TELAS.cooperado.caminho(c.id));
        a.textContent = c.id;
        id.appendChild(a);
      } else {
        id.appendChild(el('span', 'val-ressalva', c.id));
        id.title = c.motivo ?? '';
      }
      /* O motivo vira ETIQUETA, e não coluna: seria uma coluna vazia em 200
         das 202 linhas. */
      if (!c.disponivel && c.motivo) {
        const t = el('span', 'tag tag-caveat', c.motivo);
        t.title = 'A página do cooperado não abre nesta janela. Troque o período.';
        id.appendChild(t);
      }
      tr.appendChild(id);
      tr.appendChild(el('td', 'col-txt', c.area ?? ''));
      tr.appendChild(celulaNum(c.consultas_fmt, 'col-num'));
      tr.appendChild(celulaNum(c.solicitacoes_fmt, 'col-num-md'));
      tr.appendChild(celulaNum(c.custo_total_fmt, 'col-num-md'));
      return tr;
    }

    function aoOrdenar(chave) {
      const prox = proximaOrdem(ordem.chave, ordem.direcao, chave);
      ordem.chave = prox.chave;
      ordem.direcao = prox.direcao;
      gravarOrdem(ordem.chave, ordem.direcao);
      desenhar();
    }

    function desenhar() {
      /* Dois recortes que se somam: o seletor de área do chassi e o texto
         digitado. A ordem é o nome, salvo coluna escolhida no cabeçalho. */
      let lista = todos.filter((c) => {
        if (escopoAtivo.area && c.area_id !== escopoAtivo.area) return false;
        return casa(c.id, termo) || casa(c.area, termo);
      });
      const coluna = COLUNAS.find((c) => c.ordem === ordem.chave);
      lista = ordenar(lista, coluna, ordem.direcao);

      const corpo = document.createElement('tbody');
      if (!lista.length) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = COLUNAS.length;
        td.className = 'val-ressalva';
        td.textContent = 'nenhum cooperado com esse nome ou área';
        tr.appendChild(td);
        corpo.appendChild(tr);
      } else {
        for (const c of lista) corpo.appendChild(linha(c));
      }
      tabela.replaceChildren(
        cabecalho(COLUNAS, ordem.chave, ordem.direcao, aoOrdenar), corpo);
      /* O estado da vista no RODAPÉ, como nas outras duas tabelas. */
      const recortado = termo || escopoAtivo.area;
      peEstado.textContent = recortado
        ? `${lista.length} de ${todos.length} cooperados`
        : `${todos.length} cooperados na classificação`;
    }

    aplicarEscopo = desenhar;
    desenhar();
    caixa.querySelector('input').focus();
  },
});
