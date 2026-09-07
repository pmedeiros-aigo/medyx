/* lib/enxame.js — o empacotador de pontos dos gráficos de distribuição.
 *
 * Mora numa lib, e não dentro de um bloco, porque DOIS desenhos o usam: a
 * distribuição da tela de Área (um ponto por cooperado, eixo do índice) e a
 * distribuição de um exame no painel lateral da mesma tela. É geometria pura —
 * entra posição em %, sai altura em px — e nenhuma das duas telas tem opinião
 * sobre ela: se as alturas fossem calculadas duas vezes, os mesmos cooperados
 * cairiam em lugares diferentes nos dois gráficos da mesma página.
 */
'use strict';

/* Enxame por empacotamento CONTÍNUO.
 *
 * Cada ponto procura a altura mais próxima do eixo em que não ENCOSTE em nenhum
 * vizinho já colocado. Não há faixas: a altura é um número real, resultado da
 * geometria, não de uma grade.
 *
 * Três tentativas até chegar aqui, e cada uma falhou por desenhar um padrão que
 * não existe no dado:
 *   · sorteio pelo id — vizinhos caíam na mesma altura por acaso e se sobrepunham;
 *   · faixas em ciclo — sem colisão, mas escadas diagonais regulares;
 *   · faixas por colisão — sem escadas, mas os pontos encaixavam em linhas e o
 *     resultado parecia uma grade.
 *
 * A geometria: dois círculos de diâmetro d não se sobrepõem se a distância entre
 * os centros for >= d. Fixado o afastamento horizontal dx, as alturas PROIBIDAS
 * por um vizinho são o intervalo y_vizinho +/- sqrt(d^2 - dx^2). Junta-se todos
 * os intervalos dos vizinhos e escolhe-se a altura livre de menor módulo — a mais
 * perto do eixo.
 *
 * O contorno que emerge É a densidade: onde há um cooperado sozinho ele fica no
 * eixo; onde se acumulam, o grupo incha. Diz o que um histograma diria sem
 * deixar de mostrar cada cooperado.
 *
 * Determinístico: mesma medida, mesmas alturas.
 */
export function posicionarEmEnxame(pontos, larguraPx, jitter, diametro, base) {
  const limite = jitter / 2;
  const d = diametro + 1;                 // 1px de folga para não encostarem
  const ordem = pontos
    .map((p, i) => [i, (p.pos_pct / 100) * larguraPx])
    .sort((a, b) => a[1] - b[1]);

  const colocados = [];                   // {x, y} já resolvidos
  const alturas = new Array(pontos.length);

  for (const [indice, x] of ordem) {
    const proibidos = [];
    for (const q of colocados) {
      const dx = Math.abs(x - q.x);
      if (dx >= d) continue;
      const meia = Math.sqrt(d * d - dx * dx);
      proibidos.push([q.y - meia, q.y + meia]);
    }

    // candidatos: o eixo e as bordas de cada intervalo proibido — é onde a
    // primeira altura livre sempre está
    const candidatos = [0];
    for (const [de, ate] of proibidos) candidatos.push(de, ate);
    candidatos.sort((a, b) => Math.abs(a) - Math.abs(b));

    let y = null;
    for (const c of candidatos) {
      if (Math.abs(c) > limite) continue;
      const livre = proibidos.every(([de, ate]) => c <= de + 0.01 || c >= ate - 0.01);
      if (livre) { y = c; break; }
    }
    // enxame cheio até o teto: fica na borda, encostando, em vez de estourar a
    // área de plotagem
    if (y === null) y = colocados.length % 2 ? limite : -limite;

    colocados.push({ x, y });
    alturas[indice] = Math.round(base + y);
  }
  return alturas;
}
