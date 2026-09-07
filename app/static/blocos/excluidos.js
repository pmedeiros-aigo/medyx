/* excluidos.js — quem não entra na construção da referência, e por quê.
 *
 * Abre pela ação da estatística "Comparáveis" ("ver os 6 fora da referência").
 * Substitui a leitura que a barra de composição dava: ela mostrava a PROPORÇÃO
 * em três segmentos, mas o motivo de cada exclusão nunca coube nela, e o motivo
 * é o que se contesta. A proporção agora está no próprio número (63 de 64).
 *
 * ── o que este painel mostra, e o que ele deixou de mostrar (2026-09-05) ────
 * Só o cooperado e as consultas dele na janela. Saíram, a pedido do usuário, a
 * natureza da exclusão ("definitiva · por desenho da análise" / "provisória ·
 * regra em validação"), a marca de "triagem clínica pendente" e o motivo por
 * extenso — que na prática repetia a natureza ("Regra provisória da
 * classificação v1.0, em validação clínica.").
 *
 * A regra do léxico ("exclusão SEM MOTIVO não é publicável") continua cumprida,
 * em outra superfície: a linha do cooperado na tabela carrega a etiqueta "não
 * forma a referência" com motivo e natureza no `title` (`tabela.js`,
 * `celulaIdentidade`). O motivo não sumiu do produto, saiu da LISTA — que é
 * uma resposta de conferência ("quem são os 6?"), e seis parágrafos de método
 * empilhados respondiam outra pergunta.
 *
 * Nada foi recalculado: `motivos`, `natureza`, `natureza_rotulo` e
 * `revisao_pendente` seguem no payload, à espera de quem os queira.
 *
 * ── fronteira visual ────────────────────────────────────────────────────────
 * Geometria de GAVETA, não de modal centrado: é uma lista que se lê de cima a
 * baixo e pode passar de uma tela. Reusa `.painel-lateral` / `.pnl-hd` /
 * `.pnl-corpo` / `.painel-x` do painel de procedimento (DIRETRIZES §5), com a
 * variante `.pnl-modal` para o que muda de verdade: aqui há cortina, porque
 * este painel não é para trabalhar ao lado da tabela, é para ler e fechar.
 */
'use strict';

import { el } from '../lib/dom.js';
import { TELAS, comRegua } from '../lib/rotas.js';


/** Uma entrada: quem, o volume que ele tem na janela, e a porta do dossiê. */
function entrada(x) {
  const l = el('div', 'pnl-ent');

  const hd = el('div', 'row row-between');
  const txt = el('div', 'stack g4');
  txt.appendChild(el('span', 'mono', x.id));
  if (x.consultas_fmt) {
    txt.appendChild(el('span', 'dlg-u', `${x.consultas_fmt} consultas na janela`));
  }
  hd.appendChild(txt);

  /* MESMO chevron da última coluna da tabela, e pelo mesmo motivo: quem lê
     "este cooperado não forma a referência" pergunta em seguida "por quê", e a
     resposta está no dossiê. Sem ele, a saída daqui era fechar a gaveta,
     procurar o cooperado na tabela e clicar lá.
     A régua viaja no link (`comRegua`), como em toda navegação do app: trocar
     de tela não devolve o analista ao padrão sem ele ter pedido. */
  const a = document.createElement('a');
  a.className = 'chev';
  a.href = comRegua(TELAS.cooperado.caminho(x.id));
  a.textContent = '\u203a';
  a.title = 'Abrir o dossiê analítico deste cooperado.';
  a.setAttribute('aria-label', `abrir dossiê analítico de ${x.id}`);
  hd.appendChild(a);

  l.appendChild(hd);
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
  const painel = el('aside', 'painel-lateral pnl-modal');
  painel.setAttribute('role', 'dialog');
  painel.setAttribute('aria-modal', 'true');
  painel.setAttribute('aria-label', 'Fora da referência');

  const topo = el('div', 'row row-between pnl-hd');
  const t = el('div', 'stack g4');
  t.appendChild(el('span', 'dlg-t', `${lista.length} fora da referência`));
  /* A frase que impede a leitura errada: estar fora da CONSTRUÇÃO da referência
     não é estar fora da análise. Eles continuam medidos contra ela. */
  t.appendChild(el('span', 'dlg-s',
    'Seguem medidos contra a referência da área; apenas não a definem.'));
  const fechar = el('button', 'painel-x', '✕');
  fechar.type = 'button';
  fechar.setAttribute('aria-label', 'Fechar');
  fechar.title = 'Fechar';
  topo.append(t, fechar);

  const corpo = el('div', 'pnl-corpo');
  for (const x of lista) corpo.appendChild(entrada(x));

  painel.append(topo, corpo);
  destino.append(scrim, painel);

  let abridor = null;

  /* Quem desenha é o CSS: aqui só se alterna classe e o atributo `hidden`, que
     o contrato já trata (`.painel-lateral[hidden]`, `.scrim.on`). */
  function mostrar(visivel) {
    scrim.classList.toggle('on', visivel);
    painel.hidden = !visivel;
    if (visivel) { abridor = document.activeElement; fechar.focus(); }
    else abridor?.focus?.();
  }
  mostrar(false);

  const sair = () => mostrar(false);
  scrim.addEventListener('click', sair);
  fechar.addEventListener('click', sair);
  document.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape' && !painel.hidden) sair();
  });

  return { abrir: () => mostrar(true) };
}
