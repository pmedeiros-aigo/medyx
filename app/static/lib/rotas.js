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
 *     /metodologia          Nota metodológica
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
  cooperado: { rotulo: 'Dossiê do Cooperado',
               caminho: (id) => `/cooperado/${encodeURIComponent(id)}` },
  metodologia: { rotulo: 'Nota Metodológica', caminho: () => '/metodologia' },
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
  if (raiz === 'metodologia') return { tela: 'metodologia' };
  return { tela: null };
}

/** Uma URL de tela com a régua atual preservada. A régua acompanha SEMPRE:
 *  trocar de tela não pode devolver o analista ao padrão sem ele ter pedido. */
export function comRegua(caminho) {
  const q = new URLSearchParams(location.search);
  /* `ord`, `dir`, `recorte`, `perfil` e `aba` são estado de apresentação da
     tela de origem e não significam nada na de destino. */
  for (const chave of ['ord', 'dir', 'recorte', 'perfil', 'aba']) q.delete(chave);
  q.delete('area');   // a área agora é caminho, não query
  const busca = q.toString();
  return busca ? `${caminho}?${busca}` : caminho;
}
