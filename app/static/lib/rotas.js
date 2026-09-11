/* lib/rotas.js — o mapa de telas, num lugar só.
 *
 * A regra das URLs deste app: **o caminho diz O QUE você está olhando; a query
 * diz COMO**. Área e cooperado são coisas, e por isso viajam no caminho; a
 * régua da análise (janela, critério, referência, piso) é modificador de
 * leitura, e por isso viaja na query, igual em toda tela.
 *
 *     /                     Panorama de oportunidades (a porta de entrada)
 *     /area/{id}            Área de atuação
 *     /cooperados           Índice de cooperados (a porta para um caso)
 *     /cooperado/{id}       Dossiê do cooperado
 *     /procedimentos        Índice de procedimentos (a porta para um SADT)
 *     /procedimento/{cd}    O procedimento na especialidade inteira
 *     /metodologia          Nota metodológica
 *     /conta                Minha conta (identidade e segurança da sessão)
 *
 * `/cooperados` no plural é a COLEÇÃO e `/cooperado/{id}` é UM. Menu nomeia
 * coleção, não documento — é por isso que a lateral diz "Cooperados" e não
 * "Dossiê".
 *
 * Antes, `/` era a Área e a área escolhida ia em `?area=` — acidente de quando
 * ela era a única tela. O preço aparecia em dois lugares: a porta de entrada do
 * app não tinha dono, e um dossiê carregava `?area=` que ninguém validava (o
 * cooperado pertence a uma área só, e o servidor a descobre pelo id).
 *
 * Este módulo é lido pelo chassi (navegação e migalha) e por `inicio.js`. Uma
 * tela nova entra aqui, e as duas coisas passam a conhecê-la.
 */
'use strict';

/** Rótulo de cada tela, para a navegação e a migalha. */
export const TELAS = {
  panorama: { rotulo: 'Panorama', caminho: () => '/' },
  area: { rotulo: 'Área de Atuação', caminho: (id) => `/area/${encodeURIComponent(id)}` },
  cooperados: { rotulo: 'Cooperados', caminho: () => '/cooperados' },
  cooperado: { rotulo: 'Cooperado',
               caminho: (id) => `/cooperado/${encodeURIComponent(id)}` },
  procedimentos: { rotulo: 'Procedimentos', caminho: () => '/procedimentos' },
  procedimento: { rotulo: 'Procedimento',
                  caminho: (cd) => `/procedimento/${encodeURIComponent(cd)}` },
  metodologia: { rotulo: 'Nota Metodológica', caminho: () => '/metodologia' },
  /* Não está na navegação lateral: a porta é o bloco de conta do rodapé. Entra
     aqui porque a migalha e `inicio.js` leem deste mapa. */
  conta: { rotulo: 'Minha Conta', caminho: () => '/conta' },
};

/**
 * Que tela a URL atual pede, e sobre qual coisa.
 * @returns {{tela: string|null, area?: string, cooperado?: string}}
 */
export function rotaAtual() {
  const seg = location.pathname.split('/').filter(Boolean);
  if (!seg.length) return { tela: 'panorama' };
  const [raiz, id] = seg;
  const alvo = id ? decodeURIComponent(id) : null;
  if (raiz === 'area') return { tela: 'area', area: alvo };
  if (raiz === 'cooperados') return { tela: 'cooperados' };
  if (raiz === 'cooperado') return { tela: 'cooperado', cooperado: alvo };
  if (raiz === 'procedimentos') return { tela: 'procedimentos' };
  if (raiz === 'procedimento') return { tela: 'procedimento', procedimento: alvo };
  if (raiz === 'metodologia') return { tela: 'metodologia' };
  if (raiz === 'conta') return { tela: 'conta' };
  return { tela: null };
}

/**
 * Uma URL de tela com a régua atual preservada. A régua acompanha SEMPRE:
 * trocar de tela não pode devolver o analista ao padrão sem ele ter pedido.
 *
 * ── por que ela também monta os parâmetros do destino ───────────────────────
 * Porque quem precisou de um parâmetro a mais montou a query à mão, e o
 * resultado foi um endereço com DOIS `?`: o link "ver na área de atuação" saía
 * como `/area/x?aba=procedimentos?criterio=p75`. O navegador lia `aba` como
 * "procedimentos?criterio=p75", nenhuma aba casava (tela em branco) e o
 * critério sumia em silêncio, com a tela recalculando no padrão.
 *
 * Uma função, um lugar que junta query. `extras` é como se acrescenta
 * parâmetro; valor `null` ou vazio REMOVE a chave, para o chamador poder
 * limpar sem montar string. E se o caminho vier com query mesmo assim, ela é
 * absorvida em vez de concatenada — a função não tem como ser usada errado.
 *
 * @param {string} caminho  caminho da tela (query aqui é aceita, mas dispensável)
 * @param {Record<string, string|number|null|undefined>} [extras]  parâmetros do destino
 * @returns {string}
 */
export function comRegua(caminho, extras = null) {
  const [base, queryDoCaminho] = String(caminho).split('?');
  const q = new URLSearchParams(location.search);
  /* `ord`, `dir`, `recorte`, `perfil` e `aba` são estado de apresentação da
     tela de origem e não significam nada na de destino. */
  for (const chave of ['ord', 'dir', 'recorte', 'perfil', 'aba']) q.delete(chave);
  q.delete('area');   // a área agora é caminho, não query
  /* O que o DESTINO pede entra depois de limpar a origem: é assim que `aba`,
     apagada acima como estado de origem, sobrevive quando é pedida de propósito. */
  for (const [chave, valor] of new URLSearchParams(queryDoCaminho ?? '')) {
    q.set(chave, valor);
  }
  for (const [chave, valor] of Object.entries(extras ?? {})) {
    if (valor == null || valor === '') q.delete(chave);
    else q.set(chave, String(valor));
  }
  const busca = q.toString();
  return busca ? `${base}?${busca}` : base;
}
