/* shell.js — o chassi compartilhado. Uma página não desenha o chassi: ela pede.
 *
 *     import { abrirPagina } from './lib/pagina.js';   // que chama montarShell
 *     // daqui pra frente a página só escreve dentro de `conteudo`
 *
 * ── fronteira de propriedade ────────────────────────────────────────────────
 *
 * TUDO na barra lateral: navegação, contexto (especialidade/área) e a régua da
 * análise. A shell monta os três; a página recebe apenas o slot de conteúdo.
 *
 * Este arquivo só ORQUESTRA. As três peças moram em módulos próprios, porque
 * mudam por motivos diferentes:
 *
 *   shell/seletores.js   os comboboxes de especialidade e área
 *   shell/criterios.js   a faixa da régua e o diálogo que a altera
 *   shell/barra.js       a migalha do rastro e a vigência dos dados
 *
 * ── fronteira de decisão visual (CLAUDE.md) ─────────────────────────────────
 *
 * Nenhuma decisão visual aqui. Abrir e fechar seletor e diálogo é CSS puro
 * (checkbox + .scrim). O único estado que o JS toca é `.on`, que é o desvio
 * autorizado do combobox. Nenhum número é calculado: tudo vem de /api/meta.
 */
'use strict';

import { buscar, buscarTexto } from '../lib/api.js';
import { montarSeletor, fecharPopover, escolher } from './seletores.js';
import { montarFaixaCriterios, montarDialogoCriterios, fecharDialogo, lembrarAbridor }
  from './criterios.js';
import { montarBarraSuperior, montarNavegacao } from './barra.js';
import { montarPeriodo } from './periodo.js';
import { montarConta, fecharMenuConta } from './conta.js';
import { rotaAtual } from '../lib/rotas.js';

/* ── fechar por teclado ─────────────────────────────────────────────────────
 * Abrir é CSS puro (checkbox). Fechar por Esc não é: CSS não escuta tecla. O
 * JS aqui não decide nada visual — desmarca a mesma caixa que o CSS já lê, e
 * devolve o foco a quem abriu. */
function ligarTeclado() {
  const cal = document.getElementById('crit-sh');
  cal.addEventListener('change', () => {
    if (cal.checked) lembrarAbridor(document.querySelector('.critact .btn'));
  });
  document.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Escape') return;
    // o mais interno primeiro: popover aberto ganha do diálogo
    for (const campo of ['esp', 'area']) {
      if (fecharPopover(campo)) { ev.preventDefault(); return; }
    }
    if (fecharMenuConta()) { ev.preventDefault(); return; }
    if (cal.checked) { ev.preventDefault(); fecharDialogo(); }
  });
}

/* CADA CONTROLE APARECE ONDE GOVERNA ALGUMA COISA (27/ago).
 *
 * A barra é o CARIMBO DE PROVENIÊNCIA da tela: ela declara sob que regra os
 * números foram calculados. Controle que não governa nada nesta tela não é
 * inofensivo — ele promete um papel que não cumpre, e o leitor passa a
 * desconfiar da barra inteira, inclusive dos controles que funcionam.
 *
 * Três famílias:
 *
 *   ESCOPO     Especialidade, Área — aparecem quando a escolha é do usuário;
 *              somem quando a COISA EM CENA já as determina.
 *   JANELA     Período — sempre: toda tela olha um intervalo.
 *   CRITÉRIOS  critério, referência, piso, n mínimo, confiança — aparecem onde
 *              há número COMPARADO.
 *
 *   Panorama    escopo · janela · critérios
 *   Área        escopo · janela · critérios
 *   Dossiê              janela · critérios     (a área é ATRIBUTO do cooperado)
 *   Cooperados  escopo · janela                (nenhum número comparado; e ali
 *                                              o escopo FILTRA a lista em vez
 *                                              de navegar, abrindo em "Todas")
 *   Conta       (nenhum)                      não é tela de análise: não há
 *                                              número, logo não há régua. A
 *                                              lateral fica só com navegação e
 *                                              o bloco de conta.
 *
 * No dossiê, escopo não era só inútil: o seletor de área PISCAVA mostrando a
 * área errada até a resposta chegar (o id do cooperado não a carrega), e usá-lo
 * expulsava da tela, porque `aoTrocarArea` navega para /area/{id}. Os dois
 * defeitos são o sintoma de um atributo de entidade vestido de filtro. A área
 * continua visível como FATO, na migalha e no "Comparado com:" do dossiê.
 *
 * Remove do DOM em vez de esconder: o que não existe não é lido por leitor de
 * tela, não recebe foco por Tab e não ocupa espaço. Decidir o que EXISTE é do
 * JS; o CSS continua dono de como as coisas se parecem. */
function ajustarControlesDaTela() {
  const { tela } = rotaAtual();
  const fora = [];
  /* A CONTA não é tela de análise: sai a FAIXA INTEIRA, não controle a
     controle. A faixa é o carimbo de proveniência dos números da tela, e numa
     tela sem número nenhum ela declararia a régua de um cálculo que não
     aconteceu. `.topbar` já fecha com a sua própria linha, então o cabeçalho
     volta a ser de uma altura só, sem remendo. */
  if (tela === 'conta') {
    document.querySelector('.critbar')?.remove();
    return;
  }
  if (tela === 'cooperado') fora.push('esp', 'area');
  for (const campo of fora) {
    document.querySelector(`[data-trig="${campo}"]`)?.closest('.fil')?.remove();
  }
  if (tela === 'cooperados') document.querySelector('[data-critact]')?.remove();
}


export async function montarShell({ aoTrocarArea, escopo } = {}) {
  // a régua viaja na URL: /api/meta recebe a MESMA query da página (é o que
  // `buscar` garante), senão a faixa de critérios recarregaria mostrando o
  // padrão em vez da escolha do analista
  const [marcacao, meta] = await Promise.all([
    buscarTexto('/static/shell/shell.html'),
    buscar('/api/meta'),
  ]);

  document.body.insertAdjacentHTML('afterbegin', marcacao);

  // Uma especialidade só, hoje — mas o controle se comporta igual ao de área:
  // abre, mostra a opção, marca com ✓. O número de opções não muda o
  // comportamento do componente, então `especialidade_unica` não trava nada.
  /* Telas que FILTRAM (e não navegam) abrem em "Todas" e recebem a escolha por
     callback. Ver `escopo` em lib/pagina.js. */
  const TODAS = 'todas';
  const filtra = Boolean(escopo?.todas);

  montarSeletor('esp',
    [...(filtra ? [{ id: TODAS, nome: 'Todas as especialidades' }] : []),
     ...meta.especialidades.map((e) => ({ id: e.id, nome: e.nome }))],
    filtra ? TODAS
           : (meta.especialidades.find((e) => e.ativa) ?? meta.especialidades[0]).id,
    filtra ? (id) => escopo.aoFiltrar('esp', id === TODAS ? null : id) : undefined);

  /* A área ativa vem do CAMINHO (`/area/{id}`), não mais da query: a área é
     uma coisa que se olha, não um modificador de leitura. Caminho sem área
     (Panorama, Nota, e o Dossiê antes de a página resolver o cooperado) cai na
     primeira da lista, para o seletor nunca aparecer sem seleção. */
  const pedida = rotaAtual().area;
  const area = meta.areas.some((a) => a.id === pedida) ? pedida : meta.areas[0].id;

  montarSeletor('area',
    [...(filtra ? [{ id: TODAS, nome: 'Todas as áreas' }] : []),
     ...meta.areas.map((a) => ({ id: a.id, nome: a.titulo, perfil: a.perfil }))],
    filtra ? TODAS : area,
    filtra ? (id) => escopo.aoFiltrar('area', id === TODAS ? null : id)
           : aoTrocarArea);

  /* Período: a janela DEFINE O UNIVERSO do cálculo (METODOLOGIA §5.1), então
     aplicar recarrega — o motor recalcula a norma inteira. `ini`/`fim`
     substituem o atalho `janela` na URL; os dois nunca convivem. */
  montarPeriodo(meta.periodo, (ini, fim) => {
    const q = new URLSearchParams(location.search);
    q.delete('janela');
    q.set('ini', ini);
    q.set('fim', fim);
    location.search = q.toString();
  });

  montarNavegacao(area);
  montarBarraSuperior(meta, area);
  montarFaixaCriterios(meta);
  montarDialogoCriterios(meta);
  /* DEPOIS de montar, não antes: `montarFaixaCriterios` escreve dentro do
     `[data-critset]`, que vive no `.critact` que esta função remove. Tirar o
     controle primeiro fazia a faixa explodir e a tela inteira não subir. */
  ajustarControlesDaTela();
  ligarTeclado();
  /* Sem `await`: o bloco de conta é contexto do chassi, e a tela não deve
     esperar por ele para desenhar a análise. Ele aparece quando chegar. */
  montarConta();

  /** O Dossiê só descobre a área DEPOIS de buscar o cooperado (o id não a
   *  carrega). Até lá o chassi mostra a primeira; esta função corrige a
   *  seleção, a migalha e os links da navegação quando a resposta chega. */
  function definirArea(id) {
    if (!id || id === area || !meta.areas.some((a) => a.id === id)) return;
    escolher('area', id);
    montarNavegacao(id);
    montarBarraSuperior(meta, id);
  }

  return {
    conteudo: document.querySelector('[data-slot="conteudo"]'),
    meta, area, definirArea,
  };
}

/** Falha na montagem é estado declarado, nunca tela branca (guia, seção 07). */
export function mostrarFalha(erro) {
  const banner = document.createElement('div');
  banner.className = 'banner banner-err';
  banner.innerHTML = '<span class="dot"></span>';
  const corpo = document.createElement('div');
  corpo.className = 'stack g4';
  const t = document.createElement('div');
  t.className = 't';
  t.textContent = 'Não foi possível montar a tela';
  const d = document.createElement('div');
  d.className = 'd';
  d.textContent = erro.message;
  corpo.append(t, d);
  banner.appendChild(corpo);
  document.body.appendChild(banner);
}
