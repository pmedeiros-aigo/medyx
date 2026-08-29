/* conta.js — Minha conta: identidade da sessão e segurança do acesso.
 *
 * A pergunta da página: "com que conta eu estou aqui, e como eu troco senha ou
 * saio?" Não é tela de análise. Nenhum motor a alimenta, nenhum número dela é
 * comparado, e por isso a faixa de critérios some no chassi: uma régua sobre
 * uma tela sem número declararia o cálculo que não houve.
 *
 * ── o que ficou de fora, e por quê ──────────────────────────────────────────
 *
 * Preferências de análise (janela, critério, referência como "meu padrão").
 * A régua vive na URL de propósito, para que um link de evidência reabra a
 * mesma leitura, e os padrões são do `config.py`, anunciados na tela como
 * recomendados (ajuste 3). Um padrão pessoal escondido num painel contradiria
 * as duas coisas: o link deixaria de reproduzir a leitura, e o "recomendado"
 * passaria a significar coisas diferentes para pessoas diferentes. Se um dia
 * fizer sentido, é decisão de método, não de tela.
 *
 * Foto de perfil. As iniciais já identificam, e o avatar já está na lateral.
 * Upload seria um recurso inteiro (guardar, cortar, servir) por nenhum ganho
 * de leitura (DIRETRIZES §8).
 *
 * Editar nome e e-mail. Vêm do login; campo editável aqui criaria duas fontes
 * para o mesmo dado.
 *
 * "Encerrar sessão em todos os dispositivos". A ação depende do provedor de
 * identidade e hoje não teria efeito nenhum. Botão que não faz o que promete é
 * pior que ausência (DIRETRIZES §17). Entra junto com o provedor.
 */
'use strict';

import { buscar } from '../lib/api.js';
import { el } from '../lib/dom.js';
import { abrirPagina } from '../lib/pagina.js';
import { TELAS } from '../lib/rotas.js';

/** Cartão no padrão das outras telas: cabeçalho com título e apoio, corpo, e
 *  rodapé opcional. Reaproveita `.tbl`, que é a superfície de bloco do app. */
function cartao(titulo, apoio) {
  const c = el('div', 'tbl');
  const cab = el('div', 'tbl-hd');
  const tt = el('div', 'stack g4');
  tt.appendChild(el('span', 't', titulo));
  if (apoio) tt.appendChild(el('span', 'sub', apoio));
  cab.appendChild(tt);
  c.appendChild(cab);
  const corpo = el('div', 'tbl-band');
  c.appendChild(corpo);
  return { cartao: c, corpo };
}

/**
 * Uma linha de atributo: rótulo, valor, apoio opcional e ação opcional.
 *
 * A MESMA linha serve identidade (rótulo + valor) e segurança (rótulo + estado
 * + botão), porque a ação é um slot, não um segundo componente.
 */
function linha({ rotulo, valor, apoio, acao }) {
  const l = el('div', 'def-row');
  l.appendChild(el('span', 'def-k', rotulo));
  const v = el('div', 'def-v');
  v.appendChild(document.createTextNode(valor));
  if (apoio) v.appendChild(el('span', 'sub', apoio));
  l.appendChild(v);
  if (acao) {
    const caixa = el('div', 'def-act');
    caixa.appendChild(acao);
    l.appendChild(caixa);
  }
  return l;
}

/** Botão que NAVEGA (sair, provedor de identidade): `<a>`, não `<button>`. */
function botaoLink(href, rotulo, classe = 'btn') {
  const a = el('a', classe, rotulo);
  a.href = href;
  return a;
}

/* ── os dois estados da tela ─────────────────────────────────────────────── */

/**
 * SEM SESSÃO. Não é erro, e por isso não vai para o banner de falha: é o
 * estado normal deste ambiente enquanto o login não foi ligado. A tela diz o
 * que está acontecendo, em vez de mostrar campos vazios ou um nome de exemplo.
 */
function semSessao(conteudo, conta) {
  const { cartao: c, corpo } = cartao(
    'Nenhuma sessão autenticada',
    'esta tela mostra a sua identidade e a segurança do seu acesso');
  const pilha = el('div', 'stack g10');
  pilha.appendChild(el('span', 'sub', conta.motivo));
  pilha.appendChild(el('span', 'note',
    'Quando o acesso por login estiver ativo, aqui aparecem o seu nome e '
    + 'e-mail, a troca de senha, a verificação em duas etapas e a ação de '
    + 'sair. Até lá não há sessão a mostrar, e inventar uma seria descrever '
    + 'um acesso que não existe.'));
  corpo.appendChild(pilha);
  conteudo.appendChild(c);
}

/** COM SESSÃO: identidade, depois segurança. Nessa ordem porque a primeira
 *  pergunta é "sou eu mesmo?" e só a segunda é "o que eu faço com isso". */
function comSessao(conteudo, conta) {
  const { usuario, seguranca } = conta;

  /* ── quem é você ───────────────────────────────────────────────────────── */
  const ident = cartao('Identidade',
    'o que o seu login informa ao Medyx');

  /* A pessoa aparece como pessoa, não como formulário: avatar, nome, e-mail.
     Nome e e-mail NÃO se repetem em linhas abaixo; repetir o mesmo dado em
     dois lugares da mesma tela é ruído (DIRETRIZES §8). */
  const cabeca = el('div', 'row g12');
  cabeca.appendChild(el('span', 'av av-lg', usuario.iniciais));
  const quem = el('div', 'stack g4');
  quem.appendChild(el('b', null, usuario.nome));
  quem.appendChild(el('span', 'sub', usuario.email));
  cabeca.appendChild(quem);
  ident.corpo.appendChild(cabeca);

  /* Perfil de acesso só aparece se existir: ausência de atributo não vira
     etiqueta (ajuste 1 do CLAUDE.md). Sem papel definido, a linha não existe,
     em vez de dizer "sem perfil". */
  if (usuario.papel) {
    const lista = el('div', 'deflist');
    lista.appendChild(linha({ rotulo: 'Perfil de acesso', valor: usuario.papel }));
    ident.corpo.appendChild(lista);
  }

  const pe = el('div', 'tbl-ft');
  pe.appendChild(el('span', null,
    'Nome e e-mail vêm do seu login. Para alterar, fale com quem administra o '
    + 'acesso ao Medyx.'));
  ident.cartao.appendChild(pe);
  conteudo.appendChild(ident.cartao);

  /* ── segurança e sessão ────────────────────────────────────────────────── */
  const seg = cartao('Segurança e sessão',
    'senha, verificação em duas etapas e saída');
  const lista = el('div', 'deflist');

  if (seguranca?.provedor) {
    /* Com provedor configurado, senha e duas etapas são dele: o Medyx leva
       para lá em vez de manter uma segunda tela de senha, que seria uma
       segunda superfície de credencial para proteger (DIRETRIZES §22). */
    lista.appendChild(linha({
      rotulo: 'Senha',
      valor: `Gerenciada pelo ${seguranca.provedor}`,
      acao: botaoLink(seguranca.url_senha, 'Trocar senha'),
    }));
    lista.appendChild(linha({
      rotulo: 'Verificação em duas etapas',
      valor: seguranca.duas_etapas ? 'Ativa' : 'Não configurada',
      apoio: seguranca.duas_etapas
        ? null
        : 'um segundo fator reduz o risco de acesso indevido a dado de saúde',
      acao: botaoLink(seguranca.url_duas_etapas,
                      seguranca.duas_etapas ? 'Gerenciar' : 'Configurar'),
    }));
  } else {
    /* Sem provedor: uma frase que explica, e nenhum botão desabilitado. Três
       controles apagados anunciariam recursos que a tela não tem como
       cumprir, e o leitor passaria a desconfiar dos que funcionam. */
    lista.appendChild(linha({
      rotulo: 'Senha e duas etapas',
      valor: 'Ainda não disponíveis',
      apoio: 'passam a ser configuráveis aqui quando o provedor de '
        + 'identidade estiver conectado',
    }));
  }

  /* Sair funciona hoje, com provedor ou sem: a rota limpa a sessão do lado do
     servidor. É a única ação viva da tela, e por isso é a única com botão. */
  lista.appendChild(linha({
    rotulo: 'Sessão',
    valor: 'Você está autenticado neste navegador',
    acao: botaoLink('/sair', 'Sair'),
  }));

  seg.corpo.appendChild(lista);
  conteudo.appendChild(seg.cartao);
}

/* ── a tela ──────────────────────────────────────────────────────────────── */

await abrirPagina({
  titulo: 'Minha Conta',
  /* Trocar de área na lateral não faz sentido aqui, mas o chassi expõe o
     seletor em toda tela e o contrato de `abrirPagina` exige o destino. Se
     alguém usar, vai para a Área, que é onde a escolha governa alguma coisa.
     (Na prática o seletor é removido nesta tela por `ajustarControlesDaTela`.) */
  aoTrocarArea: (id) => TELAS.area.caminho(id),
  montar: async ({ conteudo }) => {
    /* Coluna estreita, e não a largura fluida das telas de análise: aqui não
       há tabela nem gráfico para ocupar 1600px, e um rótulo à esquerda com o
       seu botão na outra ponta da tela não se lê como uma linha só. */
    const col = el('div', 'stack leitura');
    conteudo.appendChild(col);

    const topo = el('div', 'stack g6');
    topo.appendChild(el('h2', null, 'Minha conta'));
    topo.appendChild(el('span', 'sub',
      'sua identidade no Medyx e a segurança do seu acesso'));
    col.appendChild(topo);

    const conta = await buscar('/api/conta',
                               { anunciarEm: col, rotulo: 'carregando a sua conta…' });

    if (conta.autenticado) comSessao(col, conta);
    else semSessao(col, conta);

    /* Rodapé de versão: quem for relatar um problema precisa dizer sobre qual
       versão está falando. A proveniência dos DADOS não se repete aqui, ela
       vive nas telas de análise, onde governa a leitura de um número. */
    const rodape = el('div', 'stack g4');
    const versoes = `Medyx ${conta.app.versao} · classificação `
      + `${conta.app.classificacao}`;
    rodape.appendChild(el('span', 'note', versoes));
    if (conta.app.suporte) {
      const s = el('span', 'note');
      const a = el('a', null, conta.app.suporte);
      a.href = `mailto:${conta.app.suporte}`;
      s.appendChild(document.createTextNode('Suporte: '));
      s.appendChild(a);
      rodape.appendChild(s);
    }
    col.appendChild(rodape);
  },
});
