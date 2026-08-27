/* lib/api.js — a única porta do front para a API.
 *
 * Antes havia `fetch` em quatro arquivos, cada um com o seu jeito de montar a
 * query, de falhar e de anunciar que estava carregando. O sintoma: a linha
 * "carregando…" precisou ser colada à mão em `area.js` e de novo em
 * `dossie.js`, e o arranque frio do servidor aparecia como tela em branco em
 * quem esquecesse de colar.
 *
 * Duas regras que este módulo carrega pelos outros:
 *
 *   1  A RÉGUA VIAJA SEMPRE. Todo pedido leva a query da página (janela,
 *      critério, referência, área). É o que garante que a tela mostra o que a
 *      URL promete, e que um link de evidência reabre a mesma leitura.
 *   2  ESTADO DE CARGA É DA TELA, NÃO DO CONSOLE. `buscar` recebe onde
 *      anunciar; a primeira carga depois do servidor subir custa segundos
 *      (parquet + motores), e silêncio nesse intervalo lê como defeito.
 *
 * O front continua sem calcular nada: este módulo transporta, não interpreta.
 */
'use strict';

import { el } from './dom.js';

/** Estado de apresentação puro: não muda cálculo nenhum e sujaria o cache.
 *
 *  `recorte` e `perfil` saíram desta lista em 2026-08-19. Eles continuam sem
 *  tocar na RÉGUA — janela, critério, referência e piso seguem sendo o que
 *  chaveia os motores memoizados —, mas passaram a decidir QUEM ENTRA NA SOMA
 *  dos blocos de achado, e isso é cálculo. Quem os quiser fora de um pedido
 *  específico manda `soMotor`; quem os quiser dentro manda `extra`. */
const SO_DA_TELA = ['aba', 'ord', 'dir', 'recorte', 'perfil', 'q'];

/**
 * Busca JSON da API com a régua da página.
 *
 * @param {string} caminho        ex.: '/api/area/ginecologia'
 * @param {object} [opcoes]
 * @param {HTMLElement} [opcoes.anunciarEm]  onde mostrar "carregando…"
 * @param {string} [opcoes.rotulo]           o que dizer enquanto carrega
 * @param {boolean} [opcoes.soMotor]         descarta parâmetros de apresentação
 * @param {object}  [opcoes.extra]           pares a acrescentar à query; valor
 *        `null`/`undefined` remove o parâmetro em vez de mandá-lo vazio
 * @returns {Promise<any>}
 */
export async function buscar(caminho, { anunciarEm, rotulo, soMotor = false,
                                        extra } = {}) {
  const q = new URLSearchParams(location.search);
  if (soMotor) for (const chave of SO_DA_TELA) q.delete(chave);
  /* `extra` entra DEPOIS do descarte: um pedido pode precisar do recorte mesmo
     mandando `soMotor` (é o caso da aba Procedimentos, que quer a régua da URL
     limpa e o recorte explícito). */
  for (const [chave, valor] of Object.entries(extra ?? {})) {
    if (valor === null || valor === undefined || valor === '') q.delete(chave);
    else q.set(chave, String(valor));
  }
  const busca = q.toString();
  const url = busca ? `${caminho}?${busca}` : caminho;

  const aviso = anunciarEm ? el('span', 'sub', rotulo ?? 'carregando…') : null;
  if (aviso) anunciarEm.appendChild(aviso);
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${caminho} respondeu ${r.status}`);
    return await r.json();
  } finally {
    aviso?.remove();
  }
}

/** Busca um arquivo estático como texto (o chassi, hoje). */
export async function buscarTexto(caminho) {
  const r = await fetch(caminho);
  if (!r.ok) throw new Error(`${caminho} respondeu ${r.status}`);
  return r.text();
}
