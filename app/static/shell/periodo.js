/* shell/periodo.js — o seletor de PERÍODO da faixa de filtros.
 *
 * A janela não é um filtro de visualização: ela DEFINE O UNIVERSO do cálculo.
 * METODOLOGIA §5.1 — "a norma e o indivíduo são sempre calculados na mesma
 * janela". Trocar o período recalcula tudo, da coorte à referência.
 *
 * ── por que o painel declara consequências ──────────────────────────────────
 *
 * Escolher duas datas tem dois efeitos que ninguém adivinha:
 *
 *   · a janela é fatiada em TRIMESTRES para medir consistência, e o resto que
 *     não fecha um trimestre é descartado do fatiamento (mas continua contando
 *     no agregado);
 *   · abaixo de dois trimestres a consistência não é calculável — e como a
 *     cascata é cumulativa, os recortes "com variação persistente" e
 *     "qualificados" ficam vazios. Metade do produto sai de cena.
 *
 * Por isso o rodapé do painel lê a escolha ANTES de aplicar. Descobrir depois
 * que a fila de trabalho sumiu é descobrir tarde.
 *
 * Os atalhos ("Últimos 12 meses", "Ano atual") foram removidos em 14/ago: as
 * duas grades já são o caminho direto, e uma fila de botões acima delas era
 * uma segunda maneira de fazer a mesma escolha. Menos peça, mesmo alcance.
 *
 * Nada é calculado aqui: meses disponíveis, mínimo e a leitura da janela em
 * cena vêm de /api/meta (`periodo`).
 */
'use strict';

import { el } from '../lib/dom.js';

const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun',
               'jul', 'ago', 'set', 'out', 'nov', 'dez'];

/** 'AAAA-MM' -> {ano, mes} (mes 1..12). */
const partes = (am) => ({ ano: +am.slice(0, 4), mes: +am.slice(5, 7) });
const chave = (ano, mes) => `${ano}-${String(mes).padStart(2, '0')}`;
/* Ano INTEIRO, não abreviado: a base vai crescer para vários anos, e "mai/25"
   obriga o leitor a completar o século de cabeça. Mesma forma do servidor
   (apresentacao.rotulo_intervalo), para o gatilho e o carimbo não divergirem. */
const rotuloMes = (am) => `${MESES[partes(am).mes - 1]}/${partes(am).ano}`;

/** Quantos meses cheios o intervalo cobre (a mesma conta do servidor). */
function meses(ini, fim) {
  const a = partes(ini);
  const b = partes(fim);
  return (b.ano - a.ano) * 12 + (b.mes - a.mes) + 1;
}

/**
 * Monta o seletor de período.
 *
 * @param {object} periodo  bloco `periodo` de /api/meta
 * @param {(ini: string, fim: string) => void} aoAplicar  recebe AAAA-MM
 */
export function montarPeriodo(periodo, aoAplicar) {
  const trig = document.querySelector('[data-per-rotulo]');
  if (!trig || !periodo) return;

  const { primeiro, ultimo } = periodo.disponivel;
  const minMeses = periodo.minimo_meses ?? 3;
  const minTrimestres = periodo.min_trimestres ?? 2;

  /* O gatilho mostra a janela EM CENA (o rótulo vem do servidor quando é
     intervalo livre; nos atalhos, o texto do atalho). */
  const atual = periodo.atual ?? {};
  trig.textContent = atual.ini && atual.fim
    ? `${rotuloMes(atual.ini)} – ${rotuloMes(atual.fim)}`
    : (atual.rotulo ?? '');
  trig.classList.remove('ph');

  // rascunho: só vira análise em Aplicar
  let ini = atual.ini ?? primeiro;
  let fim = atual.fim ?? ultimo;
  let anoIni = partes(ini).ano;
  let anoFim = partes(fim).ano;

  const caixa = document.getElementById('op-p-sh');
  const leitura = document.querySelector('[data-per-leitura]');
  const aplicar = document.querySelector('[data-per-aplicar]');

  /** Uma grade de 12 meses de um ano, para um dos lados. */
  function grade(lado) {
    const alvo = document.querySelector(`[data-per-meses="${lado}"]`);
    const ano = lado === 'ini' ? anoIni : anoFim;
    const escolhido = lado === 'ini' ? ini : fim;
    alvo.replaceChildren();
    for (let m = 1; m <= 12; m += 1) {
      const am = chave(ano, m);
      // fora da base OU do lado errado do outro extremo: não é escolha válida
      const foraDaBase = am < primeiro || am > ultimo;
      const invertido = lado === 'ini' ? am > fim : am < ini;
      const bloqueado = foraDaBase || invertido;
      /* A FAIXA entre as duas pontas é preenchida: o que se escolhe é um
         intervalo, e duas células isoladas não mostram intervalo nenhum. */
      const naFaixa = am > ini && am < fim;
      const b = el('div', `per-mes${bloqueado ? ' na' : ''}`
                        + `${am === escolhido ? ' on' : naFaixa ? ' faixa' : ''}`,
                   MESES[m - 1]);
      b.title = foraDaBase ? 'sem dado neste mês'
        : invertido ? 'invertido: o início tem de vir antes do fim' : am;
      if (!bloqueado) {
        b.tabIndex = 0;
        const acionar = () => {
          if (lado === 'ini') ini = am; else fim = am;
          desenhar();
        };
        b.addEventListener('click', acionar);
        b.addEventListener('keydown', (ev) => {
          if (ev.key !== 'Enter' && ev.key !== ' ') return;
          ev.preventDefault();
          acionar();
        });
      }
      alvo.appendChild(b);
    }
  }

  /** Cabeçalho do ano, com as setas limitadas ao que a base cobre. */
  function cabecalhoAno(lado) {
    const alvo = document.querySelector(`[data-per-ano="${lado}"]`);
    const ano = lado === 'ini' ? anoIni : anoFim;
    const anoMin = partes(primeiro).ano;
    const anoMax = partes(ultimo).ano;
    alvo.replaceChildren();
    const passo = (d) => {
      const b = el('span', `nav${(d < 0 ? ano <= anoMin : ano >= anoMax) ? ' off' : ''}`,
                   d < 0 ? '‹' : '›');
      if (!b.classList.contains('off')) {
        b.tabIndex = 0;
        b.addEventListener('click', () => {
          if (lado === 'ini') anoIni += d; else anoFim += d;
          desenhar();
        });
      }
      return b;
    };
    alvo.append(passo(-1), el('span', 'y', String(ano)), passo(1));
  }

  /* A leitura do que a escolha implica. As contas de trimestre e resto são as
     MESMAS do servidor (`_leitura_da_janela`): parte inteira de meses/3, o
     resto descartado do fatiamento. Repetidas aqui só para o painel responder
     na hora — a verdade continua vindo da API depois de aplicar. */
  function desenhar() {
    grade('ini'); grade('fim');
    cabecalhoAno('ini'); cabecalhoAno('fim');

    const n = meses(ini, fim);
    const trimestres = Math.floor(n / 3);
    const curta = n < minMeses;
    const semConsistencia = trimestres < minTrimestres;

    const partesTexto = [`${rotuloMes(ini)} – ${rotuloMes(fim)}`,
                         `${n} ${n === 1 ? 'mês' : 'meses'}`,
                         `${trimestres} ${trimestres === 1 ? 'trimestre' : 'trimestres'}`];
    if (curta) {
      partesTexto.push(`abaixo do mínimo de ${minMeses} meses: a norma do grupo `
                       + 'não se sustenta nesta janela');
    } else if (semConsistencia) {
      partesTexto.push('sem consistência entre trimestres, e sem os recortes '
                       + 'de variação persistente e qualificados');
    }
    leitura.textContent = partesTexto.join(' · ');
    leitura.classList.toggle('alerta', curta || semConsistencia);
    aplicar.classList.toggle('btn-disabled', curta);
  }

  const acionarAplicar = () => {
    if (aplicar.classList.contains('btn-disabled')) return;
    caixa.checked = false;
    aoAplicar(ini, fim);
  };
  aplicar.addEventListener('click', acionarAplicar);
  aplicar.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Enter' && ev.key !== ' ') return;
    ev.preventDefault();
    acionarAplicar();
  });

  desenhar();
}
