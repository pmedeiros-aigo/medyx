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

/** Um par rótulo/valor com a referência dos pares embaixo. */
function medida(rotulo, valor, pares, semMedida) {
  const caixa = el('div', 'stack g4');
  caixa.appendChild(el('span', 'micro', rotulo));
  caixa.appendChild(el('span', 'v', valor ?? semMedida));
  /* A referência dos pares NUNCA é opcional quando existe: repetir é o
     protocolo em pré-natal e é achado em rastreio, e o mesmo "2,4 por paciente"
     lê ao contrário nos dois. Número sozinho aqui seria acusação sem régua. */
  if (pares) caixa.appendChild(el('span', 'sub', `pares: ${pares}`));
  return caixa;
}

/** Bloco com título e corpo, na moldura das tabelas. */
function secao(titulo, sub) {
  const cartao = el('div', 'tbl');
  const topo = el('div', 'tbl-hd');
  const t = el('div', 'stack g4');
  t.appendChild(el('span', 't', titulo));
  if (sub) t.appendChild(el('span', 'sub', sub));
  topo.appendChild(t);
  cartao.appendChild(topo);
  const corpo = el('div', 'tbl-band');
  cartao.appendChild(corpo);
  return { cartao, corpo };
}

function montarRegua(destino, d) {
  const g = d.regua;
  const { cartao, corpo } = secao('Posição na área',
    g?.razao_fmt ? `${g.razao_fmt} a referência dos pares` : null);
  if (!g) {
    corpo.appendChild(el('span', 'sub',
      'sem referência apurável na área para este procedimento'));
    destino.appendChild(cartao);
    return;
  }

  /* `.ruler` do contrato: eixo, faixa interquartil, referência, critério e a
     marca do cooperado. Tudo posicionado por % que vem do motor — a tela não
     calcula posição, senão a marca cairia num lugar aqui e noutro na tabela. */
  const regua = el('div', 'ruler');
  regua.appendChild(el('div', 'axis'));

  const iqr = el('div', 'iqr');
  iqr.style.left = `${g.iqr.pos_pct}%`;
  iqr.style.width = `${g.iqr.largura_pct}%`;
  iqr.title = g.iqr.rotulo;
  regua.appendChild(iqr);

  /* REFERÊNCIA e CRITÉRIO seguem os parâmetros ativos da barra de critérios —
     trocar o alvo ou o gatilho move estas linhas. Por isso cada uma carrega o
     próprio nome na legenda: linha que muda de lugar sem dizer o que é vira
     enfeite. */
  const med = el('div', 'med');
  med.style.left = `${g.referencia.pos_pct}%`;
  med.title = `${g.referencia.rotulo}: ${g.referencia.valor_fmt}`;
  regua.appendChild(med);

  if (g.criterio) {
    const crit = el('div', 'crit');
    crit.style.left = `${g.criterio.pos_pct}%`;
    crit.title = `${g.criterio.rotulo}: ${g.criterio.valor_fmt}`;
    regua.appendChild(crit);
  }

  const marca = el('div', `mk ${g.marca.classe}`);
  marca.style.left = `${g.marca.pos_pct}%`;
  marca.title = `este cooperado: ${g.marca.valor_fmt}`;
  regua.appendChild(marca);

  corpo.appendChild(regua);

  /* A legenda é o que torna a régua legível sem hover — e hover não existe no
     toque. Ordem igual à da régua: pares, referência, critério, ele. */
  const legenda = el('div', 'row g12 flexwrap');
  const chave = (classe, texto) => {
    const c = el('span', 'row g4');
    c.appendChild(el('i', `lg lg-${classe}`));
    c.appendChild(el('span', 'sub', texto));
    return c;
  };
  legenda.appendChild(chave('iqr', g.iqr.rotulo));
  legenda.appendChild(chave('med', `${g.referencia.rotulo} ${g.referencia.valor_fmt}`));
  if (g.criterio) {
    legenda.appendChild(chave('crit',
      `${g.criterio.rotulo} ${g.criterio.valor_fmt}`
      + (g.criterio.ajustado ? ' (ajustado pelo n)' : '')));
  }
  legenda.appendChild(chave('mk', `este cooperado ${g.marca.valor_fmt}`));
  corpo.appendChild(legenda);

  if (g.sem_criterio_motivo) {
    corpo.appendChild(el('span', 'sub', g.sem_criterio_motivo));
  }
  destino.appendChild(cartao);
}


function montarRepeticao(destino, d) {
  const r = d.repeticao;
  const { cartao, corpo } = secao(
    'Repetição por paciente',
    `${r.n_pacientes ?? 0} pacientes receberam este exame no período`);
  if (r.motivo) {
    /* Ausência DECLARADA, nunca célula vazia: vazio lê como zero medido. */
    corpo.appendChild(el('span', 'sub', r.motivo));
    destino.appendChild(cartao);
    return;
  }
  const linha = el('div', 'row g20 flexwrap');
  linha.appendChild(medida('Solicitações por paciente', r.ocasioes_mediana_fmt,
                           r.pares_fmt, d.sem_medida));
  linha.appendChild(medida('Pacientes que repetem', r.pct_repetem_fmt,
                           r.pct_repetem_pares_fmt, d.sem_medida));
  if (r.intervalo_dias_fmt) {
    linha.appendChild(medida('Intervalo entre repetições',
                             `${r.intervalo_dias_fmt} dias`, null, d.sem_medida));
  }
  corpo.appendChild(linha);
  destino.appendChild(cartao);
}

function montarConcentracao(destino, d) {
  const c = d.concentracao;
  if (!c) return;
  const { cartao, corpo } = secao(
    'Concentração entre pacientes',
    c.share_top_fmt ? `os que mais concentram somam ${c.share_top_fmt} das solicitações` : null);
  const lista = el('div', 'stack g8');
  const maior = Math.max(...c.linhas.map((l) => l.pct), 0.0001);
  for (const l of c.linhas) {
    const item = el('div', 'row g8');
    /* Barra proporcional ao MAIOR da lista, não ao total: a leitura aqui é
       "quanto este se destaca entre os que concentram", e contra o total todas
       as barras somem. O número exato viaja ao lado, sempre. */
    const trilho = el('div', 'bar');
    const cheia = el('i', null);
    cheia.style.width = `${Math.round((l.pct / maior) * 100)}%`;
    trilho.appendChild(cheia);
    item.appendChild(el('span', 'mono', l.id));
    item.appendChild(trilho);
    item.appendChild(el('span', 'sub',
      `${l.ocasioes} ocasiões · ${l.pct_fmt}${l.intervalo_fmt ? ` · ${l.intervalo_fmt}` : ''}`));
    lista.appendChild(item);
  }
  if (c.resto?.n_pacientes) {
    lista.appendChild(el('span', 'sub',
      `outros ${c.resto.n_pacientes} pacientes somam ${c.resto.pct_fmt}`));
  }
  corpo.appendChild(lista);
  destino.appendChild(cartao);
}

function montarAutorreferencia(destino, d) {
  const a = d.autorreferencia;
  const { cartao, corpo } = secao('Autorreferência');
  if (a.apresentavel) {
    corpo.appendChild(medida('Solicitou e executou', a.taxa_fmt,
                             null, d.sem_medida));
    /* A cobertura viaja SEMPRE junto da taxa — é premissa declarada no motor,
       não nota de rodapé: a taxa vale sobre os itens com conta localizada. */
    corpo.appendChild(el('span', 'sub',
      `apurado sobre ${a.itens_com_conta} de ${a.itens} itens (${a.cobertura_fmt})`));
  } else {
    corpo.appendChild(el('span', 'sub', a.motivo ?? d.sem_medida));
    if (a.cobertura_fmt) {
      corpo.appendChild(el('span', 'sub',
        `apenas ${a.itens_com_conta} de ${a.itens} itens têm conta localizada (${a.cobertura_fmt})`));
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

  const topo = el('div', 'row row-between');
  const titulo = el('div', 'stack g4');
  titulo.appendChild(el('span', 't', linha.descricao));
  titulo.appendChild(el('span', 'mono sub', linha.codigo));
  topo.appendChild(titulo);
  const fechar = el('button', 'painel-x', '✕');
  fechar.setAttribute('aria-label', 'Fechar painel do procedimento');
  fechar.addEventListener('click', aoFechar);
  topo.appendChild(fechar);
  destino.appendChild(topo);

  const corpo = el('div', 'stack');
  destino.appendChild(corpo);
  /* Estado de carga na PRÓPRIA superfície que vai receber o dado: painel que
     abre vazio e enche depois faz o leitor duvidar se clicou. */
  const carregando = el('span', 'sub', 'carregando…');
  corpo.appendChild(carregando);

  let d;
  try {
    d = await buscar(`/api/cooperado/${cooperadoId}/procedimento/${linha.codigo}`);
  } catch {
    carregando.textContent = 'não foi possível carregar este procedimento';
    return;
  }
  corpo.replaceChildren();

  montarRegua(corpo, d);
  montarRepeticao(corpo, d);
  montarConcentracao(corpo, d);
  montarAutorreferencia(corpo, d);

  if (d.confianca?.rotulo) {
    corpo.appendChild(el('span', 'sub', d.confianca.detalhe ?? d.confianca.rotulo));
  }
}
