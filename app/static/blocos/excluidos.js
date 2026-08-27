/* excluidos.js — quem não entra na construção da referência, e por quê.
 *
 * Abre pela ação da estatística "Comparáveis" ("ver os 6 excluídos"). Substitui
 * a leitura que a barra de composição dava: ela mostrava a PROPORÇÃO em três
 * segmentos, mas o motivo de cada exclusão nunca coube nela, e o motivo é o que
 * se contesta. A proporção agora está no próprio número (63 de 64).
 *
 * Regra do léxico que este painel existe para cumprir: exclusão SEM MOTIVO não
 * é publicável. Toda linha aqui traz o motivo, a natureza (definitiva ou regra
 * provisória em validação) e o detalhe inteiro.
 *
 * ── fronteira visual ────────────────────────────────────────────────────────
 * Nenhuma classe nova: `.modal` + a família `.dlg-*` são as mesmas do diálogo de
 * critérios, e `.tag`/`.tag-caveat` são as etiquetas semânticas do contrato. O
 * `.scrim` fecha por clique fora, igual ao resto do sistema.
 */
'use strict';

import { el } from '../lib/dom.js';


/** Uma linha: quem, o volume que tem, e o motivo com a natureza ao lado. */
function linha(x) {
  const l = el('div', 'dlg-row');
  const lb = el('div', 'dlg-lb');
  lb.appendChild(el('span', 'dlg-n', x.id));
  if (x.consultas_fmt) {
    lb.appendChild(el('span', 'dlg-u', `${x.consultas_fmt} consultas na janela`));
  }
  /* O detalhe inteiro, não o resumo: aqui há espaço, e é este texto que separa
     "exclusão por desenho da análise" de "regra provisória que pode estar
     errada" — a distinção que decide se alguém contesta a classificação. */
  const detalhes = (x.motivos ?? []).map((m) => m.detalhe).filter(Boolean).join(' ');
  if (detalhes) lb.appendChild(el('span', 'dlg-h', detalhes));
  l.appendChild(lb);

  const ct = el('div', 'dlg-ct');
  const marca = el('div', 'stack g4');
  /* Natureza PROVISÓRIA leva o tratamento de ressalva; definitiva é etiqueta
     neutra. Não é gravidade: é se há ou não o que corrigir na classificação. */
  const etiqueta = el('span',
    x.natureza === 'definitiva' ? 'tag' : 'tag tag-caveat', x.motivo);
  if (x.natureza_rotulo) etiqueta.title = x.natureza_rotulo;
  marca.appendChild(etiqueta);
  if (x.revisao_pendente) {
    marca.appendChild(el('span', 'micro', 'triagem clínica pendente'));
  }
  ct.appendChild(marca);
  l.appendChild(ct);
  return l;
}

/**
 * Monta o painel (fechado) dentro de `destino` e devolve como abri-lo.
 *
 * @param {HTMLElement} destino
 * @param {object} composicao  bloco `composicao` de /api/area/{id}
 * @returns {{abrir: () => void}}
 */
export function montarExcluidos(destino, composicao) {
  const lista = composicao?.excluidos ?? [];

  const scrim = el('span', 'scrim scrim-dim');
  scrim.style.display = 'none';
  const modal = el('div', 'modal');
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  modal.setAttribute('aria-label', 'Excluídos da construção da referência');

  const topo = el('div', 'dlg-hd');
  const t = el('div', 'stack g4');
  t.appendChild(el('span', 'dlg-t', 'Excluídos da construção da referência'));
  const sub = [
    `${lista.length} de ${composicao?.total ?? lista.length} cooperados da área`,
    composicao?.nota,
  ].filter(Boolean).join(' · ');
  t.appendChild(el('span', 'dlg-s', sub));
  const fechar = el('span', 'dlg-x', '✕');
  fechar.tabIndex = 0;
  fechar.setAttribute('role', 'button');
  fechar.setAttribute('aria-label', 'Fechar');
  topo.append(t, fechar);

  const corpo = el('div', 'dlg-bd');
  for (const x of lista) corpo.appendChild(linha(x));

  modal.append(topo, corpo);
  destino.append(scrim, modal);

  let abridor = null;

  function mostrar(visivel) {
    scrim.style.display = visivel ? 'block' : 'none';
    modal.style.display = visivel ? 'block' : 'none';
    if (visivel) { abridor = document.activeElement; fechar.focus(); }
    else abridor?.focus?.();
  }
  mostrar(false);

  const sair = () => mostrar(false);
  scrim.addEventListener('click', sair);
  fechar.addEventListener('click', sair);
  fechar.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Enter' && ev.key !== ' ') return;
    ev.preventDefault();
    sair();
  });
  document.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape' && modal.style.display === 'block') sair();
  });

  return { abrir: () => mostrar(true) };
}
