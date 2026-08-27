/* tabelas.js — o que as duas tabelas do bloco compartilham.
 *
 * "Cooperados" e "Procedimentos" são a mesma tabela ordenável com colunas
 * diferentes: mesmo cabeçalho clicável, mesma seta reservada, mesma regra de
 * ausência no fim, mesmo ciclo de três estados. Só a unidade de análise muda.
 *
 * Este módulo não sabe de nenhuma das duas. Recebe a descrição das colunas e
 * devolve marcação: quem define o que é uma coluna é cada aba.
 */
'use strict';

/* `el` vem de lib/dom.js e é REEXPORTADO: quem monta tabela quase sempre
   precisa das duas coisas, e um import só mantém as chamadas curtas. */
import { el } from './dom.js';

export { el };

/* Ordenar não é calcular: reordena o que o motor já entregou, sem produzir
 * nenhum número novo. Fica no front para não custar uma ida ao servidor a cada
 * clique — mas viaja na URL, porque a ordem faz parte do que se está vendo e um
 * link de evidência tem de reabrir a mesma tela.
 *
 * Três estados por coluna: decrescente, crescente, e de volta ao padrão. Sem o
 * terceiro, não há caminho de volta à ordem que a API entregou senão
 * recarregando. */
/**
 * A MOLDURA PADRÃO de tabela do app: cartão, cabeçalho, área rolante e rodapé,
 * com os mesmos modificadores em toda tela.
 *
 * Existe porque as três tabelas (Área, Cooperados, Dossiê) montavam a mesma
 * estrutura à mão e divergiram nos modificadores: a do Dossiê estava sem
 * `tbl-fixa` e a de Cooperados sem `tbl-sticky`, `tbl-fill` e rodapé. Nenhuma
 * era um desenho diferente de propósito; eram cópias que envelheceram
 * separadas. Uma função só, e a próxima tabela nasce igual às outras.
 *
 * O que cada modificador faz (todos já no contrato):
 *   tbl-sticky  cabeçalho preso no topo ao rolar
 *   tbl-fill    altura máxima pela janela, com rolagem interna
 *   tbl-fixa    `table-layout:fixed`, para a coluna não pular a cada repintura
 *
 * Devolve as PEÇAS: cada tela preenche o cabeçalho e o rodapé com o que é dela.
 * Este módulo não sabe o que é área, cooperado ou recorte.
 *
 * @returns {{quadro: HTMLElement, topo: HTMLElement, tabela: HTMLTableElement,
 *            pe: HTMLElement, peEstado: HTMLElement}}
 */
export function moldura() {
  const quadro = el('div', 'tbl tbl-sticky tbl-fill tbl-fixa');
  const topo = el('div', 'tbl-hd');
  const rolagem = el('div', 'tbl-scroll');
  const tabela = document.createElement('table');
  const pe = el('div', 'tbl-ft');
  const peEstado = el('span', null, '');
  rolagem.appendChild(tabela);
  pe.appendChild(peEstado);
  quadro.append(topo, rolagem, pe);
  return { quadro, topo, tabela, pe, peEstado };
}


/* CONSISTÊNCIA — a coluna de quadrados por trimestre.
 *
 * Mora aqui, e não no bloco da tabela da Área, porque o Dossiê desenha a MESMA
 * coluna por procedimento (27/ago). Duas cópias divergiriam no primeiro ajuste,
 * e é uma célula com regra de leitura própria: preenchido = passou o critério,
 * tracejado = trimestre sem medida, e o denominador por extenso ao lado porque
 * ele MUDA com o período escolhido.
 */
/* Consistência como MINI-SÉRIE, não como fração.
 *
 * "3/4" não distingue 1º-2º-3º de 1º-2º-4º: um padrão que persiste e um que
 * intermite dão a mesma fração e pedem conversas diferentes. A série mostra
 * QUAIS trimestres, na ordem, e a seta diz para onde o índice foi.
 *
 * Três estados de barra, os mesmos do `.spark` do contrato:
 *   `.crit`   sinalizado naquele trimestre
 *   (neutra)  avaliável e não sinalizado
 *   esmaecida não avaliável — não é "limpo", é "não dava para olhar", e
 *             colapsar os dois pintaria de limpo um trimestre sem medição
 *
 * A ALTURA é dado: vem de `altura_rel`, o índice daquele trimestre relativo ao
 * maior do próprio cooperado. Relativo a ele mesmo de propósito — a série lê a
 * trajetória dele, não o tamanho dele contra os outros, que é o gráfico. */
export function celulaConsistencia(c) {
  const td = el('td', 'num');
  const serie = c.trimestres;
  if (!serie?.length) {
    // sem série, o texto ocupa a célula — e à ESQUERDA, como o cabeçalho e como
    // a versão com barras. `rt` aqui deixava as duas formas da mesma coluna
    // alinhadas em lados opostos, dependendo da linha.
    td.textContent = (c.janelas_avaliaveis
      ? `${c.janelas_sinalizado} de ${c.janelas_avaliaveis} trimestres`
      : c.rotulo);
    if (c.motivo) td.title = c.motivo;
    return td;
  }

  /* QUADRADOS IGUAIS, um por trimestre — não barras de altura variável.
     A versão anterior codificava DUAS coisas num sparkline de 26px: a altura
     era o índice do trimestre e a cor dizia se ele passou o critério. Duas
     variáveis nesse tamanho não se leem, e o índice já tem coluna própria ao
     lado. Sobrou a única pergunta da coluna: passou ou não passou, e em quais.

     Sem vermelho: bloco vermelho na linha lia como alarme, e a cor crítica
     agora é a do dinheiro no gráfico. Preenchido em tinta neutra escura contra
     vazio em cinza claro basta — é a mesma gramática de um indicador de etapas.
     Trimestre não avaliável fica tracejado: é ausência de medida, não "não
     passou". */
  const caixa = el('div', 'sparkwrap');
  const barras = el('div', 'spark');
  for (const t of serie) {
    const i = document.createElement('i');
    if (t.estado === 'sinalizado') i.className = 'on';
    else if (t.estado === 'nao_avaliavel') i.className = 'na';
    i.title = `${t.janela}º trimestre: ` + (
      t.estado === 'nao_avaliavel' ? t.motivo
        : t.sinalizado ? `acima do critério · índice ${t.indice_fmt}`
        : `dentro do critério · índice ${t.indice_fmt}`);
    barras.appendChild(i);
  }
  caixa.appendChild(barras);

  /* A SETA DE TENDÊNCIA saiu (2026-08-20): ela dizia se o índice do cooperado
     sobe ou desce ao longo dos trimestres — assunto do índice, não desta
     coluna, que conta em quantos trimestres ele passou o critério. Três
     elementos na mesma célula (quadrados, seta e texto) e nenhum deles ganhava
     a atenção. A direção continua no dossiê, onde a série tem espaço. */
  /* "3 de 4 trimestres" por extenso ao lado das barras. O rótulo do motor é
     "3/4", e uma fração solta não diz de que é o denominador — que MUDA com o
     período escolhido: uma janela de 6 meses dá 2 trimestres, uma de 24 dá 8.
     Sem o denominador escrito, "3/4" e "3/8" se leem como a mesma coisa. */
  if (c.janelas_avaliaveis) {
    caixa.appendChild(el('span', 'cell-sub',
      `${c.janelas_sinalizado} de ${c.janelas_avaliaveis} trimestres`));
  }
  td.appendChild(caixa);
  td.title = [c.direcao?.texto ?? c.rotulo, c.direcao?.detalhe]
    .filter(Boolean).join(' · ');
  return td;
}


/** Comparação de busca: sem acento e sem caixa. "Reprodução" acha por
 *  "reproducao", que é como se digita com pressa. */
export function casa(texto, termo) {
  if (!termo) return true;
  const limpa = (s) => (s ?? '').normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').toLowerCase();
  return limpa(texto).includes(limpa(termo));
}

/**
 * O CAMPO DE BUSCA de uma tabela, no cabeçalho do cartão.
 *
 * Uma função e não quatro cópias: as quatro tabelas do app (cooperados da área,
 * procedimentos da área, índice de cooperados e procedimentos do dossiê) pedem
 * o mesmo campo, e cópias divergem no primeiro ajuste.
 *
 * BUSCA É LOCALIZAÇÃO, NÃO RECORTE. Ela esconde linhas que já estão na conta;
 * não muda KPI, Pareto nem excedente somado. Quem muda quem entra na conta é o
 * recorte (CLAUDE.md, lei 0), e é por isso que as duas coisas convivem sem se
 * confundir: a busca compõe com o recorte em cena, e varre o que ele deixou.
 *
 * `.search` é o componente do contrato; o `<input>` dentro dele é o desvio
 * autorizado (ver CLAUDE.md). Limpar é o × nativo do `type="search"`.
 *
 * @param {{placeholder: string, valor?: string, aoDigitar: (termo: string) => void}} opcoes
 * @returns {HTMLElement} o `.search` pronto para entrar no `.tbl-hd`
 */
export function campoDeBusca({ placeholder, valor = '', aoDigitar }) {
  const caixa = el('div', 'search');
  const lupa = el('span');
  lupa.setAttribute('aria-hidden', 'true');
  lupa.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" '
    + 'stroke="currentColor" stroke-width="2" stroke-linecap="round">'
    + '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>';
  const campo = document.createElement('input');
  campo.type = 'search';
  campo.autocomplete = 'off';
  campo.spellcheck = false;
  campo.placeholder = placeholder;
  campo.value = valor;
  campo.setAttribute('aria-label', placeholder);
  campo.addEventListener('input', () => aoDigitar(campo.value.trim()));
  caixa.append(lupa, campo);
  return caixa;
}


export function ordenar(linhas, coluna, direcao) {
  if (!coluna || !direcao) return linhas;
  const sinal = direcao === 'asc' ? 1 : -1;
  return [...linhas].sort((a, b) => {
    const va = coluna.valor(a);
    const vb = coluna.valor(b);
    // quem não tem o valor vai para o fim nas DUAS direções: ausência de medida
    // não é o menor valor, é ausência (ajuste 1)
    const na = va == null || Number.isNaN(va);
    const nb = vb == null || Number.isNaN(vb);
    if (na || nb) return na && nb ? 0 : (na ? 1 : -1);
    return (va - vb) * sinal;
  });
}

/**
 * Cabeçalho clicável.
 *
 * A definição da coluna vai no `title`, não como subtítulo dentro do `<th>`:
 * como texto ela alargava a coluna além do dado que descreve e forçava rolagem
 * horizontal.
 */
export function cabecalho(colunas, ordemAtiva, direcao, aoOrdenar) {
  const thead = document.createElement('thead');
  const tr = document.createElement('tr');
  for (const c of colunas) {
    const classes = [c.direita ? 'rt' : null, c.classe ?? null, c.ordem ? 'ord' : null,
                     c.ordem && c.ordem === ordemAtiva ? 'on' : null].filter(Boolean);
    const th = el('th', classes.join(' ') || null, c.nome);
    if (c.def) th.title = c.def;

    if (c.ordem) {
      th.tabIndex = 0;
      // aria-sort é o que um leitor de tela anuncia; a seta é só para quem vê
      th.setAttribute('aria-sort', c.ordem === ordemAtiva
        ? (direcao === 'asc' ? 'ascending' : 'descending') : 'none');
      /* A seta é sempre criada, mesmo inativa: o CSS a esconde, e assim a
         largura do cabeçalho não muda quando a ordenação troca de coluna. */
      th.appendChild(el('span', 'dir',
        c.ordem === ordemAtiva && direcao === 'asc' ? '▲' : '▼'));
      const acionar = () => aoOrdenar(c.ordem);
      th.addEventListener('click', acionar);
      th.addEventListener('keydown', (ev) => {
        if (ev.key !== 'Enter' && ev.key !== ' ') return;
        ev.preventDefault();
        acionar();
      });
    }
    tr.appendChild(th);
  }
  thead.appendChild(tr);
  return thead;
}

/**
 * Lê a ordenação da URL, validada contra as colunas de QUEM está em cena.
 *
 * As duas abas compartilham `ord`/`dir` de propósito: a ordenação pertence à
 * tabela visível, e uma chave que só existe na outra aba cai no padrão em vez de
 * deixar a vista num estado que o cabeçalho não consegue mostrar.
 */
export function ordemDaURL(colunas) {
  const q = new URLSearchParams(location.search);
  const chave = q.get('ord');
  if (!colunas.some((c) => c.ordem === chave)) return { chave: null, direcao: null };
  return { chave, direcao: q.get('dir') === 'asc' ? 'asc' : 'desc' };
}

/** Grava a ordenação na URL sem recarregar: o motor não precisa ser consultado
 *  para reordenar o que ele já entregou. */
export function gravarOrdem(chave, direcao) {
  const q = new URLSearchParams(location.search);
  if (chave) { q.set('ord', chave); q.set('dir', direcao); }
  else { q.delete('ord'); q.delete('dir'); }
  const busca = q.toString();
  history.replaceState(null, '', busca ? `?${busca}` : location.pathname);
}

/** O ciclo de três estados, comum às duas abas. */
export function proximaOrdem(atual, direcao, chave) {
  if (atual !== chave) return { chave, direcao: 'desc' };
  if (direcao === 'desc') return { chave, direcao: 'asc' };
  return { chave: null, direcao: null };
}
