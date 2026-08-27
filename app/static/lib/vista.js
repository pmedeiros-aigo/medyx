/* lib/vista.js — o ESTADO DA VISTA e sua sincronia com a URL.
 *
 * "Vista" é o que está em cena sem que nenhum número mude: qual recorte, qual
 * perfil, qual aba, por qual coluna se ordena. Não é análise — a análise viaja
 * na mesma URL (janela, critério, referência) e pertence ao servidor.
 *
 * ── por que isto existe ─────────────────────────────────────────────────────
 *
 * Este estado morava dentro de `tabela.js`, e o preço apareceu quando o bloco
 * "Perfis na área" nasceu: para escolher um perfil, ele precisava pedir à
 * TABELA (`tabela.escolherPerfil`), e a tabela precisava avisar o GRÁFICO. Um
 * bloco comandando outro por dentro, com a página no meio sem saber de nada.
 *
 * A regra que este módulo estabelece: **a página é dona do estado; os blocos
 * desenham o que recebem**. Um bloco novo passa a ser mais um assinante, não
 * mais um nó na corrente.
 *
 * A URL é a única memória: um link de evidência tem de reabrir exatamente a
 * mesma leitura. `history.replaceState` porque recortar não é navegar — o botão
 * "voltar" deve sair da tela, não desfazer um clique em chip.
 */
'use strict';

/** Chaves de apresentação na URL (as do motor ficam com lib/api.js). */
const CHAVES = ['recorte', 'perfil', 'aba', 'ord', 'dir', 'q'];

/**
 * Cria o estado da vista, já lido da URL.
 *
 * @param {object} inicial  valores quando a URL não diz nada
 * @param {(estado: object) => void} aoMudar  chamado a cada mudança, com o estado
 * @returns {{estado: object, definir: (mudanca: object) => void}}
 */
export function criarVista(inicial, aoMudar) {
  const q = new URLSearchParams(location.search);
  const estado = { ...inicial };
  for (const chave of CHAVES) {
    const v = q.get(chave);
    if (v != null && chave in estado) estado[chave] = v;
  }

  /** Grava só o que DIVERGE do padrão: URL curta é URL que se manda por e-mail. */
  function gravar() {
    const q2 = new URLSearchParams(location.search);
    for (const chave of CHAVES) {
      if (!(chave in estado)) continue;
      const v = estado[chave];
      if (v == null || v === inicial[chave]) q2.delete(chave);
      else q2.set(chave, v);
    }
    const busca = q2.toString();
    history.replaceState(null, '', busca ? `?${busca}` : location.pathname);
  }

  return {
    estado,
    /** Muda uma ou mais chaves, grava na URL e avisa a página. */
    definir(mudanca) {
      Object.assign(estado, mudanca);
      gravar();
      aoMudar(estado);
    },
  };
}
