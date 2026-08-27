/* recorte.js — o seletor de RECORTE da tela de Área.
 *
 * UM eixo, aninhado: cada opção é subconjunto da anterior. Escolha ÚNICA — o
 * leitor decide quão restrito quer olhar, sempre na mesma direção.
 *
 * ── por que virou popover (2026-08-19) ──────────────────────────────────────
 *
 * Era um segmentado com quatro pastilhas: Todos · Comparáveis · Persistentes ·
 * Qualificados. Duas coisas erradas nisso.
 *
 * A primeira: Persistentes e Qualificados são o 3º e o 7º degrau de uma cascata
 * de sete, e os quatro degraus entre eles não apareciam. A lista caía de 39
 * para 21 e nada dizia que 15 saíram por imaterialidade, 1 por classificação
 * contestada e 2 por fator de contexto — que é a queda que mais importa.
 *
 * A segunda: um trilho horizontal de pastilhas iguais LÊ COMO categorias
 * paralelas. Uma lista vertical com contagens decrescentes lê como funil, que é
 * o que a cascata é. O controle passou a dizer a forma do dado.
 *
 * Os dois primeiros itens não são degraus: são POPULAÇÃO (quem existe na área,
 * quem tem volume). Ficam num grupo à parte, e é isso que impede a leitura de
 * que "Comparáveis 63" e o degrau de 63 são a mesma coisa.
 *
 * `filtro` lê campos que o motor já entregou; nada aqui calcula. As contagens
 * vêm de `cooperados.filtros`, montadas pelo motor a partir do funil.
 */
'use strict';

import { el } from '../lib/dom.js';

const ID_CAIXA = 'rc-sh';

/* Espelho de `_RECORTES` em app/utils/blocos.py: mesma chave de URL, mesmo
   predicado. `degrau` é o nome do passo no motor, de onde sai a contagem; ele
   nunca vai para a URL, que fala a língua da tela. */
export const RECORTES = [
  { chave: 'todos', rotulo: 'Todos', grupo: 'população',
    ajuda: 'Todos os cooperados da área com atividade registrada no período.' },
  { chave: 'comparaveis', rotulo: 'Comparáveis', grupo: 'população',
    filtro: (l) => l.avaliavel,
    ajuda: 'Volume suficiente para a taxa ser estável. Não é um degrau da '
         + 'cascata: é o conjunto que sustenta comparação.' },

  { chave: 'acima-do-criterio', rotulo: 'Com procedimento acima do critério',
    grupo: 'cascata', degrau: 'acima_do_criterio',
    filtro: (l) => l.grupos.includes('acima_do_criterio') },
  { chave: 'persistente', rotulo: 'Com variação persistente',
    grupo: 'cascata', degrau: 'persistente',
    filtro: (l) => l.grupos.includes('persistente') },
  { chave: 'material', rotulo: 'Material',
    grupo: 'cascata', degrau: 'material',
    filtro: (l) => l.grupos.includes('material') },
  { chave: 'sem-fator-de-contexto', rotulo: 'Sem fator de contexto que explique',
    grupo: 'cascata', degrau: 'sem_fator_de_contexto',
    filtro: (l) => l.grupos.includes('sem_fator_de_contexto') },
  { chave: 'qualificados', rotulo: 'Qualificados',
    grupo: 'cascata', degrau: 'confianca_calculavel',
    filtro: (l) => l.grupos.includes('confianca_calculavel'),
},
];

/** O recorte pedido, validado: desconhecido cai no padrão em vez de esvaziar. */
export function recortePorChave(chave) {
  return RECORTES.find((r) => r.chave === chave) ?? RECORTES[0];
}

/**
 * Desenha o seletor de recorte.
 *
 * @param {HTMLElement} destino
 * @param {object} dados      resposta de /api/area/{id}
 * @param {(chave: string) => void} aoEscolher
 * @returns {{marcar: (chave: string) => void}}
 */
export function montarRecorte(destino, dados, aoEscolher) {
  const filtros = dados.cooperados?.filtros ?? [];
  const porDegrau = new Map(filtros.map((f) => [f.chave, f]));
  /* `filtros` chega do estrito para o amplo; invertido, é a ordem do funil.
     A QUEDA de cada opção é medida contra o degrau IMEDIATAMENTE anterior do
     MOTOR, não contra a opção anterior da lista: a classificação em revisão
     saiu da escada, e medir contra a opção visível somaria a queda dela (−1)
     na do contexto, atribuindo a uma causa o que é de duas. */
  const ordemFunil = [...filtros].reverse().map((f) => f.chave);
  const nAntesDe = (degrau) => {
    const i = ordemFunil.indexOf(degrau);
    return i > 0 ? porDegrau.get(ordemFunil[i - 1])?.n : null;
  };
  const rotuloDe = (r) => porDegrau.get(r.degrau)?.rotulo ?? r.rotulo;
  const total = dados.cooperados?.total ?? 0;
  const nDe = (r) => (r.degrau ? porDegrau.get(r.degrau)?.n
                    : r.chave === 'todos' ? total
                    : dados.cooperados.linhas.filter(r.filtro).length);

  const caixa = document.createElement('input');
  caixa.type = 'checkbox';
  caixa.id = ID_CAIXA;
  caixa.className = 'oc';
  const scrim = el('label', 'scrim scrim-rc');
  scrim.setAttribute('for', ID_CAIXA);
  scrim.setAttribute('aria-label', 'Fechar seleção');

  const campo = el('div', 'pf');
  const gatilho = el('label', 'pf-trig');
  gatilho.setAttribute('for', ID_CAIXA);
  gatilho.tabIndex = 0;
  gatilho.appendChild(el('span', null, 'Recorte'));
  /* O recorte ativo vive NO BOTÃO, sempre visível: ele é o filtro principal da
     página, e escondê-lo atrás de um clique tiraria da tela a informação de
     contra o que se está lendo tudo o mais. */
  const etiqueta = el('span', 'pf-tag');
  gatilho.appendChild(etiqueta);
  gatilho.insertAdjacentHTML('beforeend',
    '<svg class="car" width="12" height="12" viewBox="0 0 24 24" fill="none" '
    + 'stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>');

  const pop = el('div', 'pf-pop');
  const opcoes = new Map();
  let grupoAberto = null;

  for (const r of RECORTES) {
    if (r.grupo !== grupoAberto) {
      grupoAberto = r.grupo;
      pop.appendChild(el('div', 'pf-grp',
        grupoAberto === 'população' ? 'População' : 'Cascata de qualificação'));
    }
    const n = nDe(r);
    const o = el('button', 'pf-opt uni');
    o.type = 'button';
    o.insertAdjacentHTML('beforeend',
      '<span class="bx"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" '
      + 'stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" '
      + 'aria-hidden="true"><path d="M5 12l5 5 9-10"/></svg></span>');
    o.appendChild(el('span', 'nm', rotuloDe(r)));
    /* A QUEDA em cada degrau, ao lado da contagem: é a leitura que o segmentado
       não dava e a razão de o funil estar aqui. Só dentro da cascata — entre
       população e cascata a diferença não é "quem caiu", são unidades
       diferentes. */
    const antes = r.degrau ? nAntesDe(r.degrau) : null;
    if (r.grupo === 'cascata' && antes != null && n != null && antes - n > 0) {
      o.appendChild(el('span', 'dp', `−${antes - n}`));
    }
    if (n != null) o.appendChild(el('span', 'n', String(n)));
    // a definição do degrau vem do motor; a `ajuda` local cobre o que não é degrau
    o.title = [porDegrau.get(r.degrau)?.descricao, r.ajuda]
      .filter(Boolean).join(' · ');
    // escolha ÚNICA: fecha ao escolher, ao contrário do perfil
    o.addEventListener('click', () => { caixa.checked = false; aoEscolher(r.chave); });
    pop.appendChild(o);
    opcoes.set(r.chave, o);
  }

  /* A CLASSIFICAÇÃO EM REVISÃO não é opção do seletor: não é degrau de método,
     é pendência de cadastro. Some da escada e vira exclusão DECLARADA aqui, com
     a contagem — esconder a queda dentro do degrau seguinte era o defeito que
     este seletor veio corrigir. */
  const clf = porDegrau.get('classificacao_firme');
  const antesClf = porDegrau.get('material')?.n;
  if (clf && antesClf != null && antesClf - clf.n > 0) {
    const ft = el('div', 'pf-ft');
    const nota = el('span', 'pf-nota',
      `${antesClf - clf.n} fora por classificação de área em revisão`);
    nota.title = clf.descricao ?? '';
    ft.appendChild(nota);
    pop.appendChild(ft);
  }

  campo.append(caixa, scrim, gatilho, pop);
  /* Sem rótulo "Recorte" FORA do botão: ele já está dentro, como no Perfil ao
     lado. O segmentado precisava do rótulo externo porque as pastilhas não
     tinham onde carregá-lo. */
  destino.appendChild(campo);

  return {
    marcar: (chave) => {
      const r = recortePorChave(chave);
      const n = nDe(r);
      const rot = rotuloDe(r);
      etiqueta.textContent = n == null ? rot : `${rot} · ${n}`;
      campo.classList.add('tem-perfil');   // o botão sempre carrega o ativo
      for (const [k, o] of opcoes) o.classList.toggle('on', k === r.chave);
    },
  };
}
