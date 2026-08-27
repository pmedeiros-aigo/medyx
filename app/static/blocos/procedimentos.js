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

/* As oito colunas. `ordem` é a chave na URL; `valor` extrai o número que ordena
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
       + 'internos. Em quarentena até a tabela contratual — não é economia '
       + 'realizada.',
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

function linhaDaTabela(l) {
  const q = l.qualidade;
  const fraca = !q.apresentavel;
  const tr = document.createElement('tr');
  tr.dataset.codigo = l.codigo;
  tr.append(
    celulaProcedimento(l),
    numero(l.prevalencia_fmt),
    numero(String(l.n_solicitantes_elegiveis), fraca),
    numero(l.referencia?.mediana_fmt ?? '', fraca),
    celulaQualidade(q),
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
export function montarProcedimentos(destino, area) {
  /* MESMA moldura das outras tabelas do app (lib/tabelas.js). Esta montava a
     sua à mão e estava sem `tbl-fixa`, então a largura das colunas pulava a
     cada repintura, ao contrário da tabela de Cooperados ao lado. */
  const { quadro, topo, tabela, peEstado: rodape } = moldura();
  const titulo = el('div', 'stack g4');
  titulo.appendChild(el('span', 't', 'Procedimentos da área'));
  titulo.appendChild(el('span', 'sub',
    'em que a área varia: prevalência, referência e o excedente de cada '
    + 'procedimento'));
  /* A DECLARAÇÃO DE POPULAÇÃO. Esta tabela é metade régua e metade achado:
     prevalência, solicitantes, referência e qualidade são da área e não se
     movem; acima do critério, excedente, R$ e % acumulado seguem o recorte.
     Sem dizer isso em voz alta, as duas metades ficam lado a lado somando
     conjuntos diferentes — que é exatamente o defeito que o recorte veio
     corrigir. A frase vem redigida do motor. */
  const subRecorte = el('span', 'sub', '');
  titulo.appendChild(subRecorte);
  topo.appendChild(titulo);

  /* BUSCA: localiza dentro do que já está em cena, sem tocar em soma nenhuma.
     Casa código e descrição — quem tem o código na mão cola, quem não tem
     digita o nome. */
  let termo = '';
  topo.appendChild(campoDeBusca({
    placeholder: 'Buscar por nome ou código',
    aoDigitar: (t) => { termo = t; if (dados) desenhar(); },
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
    const achadas = termo
      ? dados.linhas.filter((l) => casa(l.descricao, termo) || casa(l.codigo, termo))
      : dados.linhas;
    const visiveis = ordenar(achadas, coluna, direcao);

    const corpo = document.createElement('tbody');
    for (const l of visiveis) corpo.appendChild(linhaDaTabela(l));
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
    const quantos = termo ? `${visiveis.length} de ${r.total}` : `${r.total}`;
    rodape.textContent =
      `${quantos} procedimentos · ${r.sem_referencia_apresentavel} com referência `
      + `não conclusiva (${r.nota_n_minimo})${dizBusca} · ordenado por ${dizOrdem}`;
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

  return { render };
}
