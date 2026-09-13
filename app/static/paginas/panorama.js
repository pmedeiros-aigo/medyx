/* panorama.js — o Panorama da especialidade, a porta de entrada.
 *
 * A pergunta da página: "onde está o custo excedente, e por onde começar?" É a
 * tela que precede a Área — primeiro se escolhe ONDE olhar, depois se olha.
 *
 * ── o que ela junta, e o que ela nunca junta ───────────────────────────────
 * Junta pessoas e valores entre as áreas; não junta réguas. Todo excedente que
 * chega aqui foi medido contra a referência da área do próprio cooperado, e é
 * por isso que a unidade comum é o excesso e não a posição: percentil
 * comparando médicos de áreas diferentes é o pecado capital do método, e por
 * isso não existe nesta tela.
 *
 * ── o que ela tem ──────────────────────────────────────────────────────────
 * Escopo da especialidade, o extrato das áreas de atuação (uma linha por
 * área, fechando num total), as principais oportunidades cruzando as áreas e os
 * dois Paretos (onde o excesso se concentra e quais procedimentos o puxam em
 * mais de uma área).
 *
 * O funil da especialidade ficou de fora por decisão, não por esquecimento.
 *
 * Nada é calculado aqui. Texto, ordem e formato vêm prontos do motor.
 */
'use strict';

import { buscar } from '../lib/api.js';
import { el } from '../lib/dom.js';
import { abrirPagina } from '../lib/pagina.js';
import { TELAS, comRegua } from '../lib/rotas.js';
/* A MESMA MOLDURA das outras tabelas do app, e o mesmo cabeçalho: o extrato
   das áreas não é um desenho novo, é a tabela que a página inteira já fala,
   com as colunas desta tela. */
import { moldura, cabecalho } from '../lib/tabelas.js';
/* O MESMO BLOCO da tela de Área, com o conjunto trocado: lá os pares de uma
   área, aqui os de todas as que têm régua. Um desenho, duas escalas. */
import { montarOportunidades } from '../blocos/oportunidades.js';
import { montarPareto } from '../blocos/pareto.js';


/**
 * O enquadramento da especialidade, em UMA linha de texto sob o título.
 *
 * Mesma construção da linha de contexto da tela de Área (`cabecalho.js`), e de
 * propósito: os dois situam a leitura antes de qualquer bloco, e quem aprendeu
 * a ler um lê o outro. Cada parte carrega a própria definição no hover.
 */
function contexto(partes) {
  const linha = el('span', 'sub');
  partes.forEach((parte, i) => {
    if (i) linha.append(document.createTextNode(' · '));
    const p = el('span', null, parte.texto);
    if (parte.titulo) p.title = parte.titulo;
    linha.appendChild(p);
  });
  return linha;
}


/**
 * Uma CÉLULA DE NÚMERO do extrato: o valor, e a razão que anda com ele.
 *
 * O apoio é a MESMA medida numa segunda leitura (quanto é, e quanto pesa), e é
 * por isso que ele mora sob o valor e não em coluna própria: uma coluna para
 * cada faria o extrato parecer ter dez medidas onde há cinco.
 *
 * AUSÊNCIA DECLARADA: onde não há medida, o valor recua e o motivo vai no
 * hover. Nunca zero, nunca célula vazia — zero afirmaria que não há variação, e
 * vazio manda o leitor procurar o número que não existe.
 */
function celulaNumero(c, classe) {
  const td = el('td', `${classe} rt`);
  const v = el('span', c.motivo ? 'ext-v pano-ausente' : 'ext-v', c.valor_fmt);
  if (c.titulo || c.motivo) v.title = c.motivo ?? c.titulo;
  td.appendChild(v);
  if (c.apoio) td.appendChild(el('span', 'cell-sub', c.apoio));
  return td;
}


/**
 * A célula de IDENTIDADE da área: o nome, a etiqueta de ressalva quando ela
 * cabe, e a população embaixo.
 *
 * O NOME É O LINK, e não a linha inteira. O gesto útil deste bloco é comparar
 * as áreas entre si; linha inteira clicável prometeria drill-down onde o
 * desenho cataloga. A porta para a área continua existindo — ela só não é o
 * clique acidental de quem estava lendo a coluna ao lado.
 *
 * A POPULAÇÃO fica sob o nome, e não em coluna: ela é identidade da linha
 * (contra quantos a área é medida), não uma sexta medida. Taxa sem denominador
 * não diz se é prática ou ruído.
 */
function celulaArea(l) {
  const td = el('td', 'col-area');
  const nome = el('span', 'ext-nome');
  if (l.id) {
    const a = document.createElement('a');
    a.href = comRegua(TELAS.area.caminho(l.id));
    a.textContent = l.nome;
    a.title = l.acao;
    nome.appendChild(a);
  } else {
    nome.textContent = l.nome;
  }
  /* A ETIQUETA ÚNICA da referência da especialidade (LEXICO), na mesma posição
     em que ela aparece no dossiê e no índice de procedimentos: ao lado do nome,
     com a frase do motor no hover. */
  if (l.etiqueta) {
    const t = el('span', 'tag tag-ref', l.etiqueta);
    if (l.titulo_etiqueta) t.title = l.titulo_etiqueta;
    nome.append(document.createTextNode(' '), t);
  }
  td.append(nome, el('span', 'cell-sub', l.populacao));
  return td;
}


/**
 * A célula da FATIA: a única barra do extrato, e o percentual ao lado.
 *
 * É a fatia da área no excedente da ESPECIALIDADE — as fatias somam 100% e a
 * barra cheia do total é esse inteiro. Normalizar pela maior área responderia
 * "qual é a maior", que as colunas de R$ já dizem.
 *
 * SEM MEDIDA NÃO DESENHA BARRA. Trilho com preenchimento zero afirmaria
 * "excedente = 0", e ali não falta variação: falta norma. O trilho fica
 * tracejado, que é a gramática de ressalva do app, e o motivo vive no hover.
 */
function celulaFatia(f) {
  const td = el('td', 'col-fatia');
  const caixa = el('div', 'ext-fatia');
  const trilho = el('span', f.sinaliza ? 'trilho' : 'trilho trilho-vazio');
  if (f.sinaliza) {
    const i = document.createElement('i');
    i.style.width = `${f.largura_pct}%`;
    trilho.appendChild(i);
  }
  caixa.appendChild(trilho);
  caixa.appendChild(el('span', 'ext-pct', f.valor_fmt ?? ''));
  if (f.titulo) td.title = f.titulo;
  td.appendChild(caixa);
  return td;
}


/** Uma linha do extrato, na ordem das colunas que o motor declarou. */
function linhaDeArea(l) {
  const tr = document.createElement('tr');
  if (!l.comparavel) tr.className = 'ext-sem-regua';
  tr.append(celulaArea(l),
            celulaNumero(l.custo, 'col-num-md'),
            celulaNumero(l.excedente, 'col-num-md ext-forte'),
            celulaFatia(l.fatia),
            celulaNumero(l.qualificados, 'col-num'));
  return tr;
}


/* `areas`, e não `area`: a chave `area` na raiz é rota LEGADA e o servidor a
   redireciona para /area/{id}, levando o leitor para fora do Panorama. */
/* `areas`, e não `area`: a chave `area` na raiz é rota LEGADA e o servidor a
   redireciona para /area/{id}, levando o leitor para fora do Panorama. */
const areasEscolhidas = (new URLSearchParams(location.search).get('areas') || '')
  .split(',').filter(Boolean);


/**
 * O filtro de ÁREAS, de escolha múltipla, no lugar do seletor da barra.
 *
 * O seletor de área do chassi é de escolha única e serve para NAVEGAR: escolher
 * uma área leva à tela dela. Aqui a pergunta é outra — quais áreas entram na
 * comparação —, e ela é múltipla por natureza: comparar duas áreas de sete é
 * uma leitura legítima que a escolha única não expressa.
 *
 * Mesmo componente do filtro de Perfil da tela de Área (`.pf-*` do contrato):
 * gatilho com etiqueta, caixas marcáveis que não fecham ao clicar, rodapé com
 * saída. O que muda é o rodapé ter APLICAR: trocar de área recalcula no motor,
 * e recarregar a cada clique tornaria impossível escolher duas.
 */
function montarFiltroDeAreas(destino, areas, escolhidas) {
  const ID = 'pf-areas';
  const marcadas = new Set(escolhidas);

  const caixa = document.createElement('input');
  caixa.type = 'checkbox';
  caixa.id = ID;
  caixa.className = 'oc';
  const scrim = el('label', 'scrim scrim-pf');
  scrim.setAttribute('for', ID);
  scrim.setAttribute('aria-label', 'Fechar seleção');

  const campo = el('div', 'pf');
  const gatilho = el('label', 'pf-trig');
  gatilho.setAttribute('for', ID);
  gatilho.tabIndex = 0;
  gatilho.appendChild(el('span', null, 'Áreas'));
  const etiqueta = el('span', 'pf-tag');
  gatilho.appendChild(etiqueta);
  gatilho.insertAdjacentHTML('beforeend',
    '<svg class="car" width="12" height="12" viewBox="0 0 24 24" fill="none" '
    + 'stroke-width="2" stroke-linecap="round" aria-hidden="true">'
    + '<path d="M6 9l6 6 6-6"/></svg>');

  const pop = el('div', 'pf-pop');
  const opcoes = new Map();
  for (const a of areas) {
    const o = el('button', 'pf-opt');
    o.type = 'button';
    o.insertAdjacentHTML('beforeend',
      '<span class="bx"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" '
      + 'stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" '
      + 'aria-hidden="true"><path d="M5 12l5 5 9-10"/></svg></span>');
    o.appendChild(el('span', 'nm', a.titulo));
    o.appendChild(el('span', 'n', String(a.n_total)));
    o.title = a.perfil ?? '';
    // NÃO fecha ao marcar: escolha múltipla se faz em sequência
    o.addEventListener('click', () => {
      if (marcadas.has(a.id)) marcadas.delete(a.id); else marcadas.add(a.id);
      refletir();
    });
    pop.appendChild(o);
    opcoes.set(a.id, o);
  }

  const rodape = el('div', 'pf-ft');
  const limpar = el('button', 'pf-limpar', 'Todas as áreas');
  limpar.type = 'button';
  limpar.addEventListener('click', () => { marcadas.clear(); aplicar(); });
  const aplicarBtn = el('button', 'pf-limpar', 'Aplicar');
  aplicarBtn.type = 'button';
  aplicarBtn.addEventListener('click', aplicar);
  rodape.append(limpar, aplicarBtn);
  pop.appendChild(rodape);

  /* APLICAR recarrega: a escolha muda o conjunto que o motor soma, e a régua
     do app viaja na URL. É o mesmo gesto do seletor de período. */
  function aplicar() {
    const q = new URLSearchParams(location.search);
    if (marcadas.size && marcadas.size < areas.length) {
      q.set('areas', [...marcadas].join(','));
    } else {
      q.delete('areas');
    }
    location.search = q.toString();
  }

  function refletir() {
    for (const [id, o] of opcoes) o.classList.toggle('on', marcadas.has(id));
    /* Uma área aparece pelo NOME; várias viram contagem, senão o botão empurra
       o resto da faixa para fora da linha. Nenhuma quer dizer todas. */
    const nomes = areas.filter((a) => marcadas.has(a.id)).map((a) => a.titulo);
    etiqueta.textContent = nomes.length === 1 ? nomes[0]
      : nomes.length ? `${nomes.length} áreas` : 'Todas';
    /* `tem-perfil` é o que o contrato usa para revelar a etiqueta do gatilho.
       O nome é do filtro de Perfil, onde a classe nasceu; o que ela significa é
       "há seleção em cena", e é isso que vale aqui. Renomear a classe mexeria
       no filtro de Perfil sem necessidade. */
    campo.classList.add('tem-perfil');
  }
  refletir();

  campo.append(caixa, scrim, gatilho, pop);
  destino.replaceChildren(el('span', 'fil-lbl', 'Áreas de atuação'), campo);
}

await abrirPagina({
  titulo: 'Panorama',
  aoTrocarArea: (id) => TELAS.area.caminho(id),
  montar: async ({ conteudo, meta }) => {
    /* O SELETOR DE ÁREA DO CHASSI é de escolha única e NAVEGA. Nesta tela ele
       é substituído, no mesmo lugar da barra, por um filtro de escolha
       múltipla: a pergunta aqui é quais áreas entram na comparação, e sair do
       Panorama ao escolher uma é o oposto do que o controle promete. */
    const slot = document.querySelector('.sel-area')?.closest('.fil');
    if (slot) montarFiltroDeAreas(slot, meta?.areas ?? [], areasEscolhidas);

    const d = await buscar('/api/panorama',
                           { anunciarEm: conteudo, rotulo: 'Calculando' });

    /* Título e contexto na MESMA unidade de leitura, como na Área: o `gap` da
       coluna da página separaria a linha do título como se fosse outro bloco. */
    const topo = el('div', 'stack g6');
    topo.appendChild(el('h2', null, d.titulo));
    if (d.contexto?.length) topo.appendChild(contexto(d.contexto));
    conteudo.appendChild(topo);

    if (d.areas?.linhas?.length) {
      /* A MOLDURA PADRÃO, sem `tbl-fill` nem `tbl-sticky`: as duas servem às
         tabelas que são o corpo da tela e rolam por dentro. Este extrato tem
         uma linha por área de atuação — ele cabe inteiro, e prender o
         cabeçalho de uma tabela que não rola não prende nada. */
      const { quadro, topo, tabela, pe } = moldura();
      quadro.classList.remove('tbl-fill', 'tbl-sticky');
      quadro.classList.add('tbl-areas');
      pe.remove();
      topo.append(el('span', 't', d.areas.titulo),
                  el('span', 'sub', d.areas.subtitulo));

      /* O CABEÇALHO vem do motor: rótulo e definição de cada coluna são texto
         de produto, e a UI imprime, não redige (léxico). Sem ordenação — a
         ordem do extrato é a da leitura (quem tem referência primeiro, pelo
         excedente), e uma seta prometeria reordenar um conjunto que foi
         escolhido por essa ordem. */
      tabela.appendChild(cabecalho(
        (d.areas.colunas ?? []).map((c) => ({
          nome: c.rotulo, def: c.titulo, direita: c.direita, classe: c.classe,
        })), null, null, () => {}));

      const corpo = document.createElement('tbody');
      for (const l of d.areas.linhas) corpo.appendChild(linhaDeArea(l));
      tabela.appendChild(corpo);

      /* O TOTAL em `<tfoot>`, e não numa faixa fora da tabela: ele soma as
         colunas acima, então tem de estar ALINHADO a elas. Um rodapé de cartão
         (`.tbl-ft`) é texto sobre a tabela; isto é a última linha dela. */
      if (d.areas.total) {
        const rodape = document.createElement('tfoot');
        const tr = document.createElement('tr');
        const t = d.areas.total;
        tr.append(celulaArea(t),
                  celulaNumero(t.custo, 'col-num-md'),
                  celulaNumero(t.excedente, 'col-num-md ext-forte'),
                  celulaFatia(t.fatia),
                  celulaNumero(t.qualificados, 'col-num'));
        rodape.appendChild(tr);
        tabela.appendChild(rodape);
      }
      conteudo.appendChild(quadro);
    }

    /* PRINCIPAIS OPORTUNIDADES da especialidade. Sem `aoAbrir`: o painel do
       procedimento é da tela de Área, e abri-lo daqui exigiria escolher uma
       área para dentro da qual medir — que é justamente o que esta tela não
       faz. O nome continua levando ao dossiê. */
    montarOportunidades(conteudo, d, null,
                        (id) => comRegua(TELAS.cooperado.caminho(id)));

    /* OS DOIS PARETOS, lado a lado. São o mesmo bloco das outras telas com o
       conjunto trocado: à esquerda os cooperados de todas as áreas, à direita
       os procedimentos, com a contagem de áreas na leitura de cada linha.

       Sem `aoEscolher`: o fio entre Pareto e tabela é da tela de Área, onde as
       duas superfícies mostram o mesmo conjunto. Aqui a lista ao lado é outra
       unidade (o par), e apontar um cooperado nela não teria uma linha só. */
    if (d.concentracao || d.transversais) {
      const par = el('div', 'pano-duplas');
      if (d.concentracao) montarPareto(par, d.concentracao, null, 'pano-coop');
      if (d.transversais) montarPareto(par, d.transversais, null, 'pano-proc');
      conteudo.appendChild(par);
    }

    if (d.proveniencia?.carimbo) {
      conteudo.appendChild(el('span', 'note', d.proveniencia.carimbo));
    }
  },
});
