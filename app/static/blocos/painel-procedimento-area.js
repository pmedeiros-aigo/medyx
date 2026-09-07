/* blocos/painel-procedimento-area.js — o painel lateral de UM exame da área.
 *
 * O irmão de `painel-procedimento.js` com a unidade de análise trocada. Lá a
 * pergunta é "de onde vem o volume DESTE médico"; aqui é **este exame é norma
 * da área ou hábito de alguns**, e a diferença não é de grau.
 *
 * O caso que motivou o painel, em Ginecologia:
 *
 *   US Transvaginal            mediana 0,283 · P75 0,355   difuso, 15 acima
 *   US Estruturas Superficiais mediana 0,032 · P75 0,135   subgrupo, 13 acima
 *
 * Nas colunas da tabela as duas linhas se parecem — prevalência alta, excedente
 * grande. Na distribuição, não: no segundo o P75 é quatro vezes a referência,
 * "normal" é quase zero e um punhado transformou o exame em rotina. O primeiro
 * é discussão de protocolo, o segundo é auditoria. Nenhuma coluna da tabela
 * separa os dois, e é isso que o painel existe para mostrar.
 *
 * ── mesma casca, outro conteúdo ─────────────────────────────────────────────
 *
 * Estética, gramática e componentes são os do painel do dossiê: `.pnl-sec` como
 * seção sem cartão, `.pnl-rot` para o rótulo, `.v` para a frase de leitura,
 * `.pnl-vals`/`.pnl-val` para os números com marca, `.plot .plot-sm` para o box
 * plot e `evolucao.js` para os trimestres. Quem aprendeu a ler um lê o outro.
 *
 * ── o que este arquivo NÃO faz ──────────────────────────────────────────────
 *
 * Não calcula e não redige. A API manda tudo formatado, com as frases de
 * leitura escritas e os motivos de ausência declarados; aqui só se imprime.
 */
'use strict';

import { el, posicionado } from '../lib/dom.js';
import { buscar } from '../lib/api.js';
import { posicionarEmEnxame } from '../lib/enxame.js';
import { montarEvolucao as montarSerieTrimestral } from './evolucao.js';
import { colapsavel } from '../lib/colapsar.js';

/**
 * Uma seção do painel — a mesma de `painel-procedimento.js`.
 *
 * `recolhivel` acrescenta a seta do resto do app (`lib/colapsar.js`, a mesma
 * dos cartões de gráfico da página). Só a lista de nomes a recebe: ela é a
 * única seção que cresce com o dado — de 3 a 10 nomes, mais a cauda revelada —
 * e a única que o leitor pode querer fora do caminho enquanto compara os
 * números das outras. As demais têm altura fixa e recolher cada uma delas
 * custaria mais cliques do que rolagem.
 */
function secao(rotulo, definicao, { figura = false, recolhivel = null } = {}) {
  const bloco = el('section', `pnl-sec${figura ? ' pnl-sec-fig' : ''}`);
  const t = el('span', 'pnl-rot', rotulo);
  if (definicao) t.title = definicao;
  /* Com a seta, o rótulo passa a dividir uma LINHA com ela; sem, continua sendo
     o primeiro filho direto, como nas outras seções e no painel do dossiê. */
  if (recolhivel) {
    const cab = el('div', 'pnl-sec-hd');
    cab.appendChild(t);
    bloco.appendChild(cab);
  } else {
    bloco.appendChild(t);
  }
  const corpo = el('div', 'pnl-cnt');
  bloco.appendChild(corpo);
  return {
    cartao: bloco,
    corpo,
    /* A seta só entra DEPOIS de a seção estar montada: `colapsavel` reaplica o
       estado salvo, e aplicá-lo antes do conteúdo existir esconderia um corpo
       vazio e mediria a altura errada. */
    recolher: () => {
      if (recolhivel) colapsavel(bloco, recolhivel, { seletorTopo: '.pnl-sec-hd' });
    },
  };
}


/**
 * A DISTRIBUIÇÃO DA ÁREA neste exame: o box plot do painel do dossiê com o
 * enxame da tela de Área por cima.
 *
 * No painel do cooperado o box plot carrega UM ponto, porque a pergunta é "onde
 * ele está". Aqui não há um ponto para achar: há a FORMA, e a forma é a
 * resposta. Por isso os pontos entram — sem eles, duas distribuições muito
 * diferentes desenhariam a mesma caixa.
 *
 * A tinta segue a variante E do artboard "Medyx Escala de Cor" ("sem escala e
 * sem brilho"): DOIS ESTADOS, e só. Quem está dentro do padrão da área é massa
 * cinza; quem cruzou o critério é verde chapado. Sem rampa e sem halo — um
 * ponto é um ponto, e o contraste já basta para o olho achar os poucos que
 * importam.
 *
 * O que se perde, e onde ele é recuperado: a tinta deixa de dizer QUANTO. A
 * lista logo abaixo ordena por excedente e acende o ponto no hover, que é o
 * canal onde essa pergunta passou a viver.
 *
 * O enxame precisa da LARGURA EM PIXELS da plotagem, que só existe depois de o
 * elemento estar no documento — por isso os pontos entram num segundo passe,
 * como na tela de Área.
 */
function distribuicao(destino, d) {
  const g = d.distribuicao;
  const { cartao, corpo } = secao('Distribuição na área',
    'Solicitações deste exame por consulta, um ponto por cooperado que o '
    + 'solicita. A posição é régua da área e não se move com o recorte; o verde '
    + 'marca quem passou o critério de revisão.', { figura: true });
  if (!g) {
    corpo.appendChild(el('span', 'sub',
      'Cooperados insuficientes na área para análise comparativa.'));
    destino.appendChild(cartao);
    return null;
  }

  /* A LEITURA antes do desenho: ela diz o que a forma significa, e sem ela o
     leitor precisa saber interpretar assimetria de box plot para tirar do
     gráfico a única conclusão que ele carrega. Vem redigida do motor. */
  if (g.leitura) corpo.appendChild(el('span', 'v', g.leitura));

  const plot = el('div', 'plot plot-sm plot-enxame');
  if (g.haste) {
    plot.appendChild(posicionado('div', 'haste', g.haste.pos_pct, g.haste.largura_pct));
    plot.appendChild(posicionado('div', 'tampa', g.haste.pos_pct));
    plot.appendChild(posicionado('div', 'tampa',
                                 g.haste.pos_pct + g.haste.largura_pct));
  }
  plot.appendChild(posicionado('div', 'iqrband', g.iqr.pos_pct, g.iqr.largura_pct));
  plot.appendChild(posicionado('div', 'refline', g.referencia.pos_pct));
  if (g.criterio) {
    plot.appendChild(posicionado('div', 'refline tracejada', g.criterio.pos_pct));
  }
  corpo.appendChild(plot);

  const vals = el('div', 'pnl-vals');
  const par = (rotulo, valor, marca) => {
    const c = el('div');
    const r = el('span', 'micro pnl-mk-rot');
    if (marca) r.appendChild(el('i', `pnl-mk ${marca}`));
    r.appendChild(document.createTextNode(rotulo));
    c.appendChild(r);
    c.appendChild(el('span', 'pnl-val', valor));
    return c;
  };
  vals.appendChild(par(g.referencia.rotulo, g.referencia.valor_fmt, 'mk-ref'));
  if (g.criterio) {
    vals.appendChild(par(g.criterio.rotulo
      + (g.criterio.ajustado ? ' · ajustado ao tamanho do grupo' : ''),
      g.criterio.valor_fmt, 'mk-crit'));
  }
  corpo.appendChild(vals);

  /* A LEGENDA DOS PONTOS, do artboard: duas marcas, que são os próprios pontos
     no tamanho e na tinta em que aparecem acima. Sem ela, "cinza" e "verde"
     ficam por conta do leitor deduzir — e a variante E aposta justamente em
     não ter nada mais para decodificar. */
  const legenda = el('div', 'legend');
  const marca = (classe, texto) => {
    const sp = document.createElement('span');
    sp.append(el('i', classe), document.createTextNode(texto));
    legenda.appendChild(sp);
  };
  marca('pt-mk-fundo', 'Dentro do padrão da área');
  if (g.criterio) marca('pt-mk-acima', 'Acima do critério de revisão');
  corpo.appendChild(legenda);
  corpo.appendChild(el('span', 'sub',
    `Referência apurada entre ${g.n_pares}`
    + (g.n_area ? ` dos ${g.n_area}` : '')
    + ' cooperados da área, os que solicitam este exame.'));
  if (g.sem_criterio_motivo) corpo.appendChild(el('span', 'sub', g.sem_criterio_motivo));
  destino.appendChild(cartao);

  /* SEGUNDO PASSE: o empacotador do enxame lê a largura real da plotagem, e
     dentro de um elemento fora do documento ela é 0 — todos os pontos
     empilhariam no mesmo lugar. */
  const estilo = getComputedStyle(document.documentElement);
  const diametro = parseFloat(estilo.getPropertyValue('--ch-dot')) || 7;
  /* O JITTER CHEIO da tela de Área, que o `.plot-enxame` comporta: a 56px de
     altura o empacotador estourava o teto em 14 dos 53 pontos, com 26 colisões,
     e a nuvem parecia empilhada. */
  const jitter = parseFloat(estilo.getPropertyValue('--ch-jitter')) || 34;
  const base = Math.round(plot.clientHeight / 2);
  const alturas = posicionarEmEnxame(g.pontos, plot.clientWidth, jitter,
                                     diametro, base);
  /* Quem está FORA do recorte recua, com a mesma mecânica da distribuição da
     tela de Área: a posição continua sendo a régua da área inteira, mas o
     excedente que pinta o ponto é o do conjunto em cena. */
  if (g.n_fora_do_recorte) plot.classList.add('com-recorte');
  g.pontos.forEach((p, i) => {
    const s = posicionado('span',
      `pt${p.acima ? ' pt-acima' : ''}${p.em_cena ? ' pt-no-recorte' : ''}`,
      p.pos_pct);
    /* `--i` NÃO é escrito aqui: a variante E não tem rampa, e uma intensidade
       pendurada no elemento sem nada que a leia é o próximo valor a divergir em
       silêncio. O campo continua no payload porque é a mesma forma que os
       outros gráficos de distribuição consomem. */
    s.style.bottom = `${alturas[i]}px`;
    /* O BALÃO ancorado pela borda nos extremos do eixo: no centro do ponto ele
       nasce fora da gaveta e era ele que criava a barra de rolagem horizontal. */
    const lado = p.pos_pct > 72 ? ' tip-fim' : (p.pos_pct < 28 ? ' tip-ini' : '');
    const dica = el('span', `tip${lado}`);
    dica.appendChild(el('b', null, `${p.id} · ${p.valor_fmt}`));
    dica.appendChild(el('em', null, p.leitura));
    if (p.excedente_fmt) {
      dica.appendChild(el('em', null,
        `${p.excedente_fmt} solicitações acima`
        + (p.reais_fmt ? ` · ${p.reais_fmt}` : '')));
    }
    if (p.consultas_fmt) {
      dica.appendChild(el('em', null, `${p.consultas_fmt} consultas na janela`));
    }
    s.appendChild(dica);
    s.dataset.coop = p.id;
    plot.appendChild(s);
  });
  return plot;
}


/* QUANTAS CONVERSAS RESOLVEM. A pergunta prática que fecha a distribuição:
   saber que o excedente é de um subgrupo não diz de quantos. */
function nucleo(destino, d) {
  const n = d.nucleo;
  if (!n) return;
  const { cartao, corpo } = secao('Concentração entre cooperados',
    'Quantos cooperados somam a maior parte do excedente deste exame no '
    + 'recorte, na ordem do maior para o menor.');
  corpo.appendChild(el('span', 'v', n.frase));
  if (n.reais_fmt) {
    corpo.appendChild(el('span', 'sub',
      `${n.reais_fmt} de custo excedente entre eles.`));
  }
  destino.appendChild(cartao);
}


/* QUEM. É a seção que fecha o painel em AÇÃO: o passo seguinte do auditor é
   sempre uma pessoa, e sem esta lista a resposta exigia fechar o painel, trocar
   de aba e procurar o exame na tabela de cada cooperado.
   Lista truncada com o resto declarado: oito nomes cabem na coluna, e o nono em
   diante é a cauda que a seção acima já resumiu. */
function acima(destino, d, hrefDoCooperado, plot) {
  const a = d.acima;
  const { cartao, corpo, recolher } = secao('Acima do critério',
    'Cooperados em cena cuja frequência neste exame passou o critério de '
    + 'revisão da área, do maior excedente para o menor.',
    { recolhivel: 'painel-exame-acima' });
  if (!a?.linhas?.length) {
    corpo.appendChild(el('span', 'sub',
      'Nenhum cooperado em cena passou o critério neste exame.'));
    destino.appendChild(cartao);
    recolher();
    return;
  }

  /* MESMA entrada da gaveta de excluídos (`.pnl-ent`), e pelo mesmo motivo: é
     uma lista de pessoas com o chevron do dossiê no fim. Um componente, duas
     listas — a alternativa era um segundo desenho de linha de pessoa no mesmo
     app.

     QUANTOS APARECEM vem do motor (`n_visiveis`): é o núcleo que soma 80% do
     excedente, a mesma regra que a seção logo acima anuncia. O resto existe no
     payload e é revelado sob demanda — a cauda não é escondida, é adiada
     (§10, disclosure progressivo). */
  const entradas = [];
  a.linhas.forEach((l, i) => {
    const ent = el('div', 'pnl-ent');
    ent.dataset.coop = l.id;
    if (i >= a.n_visiveis) ent.hidden = true;
    const hd = el('div', 'row row-between');
    const txt = el('div', 'stack g4');
    txt.appendChild(el('span', 'mono', l.id));
    txt.appendChild(el('span', 'dlg-u',
      `${l.taxa_fmt} por consulta`
      + (l.razao_fmt ? ` · ${l.razao_fmt} a referência` : '')
      + ` · ${l.excedente_fmt} solicitações acima`
      + (l.reais_fmt ? ` · ${l.reais_fmt}` : '')));
    hd.appendChild(txt);
    if (hrefDoCooperado) {
      const link = document.createElement('a');
      link.className = 'chev';
      link.href = hrefDoCooperado(l.id);
      link.textContent = '\u203a';
      link.title = 'Abrir o dossiê analítico deste cooperado.';
      link.setAttribute('aria-label', `abrir dossiê analítico de ${l.id}`);
      hd.appendChild(link);
    }
    ent.appendChild(hd);
    corpo.appendChild(ent);
    entradas.push(ent);
  });

  /* A REGRA DO CORTE dita em voz alta, logo abaixo da lista: sem ela "por que
     oito e não treze" fica sem resposta na tela, e um corte sem regra lê como
     arbitrário — que é o que ele era antes. */
  if (a.criterio_do_corte && a.resto) {
    corpo.appendChild(el('span', 'sub', a.criterio_do_corte));
  }
  if (a.resto) {
    /* MESMA marcação da ação da linha de contexto ("ver os 6 fora da
       referência"): link inline, não botão. É a convenção do app para revelar
       uma lista sem sair de onde se está. */
    const linha = el('div');
    const link = document.createElement('a');
    link.href = '#';
    link.textContent = `Ver os outros ${a.resto} acima do critério`;
    link.addEventListener('click', (ev) => {
      ev.preventDefault();
      const abrindo = link.dataset.aberto !== 'sim';
      for (let i = a.n_visiveis; i < entradas.length; i += 1) {
        entradas[i].hidden = !abrindo;
      }
      link.dataset.aberto = abrindo ? 'sim' : 'nao';
      /* "Mostrar só os que concentram o excedente" saiu em 2026-09-07: TODOS os
         listados têm excedente — é o que "acima do critério" significa —, e a
         frase sugeria que os outros cinco não tivessem. O que separa os dois
         grupos é a FATIA que cada um carrega, e é isso que o rótulo diz agora,
         com o mesmo 80% da seção acima. */
      link.textContent = abrindo
        ? `Mostrar só os ${a.n_visiveis} que somam ${a.fracao_fmt} do excedente`
        : `Ver os outros ${a.resto} acima do critério`;
    });
    linha.appendChild(link);
    corpo.appendChild(linha);
  }

  /* O FIO ENTRE A LISTA E O GRÁFICO. A lista ordena por EXCEDENTE e o eixo do
     gráfico é a TAXA — grandezas diferentes, porque o excedente é a distância à
     referência VEZES as consultas. Em US Estruturas Superficiais o primeiro da
     lista é o 11º ponto mais à direita, e o ponto mais à direita de todos nem
     entra na lista. A cor já os reconciliou (o mais escuro é o primeiro da
     lista); o hover fecha a leitura, mostrando QUAL ponto é cada nome.
     Mesma mecânica do `destacar` entre a distribuição e a tabela de cooperados
     da página. */
  if (plot) {
    const acender = (id) => {
      plot.classList.toggle('com-selecao', !!id);
      for (const pt of plot.querySelectorAll('.pt')) {
        pt.classList.toggle('pt-escolhido', !!id && pt.dataset.coop === id);
      }
    };
    for (const ent of entradas) {
      ent.addEventListener('mouseenter', () => acender(ent.dataset.coop));
      ent.addEventListener('mouseleave', () => acender(null));
      ent.addEventListener('focusin', () => acender(ent.dataset.coop));
      ent.addEventListener('focusout', () => acender(null));
    }
    /* e o caminho de volta: o ponto acende a linha dele */
    for (const pt of plot.querySelectorAll('.pt')) {
      const marcar = (on) => {
        const ent = entradas.find((e) => e.dataset.coop === pt.dataset.coop);
        ent?.classList.toggle('pnl-ent-alvo', on);
      };
      pt.addEventListener('mouseenter', () => marcar(true));
      pt.addEventListener('mouseleave', () => marcar(false));
    }
  }
  destino.appendChild(cartao);
  recolher();
}


/* QUANTO PESA. A primeira seção do corpo, porque decide se vale a pena ler o
   resto: um exame com 0,3% do custo da área não muda a conversa, por mais
   assimétrica que seja a distribuição dele. */
function peso(destino, d) {
  const p = d.peso;
  if (!p) return;
  const { cartao, corpo } = secao('Peso na área',
    'Participação deste exame no que os cooperados em cena solicitaram no '
    + 'período. Preços internos provisórios, ainda não homologados contra a '
    + 'tabela contratual.');
  corpo.appendChild(el('span', 'v',
    `${p.proporcao_fmt} das solicitações do recorte`
    + (p.proporcao_custo_fmt ? ` e ${p.proporcao_custo_fmt} do custo.` : '.')));
  corpo.appendChild(el('span', 'sub',
    `Volume: ${p.solicitacoes_fmt} solicitações`
    + (p.custo_unitario_fmt ? ` · ${p.custo_unitario_fmt} por solicitação` : '')));
  if (p.custo_total_fmt) {
    const c = el('span', 'sub',
      `Custo: ${p.custo_total_fmt} no período`
      + (p.excedente_pct_fmt ? ` · ${p.excedente_pct_fmt} acima da referência` : ''));
    c.title = 'Valor apurado com o preço mediano das contas do período.';
    corpo.appendChild(c);
  }
  destino.appendChild(cartao);
}


/* PARA QUEM. Mesma barra com o traço da referência da tela do cooperado: a
   fatia do recorte contra a fatia da área na mesma faixa. Quando o recorte é a
   área inteira as duas coincidem, e a comparação some sozinha. */
function faixas(destino, d) {
  const f = d.faixas;
  if (!f?.faixas?.length) return;
  const { cartao, corpo } = secao('Solicitações por faixa etária',
    'Repartição das solicitações deste exame pela idade de quem as recebeu, '
    + 'ao lado da mesma repartição na área de atuação.', { figura: true });

  /* MESMA marcação do painel do dossiê (`.cart-faixas`): a barra é a fatia do
     recorte e o traço é a da área. Quando o recorte é a área inteira os dois
     coincidem, e a comparação some sozinha, sem caso especial. */
  const grade = el('div', 'cart-faixas');
  for (const x of f.faixas) {
    const item = el('div', 'cart-f');
    const rot = el('div', 'row row-between');
    rot.appendChild(el('span', 'cart-f-k', `${x.rotulo} · ${x.n_fmt}`));
    rot.appendChild(el('span', 'cart-f-v', x.fracao_fmt));
    item.appendChild(rot);

    const trilho = el('div', 'cart-bar');
    const cheia = el('i', null);
    cheia.style.width = `${x.largura_pct}%`;
    trilho.appendChild(cheia);
    if (x.area_pct != null) {
      const marca = el('b', null);
      marca.style.left = `${x.area_pct}%`;
      trilho.appendChild(marca);
    }
    trilho.title = x.titulo;
    item.appendChild(trilho);

    const ref = el('span', 'cart-f-a tem-hover', x.area_fmt);
    ref.title = 'Fatia desta faixa etária entre todas as solicitações deste '
      + 'exame na área de atuação, sob a mesma janela e o mesmo recorte de '
      + 'consultas.';
    item.appendChild(ref);
    grade.appendChild(item);
  }
  corpo.appendChild(grade);

  const legenda = el('div', 'legend');
  const marca = (classe, texto) => {
    const sp = document.createElement('span');
    sp.append(el('i', classe), document.createTextNode(texto));
    legenda.appendChild(sp);
  };
  marca('cart-mk-eu', 'Neste recorte');
  marca('cart-mk-area', 'Referência da área');
  corpo.appendChild(legenda);
  destino.appendChild(cartao);
}


/* QUANTAS VEZES NOS MESMOS. Distingue "muitos pacientes uma vez" de "poucos
   pacientes muitas vezes" — dois excedentes idênticos no número e diferentes na
   conversa. A lista de quem concentra, que o painel do dossiê traz, não existe
   aqui: um beneficiário responder por mais de 10% das solicitações de um exame
   na ÁREA inteira não acontece, e lista vazia lê como dado faltando. */
function repeticao(destino, d) {
  const r = d.repeticao;
  if (!r) return;
  const { cartao, corpo } = secao('Repetição por beneficiário',
    'Beneficiários que receberam este exame no recorte, quantas vezes em '
    + 'média e que parcela deles voltou a recebê-lo no período.');
  corpo.appendChild(el('span', 'v',
    `${r.n_beneficiarios_fmt} beneficiários`
    + (r.itens_por_beneficiario_fmt
      ? `, ${r.itens_por_beneficiario_fmt} solicitações cada.` : '.')));
  if (r.pct_repetem_fmt) {
    corpo.appendChild(el('span', 'sub',
      `${r.pct_repetem_fmt} receberam mais de uma vez (${r.n_repetem_fmt})`
      + (r.intervalo_fmt ? ` · intervalo mediano de ${r.intervalo_fmt} dias`
                         : '')));
  }
  destino.appendChild(cartao);
}


/* QUEM EXECUTOU. No agregado da área o portão de cobertura passa com folga mais
   vezes do que por par, e é por isso que a leitura vale mais aqui: por
   (cooperado, exame) a cobertura mediana é de 11%, e sobre 11% a taxa salta
   entre 0% e 100%. */
function autorreferencia(destino, d) {
  const a = d.autorreferencia;
  const { cartao, corpo } = secao('Autorreferenciamento',
    'Parcela das solicitações executadas pelo próprio solicitante, apurada '
    + 'sobre as solicitações com conta localizada. Indicador para '
    + 'investigação, não conclusão.');
  if (a.apresentavel) {
    corpo.appendChild(el('span', 'v', a.taxa_fmt));
    const cob = el('span', 'sub',
      `Base: ${a.itens_com_conta_fmt} de ${a.itens_fmt} solicitações com `
      + `executante identificado (${a.cobertura_fmt})`);
    cob.title = 'Quem executou um pedido só é conhecido quando a solicitação '
      + 'encontra a conta correspondente. O método presume que os demais se '
      + 'comportam como os observados.';
    corpo.appendChild(cob);
  } else {
    corpo.appendChild(el('span', 'sub', a.motivo ?? d.sem_medida));
    if (a.cobertura_fmt) {
      corpo.appendChild(el('span', 'sub',
        `Executante identificado em ${a.itens_com_conta_fmt} de `
        + `${a.itens_fmt} solicitações (${a.cobertura_fmt}), abaixo do mínimo `
        + 'para apurar a taxa.'));
    }
  }
  destino.appendChild(cartao);
}


/* FOI SEMPRE ASSIM. A última pergunta do painel, como no dossiê. A série corre
   sobre os cooperados ACIMA DO CRITÉRIO, e não sobre o recorte inteiro: é o que
   faz os quatro trimestres somarem o excedente que a seção "Peso na área"
   anuncia. */
function evolucao(destino, d) {
  const linhas = d.evolucao?.linhas;
  if (!linhas?.length) return;
  const { cartao, corpo } = secao('Custo por trimestre',
    'Custo deste exame em cada trimestre do período entre os cooperados acima '
    + 'do critério, com a parcela acima da referência da área destacada. Os '
    + 'quatro somam o custo excedente do ano.', { figura: true });
  montarSerieTrimestral(corpo, d.evolucao, { semCartao: true });

  /* O VOLUME QUE PRODUZIU CADA BARRA, na MESMA grade do painel do dossiê: uma
     barra de R$ 44 mil não diz se são 800 pedidos ou 80, e é essa a diferença
     entre tendência e ruído. Rótulo em cima, valores embaixo, cada um sob a sua
     barra pela calha compartilhada (`--evo-calha`). */
  const grade = el('div', 'evo-tab');
  grade.style.setProperty('--evo-cols', String(linhas.length));
  const linha = (rot, valores) => {
    grade.appendChild(el('span', 'evo-tab-k', rot));
    const faixa = el('div', 'evo-tab-v');
    for (let i = 0; i < linhas.length; i += 1) {
      faixa.appendChild(el('span', null, valores[i] ?? ''));
    }
    grade.appendChild(faixa);
  };
  linha('custo total', linhas.map((l) => l.custo_fmt ?? ''));
  if (linhas.some((l) => l.excedente_reais_fmt)) {
    /* O RÓTULO SEGUE O SINAL, como no painel do dossiê: o número do ano é
       cortado em zero, a série trimestral não é (os quatro precisam somar o
       ano), e aí um trimestre abaixo da referência entra negativo. Negativo,
       eles não são "custo excedente": são a CONTRIBUIÇÃO de cada trimestre. */
    const temNegativo = linhas.some((l) => l.exc_negativo);
    linha(temNegativo ? 'contribuição para o excedente do ano'
                      : 'acima da referência',
          linhas.map((l) => l.excedente_reais_fmt ?? ''));
  }
  linha('solicitações', linhas.map((l) => l.solicitacoes_fmt ?? ''));
  linha('beneficiários', linhas.map((l) => l.pacientes_fmt ?? ''));
  linha('por beneficiário', linhas.map((l) => l.por_paciente_fmt ?? ''));
  corpo.appendChild(grade);
  destino.appendChild(cartao);
}


/**
 * Monta (ou atualiza) o painel lateral do exame na tela de área.
 *
 * @param {HTMLElement} destino  a gaveta, já no <body>
 * @param {string} area  id da área, para o endpoint
 * @param {{codigo: string, descricao: string}} linha  a linha ou barra clicada
 * @param {object} recorte  o recorte ativo, que o achado do painel obedece
 * @param {() => void} aoFechar
 * @param {(id: string) => string} [hrefDoCooperado]  destino de cada nome
 * @param {(cd: string, ids: string[]) => void} [aoVerNaTabela]  leva os nomes
 *   para a aba Cooperados, localizados neste exame
 */
export async function abrirPainelDoExame(destino, area, linha, recorte,
                                         aoFechar, hrefDoCooperado,
                                         aoVerNaTabela) {
  destino.replaceChildren();
  destino.hidden = false;

  const topo = el('div', 'row row-between pnl-hd');
  const titulo = el('div', 'stack g4');
  titulo.appendChild(el('span', 't', linha.descricao ?? ''));
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
  const carregando = el('span', 'sub', 'Carregando…');
  corpo.appendChild(carregando);

  let d;
  try {
    d = await buscar(
      `/api/area/${encodeURIComponent(area)}/procedimento/${encodeURIComponent(linha.codigo)}`,
      { soMotor: true, extra: recorte ?? {} });
  } catch {
    carregando.textContent = 'Não foi possível carregar o detalhe deste procedimento.';
    return;
  }
  corpo.replaceChildren();

  /* A IDENTIDADE do exame antes de tudo: prevalência e qualidade da referência
     são as duas colunas da tabela que qualificam TODO o resto do painel, e a
     linha clicada fica atrás da gaveta. Uma linha, não uma seção. */
  if (d.qualidade) {
    const ident = el('div', 'pnl-ent');
    ident.appendChild(el('span', 'sub',
      `${d.qualidade.prevalencia_fmt} dos comparáveis solicitam · referência `
      + `${d.qualidade.rotulo} com ${d.qualidade.n_solicitantes} solicitantes`
      + (d.recorte?.rotulo ? ` · em cena: ${d.recorte.rotulo} (${d.recorte.n})` : '')));
    corpo.appendChild(ident);
  }

  /* Ordem de leitura: quanto pesa -> como se distribui -> quantos concentram ->
     quem são -> para quem -> quantas vezes nos mesmos -> quem executou -> como
     se comportou no tempo. É a mesma sequência do painel do dossiê com o
     sujeito trocado; o que muda é o meio da cadeia, onde lá se pergunta "em
     quais pacientes" e aqui "em quais cooperados". */
  peso(corpo, d);
  /* o gráfico devolve a plotagem: a lista abaixo acende o ponto de cada nome
     nela, e é esse fio que resolve a distância entre as duas ordens */
  const plot = distribuicao(corpo, d);
  nucleo(corpo, d);
  acima(corpo, d, hrefDoCooperado, plot);
  faixas(corpo, d);
  repeticao(corpo, d);
  autorreferencia(corpo, d);
  evolucao(corpo, d);

  /* RODAPÉ com a saída, como no painel do dossiê. A gaveta responde "quem pede
     este exame fora do padrão"; a pergunta seguinte é "e como esses estão no
     resto da prática deles?", e essa é a tabela de Cooperados — com ordenação,
     colunas agregadas e busca, que a lista da gaveta não tem e não deve ter.
     O link LOCALIZA a tabela nestes nomes; não recorta nada, e a régua e todos
     os agregados da página continuam onde estavam. */
  if (aoVerNaTabela && d.acima?.n) {
    const pe = el('div', 'pnl-ft');
    const b = el('button', 'btn');
    b.type = 'button';
    b.textContent = `Ver ${d.acima.n === 1 ? 'o cooperado' : `os ${d.acima.n}`} `
      + 'na tabela de Cooperados';
    b.addEventListener('click', () => {
      aoVerNaTabela(d.codigo, d.acima.linhas.map((l) => l.id));
    });
    pe.appendChild(b);
    destino.appendChild(pe);
  }
}
