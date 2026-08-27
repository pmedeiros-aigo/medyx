/* cooperados.js — o ÍNDICE de cooperados, em /cooperados.
 *
 * A pergunta da página: "quero olhar um médico específico, e não sei a área
 * dele". Até aqui só se chegava a um dossiê descobrindo antes a área e achando
 * a linha na tabela; errar a área fazia concluir que ele não estava na base.
 *
 * É uma PORTA, não uma análise, e por isso NÃO TEM NÚMERO NENHUM — nem
 * comparado, nem de contagem. Três razões:
 *
 *   · quem procura um cooperado quer achá-lo e entrar; número é ruído no
 *     caminho;
 *   · a lista atravessa as oito áreas, e qualquer coluna ordenável convida a
 *     lê-la como ranking, que entre peer groups é a comparação proibida;
 *   · sem número comparado não há o que carimbar, e uma faixa de critérios
 *     aqui prometeria uma régua que a tela não usa (o shell a esconde).
 *
 * Quem quer medida abre o dossiê, onde há régua. Quem quer fila ordenada por
 * oportunidade usa o Panorama, que já é isso.
 *
 * Os seletores de Especialidade e Área FILTRAM esta lista, e não navegam: abrem
 * em "Todas" e recortam o que está em cena. É a diferença entre um filtro e uma
 * navegação disfarçada, e aqui eles são filtro de verdade (ver `escopo` em
 * lib/pagina.js).
 *
 * ── fronteira visual ────────────────────────────────────────────────────────
 * Nenhuma classe nova. `.tbl`/`.tbl-hd`/`.tbl-scroll` são a moldura de sempre,
 * `.search` é o campo do contrato (o desvio autorizado do `<input>`), e a
 * tabela sai pelo `lib/tabelas.js`, o mesmo da tela de Área.
 */
'use strict';

import { el } from '../lib/dom.js';
import { buscar } from '../lib/api.js';
import { abrirPagina } from '../lib/pagina.js';
import { TELAS, comRegua } from '../lib/rotas.js';
import { cabecalho, moldura, campoDeBusca, casa } from '../lib/tabelas.js';

/* Duas colunas, nenhuma ordenável: a ordem é o nome, e ela não muda. Coluna
   ordenável numa lista que atravessa áreas é o convite a ranquear. */
const COLUNAS = [
  { nome: 'Cooperado', classe: 'col-id' },
  { nome: 'Área de atuação', classe: 'col-txt' },
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
      anunciarEm: conteudo, rotulo: 'carregando o elenco', soMotor: true,
    });
    const todos = dados.cooperados ?? [];
    sub.textContent = `${dados.total} cooperados na classificação · `
      + `${dados.n_disponiveis} com atividade no período`;

    let termo = '';
    const caixa = campoDeBusca({
      placeholder: 'Buscar por nome ou área',
      aoDigitar: (t) => { termo = t; desenhar(); },
    });

    /* MESMA moldura das tabelas da Área e do Dossiê (lib/tabelas.js). */
    const { quadro, topo: cabecalhoTabela, tabela, peEstado } = moldura();
    const tt = el('div', 'stack g4');
    tt.appendChild(el('span', 't', 'Todos os cooperados'));
    cabecalhoTabela.append(tt, caixa);
    conteudo.appendChild(quadro);

    /** Uma linha. Quem não tem atividade no período fica esmaecido e sem link:
     *  o dossiê dele não renderiza nesta janela. Continua LISTADO, porque
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
         das 202 linhas. `.tag-caveat` é a mesma do "classificação em revisão"
         do dossiê, que é o mesmo tipo de ressalva. */
      if (!c.disponivel && c.motivo) {
        const t = el('span', 'tag tag-caveat', c.motivo);
        t.title = 'o dossiê não abre nesta janela; troque o período';
        id.appendChild(t);
      }
      tr.appendChild(id);
      tr.appendChild(el('td', 'col-txt', c.area ?? ''));
      return tr;
    }

    function desenhar() {
      /* Dois recortes que se somam: o seletor de área do chassi e o texto
         digitado. Nenhum deles reordena — a ordem é sempre o nome. */
      const lista = todos.filter((c) => {
        if (escopoAtivo.area && c.area_id !== escopoAtivo.area) return false;
        return casa(c.id, termo) || casa(c.area, termo);
      });

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
      tabela.replaceChildren(cabecalho(COLUNAS, null, null, null), corpo);
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
