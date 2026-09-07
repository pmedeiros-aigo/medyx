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
 * pares ao lado e os motivos de ausência escritos; aqui só se imprime.
 *
 * A posição vem em BOX PLOT, o mesmo componente `.plot` da distribuição da tela
 * de Área, na variante compacta: aqui a pergunta é "onde ele está", e o enxame
 * de 60 pontos numa coluna de 380px vira ruído. A forma da distribuição
 * continua sendo pergunta da tela de Área, a um clique. Os dois compartilham a
 * geometria do motor (`_escala`/`_pos`), então a marca cai no mesmo lugar nas
 * duas telas.
 */
'use strict';

import { el, posicionado } from '../lib/dom.js';
/* Apelido obrigatório: este arquivo já tem um `montarEvolucao` local, que é
   outra coisa (a consistência entre trimestres, em quadrados). */
import { montarEvolucao as montarSerieTrimestral } from './evolucao.js';
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
 * O rótulo é `.pnl-rot` e o número é `.v`: a hierarquia vem do TAMANHO e da cor,
 * não de uma caixa em volta. É a mesma gramática das faixas de KPI do dossiê.
 *
 * ── um ritmo só, e ele mora no CSS ──────────────────────────────────────────
 * O espaço entre o rótulo e o conteúdo é o MESMO espaço entre duas linhas de
 * conteúdo, e é igual em todas as seções. Antes cada seção montava o próprio
 * empilhamento (`stack g6` por fora, `stack g4` por dentro), e o resultado era
 * um ritmo diferente por seção: o rótulo caía a 8px do texto aqui e a 6px ali,
 * e as linhas de apoio se agrupavam em blocos que não significavam nada.
 * Quem tem gráfico respira mais (`.pnl-sec-fig`), porque desenho encostado no
 * rótulo lê como parte dele.
 */
function secao(rotulo, definicao, { figura = false } = {}) {
  const bloco = el('section', `pnl-sec${figura ? ' pnl-sec-fig' : ''}`);
  const t = el('span', 'pnl-rot', rotulo);
  if (definicao) t.title = definicao;
  bloco.appendChild(t);
  const corpo = el('div', 'pnl-cnt');
  bloco.appendChild(corpo);
  return { cartao: bloco, corpo };
}


/**
 * BOX PLOT da área para este exame, com um ponto: o cooperado.
 *
 * É o MESMO componente da distribuição da tela de Área (`.plot`, com `.haste`,
 * `.tampa`, `.iqrband`, `.refline` e `.pt`), na variante compacta `.plot-sm`.
 * Uma leitura, um desenho: manter dois gráficos diferentes para "onde ele está
 * na área" obrigava o leitor a reaprender a figura ao trocar de tela.
 *
 * Substituiu (2026-09-06) uma curva de densidade em SVG desenhada só aqui. A
 * curva mostrava a forma e escondia os quartis, que é o que se lê num painel de
 * caso; e ela trazia um segundo vocabulário visual (área preenchida, traços de
 * 1px) que não existia em nenhum outro lugar do app.
 *
 * DISCRIÇÃO É A REGRA: a caixa e a haste são neutras, as duas linhas se
 * distinguem pelo TRAÇO (contínua = referência, tracejada = critério) e não
 * pela cor, e o único elemento com tinta é o ponto do cooperado. É ele o
 * assunto do painel, e é o único que o olho precisa achar sozinho.
 *
 * Nada é calculado aqui: todas as posições vêm em `pos_pct` do motor.
 */
function boxplot(g) {
  const plot = el('div', 'plot plot-sm');

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

  /* O ponto por último, para ficar por cima da caixa e das linhas. O anel da
     cor do papel em volta dele (no CSS) é o que o separa da borda da caixa
     quando os dois coincidem. */
  const eu = posicionado('span', 'pt pt-eu', g.marca.pos_pct);
  plot.appendChild(eu);
  return plot;
}


function montarRegua(destino, d) {
  const g = d.regua;
  const { cartao, corpo } = secao('Frequência de solicitação',
    'Solicitações deste procedimento por consulta atendida, comparadas com o '
    + 'demais cooperados da área de atuação. A referência e o critério seguem os '
    + 'parâmetros ativos da análise.', { figura: true });
  if (!g) {
    corpo.appendChild(el('span', 'sub',
      'Cooperados insuficientes na área para análise comparativa.'));
    destino.appendChild(cartao);
    return;
  }

  if (g.razao_fmt) {
    corpo.appendChild(el('span', 'v', `${g.razao_fmt} a referência da área.`));
  }
  const fig = boxplot(g);
  fig.setAttribute('role', 'img');
  fig.setAttribute('aria-label',
    `Distribuição da área neste exame`
    + (g.haste ? `, de ${g.haste.min_fmt} a ${g.haste.max_fmt}` : '')
    + `. Este cooperado: ${g.marca.valor_fmt} solicitações por consulta. `
    + `${g.referencia.rotulo}: ${g.referencia.valor_fmt}.`);
  corpo.appendChild(fig);

  /* Cada valor recebe a MARCA com que ele aparece no gráfico logo acima: ponto
     cheio para o cooperado, traço contínuo para a referência, traço tracejado
     para o critério.
     Revoga a decisão anterior de não ter legenda ("a posição no gráfico já os
     identifica"): identifica para quem já sabe qual é qual. A marca custa 8px e
     tira do leitor a tarefa de casar três números com três traços de memória. */
  const vals = el('div', 'pnl-vals');
  /* Os TRÊS valores saem iguais. Quem distingue um do outro é a marca ao lado
     do rótulo, que é a mesma forma do desenho acima; tingir o número do
     cooperado de outra cor codificava o mesmo fato duas vezes e o tirava do
     padrão de número do resto do painel. */
  const par = (rotulo, valor, marca) => {
    const c = el('div');
    const r = el('span', 'micro pnl-mk-rot');
    if (marca) r.appendChild(el('i', `pnl-mk ${marca}`));
    r.appendChild(document.createTextNode(rotulo));
    c.appendChild(r);
    c.appendChild(el('span', 'pnl-val', valor));
    return c;
  };
  vals.appendChild(par('Este cooperado', g.marca.valor_fmt, 'mk-pt'));
  vals.appendChild(par(g.referencia.rotulo, g.referencia.valor_fmt, 'mk-ref'));
  if (g.criterio) {
    vals.appendChild(par(g.criterio.rotulo
      + (g.criterio.ajustado ? ' · ajustado ao tamanho do grupo' : ''),
      g.criterio.valor_fmt, 'mk-crit'));
  }
  corpo.appendChild(vals);
  corpo.appendChild(el('span', 'sub',
    `Referência apurada entre ${g.n_pares}`
    + (g.n_area ? ` dos ${g.n_area}` : '')
    + ` cooperados da área, os que solicitam este exame.`));
  if (g.sem_criterio_motivo) corpo.appendChild(el('span', 'sub', g.sem_criterio_motivo));
  destino.appendChild(cartao);
}


/* A SÉRIE DO EXAME, no fim do painel: as seções acima dizem onde ele está hoje,
   e esta responde a pergunta que sobra, se sempre esteve. Mesma barra do dossiê
   (custo em cinza, excedente dentro dele) e a mesma régua congelada, porque é o
   mesmo dinheiro visto por um recorte mais estreito.
   Sem o grid de cartões por trimestre: no painel não há largura para quatro. Os
   números por trimestre vivem na grade sob o gráfico, alinhados às barras. */
function montarEvolucaoDoExame(destino, d) {
  const linhas = d.evolucao?.linhas;
  if (!linhas?.length) return;
  const { cartao, corpo } = secao('Custo por trimestre',
    'Custo deste exame em cada trimestre do período, com a parcela acima da '
    + 'referência da área destacada quando ela existe. O quadrado da última '
    + 'linha marca outra coisa: os trimestres que passaram do critério de '
    + 'revisão, que fica acima da referência. Um trimestre pode ter parcela '
    + 'acima da referência sem ter passado do critério.', { figura: true });
  montarSerieTrimestral(corpo, d.evolucao, { semCartao: true });

  /* ── O VOLUME QUE PRODUZIU CADA BARRA ──────────────────────────────────────
     Uma barra de R$ 39 mil não diz se são 82 pedidos ou 3, e é essa a diferença
     entre tendência e ruído (rigor §1: o denominador anda junto do valor).
     `por paciente` é a única leitura nova das três; as outras duas são o
     denominador dela.
     Grade e não cartões: a coluna é estreita demais para quatro cartões lado a
     lado, e empilhados eles empurrariam o resto do painel para fora da tela.
     A grade CAI DEBAIXO DAS BARRAS: ela usa a mesma calha de rótulos e o mesmo
     vão entre colunas do gráfico (`--evo-calha`, no CSS), e por isso não repete
     mais o cabeçalho T1..T4 — o rótulo da barra logo acima já nomeia a coluna.
     Repetido, ele punha duas linhas de T1..T4 desalinhadas a 40px uma da outra,
     e era isso que fazia o leitor conferir de qual trimestre era cada número. */
  /* ── O QUE PRODUZIU CADA BARRA, alinhado sob ela ──────────────────────────
     RÓTULO EM CIMA, valores embaixo, e não rótulo à esquerda: a coluna de
     rótulos obrigava o GRÁFICO a recuar 88px para casar com ela, e o bloco
     inteiro começava mais à direita que todo o resto da aba. Sem a coluna, o
     rótulo ocupa a linha cheia a partir da borda da seção, e as quatro colunas
     de valor herdam a mesma calha do eixo (`--evo-calha`), que agora é só o que
     as marcas do eixo pedem. Resultado: tudo começa na mesma vertical e cada
     número continua exatamente sob a sua barra. */
  const grade = el('div', 'evo-tab');
  grade.style.setProperty('--evo-cols', String(linhas.length));
  const linha = (rot, montarCelula) => {
    grade.appendChild(el('span', 'evo-tab-k', rot));
    const faixa = el('div', 'evo-tab-v');
    for (let i = 0; i < linhas.length; i += 1) faixa.appendChild(montarCelula(i));
    grade.appendChild(faixa);
  };
  const texto = (valores) => (i) => el('span', null, valores[i] ?? '');

  /* O DINHEIRO ABRE A TABELA, nas duas linhas que a barra desenha: o custo do
     trimestre e a parcela dele acima da referência. Nenhum dos dois é escrito
     sobre o gráfico. Numa coluna de 48px, número sobre o desenho ou é cortado
     pela largura da barra, ou invade a coluna vizinha.
     A divisão que sai daí é a de sempre em produto de análise: o gráfico
     responde "como isso se move", a tabela responde "quanto exatamente". */
  linha('custo total', texto(linhas.map((l) => l.custo_fmt ?? '')));
  if (linhas.some((l) => l.excedente_reais_fmt)) {
    /* Ou o motor mediu o excedente e as quatro linhas o têm, ou não mediu e a
       linha inteira não existe: não há célula vazia possível aqui.

       O RÓTULO SEGUE O SINAL, e é o que resolve a contradição que o negativo
       criava. O número anual é CORTADO em zero: excedente nunca é negativo, por
       definição. A série trimestral NÃO é cortada, porque os quatro precisam
       somar exatamente o número do ano — e aí um trimestre em que ele pediu
       menos que a referência preveria entra negativo.
       Esses quatro números não são, portanto, "custo excedente": são a
       CONTRIBUIÇÃO de cada trimestre para o número do ano, e contribuição
       negativa é um trimestre que puxou o ano para baixo. Com todos positivos a
       linha continua sendo "acima da referência", que é mais direto. */
    const temNegativo = linhas.some((l) => l.exc_negativo);
    linha(temNegativo ? 'contribuição para o excedente do ano'
                      : 'acima da referência',
          texto(linhas.map((l) => l.excedente_reais_fmt ?? '')));
  }
  linha('solicitações', texto(linhas.map((l) => l.solicitacoes_fmt ?? '')));
  linha('pacientes', texto(linhas.map((l) => l.pacientes_fmt ?? '')));
  linha('por paciente', texto(linhas.map((l) => l.por_paciente_fmt ?? '')));

  /* A CONSISTÊNCIA entra como linha desta tabela, e não como seção própria. Ela
     responde outra pergunta (passou do critério?) sob outra régua (a do PRÓPRIO
     trimestre, não a do ano), e o texto da seção explica a diferença.
     Alinhada aqui, o quadrado ganha denominador: vazio ao lado de 76
     solicitações significa uma coisa, ao lado de 3 significa outra. */
  const tri = d.trimestres;
  if (tri?.length === linhas.length) {
    linha('acima do critério', (i) => {
      const q = tri[i];
      const cel = el('span', null);
      const quadro = el('div', 'spark');
      const marca = document.createElement('i');
      if (q.estado === 'sinalizado') marca.className = 'on';
      else if (q.estado === 'nao_avaliavel') marca.className = 'na';
      marca.title = q.estado === 'nao_avaliavel'
        ? (q.motivo ?? 'Trimestre sem medida.')
        : (q.sinalizado ? 'Acima do critério de revisão neste trimestre.'
                        : 'Dentro da referência neste trimestre.');
      quadro.appendChild(marca);
      cel.appendChild(quadro);
      return cel;
    });
  }
  corpo.appendChild(grade);
  destino.appendChild(cartao);
}


function montarRepeticao(destino, d) {
  const r = d.repeticao;
  const { cartao, corpo } = secao('Repetição por beneficiário',
    'Beneficiários que receberam este procedimento mais de uma vez no período, '
    + 'e o intervalo entre as solicitações. Repetição é rotina em acompanhamento '
    + 'e é achado em rastreio: a leitura depende da referência da área.');
  if (r.motivo) {
    /* Ausência declarada, com o motivo do léxico — célula vazia lê como zero
       medido, e não é. */
    corpo.appendChild(el('span', 'sub', r.motivo));
    destino.appendChild(cartao);
    return;
  }

  const frase = el('span', 'v');
  frase.textContent = `${r.pct_repetem_fmt} dos beneficiários com mais de uma solicitação.`;
  corpo.appendChild(frase);

  corpo.appendChild(el('span', 'sub',
    `Referência da área: ${r.pct_repetem_pares_fmt}`));
  if (r.intervalo_fmt) {
    const i = el('span', 'sub',
      `Intervalo entre solicitações: ${r.intervalo_fmt} dias`
      + (r.intervalo_pares_fmt ? ` · área: ${r.intervalo_pares_fmt} dias` : ''));
    i.title = 'Dias entre solicitações consecutivas do mesmo procedimento para o '
      + 'mesmo beneficiário, apurado apenas sobre quem repetiu.';
    corpo.appendChild(i);
  }
  /* Sem repetir "N beneficiários com este procedimento": a seção Alcance, acima,
     já traz esse número junto do denominador da carteira. */
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


/* PARA QUEM ele pede este exame, e como a área reparte as dela.
 *
 * Vem logo depois de Alcance por ser a mesma pergunta com um corte: alcance diz
 * para QUANTOS da carteira, esta seção diz para QUEM. E fecha a defesa que o
 * cartão do dossiê abre: lá se vê que a carteira dele é mais velha que a da
 * área, o que explica volume; aqui se vê se a repartição dos pedidos acompanha
 * a carteira ou vai além dela.
 *
 * A CONTAGEM é o número da linha; a FATIA é o que compara, porque contagem de
 * um cooperado não tem contrapartida num grupo de 63. Mesmo desenho da carteira
 * atendida (`.cart-*`): barra é a fatia dele, traço é a da área.
 */
function montarFaixas(destino, d) {
  const f = d.faixas;
  if (!f) return;
  const { cartao, corpo } = secao('Solicitações por faixa etária',
    'Repartição das solicitações deste exame pela idade de quem as recebeu, '
    + 'ao lado da mesma repartição na área de atuação.', { figura: true });

  const grade = el('div', 'cart-faixas');
  for (const x of f.faixas) {
    const item = el('div', 'cart-f');
    const rot = el('div', 'row row-between');
    /* a CONTAGEM ao lado da faixa, que é o que se perguntou; a fatia à direita,
       que é o comprimento da barra logo abaixo */
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
  /* Os MESMOS rótulos da régua no topo do painel ("Este cooperado" /
     "Referência de adequação"): é a mesma dupla, e dois nomes para ela no mesmo
     painel fariam procurar a diferença. */
  marca('cart-mk-eu', 'Este cooperado');
  marca('cart-mk-area', 'Referência da área');
  corpo.appendChild(legenda);

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
    `${a.pct_fmt} da carteira com solicitação deste procedimento.`));
  if (a.pares_fmt) {
    corpo.appendChild(el('span', 'sub', `Referência da área: ${a.pares_fmt}`));
  }
  corpo.appendChild(el('span', 'sub',
    `Base: ${a.n_beneficiarios} de ${a.n_carteira} beneficiários atendidos no período`));
  destino.appendChild(cartao);
}


/* A função `montarEvolucao` local vivia aqui e desenhava a seção "Consistência
   no período". Foi removida em 2026-09-06: os quadrados passaram a ser uma
   linha da grade de `montarEvolucaoDoExame`, alinhados ao volume de cada
   trimestre. Nenhum dado se perdeu, mudou de lugar. */


function montarPeso(destino, d) {
  const p = d.peso;
  if (!p) return;
  const { cartao, corpo } = secao('Participação no período',
    'Participação deste procedimento no total solicitado pelo cooperado no '
    + 'período e valor correspondente. Preços internos provisórios, ainda não '
    + 'homologados contra a tabela contratual.');
  corpo.appendChild(el('span', 'v',
    `${p.proporcao_fmt} do total solicitado pelo cooperado.`));
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
      `Base: ${a.itens_com_conta} de ${a.itens} solicitações com executante `
      + `identificado (${a.cobertura_fmt})`);
    cob.title = 'Quem executou um pedido só é conhecido quando a solicitação '
      + 'encontra a conta correspondente. O método presume que os demais se '
      + 'comportam como os observados.';
    corpo.appendChild(cob);
  } else {
    corpo.appendChild(el('span', 'sub', a.motivo ?? d.sem_medida));
    if (a.cobertura_fmt) {
      corpo.appendChild(el('span', 'sub',
        `Executante identificado em ${a.itens_com_conta} de ${a.itens} solicitações `
        + `(${a.cobertura_fmt}), abaixo do mínimo para apurar a taxa.`));
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
 * @param {string} [areaHref]  destino do rodapé ("ver na área de atuação")
 */
export async function abrirPainel(destino, cooperadoId, linha, aoFechar, areaHref) {
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
  const carregando = el('span', 'sub', 'Carregando…');
  corpo.appendChild(carregando);

  let d;
  try {
    d = await buscar(`/api/cooperado/${cooperadoId}/procedimento/${linha.codigo}`);
  } catch {
    carregando.textContent = 'Não foi possível carregar o detalhe deste procedimento.';
    return;
  }
  corpo.replaceChildren();

  /* Ordem de leitura (2026-09-06): quanto pede (comparação) -> quanto pesa ->
     para quantos (alcance) -> concentra em quem -> repete neles -> como se
     comportou no tempo -> quem executou.
     Vai do fato mais forte ao contexto e fecha no tempo: o gráfico por
     trimestre é a última pergunta ("foi sempre assim?"), e no meio do painel
     ele partia a sequência de leituras de carteira, que se explicam em
     cadeia (alcance dá o denominador, faixa etária diz para quem, concentração
     diz em quem, repetição diz quantas vezes nesses mesmos). */
  montarRegua(corpo, d);
  montarPeso(corpo, d);
  montarAlcance(corpo, d);
  montarFaixas(corpo, d);
  montarConcentracao(corpo, d);
  montarRepeticao(corpo, d);
  montarEvolucaoDoExame(corpo, d);
  /* `montarEvolucao` (a consistência em quadrados) saiu daqui em 2026-09-06:
     ela virou uma LINHA da grade sob o gráfico de custo por trimestre, onde os
     quadrados ficam alinhados ao volume que os explica. Como seção própria, ela
     gastava um bloco inteiro para uma frase e quatro quadrados, e repetia a
     coluna Consistência da tabela de onde o painel foi aberto. */
  montarAutorreferencia(corpo, d);

  /* O piso de confiança da variação excedente saiu daqui (ago/2026): ele já
     está na coluna de custo excedente da tabela, ao lado do número que
     qualifica, e repetido no painel virava ruído no fim de tudo. */

  /* RODAPÉ com a saída: o painel responde "como este cooperado pede este
     exame", e a pergunta seguinte é "e os outros da área?". Sem esta porta, a
     resposta exigia fechar o painel, subir a página e trocar de tela pela
     lateral. Fixo, fora da rolagem, como o cabeçalho. */
  if (areaHref) {
    const pe = el('div', 'pnl-ft');
    const a = document.createElement('a');
    a.className = 'btn';
    a.href = areaHref;
    a.textContent = 'Ver na área de atuação';
    pe.appendChild(a);
    destino.appendChild(pe);
  }
}
