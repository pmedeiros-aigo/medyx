/* tema.js — o tema como estado do DOCUMENTO, não de cada tela.
 *
 * Portado do `theme.js` do Claude Design (set/2026), com a mesma chave de
 * armazenamento e o mesmo atributo, para que as duas superfícies concordem.
 *
 * Regras:
 *   · a preferência é uma só, em localStorage (chave medyx.tema);
 *   · são DOIS estados, 'light' | 'dark'. Sem escolha gravada o padrão vem do
 *     sistema operacional (prefers-color-scheme); a partir do primeiro clique a
 *     escolha do usuário manda, e o sistema para de mandar;
 *   · o tema resolvido é escrito em <html data-tema> ANTES da primeira pintura,
 *     e é por isso que este arquivo é um <script> clássico no <head> do
 *     index.html, e não um módulo: módulo é adiado, e adiado significa um
 *     flash branco antes do escuro entrar;
 *   · nenhuma tela guarda tema. Quem precisa dele lê `atual()` e assina
 *     `aoMudar()`.
 *
 * Não faz parte do chassi montado por shell.js: quando shell.js roda, o tema já
 * está aplicado há muito tempo.
 */
(function () {
  var CHAVE = 'medyx.tema';
  var mq = window.matchMedia('(prefers-color-scheme: dark)');
  var ouvintes = [];

  function ler() {
    try {
      var v = localStorage.getItem(CHAVE);
      if (v === 'light' || v === 'dark') return v;
    } catch (e) { /* modo privado, armazenamento bloqueado: cai no sistema */ }
    return mq.matches ? 'dark' : 'light';
  }
  function gravado() {
    try {
      var v = localStorage.getItem(CHAVE);
      return v === 'light' || v === 'dark';
    } catch (e) { return false; }
  }

  function aplicar() {
    var r = ler();
    document.documentElement.setAttribute('data-tema', r);
    ouvintes.slice().forEach(function (f) { try { f(r); } catch (e) {} });
    return r;
  }

  /* O sistema operacional só manda enquanto o usuário nunca escolheu. */
  var aoTrocarSO = function () { if (!gravado()) aplicar(); };
  if (mq.addEventListener) mq.addEventListener('change', aoTrocarSO);
  else if (mq.addListener) mq.addListener(aoTrocarSO);

  /* Preferência trocada em OUTRA aba: sem isto, "uma preferência só" valeria
     apenas dentro do documento que a mudou. */
  window.addEventListener('storage', function (e) {
    if (e.key === CHAVE || e.key === null) aplicar();
  });

  window.MedyxTema = {
    atual: ler,
    definir: function (p) {
      try { localStorage.setItem(CHAVE, p === 'dark' ? 'dark' : 'light'); }
      catch (e) { /* sem persistência: vale para esta sessão */ }
      return aplicar();
    },
    alternar: function () { return this.definir(ler() === 'dark' ? 'light' : 'dark'); },
    /** assina a troca; devolve a função de cancelamento */
    aoMudar: function (f) {
      ouvintes.push(f);
      return function () {
        ouvintes = ouvintes.filter(function (g) { return g !== f; });
      };
    },
  };

  aplicar();
})();
