/* shell/seletores.js — os comboboxes da barra lateral (especialidade e área).
 *
 * Abrir e fechar é CSS puro (checkbox + .scrim, o desvio autorizado do
 * contrato); o JS só alterna `.on` e avisa quem escolheu. Nenhuma decisão
 * visual, nenhum número.
 */
'use strict';

/* ── combobox ─────────────────────────────────────────────────────────────── */

const trigger = (campo) => document.querySelector(`[data-trig="${campo}"]`);
const lista = (campo) => document.querySelector(`[data-opcoes="${campo}"]`);
const caixa = (campo) => document.getElementById(campo === 'esp' ? 'op-e-sh' : 'op-a-sh');

/** Uma opção do popover: nome + marca de seleção (seletor MVP do guia).
 *
 * `perfil` vai para o `title`: o rótulo diz o NOME da área, o hover diz o que a
 * distingue das vizinhas. Sem isso, "Ginecologia", "Ginecologia e Obstetrícia" e
 * "Obstetrícia" são três nomes parecidos sem nada que explique a diferença — e a
 * diferença (intensidade obstétrica) é justamente o que decide contra quem cada
 * cooperado é comparado. */
function opcao(id, nome, perfil) {
  const el = document.createElement('label');
  el.className = 'opt';
  el.tabIndex = 0;
  el.dataset.id = id;
  if (perfil) el.title = perfil;
  const n = document.createElement('span');
  n.className = 'oname';
  n.textContent = nome;
  const ck = document.createElement('span');
  ck.className = 'ock';
  ck.textContent = '✓';
  el.append(n, ck);
  return el;
}

/** Um valor possível do gatilho. Só o que estiver com `.on` aparece. */
function valor(id, nome) {
  const el = document.createElement('span');
  el.className = 'v';
  el.dataset.id = id;
  el.textContent = nome;
  return el;
}

/** Marca a escolha: `.on` no valor e na opção, nos dois lugares ao mesmo tempo. */
export function escolher(campo, id) {
  const trig = trigger(campo);
  /* O seletor pode não existir: telas onde ele não governa nada são montadas
     sem ele (ver `ajustarControlesDaTela` no shell). Sair calado é o certo —
     não há o que marcar. */
  if (!trig || !lista(campo)) return;
  for (const v of trig.querySelectorAll('.v')) v.classList.toggle('on', v.dataset.id === id);
  for (const o of lista(campo).children) o.classList.toggle('on', o.dataset.id === id);
}

/** Preenche um seletor e liga a escolha. `aoTrocar` recebe o id escolhido. */
export function montarSeletor(campo, itens, escolhido, aoTrocar) {
  const trig = trigger(campo);
  const pop = lista(campo);
  if (!trig || !pop) return;   // tela montada sem este controle
  trig.querySelector('.ph')?.remove();
  const car = trig.querySelector('.car');
  for (const { id, nome, perfil } of itens) {
    trig.insertBefore(valor(id, nome), car);
    pop.appendChild(opcao(id, nome, perfil));
  }
  escolher(campo, escolhido);

  const trocar = (opt) => {
    escolher(campo, opt.dataset.id);
    caixa(campo).checked = false;   // escolher fecha: o CSS lê o estado da caixa
    aoTrocar?.(opt.dataset.id);
  };
  pop.addEventListener('click', (ev) => {
    const opt = ev.target.closest('.opt');
    if (opt) trocar(opt);
  });
  pop.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Enter' && ev.key !== ' ') return;
    const opt = ev.target.closest('.opt');
    if (!opt) return;
    ev.preventDefault();
    trocar(opt);
  });
}

/** Fecha um popover aberto e devolve o foco a quem o abriu. Fechar por Esc não
 *  é CSS (CSS não escuta tecla); aqui só se desmarca a mesma caixa que o CSS lê. */
export function fecharPopover(campo) {
  const cx = caixa(campo);
  if (!cx?.checked) return false;
  cx.checked = false;
  trigger(campo).focus();
  return true;
}
