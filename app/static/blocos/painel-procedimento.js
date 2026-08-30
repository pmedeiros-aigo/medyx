/* blocos/painel-procedimento.js — o painel lateral de UM procedimento.
 *
 * Abre ao clicar numa linha da tabela de procedimentos do dossiê e fica AO LADO
 * dela, não sobre ela. A escolha é de leitura, não de estética: o auditor chega
 * aqui porque uma linha chamou atenção, e a pergunta seguinte é sempre
 * comparativa — "e no exame de baixo?". Painel ao lado deixa ele trocar de
 * linha sem fechar nada; gaveta empurraria o resto da tabela para fora da tela
 * e modal cobriria justamente o que ele quer comparar.
 *
 * ── por que não virou coluna ────────────────────────────────────────────────
 *
 * A tabela já carrega dez colunas. O que este painel mostra é evidência de
 * SEGUNDO nível: ninguém abre o dossiê procurando por ela, e quem procura já
 * sabe qual linha quer. Colocar repetição, concentração e autorreferência na
 * grade custaria a leitura das dez que já estão lá para servir a um caso que
 * acontece uma vez por sessão.
 *
 * ── o que este arquivo NÃO faz ──────────────────────────────────────────────
 *
 * Não calcula e não decide o que é achado. A API manda tudo formatado, com os
 * pares ao lado e os motivos de ausência escritos; aqui só se imprime. O
 * A posição vem em RÉGUA (`.ruler` do contrato), não no gráfico de pontos da
 * tela de área: aqui a pergunta é "onde ele está", e 56 pontos numa coluna de
 * 380px viram ruído. A forma da distribuição continua sendo pergunta da tela de
 * Área, a um clique. Régua e gráfico compartilham a geometria do motor
 * (`_escala`/`_pos`), então a marca cai no mesmo lugar nas duas telas.
 */
'use strict';

import { el } from '../lib/dom.js';
import { buscar } from '../lib/api.js';

/**
 * Uma seção do painel.
 *
 * O painel é UMA superfície: a divisão entre seções é uma régua fina e o
 * respiro entre elas, nunca um cartão. A versão anterior empilhava sete `.tbl`
 * — cada um com borda, sombra e raio — dentro de um `<aside>` que já tinha
 * borda: borda dentro de borda, sete vezes, e 257px a mais de altura que a
 * tabela ao lado só de moldura.
 *
 * O rótulo é `.micro` e o número é `.v`: a hierarquia vem do TAMANHO e da cor,
 * não de uma caixa em volta. É a mesma gramática das faixas de KPI do dossiê.
 */
function secao(rotulo, definicao) {
  const bloco = el('section', 'pnl-sec');
  const t = el('span', 'micro pnl-rot', rotulo);
  if (definicao) t.title = definicao;
  bloco.appendChild(t);
  const corpo = el('div', 'stack g6');
  bloco.appendChild(corpo);
  return { cartao: bloco, corpo };
}


const NS = 'http://www.w3.org/2000/svg';
const svg = (tag, attrs) => {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
};

/**
 * Curva de densidade + caixa de quartis + a marca do cooperado.
 *
 * Substituiu uma régua de linhas de 1px (ago/2026): ela era exata e ilegível —
 * três traços indistinguíveis num eixo de 18px, que só se liam pela legenda.
 * A curva mostra ONDE o grupo se acumula sem precisar de legenda nenhuma, e a
 * distância entre a massa e a marca é a leitura inteira.
 *
 * Sem eixo numerado: os valores que importam já estão escritos embaixo, e um
 * eixo de índice de solicitação por consulta (0,015 · 0,15 · 0,36) é ruído em
 * 380px. Nada aqui é calculado — as alturas e as posições vêm do motor.
 */
function grafico(g) {
  const L = 380, H = 84, BASE = 58, CX = 70;   // caixa e curva partilham o eixo
  const s = svg('svg', { viewBox: `0 0 ${L} ${H}`, class: 'dens', 'aria-hidden': 'true' });
  const x = (pct) => (pct / 100) * L;

  if (g.densidade?.length) {
    const passo = L / (g.densidade.length - 1);
    const pts = g.densidade.map((v, i) => `${(i * passo).toFixed(1)},${(BASE - v * 40).toFixed(1)}`);
    s.appendChild(svg('path', {
      class: 'dens-area',
      d: `M0,${BASE} L${pts.join(' L')} L${L},${BASE} Z`,
    }));
  }

  /* Caixa dos quartis, fina, sob a curva: dá o resumo numérico da mesma
     distribuição que a curva descreve, sem competir com ela. */
  s.appendChild(svg('rect', {
    class: 'dens-box', x: x(g.iqr.pos_pct), y: BASE + 4,
    width: Math.max(x(g.iqr.largura_pct), 1), height: 8, rx: 1,
  }));
  s.appendChild(svg('line', {
    class: 'dens-med', x1: x(g.referencia.pos_pct), x2: x(g.referencia.pos_pct),
    y1: BASE + 2, y2: BASE + 14,
  }));
  if (g.criterio) {
    s.appendChild(svg('line', {
      class: 'dens-crit', x1: x(g.criterio.pos_pct), x2: x(g.criterio.pos_pct),
      y1: BASE - 34, y2: BASE + 14,
    }));
  }
  /* A MARCA atravessa a curva inteira: é o único elemento que o olho precisa
     achar sozinho, e ela é o assunto do bloco. */
  s.appendChild(svg('line', {
    class: `dens-mk ${g.marca.classe}`, x1: x(g.marca.pos_pct), x2: x(g.marca.pos_pct),
    y1: 6, y2: BASE + 14,
  }));
  return s;
}

function montarRegua(destino, d) {
  const g = d.regua;
  const { cartao, corpo } = secao('Frequência de solicitação',
    'Solicitações deste procedimento por consulta atendida, comparadas com o '
    + 'grupo de pares da área de atuação. A referência e o critério seguem os '
    + 'parâmetros ativos da análise.');
  if (!g) {
    corpo.appendChild(el('span', 'sub',
      'grupo de pares insuficiente para análise comparativa'));
    destino.appendChild(cartao);
    return;
  }

  if (g.razao_fmt) {
    corpo.appendChild(el('span', 'v', `${g.razao_fmt} a referência do grupo de pares`));
  }
  const fig = grafico(g);
  fig.setAttribute('role', 'img');
  fig.setAttribute('aria-label',
    `Este cooperado: ${g.marca.valor_fmt} solicitações por consulta. `
    + `${g.referencia.rotulo}: ${g.referencia.valor_fmt}.`);
  corpo.appendChild(fig);

  /* Três valores, sem legenda de cores: quem lê quer os números, e a posição
     de cada um no gráfico já os identifica. A legenda anterior gastava uma
     linha para dizer "metade central dos pares", que ninguém procurava. */
  const vals = el('div', 'row g16 flexwrap');
  const par = (rotulo, valor, classe) => {
    const c = el('div', 'stack g4');
    c.appendChild(el('span', 'micro', rotulo));
    c.appendChild(el('span', `v ${classe ?? ''}`, valor));
    return c;
  };
  vals.appendChild(par('este cooperado', g.marca.valor_fmt, 'v-mk'));
  vals.appendChild(par(g.referencia.rotulo, g.referencia.valor_fmt));
  if (g.criterio) {
    vals.appendChild(par(g.criterio.rotulo
      + (g.criterio.ajustado ? ' · ajustado ao tamanho do grupo' : ''),
      g.criterio.valor_fmt));
  }
  corpo.appendChild(vals);
  corpo.appendChild(el('span', 'sub',
    `${g.n_pares} cooperados da área solicitam este procedimento`));
  if (g.sem_criterio_motivo) corpo.appendChild(el('span', 'sub', g.sem_criterio_motivo));
  destino.appendChild(cartao);
}


function montarRepeticao(destino, d) {
  const r = d.repeticao;
  const { cartao, corpo } = secao('Repetição por beneficiário',
    'Beneficiários que receberam este procedimento mais de uma vez no período, '
    + 'e o intervalo entre as solicitações. Repetição é rotina em acompanhamento '
    + 'e é achado em rastreio: a leitura depende da referência do grupo de pares.');
  if (r.motivo) {
    /* Ausência declarada, com o motivo do léxico — célula vazia lê como zero
       medido, e não é. */
    corpo.appendChild(el('span', 'sub', r.motivo));
    destino.appendChild(cartao);
    return;
  }

  const frase = el('span', 'v');
  frase.textContent = `${r.pct_repetem_fmt} dos beneficiários receberam mais de uma vez`;
  corpo.appendChild(frase);

  const linhas = el('div', 'stack g4');
  linhas.appendChild(el('span', 'sub',
    `referência do grupo de pares: ${r.pct_repetem_pares_fmt}`));
  if (r.intervalo_fmt) {
    const i = el('span', 'sub',
      `intervalo entre solicitações: ${r.intervalo_fmt} dias`
      + (r.intervalo_pares_fmt ? ` · pares da área: ${r.intervalo_pares_fmt} dias` : ''));
    i.title = 'Dias entre solicitações consecutivas do mesmo procedimento para o '
      + 'mesmo beneficiário, apurado apenas sobre quem repetiu.';
    linhas.appendChild(i);
  }
  /* Sem repetir "N beneficiários com este procedimento": a seção Alcance,
     logo acima, já traz esse número junto do denominador da carteira. */
  corpo.appendChild(linhas);
  destino.appendChild(cartao);
}


function montarConcentracao(destino, d) {
  const c = d.concentracao;
  if (!c) return;
  /* A CONCLUSÃO é o título do card; a lista, quando existe, é a evidência dela.
     A versão anterior fazia o contrário — despejava cinco linhas e um rodapé
     comparativo e deixava a leitura por conta do auditor, que numa distribuição
     plana lia cinco vezes "1%" e concluía que havia algo ali. */
  const { cartao, corpo } = secao('Concentração por beneficiário',
    'Como as solicitações deste procedimento se distribuem entre os beneficiários '
    + 'do cooperado. Beneficiários acima do limiar de participação são listados; '
    + 'sem nenhum acima, a distribuição está espalhada.');

  corpo.appendChild(el('span', 'v', c.titulo));

  if (c.linhas.length) {
    const lista = el('div', 'stack g8');
    const maior = Math.max(...c.linhas.map((l) => l.pct), 0.0001);
    for (const l of c.linhas) {
      const item = el('div', 'row g8');
      /* Barra proporcional ao MAIOR da lista: a leitura é "quanto este se
         destaca entre os que se destacam". O número exato viaja ao lado. */
      const trilho = el('div', 'bar');
      const cheia = el('i', null);
      cheia.style.width = `${Math.round((l.pct / maior) * 100)}%`;
      trilho.appendChild(cheia);
      item.appendChild(el('span', 'mono', l.id));
      item.appendChild(trilho);
      const det = el('span', 'sub',
        `${l.pct_fmt} · ${l.itens_fmt} solicitações em ${l.ocasioes} `
        + `${l.ocasioes === 1 ? 'consulta' : 'consultas'}`
        + `${l.intervalo_fmt ? ` · ${l.intervalo_fmt}` : ''}`);
      det.title = 'Participação deste beneficiário no total solicitado do '
        + 'procedimento, volume de solicitações, consultas em que foram pedidas '
        + 'e intervalo médio entre elas.';
      item.appendChild(det);
      lista.appendChild(item);
    }
    corpo.appendChild(lista);
  }

  /* A comparação com os pares em PALAVRAS; os percentuais ficam no hover, para
     quem quiser conferir. Frase primeiro, número depois — não o contrário. */
  if (c.comparacao) corpo.appendChild(el('span', 'sub', c.comparacao));
  destino.appendChild(cartao);
}


function montarAlcance(destino, d) {
  const a = d.alcance;
  if (!a) return;
  const { cartao, corpo } = secao('Alcance na carteira',
    'Fatia dos beneficiários do cooperado que recebeu este procedimento no '
    + 'período. Responde se o procedimento é rotina na carteira ou exceção, '
    + 'leitura que a frequência por consulta não dá.');
  corpo.appendChild(el('span', 'v',
    `${a.pct_fmt} da carteira recebeu este procedimento`));
  const det = el('div', 'stack g4');
  if (a.pares_fmt) {
    det.appendChild(el('span', 'sub',
      `referência do grupo de pares: ${a.pares_fmt}`));
  }
  det.appendChild(el('span', 'sub',
    `${a.n_beneficiarios} de ${a.n_carteira} beneficiários atendidos no período`));
  corpo.appendChild(det);
  destino.appendChild(cartao);
}


function montarEvolucao(destino, d) {
  const t = d.trimestres;
  if (!t?.length) return;
  const acima = t.filter((x) => x.sinalizado).length;
  const { cartao, corpo } = secao('Evolução no período',
    'Trimestres em que a frequência ficou acima do critério de revisão. '
    + 'Padrão que se repete em trimestres distintos separa variação sustentada '
    + 'de oscilação de uma janela só.');
  /* Mesmo desenho de quadrados da coluna Consistência da tabela: um quadrado
     por trimestre, preenchido indica trimestre acima. Dois desenhos para o
     mesmo dado ensinariam duas leituras. */
  /* `.on` / `.na` são as classes do contrato — as mesmas que `celulaConsistencia`
     usa na tabela. Eu havia escrito `.crit`, que não existe em `.spark` e deixava
     os quatro quadrados cinza mesmo com quatro trimestres acima do critério. */
  corpo.appendChild(el('span', 'v',
    `${acima} de ${t.length} trimestres acima do critério de revisão`));
  const barras = el('div', 'spark');
  for (const q of t) {
    const i = document.createElement('i');
    if (q.estado === 'sinalizado') i.className = 'on';
    else if (q.estado === 'nao_avaliavel') i.className = 'na';
    i.title = `${q.janela}º trimestre: ` + (
      q.estado === 'nao_avaliavel' ? q.motivo
        : q.sinalizado ? 'acima do critério de revisão' : 'dentro da referência');
    barras.appendChild(i);
  }
  corpo.appendChild(barras);
  destino.appendChild(cartao);
}


function montarPeso(destino, d) {
  const p = d.peso;
  if (!p) return;
  const { cartao, corpo } = secao('Peso na prática',
    'Participação deste procedimento no total solicitado pelo cooperado no '
    + 'período e valor correspondente. Preços internos provisórios, ainda não '
    + 'homologados contra a tabela contratual.');
  corpo.appendChild(el('span', 'v',
    `${p.proporcao_fmt} de tudo que o cooperado solicitou`));
  const det = el('div', 'stack g4');
  det.appendChild(el('span', 'sub',
    `${p.solicitacoes_fmt} solicitações`
    + (p.custo_unitario_fmt ? ` · ${p.custo_unitario_fmt} cada` : '')));
  if (p.custo_total_fmt) {
    const c = el('span', 'sub',
      `${p.custo_total_fmt} no período`
      + (p.excedente_pct_fmt ? `, ${p.excedente_pct_fmt} acima da referência` : ''));
    c.title = 'Valor apurado com preço mediano das contas do período. '
      + 'Preço interno provisório, em quarentena até a homologação.';
    det.appendChild(c);
  }
  corpo.appendChild(det);
  destino.appendChild(cartao);
}


function montarAutorreferencia(destino, d) {
  const a = d.autorreferencia;
  const { cartao, corpo } = secao('Autorreferenciamento',
    'Parcela das solicitações executadas pelo próprio solicitante, apurada sobre '
    + 'as solicitações com conta localizada. Indicador para investigação, não conclusão.');
  if (a.apresentavel) {
    corpo.appendChild(el('span', 'v', a.taxa_fmt));
    /* A cobertura viaja SEMPRE junto da taxa — é premissa declarada no motor,
       não nota de rodapé: a taxa vale sobre os itens com conta localizada. */
    const cob = el('span', 'sub',
      `Apurado sobre os ${a.cobertura_fmt} dos pedidos em que se sabe quem `
      + `executou (${a.itens_com_conta} de ${a.itens}).`);
    cob.title = 'Quem executou um pedido só é conhecido quando a solicitação '
      + 'encontra a conta correspondente. O método presume que os demais se '
      + 'comportam como os observados.';
    corpo.appendChild(cob);
  } else {
    corpo.appendChild(el('span', 'sub', a.motivo ?? d.sem_medida));
    if (a.cobertura_fmt) {
      corpo.appendChild(el('span', 'sub',
        `Em apenas ${a.cobertura_fmt} dos pedidos se sabe quem executou `
        + `(${a.itens_com_conta} de ${a.itens}), pouco para apurar a taxa.`));
    }
  }
  destino.appendChild(cartao);
}

/**
 * Monta (ou atualiza) o painel lateral.
 *
 * @param {HTMLElement} destino  a coluna lateral, já no layout
 * @param {string} cooperadoId
 * @param {object} linha  a linha da tabela que foi clicada
 * @param {() => void} aoFechar
 */
export async function abrirPainel(destino, cooperadoId, linha, aoFechar) {
  destino.replaceChildren();
  destino.hidden = false;

  /* Cabeçalho FIXO: o painel rola por dentro e, sem isso, o nome do
     procedimento sai de cena logo no primeiro scroll — junto com o botão de
     fechar, que é a única saída. */
  const topo = el('div', 'row row-between pnl-hd');
  const titulo = el('div', 'stack g4');
  titulo.appendChild(el('span', 't', linha.descricao));
  titulo.appendChild(el('span', 'mono sub', linha.codigo));
  topo.appendChild(titulo);
  const fechar = el('button', 'painel-x', '✕');
  fechar.setAttribute('aria-label', 'Fechar detalhe do procedimento');
  fechar.title = 'Fechar';
  fechar.addEventListener('click', aoFechar);
  topo.appendChild(fechar);
  destino.appendChild(topo);

  const corpo = el('div', 'pnl-corpo');
  destino.appendChild(corpo);
  /* Estado de carga na PRÓPRIA superfície que vai receber o dado: painel que
     abre vazio e enche depois faz o leitor duvidar se clicou. */
  const carregando = el('span', 'sub', 'carregando…');
  corpo.appendChild(carregando);

  let d;
  try {
    d = await buscar(`/api/cooperado/${cooperadoId}/procedimento/${linha.codigo}`);
  } catch {
    carregando.textContent = 'não foi possível carregar o detalhe deste procedimento';
    return;
  }
  corpo.replaceChildren();

  /* Ordem de leitura: quanto pede (comparação) -> para quantos (alcance) ->
     repete? -> concentra? -> desde quando -> quanto pesa -> quem executou.
     Vai do fato mais forte ao contexto, e o dinheiro entra depois da evidência
     que o sustenta, nunca antes. */
  montarRegua(corpo, d);
  montarAlcance(corpo, d);
  montarRepeticao(corpo, d);
  montarConcentracao(corpo, d);
  montarEvolucao(corpo, d);
  montarPeso(corpo, d);
  montarAutorreferencia(corpo, d);

  /* O piso de confiança da variação excedente saiu daqui (ago/2026): ele já
     está na coluna de custo excedente da tabela, ao lado do número que
     qualifica, e repetido no painel virava ruído no fim de tudo. */
}
