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
 * Escopo da especialidade, um cartão por área de atuação, as principais
 * oportunidades cruzando as áreas e os dois Paretos (onde o excesso se
 * concentra e quais procedimentos o puxam em mais de uma área).
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
 * Um cartão de área: custo total e custo excedente (com o % que ele representa
 * ao lado), sempre os dois e sempre na mesma ordem, mais a população que os
 * sustenta.
 *
 * TODAS as áreas viram cartão, do MESMO tamanho e com os MESMOS campos: a tela é
 * o catálogo da especialidade, e cartão que muda de forma conforme a área some
 * com a comparação, que é a razão de eles estarem lado a lado. Onde não há
 * medida, a linha declara a ausência com o motivo no hover.
 *
 * A BARRA é a fatia da área no excedente da especialidade, não a fatia da
 * maior: a pergunta do cartão é quanto do problema está ali, e normalizar pela
 * maior faria a segunda área parecer maior sempre que a primeira encolhesse.
 */
function cartaoDeArea(c) {
  /* CARTÃO, NÃO LINK. Ele descreve a área; quem quiser entrar nela usa o
     seletor da barra ou a navegação. Um cartão inteiro clicável promete
     drill-down onde o gesto útil é comparar as áreas entre si. */
  const a = el('div', c.comparavel ? 'kpi' : 'kpi kpi-sem-regua');
  a.appendChild(el('span', 'k', c.nome));

  /* AS MESMAS TRÊS LINHAS em todo cartão, na mesma ordem, com a `.deflist` do
     contrato: rótulo à esquerda, valor à direita. Cartão que muda de campos
     conforme a área obriga o leitor a reaprender o desenho a cada um, e some
     com a comparação, que é a razão de eles estarem lado a lado. */
  const lista = el('div', 'deflist pano-lista');
  for (const l of c.linhas ?? []) {
    const linha = el('div', 'def-row');
    const k = el('span', 'def-k', l.rotulo);
    if (l.titulo) k.title = l.titulo;
    linha.appendChild(k);
    /* AUSÊNCIA DECLARADA: onde não há medida, o valor recua e o motivo vai no
       hover. Nunca zero, nunca célula vazia — zero afirmaria que não há
       variação, e vazio manda procurar o número que não existe. */
    const v = el('span', l.motivo ? 'def-v pano-ausente' : 'def-v', l.valor_fmt);
    if (l.destaque && !l.motivo) v.classList.add('pano-v-forte');
    if (l.motivo) v.title = l.motivo;
    /* O APOIO ao lado do valor: é a mesma medida numa segunda leitura (quanto é
       e quanto pesa), e uma linha própria faria o cartão parecer ter três
       medidas onde há duas. */
    if (l.apoio) {
      const ap = el('span', 'sub pano-apoio', l.apoio);
      if (l.titulo_apoio) ap.title = l.titulo_apoio;
      v.appendChild(ap);
    }
    linha.appendChild(v);
    lista.appendChild(linha);
  }
  a.appendChild(lista);

  a.appendChild(el('span', 'micro', c.populacao));
  /* A ÚLTIMA LINHA quebra nos cartões sem régua: ali ela é o MOTIVO de as três
     medidas acima não existirem, e truncá-lo em "cooperados insuficientes
     para…" deixa na tela exatamente a metade que não informa. Nos cartões com
     régua é um rótulo telegráfico ("21 casos qualificados") e cabe numa linha. */
  const q = el('span', c.comparavel ? 'micro' : 'micro pano-motivo',
               c.qualificados);
  if (c.titulo_qualificados) q.title = c.titulo_qualificados;
  a.appendChild(q);
  return a;
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

    if (d.areas?.cartoes?.length) {
      const bloco = el('div', 'stack g10');
      const t = el('div', 'stack g4');
      t.appendChild(el('h3', null, d.areas.titulo));
      t.appendChild(el('span', 'sub', d.areas.subtitulo));
      bloco.appendChild(t);

      /* UMA GRADE, UM TAMANHO. Houve uma versão com dois cartões grandes para
         as áreas com régua e uma faixa compacta para o resto: os grandes
         prometiam responder "onde o excesso está", e essa é pergunta de Pareto,
         que tem seção própria mais abaixo. Cartão grande sobre uma lista de
         áreas afirma concentração onde o desenho só cataloga.

         O que distingue as áreas continua sendo o CONTEÚDO do cartão e o recuo
         de quem não tem régua, não o tamanho. */
      const grade = el('div', 'kpis kpis-areas');
      for (const c of d.areas.cartoes) grade.appendChild(cartaoDeArea(c));
      bloco.appendChild(grade);
      conteudo.appendChild(bloco);
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
