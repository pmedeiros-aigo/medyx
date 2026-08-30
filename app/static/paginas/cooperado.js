/* cooperado.js — a tela "Dossiê do cooperado" (espec §3), em /cooperado/{id}.
 *
 * A pergunta da página: "por que este caso existe, e o que o defende?"
 * Ordem de leitura: quem é (cabeçalho, cada número com o par da área ao lado)
 * → a leitura do caso, narrativa de cima a baixo (posição → origem →
 * consistência → concentração → variação excedente) → a evidência por
 * procedimento → os fatores de contexto que defendem o cooperado antes de
 * qualquer conversa. Vocabulário interno do método NÃO chega à tela
 * (decisão 2026-08-14): a regra mora nos hovers e na Nota Metodológica.
 *
 * Lê /api/cooperado/{id}. Nada é calculado aqui: números, frases e rótulos vêm
 * do motor; a régua da análise viaja na query e volta na proveniência.
 *
 * ── fronteira visual ────────────────────────────────────────────────────────
 * Nenhuma classe nova. `.stats` é a faixa do guia (§08), `.tbl/.tbl-hd/.tbl-band`
 * a moldura dos blocos, `.pctl/.ruler` a posição, `.spark` a série, `.tag`/`.pill`
 * as etiquetas e chips, `.note` as notas de método.
 */
'use strict';

import { buscar } from '../lib/api.js';
import { abrirPagina } from '../lib/pagina.js';
import { TELAS, rotaAtual } from '../lib/rotas.js';
import { abrirPainel } from '../blocos/painel-procedimento.js';
import { montarPareto } from '../blocos/pareto.js';
import { el, ordenar, cabecalho, ordemDaURL, gravarOrdem, proximaOrdem, moldura,
         celulaConsistencia, campoDeBusca, casa } from '../lib/tabelas.js';

/* O id vem do CAMINHO (`/cooperado/{id}`). A área NÃO viaja na URL: um
   cooperado pertence a uma área só, e o servidor a descobre pelo id — carregar
   `?area=` era um dado que ninguém validava e que podia mentir. */
const idCooperado = rotaAtual().cooperado;

/* ── blocos ────────────────────────────────────────────────────────────────── */

/** Cabeçalho: identidade + a faixa em que TODO número leva o par da área. */
function montarIdentidade(destino, d) {
  const topo = el('div', 'stack g6');
  const linha = el('div', 'row flexwrap');
  linha.appendChild(el('h2', null, d.cooperado.id));
  for (const sp of d.cooperado.sub_perfis ?? []) {
    const t = el('span', 'tag tag-attr', sp.rotulo);
    if (sp.ajuda) t.title = sp.ajuda;
    linha.appendChild(t);
  }
  if (d.cooperado.em_revisao) {
    const t = el('span', 'tag tag-caveat', d.cooperado.em_revisao.rotulo);
    if (d.cooperado.em_revisao.motivo) t.title = d.cooperado.em_revisao.motivo;
    linha.appendChild(t);
  }
  if (d.cooperado.avaliavel && !d.cooperado.forma_referencia) {
    const t = el('span', 'tag tag-off', 'não forma a referência');
    t.title = 'Avaliado contra a referência da área, sem integrar o cálculo dela.';
    linha.appendChild(t);
  }
  topo.appendChild(linha);

  /* Sem "voltar à área" aqui: a migalha da barra superior navega (a área é
     link a partir do dossiê), e dois caminhos para o mesmo lugar a 40px um do
     outro é ruído, não afordância. */
  topo.appendChild(el('span', 'sub', d.cooperado.area.titulo));
  if (d.justificativa?.resumo) topo.appendChild(el('span', 'sub', d.justificativa.resumo));
  destino.appendChild(topo);

  /* A MESMA faixa de KPIs da tela de Área (`.kpis`/`.kpi`), e não mais `.stats`.
     As duas telas mostravam a mesma coisa em dois pesos e dois tamanhos de
     número; o `.stats` era herança do guia antes de a faixa de KPIs existir.
     Os filhos já eram `.k`/`.v`/`.h`, que é o que o `.kpi` também usa, então a
     troca é de container, sem classe nova. O pontilhado de "tem hover" segue a
     mesma regra do bloco de cards: só onde há explicação para mostrar. */
  const faixa = el('div', 'kpis');
  for (const e of d.cabecalho ?? []) {
    const bloco = el('div', 'kpi');
    bloco.appendChild(el('span', 'k', e.rotulo));
    bloco.appendChild(el('span', 'v', e.valor_fmt));
    /* DOIS hovers, cada um no elemento que ele explica: o do valor diz o que a
       métrica mede; o da linha de baixo diz como a referência da área foi
       construída. Um hover só, no bloco inteiro, obrigava a mesma frase a
       responder duas perguntas. */
    if (e.titulo_longo) bloco.title = e.titulo_longo;
    const apoio = el('span', e.par_titulo ? 'h tem-hover' : 'h', e.par_fmt);
    if (e.par_titulo) apoio.title = e.par_titulo;
    bloco.appendChild(apoio);
    faixa.appendChild(bloco);
  }
  destino.appendChild(faixa);
}

/** Um item da leitura: rótulo pequeno em cima, conteúdo embaixo. */
function item(rotulo, conteudo) {
  const bloco = el('div', 'stack g4');
  bloco.appendChild(el('span', 'micro', rotulo));
  bloco.appendChild(conteudo);
  return bloco;
}

/** Leitura do caso: narrativa em seções, de cima a baixo, na ordem em que a
 *  pergunta se faz — onde ele está → o que puxa → o padrão se repete? → como
 *  se distribui nos pacientes → quanto é. O subtítulo do card é o CASO numa
 *  frase (redigida no motor), nunca a regra do método. */
function montarLeitura(destino, d) {
  const L = d.leitura;
  const cartao = el('div', 'tbl');
  const topo = el('div', 'tbl-hd');
  const titulo = el('div', 'stack g4');
  titulo.appendChild(el('span', 't', 'Leitura do caso'));
  if (L.frase) titulo.appendChild(el('span', 'sub', L.frase));
  topo.appendChild(titulo);
  cartao.appendChild(topo);

  const corpo = el('div', 'tbl-band');
  const pilha = el('div', 'stack g10');

  // 1 · posição na área: selo + tradução na mesma linha
  const pos = L.posicao ?? {};
  const cx = el('div', 'row');
  cx.appendChild(el('span', `pctl ${pos.classe ?? ''}`, pos.rotulo ?? ''));
  cx.appendChild(el('span', 'sub', pos.traducao ?? pos.indisponivel_motivo ?? ''));
  pilha.appendChild(item('Posição na área', cx));

  // 2 · origem do excedente: difusa/concentrada + o procedimento principal
  const or_ = L.origem_excedente;
  if (or_) {
    const co = el('div', 'stack g4');
    co.appendChild(el('span', null, or_.leitura ?? ''));
    if (or_.topo?.descricao) {
      co.appendChild(el('span', 'sub',
        `principal: ${or_.topo.descricao.trim()} (${or_.topo.razao_fmt} a referência, `
        + `${or_.topo.pct_fmt} do excedente dele)`));
    }
    pilha.appendChild(item('Origem do excedente', co));
  }

  // 3 · consistência: mini-série + direção
  const c = L.consistencia ?? {};
  const cc = el('div', 'row');
  if (c.trimestres?.length) {
    const caixa = el('div', 'sparkwrap');
    const barras = el('div', 'spark');
    const ALTURA_MAX = 26;
    for (const t of c.trimestres) {
      const i = document.createElement('i');
      if (t.estado === 'sinalizado') i.className = 'crit';
      i.style.height = `${Math.round((t.altura_rel ?? 0.12) * ALTURA_MAX)}px`;
      if (t.estado === 'nao_avaliavel') i.style.opacity = '.35';
      i.title = `${t.janela}º trimestre: ` + (
        t.estado === 'nao_avaliavel' ? t.motivo
          : `índice ${t.indice_fmt}${t.sinalizado ? ', algum procedimento acima do critério' : ''}`);
      barras.appendChild(i);
    }
    caixa.appendChild(barras);
    if (c.direcao) caixa.appendChild(el('span', `dir ${c.direcao.classe}`, c.direcao.seta));
    cc.appendChild(caixa);
    cc.appendChild(el('span', 'sub', c.direcao?.texto ?? c.rotulo ?? ''));
  } else {
    cc.appendChild(el('span', 'sub', c.motivo ?? 'sem medida'));
  }
  pilha.appendChild(item('Consistência entre trimestres', cc));

  // 4 · concentração por beneficiário: rotina/case-mix, com os números
  const conc = L.concentracao;
  if (conc?.rotulo) {
    const cn = el('span', null,
      conc.pct_carteira_fmt
        ? `${conc.rotulo} · ${conc.pct_carteira_fmt} da carteira recebe o `
          + `procedimento principal (pares: ${conc.pct_carteira_pares_fmt})`
        : conc.rotulo);
    cn.title = 'Leitura agregada por procedimento. Não há análise individual '
             + 'de beneficiário.';
    pilha.appendChild(item('Concentração por beneficiário', cn));
  }

  // 5 · variação excedente: solicitações · R$ em quarentena · piso
  const ex = L.excedente ?? {};
  const ce = el('div', 'stack g4');
  let textoEx = ex.motivo ? ex.itens_fmt
    : `${ex.itens_fmt} solicitações${ex.reais_fmt ? ` · ${ex.reais_fmt} (em quarentena)` : ''}`;
  if (!ex.motivo && ex.piso_fmt) textoEx += ` · piso: ${ex.piso_fmt}`;
  const linhaEx = el('span', null, textoEx);
  linhaEx.title = ex.motivo ?? (
    'R$ com preço interno derivado das contas, até a tabela oficial; o piso é o '
    + 'cenário conservador da reamostragem por paciente, somado nos procedimentos '
    + 'em que ela é possível');
  ce.appendChild(linhaEx);
  if (ex.pareto) {
    ce.appendChild(el('span', 'sub',
      `${ex.pareto.pct_do_total_fmt} do excedente da área · `
      + `${ex.pareto.posto}º de ${ex.pareto.total} cooperados`));
  }
  pilha.appendChild(item('Variação excedente', ce));

  corpo.appendChild(pilha);
  cartao.appendChild(corpo);
  destino.appendChild(cartao);
}

/* ── tabela de procedimentos ───────────────────────────────────────────────── */

/* Uma unidade por coluna, declarada UMA vez no cabeçalho: índice e referência
 * em solicitações POR MIL consultas. A cascata é do CASO, não do procedimento
 * — a coluna que a mostrava saiu; o piso de confiança, quando existe, é
 * sub-linha da própria variação excedente. */
/* AS COLUNAS (27/ago). A leitura vai da prática dele para o dinheiro, com a
   comparação no meio: quanto pediu · com que frequência · quanto os pares pedem
   · quantas vezes mais · que fatia da prática dele é · em quantos trimestres ·
   e só então o custo.

   Frequência e Referência na MESMA unidade (por consulta), porque a Razão entre
   elas é a divisão das duas: unidades diferentes fariam as três células se
   contradizerem na mesma linha.

   Largura: `col-num` nas oito de número, `col-txt` na consistência (é gráfico
   com texto, alinhado à esquerda como na tabela da área). */
const COLUNAS = [
  { nome: 'Procedimento', classe: 'col-txt' },
  { nome: 'Solicitações', direita: true, classe: 'col-num',
    def: 'Quantidade solicitada deste procedimento no período.',
    ordem: 'solicitacoes', valor: (l) => l.solicitacoes },
  { nome: 'Frequência', direita: true, classe: 'col-num',
    def: 'Solicitações deste procedimento por consulta atendida.',
    ordem: 'taxa', valor: (l) => l.taxa },
  { nome: 'Referência', direita: true, classe: 'col-num',
    def: 'Solicitações por consulta apuradas na área de atuação, para este '
       + 'mesmo procedimento. É a base de cálculo do custo excedente.' },
  { nome: 'Razão', direita: true, classe: 'col-num',
    def: 'Quantas vezes a frequência observada supera a referência da área.',
    ordem: 'razao', valor: (l) => l.razao },
  { nome: 'Proporção', direita: true, classe: 'col-num',
    def: 'Participação deste procedimento no total solicitado no período, '
       + 'em volume e não em valor.',
    ordem: 'proporcao', valor: (l) => l.proporcao },
  { nome: 'Consistência', classe: 'col-txt',
    def: 'Trimestres do período em que a frequência ficou acima do critério. '
       + 'Um quadrado por trimestre; preenchido indica trimestre acima.',
    ordem: 'consistencia', valor: (l) => l.persistencia?.n_sinalizado },
  { nome: 'Custo unitário', direita: true, classe: 'col-num',
    def: 'Valor unitário apurado nas contas do período. Preço interno '
       + 'provisório, ainda não homologado contra a tabela contratual.',
    ordem: 'custo_unitario', valor: (l) => l.custo_unitario },
  { nome: 'Custo total', direita: true, classe: 'col-num',
    def: 'Valor de tudo que foi solicitado deste procedimento no período. '
       + 'Mede o porte, não o desvio.',
    ordem: 'custo_total', valor: (l) => l.custo_total },
  { nome: 'Custo excedente', direita: true, classe: 'col-num',
    def: 'Valor das solicitações acima da referência da área. Indica '
       + 'oportunidade de revisão, não economia já realizada.',
    ordem: 'excedente', valor: (l) => l.excedente_itens },
];

function linhaProcedimento(l, semMedida = '', aoAbrir = null) {
  const tr = document.createElement('tr');
  if (l.sinalizado) tr.classList.add('acima');
  /* A linha inteira é o gatilho do painel — alvo grande, sem um botão a mais
     numa tabela de dez colunas. Teclado incluído: `tabIndex` + Enter/Espaço,
     porque linha clicável sem foco é linha que só existe para o mouse. */
  if (aoAbrir) {
    tr.classList.add('clicavel');
    tr.tabIndex = 0;
    tr.setAttribute('role', 'button');
    tr.setAttribute('aria-label', `Detalhar ${l.descricao}`);
    const acionar = () => aoAbrir(l);
    tr.addEventListener('click', acionar);
    tr.addEventListener('keydown', (ev) => {
      if (ev.key !== 'Enter' && ev.key !== ' ') return;
      ev.preventDefault();
      acionar();
    });
  }

  const nome = el('td', 'cell-name');
  nome.appendChild(document.createTextNode(l.codigo));
  const sub = el('span', 'cell-sub', l.descricao);
  sub.title = l.descricao;
  nome.appendChild(sub);

  /* CUSTO EXCEDENTE: o R$ é o número da coluna; a contagem de solicitações
     excedentes e o piso de confiança descem como sub-linha, que é onde a
     tabela da área também põe o que qualifica o número. */
  const exc = el('td', 'rt num', l.excedente_reais_fmt ?? semMedida);
  if (l.excedente_motivo) exc.title = l.excedente_motivo;
  if (!l.medido) exc.classList.add('val-ressalva');
  if (l.excedente_reais_fmt) {
    exc.title = 'Valorado a preços internos provisórios, apurados nas contas do '
              + 'período e ainda não homologados contra a tabela contratual.';
  }
  if (l.excedente_itens) {
    exc.appendChild(el('div', 'cell-sub', `${l.excedente_fmt} solicitações`));
  }
  if (l.confianca?.rotulo) {
    /* `div` e não `span`: `.cell-sub` só ganha display do contrato dentro de
       `.cell-name`; aqui a quebra de linha vem da própria tag de bloco, sem
       CSS novo nem estilo inline. */
    const piso = el('div', 'cell-sub', l.confianca.rotulo);
    piso.title = l.confianca.detalhe;
    exc.appendChild(piso);
  }

  /* MESMA célula de consistência da tabela da área (lib/tabelas.js): quadrados
     por trimestre, denominador por extenso. Aqui a série é DO PROCEDIMENTO. */
  const pers = celulaConsistencia({
    trimestres: l.trimestres,
    rotulo: l.persistencia?.rotulo ?? semMedida,
    janelas_sinalizado: l.persistencia?.n_sinalizado,
    janelas_avaliaveis: l.persistencia?.n_avaliaveis,
    motivo: !l.medido ? l.motivo_nao_medido
      : (l.persistencia && !l.persistencia.reportavel)
        ? 'janelas avaliáveis abaixo do mínimo: persistência não reportável' : null,
  });
  if (!l.medido) pers.classList.add('val-ressalva');

  /* SEM REFERÊNCIA NA ÁREA: as colunas que dependem de par vêm vazias e
     esmaecidas, com o motivo no title; as que não dependem (solicitações,
     frequência, proporção, custo unitário e total) vêm cheias. O procedimento
     continua listado — sumir com ele faria o leitor concluir que não existe, e
     no cooperado_85 seriam 11,8% do custo, incluindo o 2º maior gasto dele. */
  const semPar = (conteudo) => {
    const td = el('td', 'rt num', conteudo);
    if (!l.medido) {
      td.classList.add('val-ressalva');
      td.title = l.motivo_nao_medido ?? '';
    }
    return td;
  };

  tr.append(
    nome,
    el('td', 'rt num', l.solicitacoes_fmt),
    el('td', 'rt num', l.taxa_fmt),
    semPar(l.referencia_fmt),
    semPar(l.razao_fmt),
    el('td', 'rt num', l.proporcao_fmt),
    pers,
    el('td', 'rt num', l.custo_unitario_fmt),
    el('td', 'rt num', l.custo_total_fmt),
    exc,
  );
  return tr;
}

function montarCusto(destino, d) {
  const p = d.pareto_custo;
  if (!p?.eixos?.length) return;

  /* DOIS CHIPS que trocam o Pareto inteiro — não a ordenação. Num Pareto a
     barra, a ordem e o acumulado são a mesma grandeza; ordenar por um eixo
     desenhando o outro deixaria o acumulado somando uma coisa numa ordem
     ditada por outra. Mesmo componente de chip do recorte da tabela abaixo. */
  const faixa = el('div', 'row flexwrap');
  faixa.appendChild(el('span', 'micro', 'Eixo'));
  const botoes = new Map();
  const caixa = el('div', null);
  destino.appendChild(faixa);
  destino.appendChild(caixa);

  const bloco = montarPareto(caixa, p.dados[p.default], null, 'custo');
  let ativo = p.default;

  function aplicar(chave) {
    if (!p.dados[chave]) return;
    ativo = chave;
    for (const [k, b] of botoes) b.classList.toggle('pill-on', k === chave);
    bloco.atualizar(p.dados[chave]);
  }

  for (const e of p.eixos) {
    const b = el('span', 'pill', e.rotulo);
    b.tabIndex = 0;
    b.setAttribute('role', 'button');
    const acionar = () => aplicar(e.chave);
    b.addEventListener('click', acionar);
    b.addEventListener('keydown', (ev) => {
      if (ev.key !== 'Enter' && ev.key !== ' ') return;
      ev.preventDefault();
      acionar();
    });
    botoes.set(e.chave, b);
    faixa.appendChild(b);
  }
  aplicar(ativo);
}


function montarProcedimentos(destino, d) {
  const dados = d.procedimentos;
  let aoAbrirLinha = null;
  /* Sem par medido (área sem referência, cooperado abaixo do piso): o bloco
     declara o estado em vez de exibir moldura vazia. */
  if (!dados?.total_medidos) {
    const aviso = el('div', 'tbl');
    const t = el('div', 'tbl-hd');
    const tt = el('div', 'stack g4');
    tt.appendChild(el('span', 't', 'Procedimentos solicitados'));
    tt.appendChild(el('span', 'sub',
      'Não há procedimento com referência apurável nesta área de atuação. '
      + 'Valem as leituras descritivas acima.'));
    t.appendChild(tt);
    aviso.appendChild(t);
    destino.appendChild(aviso);
    return;
  }
  /* MESMA moldura da tabela da Área e da de Cooperados (lib/tabelas.js): esta
     estava sem `tbl-fixa`, e a coluna pulava a cada repintura. */
  const { quadro: cartao, topo, tabela, pe, peEstado } = moldura();
  const titulo = el('div', 'stack g4');
  titulo.appendChild(el('span', 't', 'Procedimentos solicitados'));
  titulo.appendChild(el('span', 'sub',
    'Todos os procedimentos solicitados no período. Onde a área não tem '
    + 'referência apurável, as colunas de comparação ficam sem medida.'));
  topo.appendChild(titulo);

  /* BUSCA: localiza dentro do recorte em cena, sem mudar número nenhum. */
  let termo = '';
  topo.appendChild(campoDeBusca({
    placeholder: 'Buscar por nome ou código',
    aoDigitar: (t) => { termo = t; aplicar(recorteAtivo); },
  }));

  // chips do recorte (espec regra 7): em revisão (default) · todos
  const faixa = el('div', 'row flexwrap');
  faixa.appendChild(el('span', 'micro', 'Recorte'));
  const RECORTES = [
    { chave: 'revisao', rotulo: 'Em revisão', n: dados.em_revisao,
      filtro: (l) => l.sinalizado },
    { chave: 'todos', rotulo: 'Todos', n: dados.total_medidos },
  ];
  const botoes = new Map();

  let { chave: ordemAtiva, direcao } = ordemDaURL(COLUNAS);
  let recorteAtivo = 'revisao';

  function alternarOrdem(chave) {
    ({ chave: ordemAtiva, direcao } = proximaOrdem(ordemAtiva, direcao, chave));
    gravarOrdem(ordemAtiva, direcao);
    aplicar(recorteAtivo);
  }

  function aplicar(chave) {
    const r = RECORTES.find((x) => x.chave === chave) ?? RECORTES[0];
    recorteAtivo = r.chave;
    for (const [k, b] of botoes) b.classList.toggle('pill-on', k === r.chave);
    let linhas = r.filtro ? dados.linhas.filter(r.filtro) : dados.linhas;
    /* A busca é o último filtro: localiza dentro do recorte, não o substitui. */
    if (termo) linhas = linhas.filter(
      (l) => casa(l.descricao, termo) || casa(l.codigo, termo));
    const coluna = COLUNAS.find((col) => col.ordem === ordemAtiva);
    const visiveis = ordenar(linhas, coluna, direcao);
    const corpo = document.createElement('tbody');
    for (const l of visiveis) {
      const tr = linhaProcedimento(l, dados.sem_medida,
                                   (linha) => aoAbrirLinha?.(linha, tr));
      corpo.appendChild(tr);
    }
    tabela.replaceChildren(cabecalho(COLUNAS, ordemAtiva, direcao, alternarOrdem), corpo);
    const dizOrdem = coluna
      ? `${coluna.nome.toLowerCase()}, ${direcao === 'asc' ? 'crescente' : 'decrescente'}`
      : `${dados.ordenado_por} (padrão)`;
    peEstado.textContent =
      `${visiveis.length} de ${dados.total_medidos} procedimentos solicitados`
      + ` · ${dados.sem_referencia} sem referência na área · `
      + `recorte: ${r.rotulo.toLowerCase()}`
      + (termo ? ` · busca: "${termo}"` : '')
      + ` · ordenado por ${dizOrdem}`;
  }

  for (const r of RECORTES) {
    const b = el('span', 'pill', r.rotulo);
    b.tabIndex = 0;
    b.appendChild(el('span', 'cnt', ` ${r.n}`));
    const acionar = () => aplicar(r.chave);
    b.addEventListener('click', acionar);
    b.addEventListener('keydown', (ev) => {
      if (ev.key !== 'Enter' && ev.key !== ' ') return;
      ev.preventDefault();
      acionar();
    });
    botoes.set(r.chave, b);
    faixa.appendChild(b);
  }

  /* O painel é DRAWER ancorado na viewport, fora do fluxo da página: painel no
     fluxo tem altura de conteúdo e a tabela tem altura de linhas, e as duas
     nunca coincidem. Ele mora no <body> e o conteúdo cede margem (`com-painel`)
     em vez de ser coberto — a tabela continua inteira e clicável, que é a razão
     de ser painel e não modal. */
  const colPainel = el('aside', 'painel-lateral');
  colPainel.hidden = true;
  colPainel.setAttribute('role', 'complementary');
  colPainel.setAttribute('aria-label', 'Detalhe do procedimento');
  document.body.appendChild(colPainel);
  const conteudoEl = document.querySelector('.content');

  let aberto = null;
  function fechar() {
    aberto = null;
    colPainel.hidden = true;
    colPainel.replaceChildren();
    conteudoEl?.classList.remove('com-painel');
    for (const tr of tabela.querySelectorAll('tr.selecionada')) {
      tr.classList.remove('selecionada');
    }
  }
  function abrir(linha, tr) {
    /* Clicar de novo na linha aberta fecha: o mesmo gesto desfaz o que fez. */
    if (aberto === linha.codigo) { fechar(); return; }
    aberto = linha.codigo;
    for (const outra of tabela.querySelectorAll('tr.selecionada')) {
      outra.classList.remove('selecionada');
    }
    tr?.classList.add('selecionada');
    conteudoEl?.classList.add('com-painel');
    abrirPainel(colPainel, d.cooperado.id, linha, fechar);
  }
  aoAbrirLinha = (linha, tr) => abrir(linha, tr);

  /* Esc fecha — convenção de qualquer superfície sobreposta, e aqui é a única
     alternativa ao botão quando o foco está na tabela.
     Sem desmontagem: trocar de tela é `location.href`, ou seja, carregamento
     inteiro (o `replaceState` do app só grava filtro na URL, não navega). O
     ouvinte e o drawer morrem com o documento. */
  document.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape' && aberto) fechar();
  });

  destino.appendChild(faixa);
  destino.appendChild(cartao);
  aplicar('revisao');
}

/** Fatores de contexto: defendem o cooperado ANTES da conversa. */
function montarContexto(destino, d) {
  const itens = d.contexto ?? [];
  if (!itens.length) return;
  const cartao = el('div', 'tbl');
  const topo = el('div', 'tbl-hd');
  const titulo = el('div', 'stack g4');
  titulo.appendChild(el('span', 't', 'Fatores de contexto'));
  titulo.appendChild(el('span', 'sub',
    'não alteram nenhum número: dizem com que lente investigar antes de concluir'));
  topo.appendChild(titulo);
  cartao.appendChild(topo);
  const corpo = el('div', 'tbl-band');
  const linha = el('div', 'row flexwrap');
  for (const c of itens) {
    const t = el('span', c.alerta ? 'tag tag-read' : 'tag tag-attr',
      `${c.rotulo}: ${c.valor_fmt}`);
    if (c.alerta) t.prepend(el('i', 'mk'));
    if (c.ajuda) t.title = c.ajuda;
    linha.appendChild(t);
  }
  corpo.appendChild(linha);
  cartao.appendChild(corpo);
  destino.appendChild(cartao);
}

/* ── montagem ──────────────────────────────────────────────────────────────── */

await abrirPagina({
  titulo: `Dossiê · ${idCooperado}`,
  /* Trocar a área aqui leva à ÁREA escolhida: um cooperado pertence a uma área
     só, então seguir para "o dossiê dele em outra área" não existe. */
  aoTrocarArea: (id) => TELAS.area.caminho(id),
  montar: async ({ conteudo, definirArea }) => {
    const d = await buscar(`/api/cooperado/${encodeURIComponent(idCooperado)}`,
                           { anunciarEm: conteudo, rotulo: 'carregando o dossiê…' });
    /* A área do caso só se sabe agora: o chassi corrige o seletor, a migalha e
       os links da navegação. */
    definirArea(d.cooperado?.area?.id);

    montarIdentidade(conteudo, d);
    montarLeitura(conteudo, d);
    /* ONDE ESTÁ O DINHEIRO, antes da tabela: a tabela responde "como ele se
       compara em cada procedimento", e essa pergunta só faz sentido depois de
       saber quais procedimentos importam. O mesmo `montarPareto` da tela de
       Área — aqui as barras vêm com o nível de excesso dentro. */
    montarCusto(conteudo, d);
    montarProcedimentos(conteudo, d);
    montarContexto(conteudo, d);

    if (d.proveniencia?.carimbo) {
      conteudo.appendChild(el('span', 'note', d.proveniencia.carimbo));
    }
  },
});
