/* perfis.js — o filtro por SUB-PERFIL, ao lado do recorte.
 *
 * Sub-perfil é IDENTIDADE (opera, alto risco, plantão, PTGI), nunca régua:
 * escolher recorta QUEM APARECE na lista e no gráfico; a comparação continua
 * sendo com a área inteira.
 *
 * ── seleção MÚLTIPLA ────────────────────────────────────────────────────────
 *
 * Marcar dois perfis mostra quem carrega UM OU OUTRO (união), não a interseção:
 * os perfis são identidades que se acumulam, e ninguém procura "quem opera E é
 * de alto risco" — procura-se "quem é um desses". A caixa marcada é a forma
 * certa para isso; um ✓ de lista sugeriria escolha única.
 *
 * Com UM perfil em cena a tabela ganha a coluna "Posto no perfil"; com dois ou
 * mais ela sai, porque posto é a posição DENTRO de um perfil e não existe
 * definição honesta de posto entre dois.
 *
 * ── por que deixou de ser um cartão ─────────────────────────────────────────
 *
 * Isto era um bloco "Perfis na área" com título, subtítulo e uma faixa de
 * pastilhas — um cartão inteiro da altura de um gráfico para hospedar um
 * filtro. Ocupava a dobra que pertence ao conteúdo e dava a uma escolha de
 * recorte o mesmo peso visual da distribuição.
 *
 * No Clean v3 ele é um BOTÃO com popover, na mesma linha do recorte: os dois
 * são a mesma pergunta ("quem aparece"), e agora ocupam uma linha só.
 *
 * A composição da área (quantos carregam cada perfil, quantos não carregam
 * nenhum) não se perdeu: virou a contagem ao lado de cada opção e a linha do
 * rodapé do popover.
 *
 * ── fronteira visual ───────────────────────────────────────────────────────
 * Abrir e fechar é CSS puro (checkbox + scrim), como os demais seletores.
 * Nenhuma classe nova fora das declaradas em components.css para este bloco.
 */
'use strict';

import { el } from '../lib/dom.js';

const ID_CAIXA = 'pf-sh';

/**
 * Monta o botão de perfil dentro de `destino` (a faixa do recorte).
 *
 * @param {HTMLElement} destino
 * @param {object} dados  resposta de /api/area/{id}
 * @param {(chave: string|null) => void} aoAlternar  alterna um perfil; `null` limpa
 * @returns {{marcar: (chaves: string[]) => void} | null}
 */
export function montarPerfis(destino, dados, aoAlternar) {
  const perfis = dados.cooperados?.perfis ?? [];
  if (!perfis.length) return null;

  const caixa = document.createElement('input');
  caixa.type = 'checkbox';
  caixa.id = ID_CAIXA;
  caixa.className = 'oc';
  const scrim = el('label', 'scrim scrim-pf');
  scrim.setAttribute('for', ID_CAIXA);
  scrim.setAttribute('aria-label', 'Fechar seleção');

  const campo = el('div', 'pf');
  const gatilho = el('label', 'pf-trig');
  gatilho.setAttribute('for', ID_CAIXA);
  gatilho.tabIndex = 0;
  gatilho.insertAdjacentHTML('beforeend',
    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke-width="1.8" '
    + 'stroke-linecap="round" aria-hidden="true"><path d="M4 6h16M7 12h10M10 18h4"/></svg>');
  gatilho.appendChild(el('span', null, 'Perfil'));
  const etiqueta = el('span', 'pf-tag');       // só aparece com perfil em cena
  gatilho.appendChild(etiqueta);
  gatilho.insertAdjacentHTML('beforeend',
    '<svg class="car" width="12" height="12" viewBox="0 0 24 24" fill="none" '
    + 'stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>');

  const pop = el('div', 'pf-pop');
  const opcoes = new Map();

  const opcao = (chave, rotulo, n, selecionavel, motivo, ajuda) => {
    const o = el('button', selecionavel ? 'pf-opt' : 'pf-opt na');
    o.type = 'button';
    // caixa marcável: a seleção é múltipla, e ✓ de lista sugeriria escolha única
    o.insertAdjacentHTML('beforeend',
      '<span class="bx"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" '
      + 'stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" '
      + 'aria-hidden="true"><path d="M5 12l5 5 9-10"/></svg></span>');
    o.appendChild(el('span', 'nm', rotulo));
    if (n != null) o.appendChild(el('span', 'n', String(n)));
    o.title = [motivo, ajuda].filter(Boolean).join(' · ');
    if (selecionavel) {
      // NÃO fecha ao marcar: escolha múltipla se faz em sequência, e fechar a
      // cada clique obrigaria a reabrir para o segundo perfil
      o.addEventListener('click', () => aoAlternar?.(chave));
    } else {
      o.disabled = true;
    }
    pop.appendChild(o);
    opcoes.set(chave, o);
    return o;
  };

  for (const pf of perfis) {
    opcao(pf.chave, pf.rotulo, pf.n, pf.selecionavel, pf.motivo, pf.ajuda);
  }

  /* Rodapé: fecha a conta da composição (quantos não carregam perfil nenhum) e
     oferece a saída. Some quando não há perfil em cena — botão de limpar o que
     já está limpo é ruído. */
  const rodape = el('div', 'pf-ft');
  const sem = dados.cooperados?.sem_perfil;
  const nota = el('span', 'pf-nota',
    sem ? `${sem} sem sub-perfil` : '');
  const limpar = el('button', 'pf-limpar', 'Limpar seleção');
  limpar.type = 'button';
  limpar.addEventListener('click', () => { caixa.checked = false; aoAlternar?.(null); });
  rodape.append(nota, limpar);
  pop.appendChild(rodape);

  campo.append(caixa, scrim, gatilho, pop);
  destino.appendChild(campo);

  return {
    /** Reflete os perfis em cena: etiqueta no botão e caixas marcadas. */
    marcar: (chaves) => {
      const ativos = new Set(chaves ?? []);
      const nomes = perfis.filter((x) => ativos.has(x.chave)).map((x) => x.rotulo);
      /* Um perfil aparece pelo NOME; vários viram contagem — três nomes no
         botão empurrariam o resto da faixa para fora da linha. */
      etiqueta.textContent = nomes.length === 1 ? nomes[0]
        : nomes.length ? `${nomes.length} perfis` : '';
      if (nomes.length > 1) etiqueta.title = nomes.join(' · ');
      campo.classList.toggle('tem-perfil', nomes.length > 0);
      for (const [k, o] of opcoes) o.classList.toggle('on', ativos.has(k));
    },
  };
}
