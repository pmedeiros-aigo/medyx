/* tabela.js — a tabela de cooperados da área.
 *
 * É o CONTEÚDO DE TRABALHO da tela (guia, padrão de página): a única faixa
 * emoldurada, onde se lê um dado e se toma uma decisão.
 *
 * Lê `cooperados` de /api/area/{id}. Não calcula nada — nem ordena: a API já
 * entrega ordenado por variação excedente.
 *
 * ── colunas, em quatro grupos ───────────────────────────────────────────────
 *
 *   IDENTIDADE  quem é, e os sub-perfis que carrega
 *   MAGNITUDE   o volume que sustenta a leitura (consultas, solicitações, índice)
 *   EVIDÊNCIA   o que sustenta a alegação (posição no grupo, consistência)
 *   DESFECHO    o que isso implica (variação excedente, procedimentos em revisão)
 *
 * A ordem não é decorativa: quem contesta um número pergunta nessa sequência —
 * quem é, quanto fez, com que evidência, e daí o quê.
 *
 * ── regras do CLAUDE.md que governam esta tabela ────────────────────────────
 *
 *   ajuste 1  Ausência de atributo NÃO vira etiqueta. Sem sub-perfil, célula vazia.
 *   ajuste 2  Percentil NUNCA viaja sem tradução em linguagem comum, ao lado.
 *   ajuste 4  Variação excedente é sempre o valor real. Travessão só para quem não
 *             tem nenhum procedimento sinalizado — ausência de par, não zero medido.
 *   ajuste 6  Chip default da tela de Área é TODOS. `filtros[].default` da API é o
 *             default do MÉTODO, não o da tela, e não deve ser adotado cego.
 *
 * ── fronteira visual ────────────────────────────────────────────────────────
 *
 * Nenhuma classe nova. `.ruler` e seus marcadores, `.pctl-wrap`/`.pctl-t`
 * (percentil + tradução), `.pill`, `.tag`, `.help` e a família `.tbl` já existem
 * no contrato.
 *
 * Exceção declarada, mesma da barra de composição: as posições da régua saem em
 * `style` (`left`/`width` em %). São DADO, vêm de `posicao.regua` calculadas
 * pelo motor, não decisão visual.
 */
'use strict';

import { TELAS, comRegua } from '../lib/rotas.js';
import { el, ordenar, cabecalho, moldura, celulaConsistencia, campoDeBusca }
  from '../lib/tabelas.js';

/* Os chips de recorte moram em `recorte.js` e o ESTADO da vista (recorte,
   perfil, aba, ordenação) mora na página: este módulo desenha o que recebe em
   `atualizar()` e não guarda nada além do que já está no DOM. */


/* O que cada coluna significa. NÃO vai dentro de `<th>`: o th é sticky dentro de
 * `.tbl-scroll`, e a bolha do `.help` seria recortada pela rolagem — restrição
 * escrita na própria origem do contrato. Mora no `.tbl-hd`, que está fora da
 * área rolável. */
/* Um andar de cabeçalho, não dois.
 *
 * Havia um andar de grupos (Identidade · Magnitude · Evidência · Desfecho). Saiu:
 * com oito colunas o agrupamento não se paga, "Identidade" agrupava uma coluna
 * só, e os quatro nomes são vocabulário interno — quem lê a tela não pensa em
 * "magnitude", pensa em consultas.
 *
 * `ajuda` é o texto do ⓘ, no mesmo espírito das notas dos controles da barra
 * lateral: a coluna diz o nome, o ⓘ diz o que o número significa. */
/* `ordem` é a chave do parâmetro na URL; `valor` extrai o número que ordena.
 * Nada aqui calcula: só lê campos que o motor já entregou.
 *
 * DUAS COLUNAS SAÍRAM em 2026-08-20, por decisão de produto:
 *
 *   Posição no grupo    régua desenhada com a marca do cooperado sobre a
 *                       escala da área. Dizia a mesma coisa que o gráfico de
 *                       distribuição diz melhor, ocupando 200px em toda linha.
 *   Origem do excedente 260px de texto corrido no meio de uma tabela de
 *                       números. O procedimento que puxa o excedente continua
 *                       no dossiê, que é onde se investiga um caso.
 *
 * A tabela ficou com seis colunas e cabe sem rolagem horizontal. */
export const COLUNAS = [
  { nome: 'Cooperado', classe: 'col-id' },
  { nome: 'Consultas', direita: true, classe: 'col-num', ordem: 'consultas', valor: (l) => l.consultas },
  { nome: 'Exames por consulta', direita: true, classe: 'col-num-lg',
    def: 'Exames solicitados dividido por consultas atendidas na janela. '
       + 'É o índice contra o qual a área é comparada.',
    ordem: 'indice', valor: (l) => l.indice },
  /* CUSTO POR CONSULTA e VALOR TOTAL (2026-08-26): magnitude em R$, não desvio.
     Respondem "quanto custa uma consulta dele" e "quanto ele soma no período",
     que são perguntas de tamanho — o Excesso em R$, lá adiante, responde quanto
     disso está acima da referência.

     Ficam ao lado de "Exames por consulta" de propósito: as três formam a
     leitura de magnitude, e a divisão entre elas é informativa. Custo por
     consulta ÷ exames por consulta é o preço médio do exame que ele pede, e ele
     varia 6× dentro de Ginecologia — quem pede pouco e caro não se parece com
     quem pede muito e barato, e uma coluna só não separava os dois. */
  { nome: 'Custo por consulta', direita: true, classe: 'col-num-md',
    def: 'Valor de tudo que ele solicitou dividido pelas consultas da janela, '
       + 'a preços de referência internos. Em quarentena até a tabela '
       + 'contratual, como o excesso em R$.',
    ordem: 'custo', valor: (l) => l.custo_por_consulta },
  { nome: 'Valor total', direita: true, classe: 'col-num-md',
    def: 'Soma de tudo que ele solicitou na janela, a preços de referência '
       + 'internos. É o tamanho da prática dele, não o excesso.',
    ordem: 'valor_total', valor: (l) => l.valor_total },
  /* Ordena pelo n/n do procedimento MAIS PERSISTENTE (a medida do degrau
     "persistente"); as barras da célula marcam trimestres com ALGUM
     procedimento acima. Medidas diferentes de propósito, cada uma rotulada. */
  /* À ESQUERDA, e não à direita: a célula é um gráfico com um texto, não um
     número. Cabeçalho alinhado à direita sobre conteúdo que começa na esquerda
     era o desencontro mais visível da tabela. */
  { nome: 'Trimestres acima do critério', classe: 'col-txt',
    def: 'Em quantos trimestres do período ele passou o critério em algum '
       + 'exame. Os quadrados mostram a série, um por trimestre, na ordem: '
       + 'preenchido é trimestre acima.',
    ordem: 'consistencia', valor: (l) => l.consistencia?.janelas_sinalizado },
  /* O excedente em DUAS colunas (2026-08-20). Vinha numa só, como
     "17.744 · R$ 736 mil": dois números de grandezas diferentes separados por um
     ponto, sem nada dizendo qual era qual. E os nomes agora são os mesmos dos
     KPIs acima — "Excesso de solicitações" e "Excesso em R$" —, para a página
     inteira falar uma língua só. */
  { nome: 'Excesso de solicitações', direita: true, classe: 'col-num-lg',
    def: 'Solicitações a mais que a referência do grupo, no volume de consultas '
       + 'dele, somadas entre os exames em que passou o critério.',
    ordem: 'excedente', valor: (l) => l.excedente_itens },
  { nome: 'Excesso em R$', direita: true, classe: 'col-num-md',
    def: 'As mesmas solicitações excedentes valoradas a preços de referência '
       + 'internos. Em quarentena até a tabela contratual — não é economia '
       + 'realizada.',
    ordem: 'excedente_reais', valor: (l) => l.excedente_reais },
  /* Coluna de AÇÃO: sem nome, sem ordenação, largura só do alvo de toque. É a
     segunda afordância para o dossiê — a primeira é o nome como link. Com oito
     colunas a linha fica larga, e quem termina de ler a última coluna não volta
     ao começo para clicar no nome. */
  { nome: '', classe: 'col-chev' },
];

/* POSTO NO PERFIL — entra na tabela só quando um perfil está em cena, ao lado da
 * posição na referência. As duas convivem de propósito: o percentil diz onde ele
 * está na ÁREA (a comparação), o posto diz onde ele está na LISTA em cena (o
 * recorte). Trocar uma pela outra faria o recorte parecer uma segunda régua.
 *
 * Não é ordenável: o posto JÁ é a ordem por índice dentro do recorte, e uma seta
 * nele prometeria reordenar o que é a própria ordem. */
const COLUNA_POSTO = {
  nome: 'Posto no perfil', classe: 'col-num', direita: true,
  def: 'posição pelo índice entre os portadores deste perfil, na área',
};

/** Identidade: o id e, se houver, os sub-perfis. Sem sub-perfil, nada (ajuste 1). */
/* A régua da análise acompanha o link (`comRegua`): o dossiê tem de abrir sob
 * os mesmos parâmetros da tela que o originou. Recorte, ordem e aba ficam de
 * fora — são estado de apresentação DESTA tabela e não significam nada lá. */
function enderecoDoDossie(id) {
  return comRegua(TELAS.cooperado.caminho(id));
}

/* Identidade: o nome é LINK para o dossiê; as etiquetas ficam FORA dele.
 *
 * O link é a navegação, não a linha inteira: linha clicável impede selecionar
 * texto, não anuncia que é clicável, não é alcançável por teclado e disputa o
 * clique com a seleção vinda do gráfico. Um <a> resolve os quatro de graça.
 *
 * As etiquetas vão numa sub-linha (`.cell-sub`) que OCUPA espaço e empurra a
 * altura da linha. Antes flutuavam sobre as colunas de valor, porque herdavam o
 * nowrap do nome. Texto curto na etiqueta, motivo inteiro no hover. */
function celulaIdentidade(linha, excluido) {
  const td = el('td', 'cell-name');
  const link = document.createElement('a');
  link.href = enderecoDoDossie(linha.id);
  link.textContent = linha.id;
  td.appendChild(link);

  const tags = el('div', 'cell-sub');
  /* O badge é IDENTIDADE e nunca subdivide a régua — mas em dois casos ele muda
     a formação da referência numa CESTA de procedimentos, e isso um rótulo de
     duas palavras não diz. A frase vem redigida da API. */
  for (const sp of linha.sub_perfis) {
    const b = el('span', 'tag tag-attr', sp.rotulo);
    if (sp.ajuda) b.title = sp.ajuda;
    tags.appendChild(b);
  }
  /* A etiqueta "perfil explica a origem" SAIU da tabela (decisão 13/ago):
     rótulo de quatro palavras para uma relação que só o hover explicava,
     confundia mais do que informava. `perfil_explica` segue no payload; o
     lugar dessa leitura é o dossiê do cooperado, com espaço para a frase
     inteira. */
  /* FILA DE TRIAGEM CLÍNICA. A etiqueta fala da CLASSIFICAÇÃO, não do número:
     o cooperado continua medido e comparado normalmente. Antes este estado só
     era impresso pelo painel de excluídos, e três dos quatro casos da fila não
     apareciam em lugar nenhum do app. */
  if (linha.em_revisao) {
    const t = el('span', 'tag tag-caveat', linha.em_revisao.rotulo);
    t.title = `${linha.em_revisao.motivo} · ${linha.em_revisao.detalhe}`;
    tags.appendChild(t);
  }
  if (excluido) {
    // ele é medido contra a norma, só não a define — distinção que some se a
    // linha não a declarar
    const t = el('span', 'tag tag-caveat', 'não forma a referência');
    t.title = [excluido.motivo, excluido.natureza_rotulo].filter(Boolean).join(' · ');
    tags.appendChild(t);
    if (excluido.em_revisao) {
      const r = el('span', 'tag tag-caveat', 'em revisão');
      r.title = 'classificação sob contestação do médico';
      tags.appendChild(r);
    }
  }
  if (tags.children.length) td.appendChild(tags);
  return td;
}

/** Marca posicionada na régua. `pct` vem do motor; `style` aqui é dado. */
function marca(classe, esquerda, largura) {
  const s = el('span', classe);
  s.style.left = `${esquerda}%`;
  if (largura != null) s.style.width = `${largura}%`;
  return s;
}


/* Célula que NÃO SE APLICA a este cooperado: mostra o motivo, nunca vazio nem
 * um "sem medida" mudo. Quem lê a linha precisa saber por que aquele número não
 * existe — e "volume abaixo do mínimo" é a resposta, não uma falha. */
function celulaMotivo(motivo) {
  return el('td', 'cell-sub', motivo);
}

/** Consistência entre trimestres. Sem par avaliável, o motivo vira o título. */

/**
 * Variação excedente. Travessão SÓ quando não há nenhum procedimento sinalizado
 * — e aí o motivo vai no título, porque "—" sozinho lê como zero (ajuste 4).
 * O R$ ao lado é ESTIMATIVA (decisão 13/ago): preço interno provisório até a
 * tabela oficial; a derivação vai no hover, o valor fica visível.
 */
function celulaExcedente(linha) {
  const td = el('td', 'rt num', linha.excedente_fmt);
  if (linha.excedente_motivo) td.title = linha.excedente_motivo;
  return td;
}

/** O mesmo excedente na outra unidade, em coluna própria. */
function celulaExcedenteReais(linha) {
  const td = el('td', 'rt num', linha.excedente_reais_fmt ?? '');
  if (linha.excedente_reais_fmt) {
    td.title = 'Valorado a preços de referência internos (mediana das contas '
             + 'por procedimento), até a tabela contratual da Unimed entrar no '
             + 'pipeline.';
  }
  return td;
}
/* R$ POR COOPERADO: custo por consulta e valor total.
 *
 * Mesma quarentena do excesso em R$ — preço mediano das contas, não tabela
 * contratual —, e por isso o mesmo aviso. A cobertura entra no title porque um
 * total é SOMA: soma com buraco parece MENOR, não parece incompleta, e quem
 * contesta o número pergunta primeiro sobre quantos itens ela cobre.
 *
 * Célula vazia quando o motor não mediu, nunca "R$ 0": zero leria como "não
 * custa nada" no lugar de "não medido" (ajuste 4). */
function celulaReaisCoop(valorFmt, cobertura, oQue) {
  const td = el('td', 'rt num', valorFmt ?? '');
  if (valorFmt) {
    const cob = cobertura == null ? ''
      : ` Cobre ${(cobertura * 100).toFixed(1)}% dos itens solicitados (os demais não têm preço nas contas).`;
    td.title = `${oQue} a preços de referência internos (mediana das contas por `
             + `procedimento), até a tabela contratual da Unimed entrar no `
             + `pipeline.${cob}`;
  }
  return td;
}

/* Chevron do dossiê: SEMPRE visível, nunca só no hover. Afordância que aparece
 * ao passar o mouse não existe para quem navega por teclado nem para quem lê a
 * tela sem mover o cursor. Vale para toda linha, inclusive as não avaliáveis —
 * o dossiê é justamente onde se vê por que alguém não sustenta comparação. */
function celulaChevron(l) {
  const td = document.createElement('td');
  const a = document.createElement('a');
  a.className = 'chev';
  a.href = enderecoDoDossie(l.id);
  a.textContent = '\u203a';
  a.title = 'abrir dossiê analítico';
  a.setAttribute('aria-label', `abrir dossiê analítico de ${l.id}`);
  td.appendChild(a);
  return td;
}


function linhaDaTabela(l, excluido, perfilFlag) {
  const tr = document.createElement('tr');
  tr.tabIndex = 0;
  tr.dataset.id = l.id;
  /* Canaleta de 3px em `--crit` para quem está ACIMA DO CRITÉRIO (ajuste 4:
     o critério agregado governa o realce da linha). Sem fundo tingido: entrar
     em revisão não é veredito.

     Linha acima da referência mas ABAIXO do critério não recebe canaleta — quem
     carrega o âmbar nesse caso é a célula do valor (`.pctl-warn` no percentil),
     não a linha inteira. Regra escrita na origem do contrato, e é ela que mantém
     âmbar e vermelho como uma escala só. */
  /* Dois níveis, uma escala só (distância do grupo):
       vermelho  acima do critério de revisão  -> entra em revisão
       âmbar     acima da referência, abaixo do critério -> leitura de magnitude
     O nível intermediário vem de `posicao.classe`, que é onde o motor o declara;
     `estado_linha` só distingue acima do critério. */
  /* SEM canaleta colorida na linha (2026-08-20). Ela marcava "acima do critério
     agregado" — a mesma régua que saiu do gráfico de distribuição por não
     governar nada. Mantê-la aqui deixaria a tabela afirmando uma severidade que
     o resto da tela deixou de afirmar, e em vermelho, que agora é a cor do
     dinheiro. */
  /* Quem está abaixo do volume mínimo continua na lista em "Todos": some da
     comparação, não da vista. Consultas e solicitações valem; o ÍNDICE existe
     mas é instável com poucas consultas, então vai marcado com ressalva para
     que ordenar por ele não o faça parecer o pior caso da área; e as colunas que
     dependem da comparação mostram o MOTIVO. */
  const motivo = l.avaliavel ? null
    : (l.posicao?.indisponivel_motivo ?? 'não avaliável');
  const indice = el('td', 'rt num', l.indice_fmt);
  if (motivo) {
    indice.classList.add('val-ressalva');
    indice.title = `${motivo}: com poucas consultas o índice oscila e não sustenta comparação`;
  }

  /* Custo por consulta leva a MESMA ressalva do índice, e pela mesma razão:
     também é razão por consulta, e com poucas consultas oscila igual. Valor
     total não leva — é soma absoluta, não se desestabiliza com denominador
     pequeno. */
  const custo = celulaReaisCoop(l.custo_por_consulta_fmt, l.cobertura_preco,
                                'Valor solicitado por consulta');
  if (motivo && l.custo_por_consulta_fmt) {
    custo.classList.add('val-ressalva');
    custo.title = `${motivo}: com poucas consultas o custo por consulta oscila `
                + 'e não sustenta comparação';
  }

  tr.append(
    celulaIdentidade(l, excluido),
    el('td', 'rt num', l.consultas_fmt),
    indice,
  );
  /* Posto no perfil: só quando um perfil está em cena. O posto vem pronto do
     motor ("3º de 9"), calculado entre os portadores comparáveis; quem está em
     cena mas fora da comparação (recorte Todos) mostra o motivo, como as demais
     colunas comparativas. */
  if (perfilFlag) {
    const p = l.postos_perfil?.[perfilFlag];
    tr.append(motivo ? celulaMotivo(motivo) : el('td', 'rt num', p?.rotulo ?? ''));
  }
  /* Magnitude em R$ vem DEPOIS do posto e ANTES da consistência, na mesma
     ordem do cabeçalho. Não é substituída por `celulaMotivo`: quem está abaixo
     do volume mínimo perde a COMPARAÇÃO, não o custo — ele solicitou e aquilo
     tem preço, medido sem régua nenhuma. */
  tr.append(
    custo,
    celulaReaisCoop(l.valor_total_fmt, l.cobertura_preco, 'Total solicitado'),
  );
  tr.append(
    motivo ? celulaMotivo(motivo) : celulaConsistencia(l.consistencia),
    motivo ? celulaMotivo(motivo) : celulaExcedente(l),
    motivo ? celulaMotivo(motivo) : celulaExcedenteReais(l),
    celulaChevron(l),
  );
  return tr;
}

/**
 * Monta a tabela de cooperados dentro de `destino`.
 *
 * @param {HTMLElement} destino
 * @param {object} dados  resposta de /api/area/{id}
 * @returns {{aplicar: (chave: string|null) => void}}  para a barra comandar
 */
export function montarTabela(destino, dados,
                             { aoEscolherLinha, aoOrdenar, aoBuscar, busca = '' }) {
  const { cooperados, composicao, justificativa } = dados;
  const excluidoPorId = new Map((composicao?.excluidos ?? []).map((e) => [e.id, e]));

  const { quadro, topo, tabela, pe, peEstado } = moldura();
  const titulo = el('div', 'stack g4');
  /* O título nomeia a UNIDADE em cena e acompanha a aba. A linha "Comparado
     com: …" logo abaixo NÃO muda: ela declara a régua, que é a mesma nas duas.
     São camadas diferentes — o que se está listando e sob que regra. */
  const tituloBloco = el('span', 't', 'Cooperados da área');
  titulo.appendChild(tituloBloco);
  /* Justificativa em dois níveis, redigida pela API.
     O RESUMO carrega só o que não está visível em outro lugar: área, n, base e
     classificação. Gatilho e referência saíram porque já estão nos chips do topo
     e no bloco Análise da lateral — repetidos numa terceira superfície não
     informam, só empurram o resto da frase para fora do campo de leitura.
     Uma linha de justificativa por página, não uma por componente. */
  if (justificativa?.resumo) titulo.appendChild(el('span', 'sub', justificativa.resumo));
  if (justificativa?.detalhes?.length) {
    const abrir = document.createElement('a');
    abrir.href = '#';
    abrir.textContent = 'detalhes do recorte';
    abrir.className = 'micro';
    const corpo = el('div', 'note');
    corpo.textContent = justificativa.detalhes
      .map((d) => `${d.rotulo}: ${d.valor}`).join(' · ');
    // sem classe de visibilidade: o bloco existe ou não existe
    abrir.addEventListener('click', (ev) => {
      ev.preventDefault();
      if (corpo.isConnected) { corpo.remove(); abrir.textContent = 'detalhes do recorte'; }
      else { titulo.appendChild(corpo); abrir.textContent = 'ocultar detalhes'; }
    });
    titulo.appendChild(abrir);
  }
  // sem ⓘ: cada definição virou uma linha de texto no próprio cabeçalho da
  // coluna a que pertence, onde não some quando o mouse sai
  topo.appendChild(titulo);

  /* A BUSCA à direita do título, no mesmo lugar das outras tabelas do app.
     Ela LOCALIZA, não recorta: o termo entra no estado da vista da página e
     esconde linhas, sem tocar em KPI, Pareto ou excedente somado. */
  if (aoBuscar) topo.appendChild(campoDeBusca({
    placeholder: 'Buscar cooperado', valor: busca, aoDigitar: aoBuscar }));

  /* O rodapé (`peEstado`) carrega o ESTADO DA VISTA: qual recorte e qual
     ordenação estão valendo. Com ordenação por clique, o estado deixou de ser
     visível em outro lugar: a seta no cabeçalho pode estar fora do campo de
     leitura, e "por que esta linha está no topo" é a pergunta seguinte. */
  destino.appendChild(quadro);

  /**
   * Repinta a tabela com o que a PÁGINA decidiu estar em cena.
   *
   * Nenhum cálculo e nenhuma decisão: as linhas já vêm filtradas, e `rodape`
   * já vem redigido. O que este bloco faz é o que sabe fazer — desenhar
   * células, cabeçalho e a moldura.
   *
   * @param {object} vista
   * @param {object[]} vista.linhas       quem está em cena, já na ordem
   * @param {string|null} vista.perfilFlag  perfil em cena (insere a coluna do posto)
   * @param {string|null} vista.ordem     coluna ordenada, para a seta do cabeçalho
   * @param {string|null} vista.direcao
   * @param {string} vista.rodape         o estado da vista, em uma frase
   */
  function atualizar({ linhas, perfilFlag, ordem, direcao, rodape }) {
    /* O posto entra logo depois de "Exames por consulta" (índice 2), que é o
       número de que ele é o posto. O corpo já o inseria aí; o cabeçalho usava
       slice(0, 4) e o punha um lugar adiante, o que trocava Posto e Trimestres
       de coluna sempre que um perfil estava em cena. Corrigido em 2026-08-26. */
    const colunas = perfilFlag
      ? [...COLUNAS.slice(0, 3), COLUNA_POSTO, ...COLUNAS.slice(3)]
      : COLUNAS;
    const corpo = document.createElement('tbody');
    for (const l of linhas) {
      corpo.appendChild(linhaDaTabela(l, excluidoPorId.get(l.id) ?? null, perfilFlag));
    }
    tabela.replaceChildren(cabecalho(colunas, ordem, direcao, aoOrdenar), corpo);
    peEstado.textContent = rodape;
  }

  /* Destaca a linha de um cooperado escolhido FORA da tabela (um ponto do
     gráfico). `tr.selected` é do contrato e significa exatamente isto: escolha
     do usuário. Rola até a linha porque com 64 delas e 11 visíveis, destacar
     uma fora do campo de visão não destaca nada. */
  function destacar(id) {
    let alvo = null;
    for (const tr of tabela.querySelectorAll('tbody tr')) {
      const desta = tr.dataset.id === id;
      tr.classList.toggle('selected', desta);
      if (desta) alvo = tr;
    }
    /* Rola SÓ a área da tabela, nunca a página. `scrollIntoView` arrasta todos
       os contêineres roláveis acima, inclusive o documento — e aí o gráfico sobe
       junto, dando a impressão de que o ponto clicado saiu do lugar. */
    const caixa = tabela.closest('.tbl-scroll');
    if (alvo && caixa) {
      const l = alvo.getBoundingClientRect();
      const c = caixa.getBoundingClientRect();
      caixa.scrollTop += (l.top - c.top) - (c.height - l.height) / 2;
    }
    return Boolean(alvo);
  }

  /* Clicar na linha ESCOLHE o cooperado e destaca o ponto no gráfico. Não
     navega: navegar é o link no nome, e o clique no link não chega aqui.
     Clicar na mesma linha desfaz, igual ao clique no ponto. */
  tabela.addEventListener('click', (ev) => {
    if (ev.target.closest('a')) return;
    const tr = ev.target.closest('tbody tr');
    if (!tr?.dataset.id) return;
    aoEscolherLinha?.(tr.classList.contains('selected') ? null : tr.dataset.id);
  });

  return { atualizar, destacar };
}
