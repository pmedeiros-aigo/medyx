/* shell/conta.js — o bloco de conta no rodapé da lateral, e o menu dele.
 *
 * Responde, em toda tela, a "com que conta eu estou olhando isto?" — pergunta
 * que num produto que exibe cooperado nominal não é conforto, é rastreabilidade.
 *
 * ── a regra que este módulo herda ───────────────────────────────────────────
 *
 * O bloco ficou fora do chassi até hoje porque, sem autenticação, um nome fixo
 * na tela seria ficção. A regra não mudou: SEM SESSÃO, O BLOCO NÃO APARECE.
 * Quem decide é /api/conta, e o slot do `shell.html` fica `hidden`. Não há
 * estado "convidado", nem nome de exemplo, nem silhueta cinza.
 *
 * ── por que menu, e não link direto para /conta ─────────────────────────────
 *
 * Porque Sair precisa estar a um clique de QUALQUER tela. Mandar o analista
 * abrir uma página para poder sair é pedir uma navegação para executar uma
 * ação. Com o menu, /conta continua a um clique e Sair também.
 *
 * ── fronteira ───────────────────────────────────────────────────────────────
 *
 * Nada aqui calcula, e nada decide aparência: o JS alterna `.on` e escreve o
 * `aria-expanded` que o CSS lê para girar o chevron. Um estado, uma origem.
 */
'use strict';

import { buscar } from '../lib/api.js';
import { el } from '../lib/dom.js';

const ID_MENU = 'menu-conta';

/** O gatilho, quando existe (só existe com sessão). */
const gatilho = () => document.querySelector('.side-user');
const menu = () => document.getElementById(ID_MENU);

/** Fecha o menu e devolve `true` se ele estava aberto (é o que o Esc do
 *  `shell.js` precisa saber para não consumir a tecla à toa). */
export function fecharMenuConta() {
  const m = menu();
  if (!m?.classList.contains('on')) return false;
  m.classList.remove('on');
  gatilho()?.setAttribute('aria-expanded', 'false');
  gatilho()?.focus();
  return true;
}

function alternar() {
  const m = menu();
  if (!m) return;
  const abrindo = !m.classList.contains('on');
  m.classList.toggle('on', abrindo);
  gatilho().setAttribute('aria-expanded', String(abrindo));
  // Abrir pelo teclado tem de pousar o foco DENTRO do menu, senão o Tab
  // seguinte sai do painel que acabou de abrir.
  if (abrindo) m.querySelector('.menu-item')?.focus();
}

/** Um item do menu. Sempre `<a>`: os dois destinos são navegação de verdade
 *  (uma tela e uma rota do servidor), e link que finge ser botão perde o menu
 *  de contexto, o "abrir em nova aba" e a leitura correta por leitor de tela. */
function item(href, rotulo, caminhoIcone) {
  const a = el('a', 'menu-item');
  a.href = href;
  a.setAttribute('role', 'menuitem');
  a.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none"`
    + ` stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"`
    + ` aria-hidden="true">${caminhoIcone}</svg>`;
  a.appendChild(document.createTextNode(rotulo));
  return a;
}

const ICONE_CONTA = '<circle cx="12" cy="8" r="3.2"/>'
  + '<path d="M5.5 19.5c.8-3.4 3.2-5.2 6.5-5.2s5.7 1.8 6.5 5.2"/>';
const ICONE_SAIR = '<path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3"/>'
  + '<path d="M10 16l-4-4 4-4"/><path d="M6 12h11"/>';

/**
 * Monta o bloco de conta, se houver sessão.
 *
 * Falha de rede NÃO derruba a tela: o bloco simplesmente não aparece. A
 * identidade de quem está logado é contexto do chassi, não a análise que a
 * página existe para mostrar; deixar o Panorama inteiro cair porque /api/conta
 * não respondeu seria inverter a importância das duas coisas.
 */
export async function montarConta() {
  const slot = document.querySelector('[data-slot="conta"]');
  if (!slot) return;

  let conta;
  try {
    conta = await buscar('/api/conta');
  } catch {
    return;                       // sem sessão conhecida, sem bloco
  }
  if (!conta?.autenticado || !conta.usuario) return;

  const { nome, email, iniciais } = conta.usuario;

  const anc = el('div', 'menu-anc');

  const botao = el('button', 'side-user');
  botao.type = 'button';
  botao.setAttribute('aria-haspopup', 'menu');
  botao.setAttribute('aria-expanded', 'false');
  botao.setAttribute('aria-controls', ID_MENU);
  const nm = el('span', 'nm');
  nm.appendChild(el('b', null, nome));
  nm.appendChild(el('span', null, email));
  botao.append(el('span', 'av', iniciais), nm, el('span', 'car', '▾'));

  const lista = el('div', 'menu menu-acima');
  lista.id = ID_MENU;
  lista.setAttribute('role', 'menu');
  lista.append(
    item('/conta', 'Minha conta', ICONE_CONTA),
    el('div', 'menu-sep'),
    item('/sair', 'Sair', ICONE_SAIR),
  );

  anc.append(botao, lista);
  slot.replaceChildren(anc);
  slot.hidden = false;

  botao.addEventListener('click', alternar);

  /* Clicar fora fecha. Na captura, para acontecer antes de qualquer clique da
     página, e checando `closest` para o clique DENTRO do menu não se fechar
     antes de navegar. */
  document.addEventListener('click', (ev) => {
    if (!ev.target.closest('.menu-anc')) fecharMenuConta();
  }, true);

  /* Setas percorrem o menu. Sem isto o painel abre e o teclado fica preso no
     primeiro item, que é a diferença entre "acessível" e "focável"
     (DIRETRIZES §19). */
  lista.addEventListener('keydown', (ev) => {
    if (ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp') return;
    ev.preventDefault();
    const itens = [...lista.querySelectorAll('.menu-item')];
    const i = itens.indexOf(document.activeElement);
    const passo = ev.key === 'ArrowDown' ? 1 : -1;
    itens[(i + passo + itens.length) % itens.length]?.focus();
  });
}
