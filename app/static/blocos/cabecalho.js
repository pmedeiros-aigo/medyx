/* cabecalho.js — o cabeçalho da PÁGINA, acima de qualquer bloco de trabalho.
 *
 * Três linhas, nesta ordem vertical:
 *   1  título              — que área
 *   2  subtítulo           — quantos, em que janela
 *   3  linha de contexto   — o enquadramento fixo da área, texto corrido
 *
 * Fica em módulo próprio, e não dentro de `area.js`, porque o Dossiê abre com a
 * mesma dupla título/subtítulo. Quando ele chegar, o que muda é o conteúdo, não
 * a construção.
 *
 * O banner de homologação (`.banner`, fatia 5 da shell) foi construído aqui e
 * REMOVIDO por decisão do usuário em 30/jul/2026. O status de homologação segue
 * visível onde o léxico o coloca: nas tags de proveniência, com `alerta`.
 *
 * ── fronteira visual ────────────────────────────────────────────────────────
 *
 * Nenhuma classe nova, nenhum estilo inline. Tudo sai do guia:
 *   §11  a seção demonstra este cabeçalho inteiro na página de área
 *
 * `.stats` (§08) não é mais usada por esta tela — a linha de contexto é `.sub`,
 * a mesma do subtítulo logo acima, com `a` para o link. A classe continua no
 * contrato e pode voltar a servir outra página; DESVIO A REPLICAR NO DESIGN
 * (2026-08-19): a página de área não desenha mais a faixa de estatísticas.
 *
 * O guia escreve o título como `<h2 style="font-size:19px">`. O inline NÃO é
 * copiado: o contrato define `h2` em 20px, e um estilo solto no código seria
 * exatamente o segundo contrato visual que a Regra 2 impede. Diferença de 1px,
 * e a fonte da verdade continua sendo uma só.
 *
 * O respiro entre os três não é declarado aqui: `.content-inner` é uma coluna
 * flex com `gap:16px`, e eles entram como irmãos diretos dela.
 */
'use strict';

import { el } from '../lib/dom.js';


/** Título da área e a linha que situa a leitura: quantos, por quanto, quando. */
function identidade(area) {
  const bloco = el('div', 'stack g6');
  bloco.appendChild(el('h2', null, area.titulo));
  if (area.subtitulo) bloco.appendChild(el('span', 'sub', area.subtitulo));
  return bloco;
}

/**
 * O contexto fixo da área, em UMA linha de texto sob o título:
 *
 *   64 na área · 63 comparáveis (ver os 6 fora da referência) ·
 *   8 acima do critério · 96.048 solicitações excedentes · R$ 3,1 mi …
 *
 * Era a faixa `.stats` de três números-herói (guia §08) até 2026-08-19. Perdeu
 * o tamanho, não o conteúdo: os três são ENQUADRAMENTO — o leitor precisa deles
 * uma vez, no início, para saber contra o que lê o resto da página — e a 22px
 * ocupavam a dobra inteira competindo com o gráfico e a tabela, que são onde o
 * trabalho acontece.
 *
 * A AÇÃO ("ver os 6 fora da referência") entra entre parênteses, colada ao
 * número de que é complemento, e não como botão: não é uma coisa a decidir, é
 * quem não entrou na formação da referência. A barra de composição, que dava
 * essa leitura, saiu da tela; a lista continua a um clique.
 *
 * Nada é montado aqui: texto, ordem, separador e o rótulo do link vêm prontos
 * do motor. O hover de cada parte carrega a definição que a faixa mostrava na
 * linha de apoio — migrou para o `title` em vez de sumir.
 */
function contexto(dados, aoAbrirExcluidos) {
  const linha = el('span', 'sub');
  const sep = dados.separador ?? ' · ';
  (dados.partes ?? []).forEach((parte, i) => {
    if (i) linha.append(document.createTextNode(sep));
    const p = el('span', null, parte.texto);
    // a definição formal do número, à mão de quem passa o cursor
    if (parte.titulo_longo) p.title = parte.titulo_longo;
    linha.appendChild(p);
    if (!parte.acao) return;
    linha.append(document.createTextNode(' ('));
    const link = document.createElement('a');
    link.href = '#';
    link.textContent = parte.acao.rotulo;
    link.addEventListener('click', (ev) => {
      ev.preventDefault();
      aoAbrirExcluidos?.(parte.acao.chave);
    });
    linha.appendChild(link);
    linha.append(document.createTextNode(')'));
  });
  return linha;
}

/**
 * Monta o cabeçalho da página dentro de `destino` (o `.content-inner`).
 *
 * Chamar ANTES de qualquer bloco: a ordem no DOM é a ordem na tela.
 *
 * @param {HTMLElement} destino
 * @param {object} dados  resposta de /api/area/{id}
 * @param {(chave: string) => void} [aoAbrirExcluidos]  ação da estatística
 */
export function montarCabecalho(destino, dados, aoAbrirExcluidos) {
  const bloco = identidade(dados.area);
  /* DENTRO do bloco de identidade, e não como irmão dele: título, subtítulo e
     contexto são a mesma unidade de leitura, e o `gap:16px` da coluna da página
     separaria a linha do título como se fosse outro bloco. */
  if (dados.contexto?.partes?.length) {
    bloco.appendChild(contexto(dados.contexto, aoAbrirExcluidos));
  }
  destino.appendChild(bloco);
}
