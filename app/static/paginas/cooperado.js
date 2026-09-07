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
import { TELAS, comRegua, rotaAtual } from '../lib/rotas.js';
import { abrirPainel } from '../blocos/painel-procedimento.js';
import { montarEvolucao } from '../blocos/evolucao.js';
import { montarPareto } from '../blocos/pareto.js';
import { montarResumoDoCaso } from '../blocos/resumo-caso.js';
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

  /* UMA linha de contexto, não duas. A área tinha linha própria e reaparecia
     em seguida dentro de "Comparado com: Ginecologia · n=63 comparáveis";
     agora ela abre a linha da justificativa, que já diz contra quem e sobre que
     base o caso é medido. O método por extenso fica no hover. */
  const resumo = d.justificativa?.resumo ?? d.cooperado.area?.titulo ?? '';
  const contexto = el('span', 'sub');
  if (d.justificativa?.resumo_detalhe) {
    contexto.title = d.justificativa.resumo_detalhe;
  }

  /* A ÁREA VIRA LINK, e é o único caminho de volta ao grupo (set/2026). Ela
     esteve na migalha, e por isso o cabeçalho não precisava de um "voltar à
     área": dois caminhos para o mesmo lugar a 40px um do outro seria ruído.
     A migalha agora é `Cooperados › cooperado_85`, coleção e item, e a área
     saiu de lá — ela é fato ANALÍTICO, não degrau de navegação. Sem este link,
     o dossiê ficaria sem nenhuma porta para o grupo contra o qual ele é medido.

     A linha é PROSA montada em `apresentacao.py` ("Ginecologia · 63 cooperados
     comparáveis · …"), e o front não decompõe frase do motor. Por isso só o
     PREFIXO vira link, e só quando ele é exatamente o título da área; se a
     frase mudar de forma lá, isto cai em texto puro e nada quebra. */
  const area = d.cooperado.area;
  if (area?.id && resumo.startsWith(area.titulo)) {
    const link = el('a', null, area.titulo);
    link.href = comRegua(TELAS.area.caminho(area.id));
    link.title = `Abrir ${area.titulo}, o grupo contra o qual este caso é medido.`;
    contexto.append(link, resumo.slice(area.titulo.length));
  } else {
    contexto.textContent = resumo;
  }
  topo.appendChild(contexto);
  destino.appendChild(topo);

  /* A FAIXA DE SETE KPIs saiu daqui (set/2026) e virou o bloco "Leitura do
     caso" (`blocos/resumo-caso.js`), logo abaixo. Ela dava aos sete números o
     mesmo peso e nenhuma relação entre eles; os mesmos números agora chegam
     agrupados pela pergunta que respondem, e com a carteira atendida ao lado.
     Nada foi recalculado: `cabecalho` continua sendo a fonte, e o motor só o
     agrupa em `resumo_do_caso`. */
}

/* O CARTÃO "Leitura do caso" NARRATIVO saiu daqui (set/2026), junto com o
   utilitário `item()` que só ele usava. Ele repetia, palavra por palavra, o
   subtítulo do bloco de resumo logo acima, e trazia de novo a posição, a origem
   do excedente e o lugar no Pareto. Dois cartões com o mesmo título e o mesmo
   conteúdo, a um scroll um do outro.

   O que ele mostrava e NENHUMA outra superfície do dossiê mostra hoje:
     · os quadrados de consistência entre trimestres, com a direção da série;
     · a concentração por beneficiário no agregado ("49% da carteira recebe o
       procedimento principal");
     · o EXCESSO DE SOLICITAÇÕES (o número de itens; o de R$ está no resumo);
     · a linha "maior volume: <exame> (40,1× a referência)".
   Os dados continuam no payload (`leitura`), intocados: o que saiu foi o
   desenho. Reintroduzir qualquer um deles é escolher onde ele mora. */

/* AS COLUNAS da tabela de procedimentos: nome, definição para o hover do
   cabeçalho, e a chave de ordenação com o valor que a ordena. A ordem desta
   lista É a ordem das células em `linhaProcedimento`, e as duas têm de andar
   juntas.

   Coluna sem `ordem` não é ordenável (Referência é a mesma para todas as linhas
   de um mesmo exame, ordenar por ela não diz nada). */
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
    def: 'Valor unitário apurado nas contas do período, a preços de referência '
       + 'internos.',
    ordem: 'custo_unitario', valor: (l) => l.custo_unitario },
  { nome: 'Custo total', direita: true, classe: 'col-num',
    def: 'Valor de tudo que foi solicitado deste procedimento no período. '
       + 'Mede o porte, não o desvio.',
    ordem: 'custo_total', valor: (l) => l.custo_total },
  /* ORDENA POR `excedente_reais`, o número em R$ que a célula mostra, e não
     por `excedente_itens`: a coluna dizia "Custo excedente" e ordenava por
     solicitações, então o topo da ordem decrescente não era o de maior custo. */
  { nome: 'Custo excedente', direita: true, classe: 'col-num',
    def: 'Valor das solicitações acima da referência da área, apurado procedimento a '
       + 'procedimento contra a referência de cada um.',
    ordem: 'excedente_reais', valor: (l) => l.excedente_reais },
];


function linhaProcedimento(l, semMedida = '', aoAbrir = null) {
  const tr = document.createElement('tr');
  /* o código na linha é o que deixa o Pareto encontrar a linha da tabela sem
     que os dois blocos precisem conversar por índice */
  tr.dataset.cd = l.codigo;
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

  /* CUSTO EXCEDENTE: só o R$, e nada de sub-linha (set/2026).
     Havia duas embaixo dele. A primeira dizia "993 solicitações", que é a
     contagem EXCEDENTE, na mesma linha em que a coluna Solicitações dizia
     1.036, que é o total pedido. Dois números com a mesma palavra na mesma
     linha, e o leitor concluía que a tabela se contradizia. A segunda,
     "943 de 993 se sustentam", pendurava-se na primeira e ficava sem
     antecedente sozinha.
     As duas viraram HOVER, junto da ressalva de preço: quem quer a decomposição
     alcança, e a coluna volta a ter um número só. */
  const exc = el('td', 'rt num', l.excedente_reais_fmt ?? semMedida);
  if (l.excedente_motivo) exc.title = l.excedente_motivo;
  if (!l.medido) exc.classList.add('val-ressalva');
  if (l.excedente_reais_fmt) {
    exc.title = [
      'Valorado a preços internos provisórios, apurados nas contas do período '
      + 'e ainda não homologados contra a tabela contratual.',
      l.excedente_itens && `${l.excedente_fmt} das solicitações estão acima da `
        + 'referência da área.',
      l.confianca?.detalhe,
    ].filter(Boolean).join(' ');
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

function montarCusto(destino, d, aoEscolher) {
  /* O MESMO bloco da tela de Área, com o mesmo payload: barra aninhada (custo
     total em cinza, excedente dentro dele), "Ordenar por" no cabeçalho e as
     duas ordens já calculadas pelo motor.
     Sumiram daqui os chips "Eixo", que faziam à mão o que o envelope de ordens
     do `montarPareto` faz sozinho, e sumiu a segunda gramática de barra: eram
     dois Paretos de tinta única, e o leitor tinha de reaprender a barra ao
     descer da área para o dossiê. */
  if (d.pareto_custo) montarPareto(destino, d.pareto_custo, aoEscolher, 'custo');
}


function montarProcedimentos(destino, d) {
  const dados = d.procedimentos;
  let aoAbrirLinha = null;
  let abrirPorCodigo = null;
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
    /* A ORDEM só é declarada quando o leitor a ESCOLHEU. No padrão ela dizia
       "ordenado por variação excedente (padrão)", que é a mesma informação que
       o cabeçalho da coluna já dá com a seta, e alongava o rodapé com a
       descrição de um estado que ninguém mudou. Escolhida, ela fica: aí é
       resposta a "por que esta linha está no topo". */
    peEstado.textContent =
      `${visiveis.length} de ${dados.total_medidos} procedimentos solicitados`
      + ` · ${dados.sem_referencia} sem referência na área · `
      + `recorte: ${r.rotulo.toLowerCase()}`
      + (termo ? ` · busca: "${termo}"` : '')
      + (coluna ? ` · ordenado por ${coluna.nome.toLowerCase()}, `
                  + `${direcao === 'asc' ? 'crescente' : 'decrescente'}` : '');
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

  /* GAVETA SOBRE A PÁGINA, com cortina, igual à de "fora da referência" da tela
     de Área (2026-09-06). Ela continua ancorada na viewport e morando no
     <body>, pelo motivo de sempre: painel no fluxo tem altura de conteúdo e a
     tabela tem altura de linhas, e as duas nunca coincidem.
     O que mudou é que o conteúdo NÃO cede mais margem (`com-painel`). Antes a
     página inteira andava para a esquerda a cada clique: a tabela continuava
     clicável, mas ao custo de refluir tudo e de a leitura se mexer debaixo do
     cursor. Uma superfície sobreposta, um comportamento só no app. */
  /* A régua viaja no link, como em toda navegação do app; a aba e o exame são
     o que o DESTINO precisa, e vão por `extras` — montar query à mão aqui foi o
     que produziu o endereço com dois `?`. O código do exame entra na hora de
     abrir, porque só ali se sabe qual linha foi clicada. */
  const areaId = d.cooperado?.area?.id;
  const hrefDaArea = (codigo) => (areaId
    ? comRegua(TELAS.area.caminho(areaId), { aba: 'procedimentos', qp: codigo })
    : null);

  const scrim = el('span', 'scrim scrim-dim');
  document.body.appendChild(scrim);
  const colPainel = el('aside', 'painel-lateral pnl-modal');
  colPainel.hidden = true;
  colPainel.setAttribute('role', 'dialog');
  colPainel.setAttribute('aria-modal', 'true');
  colPainel.setAttribute('aria-label', 'Detalhe do procedimento');
  document.body.appendChild(colPainel);

  let aberto = null;
  function fechar() {
    aberto = null;
    colPainel.hidden = true;
    colPainel.replaceChildren();
    scrim.classList.remove('on');
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
    scrim.classList.add('on');
    /* O link leva o CÓDIGO do exame: "ver na área de atuação" tem de abrir a
       área JÁ neste procedimento, senão o leitor cai numa lista de centenas e a
       promessa do rótulo não é cumprida. */
    abrirPainel(colPainel, d.cooperado.id, linha, fechar, hrefDaArea(linha.codigo));
  }
  aoAbrirLinha = (linha, tr) => abrir(linha, tr);

  /* A MESMA porta, pelo outro lado: uma linha do Pareto conhece o código do
     procedimento, não a linha da tabela. Aqui o código vira linha, e a seleção
     só é marcada quando a linha está em cena — o Pareto lista os 251 com custo
     e a tabela abre no recorte "em revisão", então clicar numa barra que não
     está na tabela tem de abrir o painel do mesmo jeito. */
  abrirPorCodigo = (codigo) => {
    const linha = (dados.linhas ?? []).find((l) => String(l.codigo) === String(codigo));
    if (!linha) return;
    const tr = tabela.querySelector(`tr[data-cd="${CSS.escape(String(codigo))}"]`);
    abrir(linha, tr);
    if (!tr) colPainel.scrollIntoView({ block: 'nearest' });
  };

  /* Esc fecha — convenção de qualquer superfície sobreposta, e aqui é a única
     alternativa ao botão quando o foco está na tabela.
     Sem desmontagem: trocar de tela é `location.href`, ou seja, carregamento
     inteiro (o `replaceState` do app só grava filtro na URL, não navega). O
     ouvinte e o drawer morrem com o documento. */
  document.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape' && aberto) fechar();
  });
  scrim.addEventListener('click', fechar);

  destino.appendChild(faixa);
  destino.appendChild(cartao);
  aplicar('revisao');
  return { abrirPorCodigo: (cd) => abrirPorCodigo?.(cd) };
}

/* `montarContexto` saiu daqui (set/2026): os fatores viraram a faixa que fecha
   o bloco "Leitura do caso" (`blocos/resumo-caso.js`), onde eles são a última
   pergunta antes de concluir. Como cartão próprio no fim da página, ficavam
   depois de toda a evidência que eles qualificam. Os dados são os mesmos
   (`d.contexto`, de `blocos.contexto_do_cooperado`). */

/* ── montagem ──────────────────────────────────────────────────────────────── */

await abrirPagina({
  titulo: `Dossiê · ${idCooperado}`,
  /* Trocar a área aqui leva à ÁREA escolhida: um cooperado pertence a uma área
     só, então seguir para "o dossiê dele em outra área" não existe. */
  aoTrocarArea: (id) => TELAS.area.caminho(id),
  montar: async ({ conteudo, definirArea }) => {
    const d = await buscar(`/api/cooperado/${encodeURIComponent(idCooperado)}`,
                           { anunciarEm: conteudo, rotulo: 'Calculando' });
    /* A área do caso só se sabe agora: o chassi corrige o seletor, a migalha e
       os links da navegação. */
    definirArea(d.cooperado?.area?.id);

    montarIdentidade(conteudo, d);
    montarResumoDoCaso(conteudo, d);
    /* ONDE ESTÁ O DINHEIRO, antes da tabela: a tabela responde "como ele se
       compara em cada procedimento", e essa pergunta só faz sentido depois de
       saber quais procedimentos importam. O mesmo `montarPareto` da tela de
       Área — aqui as barras vêm com o nível de excesso dentro. */
    /* ANTES do Pareto: ele responde "em que procedimento está o dinheiro", e a
       pergunta anterior é se o caso está estável ou piorando. Quem já sabe que
       o excedente cresceu lê o Pareto procurando o que cresceu. */
    montarEvolucao(conteudo, d.evolucao);
    /* O Pareto é montado ANTES da tabela, mas quem sabe abrir o painel é a
       tabela. O gancho fica numa referência mutável: o clique só pode acontecer
       depois que a página inteira montou, e aí ela já está preenchida. */
    const procs = { abrir: null };
    montarCusto(conteudo, d, (cd) => procs.abrir?.(cd));
    procs.abrir = montarProcedimentos(conteudo, d)?.abrirPorCodigo;

    if (d.proveniencia?.carimbo) {
      conteudo.appendChild(el('span', 'note', d.proveniencia.carimbo));
    }
  },
});
