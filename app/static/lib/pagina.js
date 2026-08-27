/* lib/pagina.js — o começo e o fim que toda tela repete.
 *
 * Toda página faz a mesma abertura: pede o chassi, escreve no slot, e se algo
 * falhar declara o estado em vez de deixar a tela em branco. Estava copiado em
 * `area.js` e `dossie.js`, com um `try/catch` cada — e a terceira tela copiaria
 * de novo.
 *
 * O que NÃO entra aqui: nada específico de tela. Este módulo não sabe o que é
 * área, cooperado ou recorte; ele monta o chassi e chama `montar`.
 */
'use strict';

import { comRegua } from './rotas.js';
import { montarShell, mostrarFalha } from '../shell/shell.js';
import { ativarDicas } from './dica.js';

/**
 * Abre uma tela.
 *
 * @param {object} pagina
 * @param {string} pagina.titulo   vai para <title> (a aba do navegador)
 * @param {(destino: string) => string} pagina.aoTrocarArea  para onde levar
 *        quando a área muda no seletor da lateral; devolve a URL
 * @param {object} [pagina.escopo]  quando a tela FILTRA em vez de navegar:
 *        `{ todas: true, aoFiltrar(campo, id) }`. Com ele, Especialidade e Área
 *        ganham a opção "Todas", abrem nela, e escolher chama `aoFiltrar` sem
 *        recarregar. É o que separa um FILTRO de uma navegação disfarçada: o
 *        seletor passa a mudar o que está em cena, e não a tela em que se está.
 * @param {(ctx: {conteudo: HTMLElement, area: string, meta: object}) => Promise<void>}
 *        pagina.montar  o conteúdo da tela
 */
export async function abrirPagina({ titulo, aoTrocarArea, escopo, montar }) {
  /* O tooltip do app substitui o `title` nativo em TODA a tela, inclusive no
     chassi: um ouvinte só, delegado no documento. Ver lib/dica.js. */
  ativarDicas();
  document.title = `Medyx · ${titulo}`;
  try {
    const ctx = await montarShell({
      /* Trocar de área RECARREGA: o motor recalcula e a área é caminho, não
         query. A régua acompanha (`comRegua`), porque um link de evidência tem
         de reabrir a mesma leitura. */
      aoTrocarArea: (id) => { location.href = comRegua(aoTrocarArea(id)); },
      escopo,
    });
    await montar(ctx);
  } catch (erro) {
    mostrarFalha(erro);
  }
}
