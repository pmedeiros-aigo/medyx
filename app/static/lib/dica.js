/* lib/dica.js — o tooltip do app, um só para toda a tela.
 *
 * O app tinha ~45 hovers em `title` nativo. Três problemas, todos do navegador
 * e nenhum contornável por CSS: aparece depois de ~1s, tem a cara do sistema
 * operacional (que muda entre macOS, Windows e Linux) e não aceita estilo.
 * Num produto que vai a diretoria, o hover é parte do material.
 *
 * ── por que interceptar `title` em vez de trocar os 45 lugares ──────────────
 *
 * Um ouvinte só, delegado no documento: no primeiro hover o `title` é removido
 * do elemento (antes do atraso nativo disparar, então a caixa do sistema nunca
 * chega a aparecer) e guardado em `data-dica`. Quem escreve bloco novo continua
 * escrevendo `title` e ganha o tooltip do app de graça — não há API nova para
 * lembrar, e nada quebra se alguém esquecer.
 *
 * ── por que a caixa é FIXA no body, e não um ::after ────────────────────────
 *
 * `::after` no próprio elemento é mais simples e foi descartado: metade dos
 * hovers do app está dentro de `.tbl-scroll`, que é `overflow:auto` e recortaria
 * a caixa. Uma caixa `position:fixed` filha do body não é recortada por
 * ancestral nenhum, e ainda permite virar para baixo quando não há espaço em
 * cima.
 *
 * Acessibilidade: `title` também é lido por leitor de tela, e removê-lo tira
 * isso. Por isso o texto volta para o elemento em `aria-label` quando ele não
 * tem texto próprio (ícone, marca) e em `aria-description` quando tem — assim o
 * leitor de tela não perde a explicação nem passa a anunciar o hover no lugar
 * do conteúdo.
 */
'use strict';

const MARGEM = 8;      // vão entre o elemento e a caixa
let caixa = null;
let alvoAtual = null;

function caixaDoApp() {
  if (!caixa) {
    caixa = document.createElement('div');
    caixa.className = 'dica';
    caixa.setAttribute('role', 'tooltip');
    document.body.appendChild(caixa);
  }
  return caixa;
}

/** Coloca a caixa acima do elemento; abaixo quando não cabe. */
function posicionar(alvo) {
  const c = caixaDoApp();
  const r = alvo.getBoundingClientRect();
  const b = c.getBoundingClientRect();
  const acima = r.top - b.height - MARGEM;
  c.classList.toggle('abaixo', acima < 4);
  c.style.top = `${acima < 4 ? r.bottom + MARGEM : acima}px`;
  /* Centralizada no elemento e presa dentro da janela: hover numa célula da
     primeira ou da última coluna não pode empurrar a caixa para fora. */
  const meio = r.left + r.width / 2 - b.width / 2;
  c.style.left = `${Math.max(4, Math.min(meio, window.innerWidth - b.width - 4))}px`;
}

function mostrar(alvo, texto) {
  const c = caixaDoApp();
  c.textContent = texto;
  c.classList.add('on');
  alvoAtual = alvo;
  posicionar(alvo);
}

function esconder() {
  alvoAtual = null;
  caixa?.classList.remove('on');
}

/**
 * Liga o tooltip do app. Idempotente — chamar de novo não duplica ouvinte.
 */
export function ativarDicas() {
  if (document.body.dataset.dicasLigadas) return;
  document.body.dataset.dicasLigadas = '1';

  const adotar = (alvo) => {
    const texto = alvo.getAttribute('title');
    if (texto == null) return;
    alvo.removeAttribute('title');
    if (!texto.trim()) return;                 // title vazio é ausência de dica
    alvo.dataset.dica = texto;
    /* Sem texto próprio o elemento não tem nome acessível nenhum, e aí a dica é
       o nome; com texto próprio ela é descrição, e substituir o nome faria o
       leitor de tela anunciar a explicação no lugar do conteúdo. */
    if (!alvo.hasAttribute('aria-label') && !alvo.textContent.trim()) {
      alvo.setAttribute('aria-label', texto);
    } else if (!alvo.hasAttribute('aria-description')) {
      alvo.setAttribute('aria-description', texto);
    }
  };

  const entrar = (ev) => {
    const alvo = ev.target?.closest?.('[title],[data-dica]');
    if (!alvo) { esconder(); return; }
    adotar(alvo);
    const texto = alvo.dataset.dica;
    if (texto) mostrar(alvo, texto); else esconder();
  };

  // captura: pega o hover antes do atraso nativo, então a caixa do sistema
  // operacional não chega a ser desenhada nem na primeira vez
  document.addEventListener('mouseover', entrar, true);
  document.addEventListener('focusin', entrar, true);
  /* Só esconde ao sair DE VERDADE do elemento. `mouseout` também dispara ao
     entrar num filho dele (o rótulo dentro do botão, o `span` dentro da
     célula), e esconder ali fazia a caixa piscar e sumir com o cursor ainda
     parado sobre o mesmo alvo. */
  document.addEventListener('mouseout', (ev) => {
    if (!alvoAtual) return;
    const para = ev.relatedTarget;
    if (para && (alvoAtual.contains(para) || para.closest?.('[data-dica]'))) return;
    esconder();
  }, true);
  document.addEventListener('focusout', esconder, true);
  // rolar ou clicar tira a caixa: presa a uma posição que já mudou, ela mente
  document.addEventListener('scroll', esconder, true);
  document.addEventListener('click', esconder, true);
  window.addEventListener('resize', esconder);
  document.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape') esconder();
  });
}

/** Reposiciona se o alvo ainda estiver em cena (usado após render). */
export function reposicionarDica() {
  if (alvoAtual?.isConnected) posicionar(alvoAtual);
}
