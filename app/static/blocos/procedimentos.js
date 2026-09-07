/* procedimentos.js — a aba Procedimentos do bloco de trabalho.
 *
 * Mesma pergunta da aba Cooperados, outra unidade de análise: em vez de "quem
 * está fora", "em QUE a área varia". A régua é a mesma — o cabeçalho do bloco,
 * a barra de composição, os chips e o gráfico continuam valendo, e por isso não
 * são redesenhados aqui.
 *
 * Duas leituras, e a ordenação escolhe entre elas:
 *   · por VARIAÇÃO EXCEDENTE (padrão) é o Pareto — onde está a massa do problema;
 *   · por PREVALÊNCIA é a rotina da área — o que quase todo mundo pede.
 * Um procedimento raro pode dominar o excedente, e um universal pode não
 * aparecer nele. São perguntas diferentes sobre a mesma lista.
 *
 * Dados de /api/area/{id}/procedimentos, buscado só quando a aba abre pela
 * primeira vez: a aba fechada não paga o cálculo.
 *
 * Desde 14/ago o bloco monta a PRÓPRIA moldura. Antes ele emprestava a moldura
 * da tabela de cooperados e as duas se revezavam nela — o que amarrava dois
 * blocos por um detalhe de layout e obrigava a tabela de cooperados a saber da
 * existência da de procedimentos.
 *
 * ── fronteira visual ────────────────────────────────────────────────────────
 * Nenhuma classe nova. `.col-*` são as larguras do contrato, `.rt` alinha à
 * direita, `.cell-name`/`.cell-sub` são a célula de identidade que a aba
 * Cooperados já usa, `.tag`/`.tag-caveat` são as etiquetas semânticas e
 * `.val-ressalva` é o número que existe mas não sustenta comparação.
 */
'use strict';

import { buscar } from '../lib/api.js';
import { el, ordenar, cabecalho, ordemDaURL, gravarOrdem, proximaOrdem, moldura,
         campoDeBusca, casa } from '../lib/tabelas.js';

/* As nove colunas. `ordem` é a chave na URL; `valor` extrai o número que ordena
 * — nada aqui calcula, só lê campo que o motor já entregou.
 *
 * Rótulos curtos com a definição no `title`, o mesmo tratamento da aba
 * Cooperados: o cabeçalho diz o nome, o hover diz o que o número significa.
 * "Prevalência entre os pares" inteiro exigiria uma coluna maior que o número
 * que ela descreve.
 *
 * A referência NÃO é ordenável: é uma taxa por procedimento, e procedimentos
 * diferentes têm ordens de grandeza diferentes (0,02 e 3,4 na mesma coluna).
 * Ordenar por ela produziria um ranking de unidades incomparáveis. */
const COLUNAS = [
  { nome: 'Procedimento', classe: 'col-txt' },
  { nome: 'Prevalência', direita: true, classe: 'col-num-md',
    def: 'Porcentagem dos cooperados comparáveis da área que solicitam este '
       + 'exame. É régua da área e não se move com o recorte.',
    ordem: 'prevalencia', valor: (l) => l.prevalencia },
  { nome: 'Solicitantes', direita: true, classe: 'col-num-md',
    def: 'Solicitantes elegíveis que formam a referência deste exame. É régua '
       + 'da área e não se move com o recorte.',
    ordem: 'solicitantes', valor: (l) => l.n_solicitantes_elegiveis },
  { nome: 'Referência', direita: true, classe: 'col-num-md',
    def: 'Mediana do grupo neste exame, em solicitações por consulta. Taxas '
       + 'raras aparecem por mil consultas. É régua da área e não se move com '
       + 'o recorte.' },
  { nome: 'Qualidade da referência', classe: 'col-txt',
    def: 'Sólida quando há solicitantes elegíveis suficientes; não conclusiva '
       + 'abaixo do mínimo.' },
  /* O VOLUME abre o lado do achado. Prevalência diz quantos cooperados pedem
     o exame; esta diz QUANTO se pede — um exame que todos solicitam uma vez ao
     ano e outro que todos solicitam toda semana têm a mesma prevalência. É a
     coluna que responde "o que a área mais pede", e ordenar por ela troca a
     lista do Pareto pela rotina da área. */
  { nome: 'Solicitações', direita: true, classe: 'col-num-md',
    def: 'Solicitações deste exame somadas entre os cooperados em cena no '
       + 'recorte, sinalizados ou não.',
    ordem: 'solicitacoes', valor: (l) => l.n_solicitacoes },
  { nome: 'Acima do critério', direita: true, classe: 'col-num-md',
    def: 'Cooperados que passaram o critério de revisão neste exame, entre os '
       + 'que estão em cena no recorte.',
    ordem: 'acima', valor: (l) => l.n_acima_do_criterio },
  /* NOMES IGUAIS aos da tabela de Cooperados e aos dos KPIs (2026-08-20): eram
     "Variação excedente" e "R$ estimado", duas palavras diferentes para as duas
     grandezas que o resto da página chama de "Excesso de solicitações" e
     "Excesso em R$". Três vocabulários para o mesmo par de números na mesma
     tela. */
  { nome: 'Excesso de solicitações', direita: true, classe: 'col-num-lg',
    def: 'Solicitações a mais que a referência deste exame, somadas entre os '
       + 'cooperados que passaram o critério nele.',
    ordem: 'excedente', valor: (l) => l.excedente_itens },
  { nome: 'Excesso em R$', direita: true, classe: 'col-num-md',
    def: 'As mesmas solicitações excedentes valoradas a preços de referência '
       + 'internos derivados das contas do período.',
    ordem: 'reais', valor: (l) => l.excedente_reais },
  /* O acumulado é de ITENS (a ordem padrão da aba), não do R$ da coluna ao
     lado — a definição declara, senão a vizinhança sugere o contrário. O
     acumulado em R$ vive nos Paretos da página. */
  { nome: '% acumulado', direita: true, classe: 'col-num',
    def: 'Quanto do excesso de solicitações já foi somado até esta linha, na '
       + 'ordem padrão. É acumulado de solicitações, não de R$.',
    ordem: 'acumulado', valor: (l) => l.pct_acumulado },
];

/** Código em cima, descrição embaixo: o código é o que se busca no sistema, a
 *  descrição é o que se lê. */
function celulaProcedimento(l) {
  const td = el('td', 'cell-name');
  td.appendChild(document.createTextNode(l.codigo));
  const sub = el('span', 'cell-sub', l.descricao);
  /* A descrição chega cortada em 50 caracteres pela base de origem, às vezes no
     meio da palavra. O `title` carrega o que veio, e o dia em que a origem
     mandar o texto inteiro esta linha não muda. */
  sub.title = l.descricao;
  td.appendChild(sub);
  return td;
}

/** Sólida ou não conclusiva. O motivo completo fica no hover. */
function celulaQualidade(q) {
  const td = document.createElement('td');
  const etiqueta = el('span', q.apresentavel ? 'tag' : 'tag tag-caveat', q.rotulo);
  if (q.motivo) etiqueta.title = q.motivo;
  td.appendChild(etiqueta);
  return td;
}

/** Número à direita; `ressalva` esmaece e tracejada o que não sustenta
 *  comparação, em vez de deixá-lo parecer o menor valor da coluna.
 *
 *  `num` (Geist Mono) faltava aqui, e era a última diferença visual entre esta
 *  tabela e a de Cooperados: os números saíam na fonte de texto, com largura de
 *  dígito variável, e a coluna deixava de alinhar unidade com unidade. Número em
 *  mono é regra do contrato — tabela é comparação de dígitos. */
function numero(texto, ressalva) {
  const td = el('td', 'rt num');
  td.appendChild(el('span', ressalva ? 'val-ressalva' : null, texto));
  return td;
}

function linhaDaTabela(l, aoAbrir) {
  const q = l.qualidade;
  const fraca = !q.apresentavel;
  const tr = document.createElement('tr');
  tr.dataset.codigo = l.codigo;
  /* A LINHA INTEIRA é o gatilho do painel — alvo grande, sem um botão a mais
     na grade —, exatamente como na tabela de procedimentos do dossiê. Teclado
     junto: a tabela é navegável, e uma porta que só abre com o mouse não é
     porta para metade dos usuários. */
  if (aoAbrir) {
    tr.classList.add('clicavel');
    tr.tabIndex = 0;
    const acionar = () => aoAbrir(l, tr);
    tr.addEventListener('click', acionar);
    tr.addEventListener('keydown', (ev) => {
      if (ev.key !== 'Enter' && ev.key !== ' ') return;
      ev.preventDefault();
      acionar();
    });
  }
  tr.append(
    celulaProcedimento(l),
    numero(l.prevalencia_fmt),
    numero(String(l.n_solicitantes_elegiveis), fraca),
    numero(l.referencia?.mediana_fmt ?? '', fraca),
    celulaQualidade(q),
    /* O VOLUME não leva a ressalva de referência fraca: ele é contagem de
       solicitação, não comparação contra a norma, e continua exato quando a
       referência do exame não é conclusiva. */
    numero(l.n_solicitacoes_fmt),
    /* Sem referência conclusiva ninguém pode estar acima do critério: não é
       zero medido, é zero estrutural. O número vem 0 do motor e fica esmaecido
       junto com a linha, para não ser lido como "medimos e não achamos". */
    numero(String(l.n_acima_do_criterio), fraca),
    numero(l.excedente_fmt, fraca),
    /* vazio quando o par não tem preço nas contas: ausência de preço, não zero */
    numero(l.excedente_reais_fmt ?? '', fraca),
    numero(l.pct_acumulado_fmt, fraca),
  );
  return tr;
}

/**
 * Monta o cartão de Procedimentos em `destino`. A busca só acontece no
 * primeiro `render()`.
 *
 * @param {HTMLElement} destino
 * @param {string} area  id da área, para o endpoint
 * @returns {{render: () => Promise<void>}}
 */
export function montarProcedimentos(destino, area, opcoes = {}) {
  /* MESMA moldura das outras tabelas do app (lib/tabelas.js). Esta montava a
     sua à mão e estava sem `tbl-fixa`, então a largura das colunas pulava a
     cada repintura, ao contrário da tabela de Cooperados ao lado. */
  const { quadro, topo, tabela, peEstado: rodape } = moldura();
  const titulo = el('div', 'stack g4');
  titulo.appendChild(el('span', 't', 'Procedimentos da área'));
  titulo.appendChild(el('span', 'sub',
    'em que a área varia: prevalência, referência, volume e o excedente de '
    + 'cada procedimento'));
  /* A DECLARAÇÃO DE POPULAÇÃO. Esta tabela é metade régua e metade achado:
     prevalência, solicitantes, referência e qualidade são da área e não se
     movem; solicitações, acima do critério, excedente, R$ e % acumulado
     seguem o recorte.
     Sem dizer isso em voz alta, as duas metades ficam lado a lado somando
     conjuntos diferentes — que é exatamente o defeito que o recorte veio
     corrigir. A frase vem redigida do motor. */
  const subRecorte = el('span', 'sub', '');
  titulo.appendChild(subRecorte);
  topo.appendChild(titulo);

  /* ── O FILTRO DE EXCEDENTE ────────────────────────────────────────────────
     Dois em cada três procedimentos da área não têm ninguém acima do critério
     (439 de 671 em Ginecologia sequer têm referência conclusiva), e eles
     ocupam a lista inteira abaixo da linha em que o excedente acaba. Quem
     ordena por excedente vê os relevantes no topo e rola por 439 linhas de
     travessão para conferir que não há mais nada.

     É LOCALIZAÇÃO, não recorte: esconde linhas e não toca em soma nenhuma — o
     % acumulado continua o mesmo, porque quem sai contribuía com zero. Por
     isso é segmentado (escolha entre duas leituras da mesma lista) e não chip
     de recorte, e por isso o rodapé o declara junto dos outros filtros.
     Mesmo `.segfilt` do "Ordenar por" do Pareto, no mesmo `.hd-ctl`. */
  let soExcedente = opcoes.soExcedente === true;
  const ctlFiltro = el('div', 'hd-ctl row g8');
  const seg = el('div', 'segfilt');
  const botoes = new Map();
  for (const o of [{ chave: 'todos', rotulo: 'Todos' },
                   { chave: 'excedente', rotulo: 'Com excedente' }]) {
    const b = el('button', 'segfilt-o', o.rotulo);
    b.type = 'button';
    const cnt = el('span', 'cnt', '');
    b.appendChild(cnt);
    b.addEventListener('click', () => {
      const novo = o.chave === 'excedente';
      if (novo === soExcedente) return;
      soExcedente = novo;
      opcoes.aoFiltrar?.(novo);
      marcarFiltro();
      if (dados) desenhar();
    });
    botoes.set(o.chave, { b, cnt });
    seg.appendChild(b);
  }
  ctlFiltro.appendChild(seg);
  topo.appendChild(ctlFiltro);

  function marcarFiltro() {
    for (const [chave, { b }] of botoes) {
      b.classList.toggle('on', (chave === 'excedente') === soExcedente);
    }
  }
  marcarFiltro();

  /** Quem tem excedente medido: solicitações acima da referência neste exame. */
  const temExcedente = (l) => (l.excedente_itens || 0) > 0;

  /* BUSCA: localiza dentro do que já está em cena, sem tocar em soma nenhuma.
     Casa código e descrição — quem tem o código na mão cola, quem não tem
     digita o nome. */
  /* A busca vem da URL: é assim que o painel do procedimento consegue mandar o
     leitor para cá JÁ no exame que ele estava vendo, em vez de largá-lo numa
     lista de centenas de linhas. */
  let termo = opcoes.busca ?? '';
  topo.appendChild(campoDeBusca({
    placeholder: 'Buscar por nome ou código',
    valor: termo,
    aoDigitar: (t) => {
      termo = t;
      opcoes.aoBuscar?.(t);
      if (dados) desenhar();
    },
  }));
  destino.appendChild(quadro);

  let dados = null;

  let { chave: ordemAtiva, direcao } = ordemDaURL(COLUNAS);

  function alternarOrdem(chave) {
    ({ chave: ordemAtiva, direcao } = proximaOrdem(ordemAtiva, direcao, chave));
    gravarOrdem(ordemAtiva, direcao);
    desenhar();
  }

  function desenhar() {
    const coluna = COLUNAS.find((c) => c.ordem === ordemAtiva);
    /* O CONTADOR de cada opção conta sobre a lista INTEIRA, não sobre o que a
       busca deixou: ele é a promessa do botão ("clicando aqui, sobram 232"), e
       um número que muda com a busca deixa de ser promessa. */
    botoes.get('todos').cnt.textContent = String(dados.linhas.length);
    botoes.get('excedente').cnt.textContent =
      String(dados.linhas.filter(temExcedente).length);

    let achadas = soExcedente ? dados.linhas.filter(temExcedente) : dados.linhas;
    if (termo) {
      achadas = achadas.filter(
        (l) => casa(l.descricao, termo) || casa(l.codigo, termo));
    }
    const visiveis = ordenar(achadas, coluna, direcao);

    const corpo = document.createElement('tbody');
    for (const l of visiveis) corpo.appendChild(linhaDaTabela(l, opcoes.aoAbrirLinha));
    tabela.replaceChildren(
      cabecalho(COLUNAS, ordemAtiva, direcao, alternarOrdem), corpo);

    /* O rodapé diz o estado da vista, no mesmo formato da aba Cooperados: o que
       está em cena e sob que ordem. A contagem de não conclusivas entra porque
       é 2 em cada 3 linhas nesta área — quem ordena por excedente vê só as
       sólidas no topo e não faria ideia do tamanho da cauda. */
    const r = dados.resumo;
    const dizOrdem = coluna
      ? `${coluna.nome.toLowerCase()}, ${direcao === 'asc' ? 'crescente' : 'decrescente'}`
      : 'variação excedente (padrão)';
    const dizBusca = termo ? ` · busca: "${termo}"` : '';
    const dizFiltro = soExcedente ? ' · só os que têm excedente' : '';
    const parcial = termo || soExcedente;
    const quantos = parcial ? `${visiveis.length} de ${r.total}` : `${r.total}`;
    /* A contagem de referência não conclusiva só faz sentido sobre a lista
       INTEIRA: no filtro de excedente ela sairia falando de linhas que não
       estão na tela. O filtro entra no lugar dela. */
    const dizQualidade = soExcedente ? ''
      : ` · ${r.sem_referencia_apresentavel} com referência não conclusiva `
        + `(${r.nota_n_minimo})`;
    rodape.textContent =
      `${quantos} procedimentos${dizQualidade}${dizFiltro}${dizBusca}`
      + ` · ordenado por ${dizOrdem}`;
  }

  /* O recorte que os números em cena representam. A aba continua sem pagar o
     cálculo enquanto ninguém a abre, e continua não voltando ao servidor por
     nada que não mude a soma — trocar de aba ou reordenar não busca. O que
     busca é o recorte mudar, porque aí METADE das colunas muda de valor. */
  let recorteEmCena = null;
  const chave = ({ recorte, perfil } = {}) => `${recorte ?? ''}|${perfil ?? ''}`;

  async function render(recorte) {
    if (!dados || chave(recorte) !== recorteEmCena) {
      rodape.textContent = 'carregando procedimentos…';
      /* `soMotor` limpa `aba`, `ord` e `dir`, que são estado de tela e sujariam
         o cache. `recorte`/`perfil` voltam por `extra`: eles mudam a soma das
         colunas de achado, e o servidor precisa deles. */
      dados = await buscar(`/api/area/${encodeURIComponent(area)}/procedimentos`,
                           { soMotor: true, extra: recorte ?? {} });
      recorteEmCena = chave(recorte);
    }
    subRecorte.textContent = dados.resumo?.subtitulo_recorte ?? '';
    // a ordenação pode ter vindo da outra aba na URL; revalidar contra ESTAS colunas
    ({ chave: ordemAtiva, direcao } = ordemDaURL(COLUNAS));
    desenhar();
  }

  /* A MESMA porta pelo outro lado: uma barra do Pareto conhece o CÓDIGO do
     procedimento, não a linha da tabela. Aqui o código vira linha — e ela pode
     não estar em cena, porque a busca da tabela filtra o que está visível e o
     Pareto não. */
  function abrirPorCodigo(codigo) {
    const l = (dados?.linhas ?? []).find((x) => String(x.codigo) === String(codigo));
    if (!l) return;
    const tr = tabela.querySelector(
      `tr[data-codigo="${CSS.escape(String(codigo))}"]`);
    opcoes.aoAbrirLinha?.(l, tr);
  }

  return { render, abrirPorCodigo,
    marcar: (codigo) => {
    for (const tr of tabela.querySelectorAll('tr.selecionada')) {
      tr.classList.remove('selecionada');
    }
    if (!codigo) return;
    tabela.querySelector(`tr[data-codigo="${CSS.escape(String(codigo))}"]`)
      ?.classList.add('selecionada');
  } };
}
