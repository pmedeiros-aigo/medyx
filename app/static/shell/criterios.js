/* shell/criterios.js — a régua da análise: a faixa que a declara e o diálogo
 * que a altera.
 *
 * A faixa é LEITURA, nunca campo: diz sob que regra TODO número da tela foi
 * calculado. Alterar é ato deliberado, feito no diálogo, e NADA recalcula
 * enquanto ele está aberto — o diálogo acumula, resume o delta e recalcula uma
 * vez só, em Aplicar. É a diferença entre "li diferente" e "mudei a análise".
 *
 * Nada é redigido aqui: rótulos, opções, unidades e limites vêm de /api/meta.
 */
'use strict';

/* Quem abriu o diálogo, para devolver o foco no fechamento: sem isso o foco
   cai no <body> e quem navega por teclado recomeça do topo da página. */
let abridorDoDialogo = null;
let fecharDialogoInterno = null;

/** Fecha o diálogo pela via do teclado (Esc). Devolve false se não havia nada
 *  aberto, para o chamador tentar o próximo alvo. */
export function fecharDialogo() {
  if (!fecharDialogoInterno) return false;
  fecharDialogoInterno();
  return true;
}

/** Registra quem abriu, no momento em que abre. */
export function lembrarAbridor(el) {
  abridorDoDialogo = el;
}

/* ── faixa de critérios da análise ──────────────────────────────────────────
 *
 * Arranjo A de "Criterios da Analise.html", adotado em 30/jul/2026. Substitui o
 * bloco "Análise" da barra lateral e o diálogo separado de requisitos mínimos.
 *
 * A faixa é LEITURA, nunca campo: declara sob que regra todo número da tela foi
 * calculado. Alterar é ato deliberado, feito no diálogo, e NADA recalcula
 * enquanto ele está aberto — o diálogo acumula, resume o delta e recalcula uma
 * vez só, em Aplicar. É a diferença entre "li diferente" e "mudei a análise".
 *
 * Isso é uma mudança de comportamento em relação ao arranjo anterior, onde cada
 * clique num segmento da lateral recarregava a página. Era o convite ao ajuste
 * distraído que o documento existe para fechar.
 *
 * Nada é redigido aqui. Rótulos curtos e valores da faixa vêm em
 * `meta.faixa_criterios`; rótulos longos, ajuda, opções, unidades e limites vêm
 * em `meta.controles`. A tela imprime.
 */

/* Os dois grupos do diálogo, na ordem, e o que cada um contém. Régua e piso de
 * elegibilidade mudam JUNTOS, num só ato de aplicação, porque são lidos juntos:
 * "quem está fora" depende tanto da distância exigida quanto de quem entrou na
 * comparação. */
/* A JANELA saiu daqui (14/ago). Ela ganhou controle próprio na faixa (o
   seletor de Período) quando passou a aceitar intervalo livre, e ficar nos
   dois lugares dava duas maneiras de mudar a mesma coisa — com o diálogo ainda
   oferecendo só 3/6/12 meses, ou seja, capaz de DESFAZER um intervalo escolhido
   ao lado sem que ninguém pedisse. A janela define o universo do cálculo
   (METODOLOGIA §5.1); os critérios definem a régua aplicada sobre ele. São
   perguntas diferentes, e agora cada uma tem um controle. */
const GRUPOS = [
  { titulo: 'Régua de comparação', campos: ['criterio', 'referencia', 'confianca'] },
  { titulo: 'Requisitos mínimos', campos: ['piso', 'n_minimo'] },
];

/** Controles numéricos (stepper digitável); o resto é segmentado. */
const NUMERICOS = new Set(['piso', 'n_minimo']);

/** Todos os campos, achatados na ordem em que aparecem no diálogo. */
const CAMPOS = GRUPOS.flatMap((g) => g.campos);

/** Ordem dos níveis: a referência nunca pode passar do critério. */
const NIVEL = { mediana: 0, p75: 1, p90: 2 };

function elem(tag, classe, texto) {
  const e = document.createElement(tag);
  if (classe) e.className = classe;
  if (texto != null) e.textContent = texto;
  return e;
}

/* ── a faixa ─────────────────────────────────────────────────────────────── */

/** Desenha os seis pares rótulo/valor e o estado da ação. */
export function montarFaixaCriterios(meta) {
  /* CLEAN V3: a régua virou RESUMO dentro do botão, não seis chips na faixa.
     Só os valores entram ("P90 · mediana") — os rótulos estão no diálogo, ao
     lado de cada controle, que é onde eles são necessários.

     A JANELA não entra: ela tem controle próprio a dois centímetros dali (o
     seletor de Período), e repetir o intervalo aqui era dizer duas vezes o que
     já estava dito. Critério é critério. */
  const set = document.querySelector('[data-critset]');
  const criterios = meta.faixa_criterios ?? [];
  const RESUMO = ['criterio', 'referencia'];
  const resumo = criterios.filter((c) => RESUMO.includes(c.chave));
  set.textContent = (resumo.length ? resumo : criterios)
    .map((c) => c.valor_fmt).join(' · ');
  set.title = criterios.map((c) => `${c.rotulo}: ${c.valor_fmt}`).join(' · ');
  const fora = criterios.filter((c) => c.fora_do_padrao).length;

  /* A contagem "N fora do padrão" e a ação "Restaurar padrão" saíram da faixa
     (14/ago). O desvio continua sendo detectado e viaja no payload
     (`meta.desvios_do_recomendado`) e no `title` do botão; o que saiu foi a
     superfície. Volta quando houver decisão sobre onde ela pertence. */
  document.querySelector('[data-critact]')?.classList.toggle('has-mod', fora > 0);
}

/** Clique e teclado na mesma ação: nada que se aciona com o mouse fica fora do
 *  alcance de quem navega por teclado. */
function aoAcionar(el, acao) {
  el.addEventListener('click', acao);
  el.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Enter' && ev.key !== ' ') return;
    ev.preventDefault();
    acao();
  });
}

/* ── validação dos campos numéricos ──────────────────────────────────────── */

/** Valida contra a restrição RECEBIDA, nunca contra regra local. */
function dentroDoLimite(txt, restr) {
  if (!/^\d+$/.test(txt.trim())) return false;
  const n = Number(txt);
  if (restr.minimo != null && n < restr.minimo) return false;
  if (restr.maximo != null && n > restr.maximo) return false;
  return true;
}

/* Descarta tudo que não é dígito PRESERVANDO A POSIÇÃO DO CURSOR.
 *
 * Reescrever `value` recoloca o cursor no fim — editar o meio de "1250" viraria
 * uma caça ao cursor a cada tecla. A correção é contar quantos caracteres
 * descartados estavam ANTES do cursor e recuar por essa quantidade.
 *
 * Cobre colagem também: colar "1.250" deixa 1250 em vez de rejeitar a colagem.
 * Não usamos `type="number"`: ele altera o valor com o scroll do mouse, e um
 * limiar que decide quem entra na comparação não pode mudar sem intenção. */
function filtrarDigitos(el) {
  const bruto = el.value;
  const limpo = bruto.replace(/\D/g, '');
  if (limpo === bruto) return;
  const cursor = el.selectionStart ?? bruto.length;
  const descartadosAntes = (bruto.slice(0, cursor).match(/\D/g) || []).length;
  el.value = limpo;
  const novo = Math.max(0, cursor - descartadosAntes);
  el.setSelectionRange(novo, novo);
}

/* ── as linhas do diálogo ────────────────────────────────────────────────── */

/** Rótulo, unidade e explicação: a coluna da esquerda de toda linha. */
function rotuloDaLinha(ctl) {
  const lb = elem('div', 'dlg-lb');
  lb.appendChild(elem('span', 'dlg-n', ctl.rotulo));
  if (ctl.unidade) lb.appendChild(elem('span', 'dlg-u', ctl.unidade));
  if (ctl.ajuda) lb.appendChild(elem('span', 'dlg-h', ctl.ajuda));
  return lb;
}

/* Segmentado por RADIO, não por classe `.on`: o estado vive no input e o CSS o
 * lê com `input:checked + .seg-o`. Assim as seis linhas têm marcação idêntica e
 * o teclado navega o grupo nativamente (setas), sem código. */
function segmentado(campo, ctl, aoMudar) {
  const seg = elem('div', 'seg');
  for (const opt of ctl.opcoes) {
    const id = `crit-${campo}-${String(opt.valor).replace(/[^\w-]/g, '')}`;
    const radio = document.createElement('input');
    radio.type = 'radio';
    radio.name = `crit-${campo}`;
    radio.id = id;
    radio.checked = opt.valor === ctl.ativo;
    radio.addEventListener('change', () => aoMudar(opt.valor));
    const rot = elem('label', 'seg-o', opt.rotulo);
    rot.setAttribute('for', id);
    rot.tabIndex = 0;
    seg.append(radio, rot);
  }
  return seg;
}

/** Stepper digitável: o campo aceita o valor direto, − e + ficam para ajuste
 *  fino. Um limiar de faixa larga não se ajusta a cliques: sair de 100 para 150
 *  seriam 50 toques. */
function numerico(campo, ctl, aoMudar, aoInvalidar) {
  const st = elem('div', 'stepper');
  const entrada = document.createElement('input');
  entrada.className = 'stepnum';
  entrada.type = 'text';
  entrada.inputMode = 'numeric';
  entrada.value = String(ctl.ativo);
  entrada.setAttribute('aria-label', ctl.rotulo);

  const restr = { minimo: ctl.minimo, maximo: ctl.maximo, passo: ctl.passo ?? 1 };
  entrada.addEventListener('input', () => {
    filtrarDigitos(entrada);
    const txt = entrada.value;
    if (dentroDoLimite(txt, restr)) aoMudar(Number(txt), { reescrever: false });
    else aoInvalidar(restr);
  });

  const botoes = elem('span', 'btns');
  for (const dir of [-1, 1]) {
    const b = elem('label', null, dir < 0 ? '−' : '+');
    b.tabIndex = 0;
    b.setAttribute('role', 'button');
    b.setAttribute('aria-label', dir < 0 ? 'Diminuir' : 'Aumentar');
    aoAcionar(b, () => {
      let v = Number(entrada.value || ctl.ativo) + dir * restr.passo;
      if (restr.minimo != null) v = Math.max(restr.minimo, v);
      if (restr.maximo != null) v = Math.min(restr.maximo, v);
      aoMudar(v);
    });
    botoes.appendChild(b);
  }
  st.append(entrada, botoes);
  return { st, entrada };
}

/* ── o diálogo ───────────────────────────────────────────────────────────── */

/**
 * Monta o diálogo de critérios: seis linhas em dois grupos, rascunho acumulado,
 * delta no rodapé e um único recálculo em Aplicar.
 */
export function montarDialogoCriterios(meta) {
  const controles = meta.controles;
  const corpo = document.querySelector('[data-crit-corpo]');
  const modal = document.querySelector('.modal-crit');
  const cx = document.getElementById('crit-sh');
  const resumo = document.querySelector('[data-crit-resumo]');
  const aplicar = document.querySelector('[data-crit-aplicar]');

  const original = Object.fromEntries(CAMPOS.map((c) => [c, controles[c].ativo]));
  const pendente = { ...original };
  const invalido = new Set();
  const steppers = {};
  const entradas = {};
  const opcoes = {};

  function marcarInvalido(campo, restr) {
    invalido.add(campo);
    repintar({ reescrever: false });
    return restr;
  }

  function definir(campo, valor, { reescrever = true } = {}) {
    invalido.delete(campo);
    pendente[campo] = valor;
    repintar({ reescrever });
  }

  for (const grupo of GRUPOS) {
    corpo.appendChild(elem('div', 'dlg-grp', grupo.titulo));
    for (const campo of grupo.campos) {
      const ctl = controles[campo];
      const linha = elem('div', 'dlg-row');
      linha.appendChild(rotuloDaLinha(ctl));
      const ct = elem('div', 'dlg-ct');
      if (NUMERICOS.has(campo)) {
        const { st, entrada } = numerico(
          campo, ctl,
          (v, o) => definir(campo, v, o),
          (restr) => marcarInvalido(campo, restr));
        steppers[campo] = st;
        entradas[campo] = entrada;
        ct.appendChild(st);
      } else {
        const seg = segmentado(campo, ctl, (v) => definir(campo, v));
        opcoes[campo] = seg;
        ct.appendChild(seg);
      }
      linha.appendChild(ct);
      corpo.appendChild(linha);
    }
  }

  /* Combinação impossível não é erro a corrigir depois: a referência acima do
     critério aparece INDISPONÍVEL no momento da escolha, não recusada com 422
     depois de aplicar. Quem conhece a ordem dos percentis continua sendo o
     motor — aqui só se lê a ordem que ele já publicou nas opções. */
  function reavaliarReferencia() {
    const teto = NIVEL[pendente.criterio];
    const seg = opcoes.referencia;
    if (!seg || teto == null) return;
    let ativoCaiu = false;
    for (const rot of seg.querySelectorAll('.seg-o')) {
      const radio = document.getElementById(rot.getAttribute('for'));
      const valor = controles.referencia.opcoes
        .find((o) => `crit-referencia-${String(o.valor).replace(/[^\w-]/g, '')}` === radio.id)?.valor;
      const proibido = NIVEL[valor] != null && NIVEL[valor] > teto;
      rot.classList.toggle('na', proibido);
      radio.disabled = proibido;
      if (proibido && radio.checked) { radio.checked = false; ativoCaiu = true; }
    }
    // referência que deixou de ser possível volta ao recomendado, em vez de
    // ficar sem escolha nenhuma
    if (!ativoCaiu) return;
    pendente.referencia = controles.referencia.recomendado;
    const id = `crit-referencia-${String(pendente.referencia).replace(/[^\w-]/g, '')}`;
    const alvo = document.getElementById(id);
    if (alvo) alvo.checked = true;
  }

  const nome = (campo) => controles[campo].rotulo;
  const mostrar = (campo, v) => {
    const ctl = controles[campo];
    if (NUMERICOS.has(campo)) return String(v);
    return ctl.opcoes.find((o) => o.valor === v)?.rotulo ?? String(v);
  };

  function repintar({ reescrever = true } = {}) {
    reavaliarReferencia();
    for (const campo of CAMPOS) {
      if (!NUMERICOS.has(campo)) continue;
      if (reescrever && !invalido.has(campo)) entradas[campo].value = pendente[campo];
      steppers[campo].classList.toggle('invalid', invalido.has(campo));
    }

    const mudou = CAMPOS.filter((c) => pendente[c] !== original[c]);
    resumo.replaceChildren();
    if (invalido.size > 0) {
      resumo.appendChild(elem('span', 'delta', 'Corrija o valor destacado'));
    } else if (mudou.length === 0) {
      resumo.appendChild(elem('span', 'none', 'Nenhum valor alterado'));
    } else {
      resumo.appendChild(elem('span', 'delta', mudou
        .map((c) => `${nome(c)} ${mostrar(c, original[c])} → ${mostrar(c, pendente[c])}`)
        .join(' · ')));
    }
    // não se aplica uma régua que não se sabe qual é
    aplicar.classList.toggle('btn-disabled', mudou.length === 0 || invalido.size > 0);
  }

  /* UM recálculo. Todos os parâmetros mudados vão para a URL de uma vez, e o
     motor roda uma vez — a régua da tela é uma só, e aplicá-la em partes
     produziria estados intermediários que ninguém pediu. */
  aoAcionar(aplicar, () => {
    if (aplicar.classList.contains('btn-disabled')) return;
    const q = new URLSearchParams(location.search);
    for (const campo of CAMPOS) q.set(campo, String(pendente[campo]));
    location.search = q.toString();
  });

  /* ── saída ────────────────────────────────────────────────────────────────
   * As quatro saídas (Esc, ✕, Cancelar, clique fora) passam por aqui. Se só o
   * Esc perguntasse, as outras três descartariam em silêncio — e um diálogo que
   * só grava em "Aplicar" perde trabalho de verdade ao fechar. */
  function descartar() {
    invalido.clear();
    for (const campo of CAMPOS) {
      pendente[campo] = original[campo];
      if (NUMERICOS.has(campo)) continue;
      const id = `crit-${campo}-${String(original[campo]).replace(/[^\w-]/g, '')}`;
      const alvo = document.getElementById(id);
      if (alvo) alvo.checked = true;
    }
    modal.classList.remove('confirming');
    repintar();
    cx.checked = false;
    abridorDoDialogo?.focus();
  }

  function tentarFechar() {
    const pendencia = invalido.size > 0 || CAMPOS.some((c) => pendente[c] !== original[c]);
    if (!pendencia) { descartar(); return; }
    modal.classList.add('confirming');
    modal.querySelector('[data-crit-descartar]').focus();
  }

  for (const saida of modal.querySelectorAll('[for="crit-sh"]')) {
    saida.addEventListener('click', (ev) => { ev.preventDefault(); tentarFechar(); });
  }
  document.querySelector('.scrim-crit-sh')
    .addEventListener('click', (ev) => { ev.preventDefault(); tentarFechar(); });

  aoAcionar(modal.querySelector('[data-crit-continuar]'), () => {
    modal.classList.remove('confirming');
    entradas[CAMPOS.find((c) => NUMERICOS.has(c))]?.focus();
  });
  aoAcionar(modal.querySelector('[data-crit-descartar]'), descartar);

  fecharDialogoInterno = tentarFechar;
  repintar();
}
