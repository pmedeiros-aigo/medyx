/* shell/barra.js — a barra superior (migalha + vigência) e a navegação lateral.
 *
 * A migalha NAVEGA e é montada da ROTA (a marcação do shell.html é só o
 * esqueleto). Duas regras:
 *
 *   · só vira LINK o que leva a um lugar diferente da página atual — migalha
 *     que não navega é promessa quebrada, link que recarrega a mesma tela é
 *     ruído;
 *   · a régua acompanha todo link, como na navegação lateral: trocar de tela
 *     não devolve o analista ao padrão sem ele ter pedido.
 *
 * "SADT" nunca é link: módulo não é destino, é a regra do guia.
 */
'use strict';

import { TELAS, comRegua, rotaAtual } from '../lib/rotas.js';

/**
 * A migalha da tela atual: o rastro, do módulo até a folha.
 *
 * @param {object} meta   /api/meta (para o rótulo da área e a vigência)
 * @param {string} area   id da área em cena, quando houver
 */
export function montarBarraSuperior(meta, area) {
  const { tela, cooperado } = rotaAtual();
  const escolhida = meta.areas?.find((a) => a.id === area);

  const caixa = document.querySelector('.crumbs');
  if (caixa) {
    const partes = [{ txt: 'SADT' }];
    if (tela === 'panorama') {
      partes.push({ txt: TELAS.panorama.rotulo });
    } else if (tela === 'metodologia') {
      partes.push({ txt: TELAS.metodologia.rotulo });
    } else if (tela === 'cooperados') {
      partes.push({ txt: TELAS.cooperados.rotulo });
    } else if (tela === 'conta') {
      /* "SADT" é o módulo ANALÍTICO, e a conta não pertence a ele: o rastro
         começa no produto. Sem isto, a migalha classificaria a identidade do
         usuário como um assunto de SADT. */
      partes[0] = { txt: 'Medyx' };
      partes.push({ txt: TELAS.conta.rotulo });
    } else if (tela === 'area') {
      partes.push({ txt: TELAS.area.rotulo });
      partes.push({ txt: escolhida?.titulo ?? '' });
    } else if (tela === 'cooperado') {
      /* COLEÇÃO › ITEM, e nada mais (set/2026). Antes o rastro era
         "Dossiê do Cooperado › Ginecologia › cooperado_85", e tinha dois
         defeitos. "Dossiê do Cooperado" é um TIPO, não um lugar: não navegava
         e não correspondia a URL nenhuma. E a área era um pai que a URL não
         tem, já que o caminho é `/cooperado/{id}`, sem área nenhuma dentro.
         Migalha é hierarquia de CONTENÇÃO, e `/cooperados` -> `/cooperado/85`
         é a única que existe aqui.

         A área não se perde: ela continua na página, na linha de contexto do
         cabeçalho, e é lá que ganhou o link (ver `paginas/cooperado.js`). Ela
         é fato ANALÍTICO, contra quem o caso é medido, e não degrau de
         navegação. */
      partes.push({ txt: TELAS.cooperados.rotulo,
                    href: comRegua(TELAS.cooperados.caminho()) });
      partes.push({ txt: cooperado ?? '' });
    }

    const cheias = partes.filter((p) => p.txt);
    caixa.replaceChildren();
    cheias.forEach((p, i) => {
      if (i) {
        /* O separador é FORMA, desenhada pelo CSS (`.crumbs i`, chevron por
           mask). Aqui ele nasce vazio e invisível ao leitor de tela: barra ou
           chevron lidos em voz alta são ruído entre os degraus do rastro. */
        const sep = document.createElement('i');
        sep.setAttribute('aria-hidden', 'true');
        caixa.appendChild(sep);
      }
      const folha = i === cheias.length - 1;
      const e = document.createElement(folha ? 'b' : p.href ? 'a' : 'span');
      if (!folha && p.href) e.href = p.href;
      e.textContent = p.txt;
      caixa.appendChild(e);
    });
  }

  /* A vigência dos dados NÃO é escrita aqui. Ela vive no seletor de Período,
     que é onde ela pode ser mudada; repeti-la no canto da barra dava ao leitor
     duas janelas para conferir e só uma para editar. */
}

/**
 * Liga o alternador de tema da barra superior.
 *
 * O botão NÃO desenha nada: os dois ícones estão na marcação e o CSS escolhe
 * qual aparece a partir de `<html data-tema>`. Aqui só se alterna o estado
 * (`MedyxTema.alternar`) e se reescreve o rótulo, que é TEXTO — e texto é a
 * única coisa que muda com o tema e não cabe numa classe.
 *
 * O rótulo diz o que vem no PRÓXIMO clique, não o que está na tela: o ícone já
 * diz o estado atual, e um botão que anuncia o que já aconteceu não ajuda
 * ninguém a decidir se clica.
 */
export function ligarTema() {
  const b = document.querySelector('[data-tema-btn]');
  const tema = globalThis.MedyxTema;
  if (!b || !tema) return;

  const rotular = (t) => {
    const txt = t === 'dark' ? 'Mudar para o tema claro' : 'Mudar para o tema escuro';
    b.setAttribute('aria-label', txt);
    b.title = txt;
  };
  rotular(tema.atual());
  tema.aoMudar(rotular);
  b.addEventListener('click', () => tema.alternar());
}

/** Chave da preferência de lateral recolhida, no armazenamento do navegador. */
const CHAVE_LATERAL = 'medyx:lateral-curta';

/**
 * Liga o botão que recolhe a barra lateral.
 *
 * Recolhida sobra a marca, o ícone de cada tela e o avatar. O botão NÃO desenha
 * nada: alterna a classe `curta` no `.shell`, e o CSS faz o resto — os dois
 * ícones dele já vivem na marcação, como no alternador de tema ao lado.
 *
 * ── o rótulo de cada item vira `title` quando recolhe ────────────────────
 * Sem a etiqueta, um ícone sozinho é adivinhação. O texto já está no DOM, ao
 * lado do ícone; recolhido ele é copiado para o `title`, que o balão do app
 * mostra no hover. Assim nenhum nome é escrito duas vezes no código: o `title`
 * é sempre o que a etiqueta diz.
 *
 * ── a escolha PERSISTE ──────────────────────────────────────────────────
 * Quem recolhe a lateral quer trabalhar com mais largura, e não quer repetir o
 * gesto a cada tela. Fica no armazenamento do navegador, e não na URL: é
 * preferência de quem lê, não estado do que está sendo lido, e um link de
 * evidência não deve carregar o gosto de quem o mandou.
 */
export function ligarLateral() {
  const b = document.querySelector('[data-lateral-btn]');
  const shell = document.querySelector('.shell');
  if (!b || !shell) return;

  const itens = [...document.querySelectorAll('.shell-side .navitem')];
  const rotulos = itens.map((a) => a.textContent.trim());

  const aplicar = (curta) => {
    shell.classList.toggle('curta', curta);
    b.setAttribute('aria-expanded', String(!curta));
    const txt = curta ? 'Expandir a barra lateral' : 'Recolher a barra lateral';
    b.setAttribute('aria-label', txt);
    b.title = txt;
    itens.forEach((a, i) => {
      if (curta) a.title = rotulos[i];
      else a.removeAttribute('title');
    });
  };

  let inicial = false;
  try {
    inicial = localStorage.getItem(CHAVE_LATERAL) === '1';
  } catch { /* navegador sem armazenamento: abre expandida, que é o padrão */ }
  aplicar(inicial);

  b.addEventListener('click', () => {
    const curta = !shell.classList.contains('curta');
    aplicar(curta);
    try {
      localStorage.setItem(CHAVE_LATERAL, curta ? '1' : '0');
    } catch { /* sem armazenamento, a escolha vale só nesta tela */ }
  });
}

/**
 * Navegação lateral: o item ativo vem da ROTA, e a régua viaja nos links.
 *
 * O Dossiê não está na lateral, mas COOPERADOS está (27/ago): a regra é que a
 * lateral lista pontos de PARTIDA, e uma lista de cooperados é um deles. O
 * dossiê de UM continua sendo destino, alcançado pela lista, pelo Panorama ou
 * pela tabela da Área.
 *
 * O item que acende num dossiê é COOPERADOS (set/2026). Era Área de Atuação,
 * pela ideia de que a lateral mostra onde o caso mora, no peer group contra o
 * qual ele é medido. O raciocínio é bom e responde à pergunta errada: lateral e
 * migalha dizem ONDE VOCÊ ESTÁ, não contra quem o número é medido — essa é a
 * pergunta central do produto, e tem lugar próprio, na linha de contexto do
 * cabeçalho do dossiê.
 *
 * Na prática o realce pulava: quem clicava em Cooperados e abria um da lista
 * via o destaque saltar para uma tela onde não estava.
 *
 * @param {string} area  a área em cena, para o link da Área de atuação
 */
export function montarNavegacao(area) {
  const { tela } = rotaAtual();
  for (const a of document.querySelectorAll('.navitem[data-tela]')) {
    const alvo = a.dataset.tela;
    a.classList.toggle('on', alvo === tela
      // o dossiê é o ITEM da coleção Cooperados, e é ela que fica acesa
      || (tela === 'cooperado' && alvo === 'cooperados'));
    const caminho = alvo === 'area' && area
      ? TELAS.area.caminho(area)
      : TELAS[alvo]?.caminho();
    if (caminho) a.href = comRegua(caminho);
  }
}
