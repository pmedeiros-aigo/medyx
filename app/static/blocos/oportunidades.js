/* blocos/oportunidades.js — os maiores custos excedentes por par, na tela.
 *
 * É o degrau que faltava na tela de Área. O guia de produto (§9) lista cinco
 * perguntas que toda página deve responder, e esta respondia quatro: o que está
 * acontecendo (a Leitura), por que (os gráficos), onde (as tabelas) e o que
 * investigar (as gavetas). Parava antes de "o que fazer agora".
 *
 * ── por que uma TABELA ─────────────────────────────────────────────────────
 * A página já fala uma língua para "lista ordenada de coisas com números", e é
 * a tabela: moldura comum, cabeçalho com a definição em cada coluna, números
 * tabulares à direita, linha clicável e chevron para o dossiê. A primeira
 * versão deste bloco usou a entrada da gaveta lateral, que é um cartão de
 * leitura vertical, e o resultado destoava de tudo em volta — tipografia
 * diferente, linhas altas demais, e três fatos empilhados por caso onde a
 * página inteira usa colunas.
 *
 * As COLUNAS são as das outras duas tabelas, com os mesmos nomes e as mesmas
 * definições (DIRETRIZES §5): Procedimento, Frequência, Referência e Razão vêm
 * da tabela do dossiê; Cooperado, Consultas, Excesso de solicitações e Excesso
 * em R$ vêm da tabela de cooperados. Nenhum rótulo novo entra por aqui.
 *
 * ── por que não é aba ──────────────────────────────────────────────────────
 * As duas abas da página são duas LENTES do mesmo conjunto, e o leitor escolhe
 * por qual eixo olhar. Este bloco não é uma terceira lente: é a conclusão
 * tirada das duas. Como aba, ficaria atrás de um clique e no mesmo nível de
 * duas perguntas que ele responde.
 *
 * Nada é calculado aqui. O bloco segue o recorte, como os demais achados.
 */
'use strict';

import { el, moldura, cabecalho } from '../lib/tabelas.js';
import { colapsavel } from '../lib/colapsar.js';

/* CADA COLUNA ARGUMENTA A OPORTUNIDADE, e é só isso que entra.
 *
 * A primeira versão trazia Consultas, Frequência e Referência ao lado da Razão,
 * copiadas da tabela do dossiê. Lá elas são o diagnóstico de um cooperado, e a
 * tela inteira é sobre ele; aqui a pergunta é outra — vale trabalhar este caso?
 * —, e três colunas para reconstruir uma divisão que a quarta já entrega faziam
 * o bloco ler como uma quarta tabela da mesma família.
 *
 * O que sobrou responde a pergunta em três passos:
 *   Razão                    quanto está fora do padrão da área
 *   Excesso de solicitações  quanto disso é volume
 *   Excesso em R$            quanto vale, e é por ele que a lista está ordenada
 *   % do excedente da área   quanto ESTE caso move do problema inteiro
 *
 * A última é a que separa este bloco de mais uma lista ordenada: R$ 47 mil não
 * diz por si se vale uma conversa, 1,1% do excedente da área diz.
 *
 * Frequência, referência e o denominador não sumiram: viajam na leitura da
 * célula da Razão, a um hover de distância. O guia pede que o denominador esteja
 * ALCANÇÁVEL no momento da leitura (§13), não que ocupe coluna própria.
 *
 * Sem ordenação: a lista JÁ é a ordem por custo excedente, e é ela que define
 * quais casos entram. Uma seta no cabeçalho prometeria reordenar um conjunto
 * que foi escolhido por essa ordem. */
const COLUNAS = [
  { nome: 'Cooperado', classe: 'col-id' },
  { nome: 'Procedimento', classe: 'col-txt-lg col-corta' },
  { nome: 'Razão', direita: true, classe: 'col-num',
    def: 'Quantas vezes a frequência observada supera a referência da área. '
       + 'A frequência, a referência e o volume de consultas de cada caso estão '
       + 'na leitura da célula.' },
  { nome: 'Excesso de solicitações', direita: true, classe: 'col-num-lg',
    def: 'Solicitações a mais que a referência da área, no volume de consultas '
       + 'do cooperado.' },
  { nome: 'Excesso em R$', direita: true, classe: 'col-num-md',
    def: 'As mesmas solicitações excedentes valoradas a preços de referência '
       + 'internos derivados das contas do período.' },
  { nome: '% do excedente da área', direita: true, classe: 'col-num-md',
    def: 'Quanto este caso representa do custo excedente de toda a área no '
       + 'mesmo recorte.' },
  /* Coluna de AÇÃO: sem nome, sem ordenação, largura só do alvo de toque. É a
     segunda afordância para o dossiê, a primeira é o nome como link. */
  { nome: '', classe: 'col-chev' },
];


/** O link para o dossiê, na mesma forma nas duas pontas da linha. */
function paraODossie(id, href, texto, classe) {
  const a = document.createElement('a');
  if (classe) a.className = classe;
  a.href = href;
  a.textContent = texto;
  a.title = 'Abrir o dossiê analítico deste cooperado.';
  /* O nome e o chevron levam ao dossiê; a LINHA abre o procedimento na área.
     São dois destinos na mesma linha, e o clique no link não pode disparar os
     dois. */
  a.addEventListener('click', (ev) => ev.stopPropagation());
  return a;
}


/** Uma linha: o par, a régua dele e as duas magnitudes. */
function linha(l, aoAbrir, hrefDoCooperado, comArea) {
  const tr = el('tr');
  tr.dataset.coop = l.id;
  tr.dataset.codigo = l.codigo;

  const id = el('td', 'col-id');
  if (hrefDoCooperado) {
    id.appendChild(paraODossie(l.id, hrefDoCooperado(l.id), l.id));
  } else {
    id.textContent = l.id;
  }
  tr.appendChild(id);

  if (comArea) {
    const area = el('td', 'col-txt col-corta', l.area ?? '');
    area.title = l.area ?? '';
    tr.appendChild(area);
  }

  /* `col-corta` na CÉLULA, e não só no cabeçalho: com `table-layout:fixed` é o
     cabeçalho que fixa a largura, mas quem trunca é a célula. */
  const proc = el('td', 'col-txt-lg col-corta', l.descricao);
  proc.title = `${l.descricao} · código ${l.codigo}`;
  tr.appendChild(proc);

  /* `rt num`, como toda célula numérica do app: alinhada à direita, sob um
     cabeçalho que também está, e em algarismo tabular para as casas decimais
     ficarem uma embaixo da outra ao longo da coluna. */
  const razao = el('td', 'rt num col-num', l.razao_fmt);
  /* A LEITURA DA RAZÃO carrega o que saiu das colunas: a frequência dele, o
     denominador que a sustenta e a referência contra a qual ela é medida. Vem
     redigida do motor, como todo texto do app. */
  if (l.leitura_razao) razao.title = l.leitura_razao;
  tr.appendChild(razao);
  for (const [classe, texto] of [
    ['col-num-lg', l.excedente_itens_fmt], ['col-num-md', l.excedente_reais_fmt],
    ['col-num-md', l.fracao_area_fmt],
  ]) tr.appendChild(el('td', `rt num ${classe}`, texto));

  const acao = el('td', 'col-chev');
  if (hrefDoCooperado) {
    const chev = paraODossie(l.id, hrefDoCooperado(l.id), '›', 'chev');
    chev.setAttribute('aria-label', `abrir dossiê analítico de ${l.id}`);
    acao.appendChild(chev);
  }
  tr.appendChild(acao);

  if (aoAbrir) {
    tr.classList.add('clicavel');
    tr.tabIndex = 0;
    tr.setAttribute('aria-label',
                    `abrir ${l.descricao} na área, com ${l.id} em destaque`);
    const acionar = () => aoAbrir(l.codigo, l.id);
    tr.addEventListener('click', acionar);
    tr.addEventListener('keydown', (ev) => {
      if (ev.key !== 'Enter' && ev.key !== ' ') return;
      ev.preventDefault();
      acionar();
    });
  }
  return tr;
}


/**
 * Monta o bloco dentro de `destino` e devolve como atualizá-lo no recorte.
 *
 * A tabela nasce mesmo quando o recorte não deixa nenhum caso qualificado, e
 * declara isso: sumir calado deixaria o leitor sem saber se a área está sem
 * variação ou se a tela falhou (DIRETRIZES §16). Área sem critério de revisão
 * não chega aqui, porque o motor devolve `null` e a página não monta o bloco.
 *
 * @param {HTMLElement} destino
 * @param {object} dados  resposta de /api/area/{id}
 * @param {(codigo: string, coop: string) => void} [aoAbrir]  abre o painel do
 *        procedimento com o cooperado em destaque
 * @param {(id: string) => string} [hrefDoCooperado]  destino do nome e do chevron
 * @returns {{atualizar: (o: object|null) => void} | null}
 */
export function montarOportunidades(destino, dados, aoAbrir, hrefDoCooperado) {
  if (!dados?.oportunidades) return null;

  const { quadro, topo, tabela, pe, peEstado } = moldura();
  /* Sem `tbl-fill`: a altura máxima pela janela serve às tabelas que são o
     corpo da página. Esta tem cinco linhas por padrão e vive acima das abas. */
  quadro.classList.remove('tbl-fill');
  /* Gancho de identidade: é a única tabela da página que vive FORA das abas, e
     sem um nome próprio qualquer contagem de `tbody tr` na tela passa a somar
     as linhas dela com as da tabela de cooperados. */
  quadro.classList.add('tbl-oportunidades');
  const titulo = el('div', 'stack g4');
  const rotulo = el('span', 't');
  const sub = el('span', 'sub');
  titulo.append(rotulo, sub);
  topo.appendChild(titulo);
  /* `hd-ctl` é só posicionamento: encosta o resumo à direita e cede o canto
     ao botão de recolher, que entra depois. Sem ele, o cabeçalho tem três
     filhos e o `space-between` joga o resumo para o meio. */
  const resumo = el('span', 'sub hd-ctl');
  /* Guardado fora do `atualizar` porque o link de revelar precisa alternar as
     duas frases, e as duas vêm PRONTAS do motor: o navegador troca o texto, não
     recalcula soma nenhuma. */
  const frases = { fechado: '', aberto: '' };
  topo.appendChild(resumo);

  const corpo = document.createElement('tbody');
  /* O RÓTULO DA COLUNA DE FATIA vem do motor: ele diz de que total a fração é,
     e o total muda com a tela — a área, na tela de Área; a especialidade, no
     Panorama. Coluna que diz "da área" numa soma da especialidade aponta o
     percentual para o conjunto errado. */
  const colunas = COLUNAS.map((c) => (
    c.nome.startsWith('% do excedente') && dados.oportunidades.rotulo_fracao
      ? { ...c, nome: dados.oportunidades.rotulo_fracao }
      : c));
  /* A ÁREA entra como coluna só quando há mais de uma em cena. É a régua contra
     a qual cada linha foi medida, e sem ela uma lista que cruza áreas não diz
     de onde vem o excedente de cada caso. Na tela de Área ela seria a mesma
     palavra repetida em todas as linhas. */
  const comArea = Boolean(dados.oportunidades.mostrar_area);
  if (comArea) {
    colunas.splice(1, 0, {
      nome: 'Área de atuação', classe: 'col-txt',
      def: 'Área de atuação do cooperado. É a referência contra a qual o '
         + 'excesso deste caso foi medido.',
    });
  }
  tabela.append(cabecalho(colunas), corpo);
  const acoes = el('span', 'opo-acao');
  pe.appendChild(acoes);
  destino.appendChild(quadro);

  function atualizar(o) {
    rotulo.textContent = o?.titulo ?? 'Principais oportunidades';
    sub.textContent = o?.subtitulo ?? '';
    frases.fechado = o?.resumo ?? '';
    frases.aberto = o?.resumo_todos ?? frases.fechado;
    resumo.textContent = frases.fechado;
    resumo.title = o?.resumo_titulo ?? '';
    resumo.hidden = !frases.fechado;
    acoes.replaceChildren();

    if (!o?.linhas?.length) {
      corpo.replaceChildren();
      peEstado.replaceChildren(
        el('span', null, 'Nenhum caso qualificado neste recorte.'));
      return;
    }

    const linhas = o.linhas.map((l) => linha(l, aoAbrir, hrefDoCooperado, comArea));
    linhas.forEach((tr, i) => { if (i >= o.n_visiveis) tr.hidden = true; });
    corpo.replaceChildren(...linhas);

    /* O RODAPÉ carrega o que vale para TODAS as linhas: a regra que define caso
       qualificado e, quando existe, a ressalva de preço com a contagem. Dito
       uma vez, e não repetido em cada linha, que era o que fazia a versão
       anterior gastar três linhas de texto por caso sem separar um do outro. */
    peEstado.replaceChildren(
      ...(o.notas ?? []).map((n) => el('span', 'opo-nota', n)));

    /* O RESTO é adiado, não escondido (§10). Link com alternância, a mesma
       marcação de "ver os 6 fora da referência": é a convenção do app para
       revelar uma lista sem sair de onde se está, e ela volta a fechar. */
    if (o.resto) {
      const link = document.createElement('a');
      link.href = '#';
      const fechado = `Ver mais ${o.resto} casos`;
      link.textContent = fechado;
      link.addEventListener('click', (ev) => {
        ev.preventDefault();
        const abrindo = link.dataset.aberto !== 'sim';
        linhas.forEach((tr, i) => {
          if (i >= o.n_visiveis) tr.hidden = !abrindo;
        });
        link.dataset.aberto = abrindo ? 'sim' : 'nao';
        link.textContent = abrindo ? `Mostrar só os ${o.n_visiveis} maiores`
                                   : fechado;
        /* O CABEÇALHO ACOMPANHA a lista: ele soma o custo excedente do que está
           em cena, e continuar falando de cinco casos com vinte na tela seria a
           frase descrevendo outra coisa que a tabela abaixo. */
        resumo.textContent = abrindo ? frases.aberto : frases.fechado;
      });
      acoes.appendChild(link);
    }
  }

  atualizar(dados.oportunidades);
  /* Recolhível DEPOIS de montado, como os demais cartões da página: quem não
     trabalha por esta lista fecha uma vez e a página lembra. */
  colapsavel(quadro, 'oportunidades');
  return { atualizar };
}
