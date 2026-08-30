/* conta.js — Minha conta: identidade e segurança do acesso.
 *
 * A pergunta da página: "com que conta eu estou aqui, e como eu troco senha ou
 * saio?" Não é tela de análise. Nenhum motor a alimenta, nenhum número dela é
 * comparado, e por isso a faixa de critérios some no chassi: uma régua sobre
 * uma tela sem número declararia o cálculo que não houve.
 *
 * ── composição: a identidade é o CABEÇALHO, não um cartão ───────────────────
 *
 * A primeira versão punha identidade e segurança em dois cartões. Ficava pobre,
 * e o defeito não era falta de conteúdo: era moldura demais para pouco fato.
 * Um cartão intitulado "Identidade" numa página chamada "Minha conta" repete o
 * título com outras palavras, e uma barra de rodapé com uma frase explicativa
 * ocupando 720px anuncia vazio (DIRETRIZES §8: cartão desnecessário, moldura
 * excessiva, texto redundante).
 *
 * O arranjo agora é o de produto maduro: a pessoa É o cabeçalho da página
 * (avatar, nome, e-mail, papel), e abaixo vem UMA seção com as ações, sem
 * moldura nenhuma. A estrutura vem da régua sob o título e das divisórias
 * entre linhas, não de caixas. Menos moldura, mais hierarquia.
 *
 * ── linguagem ───────────────────────────────────────────────────────────────
 *
 * Voz institucional, frase curta, verbo no processo (LEXICO_PRODUTO §Tom).
 * Nada de "fale com quem administra", "aqui aparecem", "até lá": a tela informa
 * um estado, não conversa com quem lê.
 *
 * ── o que ficou de fora, e por quê ──────────────────────────────────────────
 *
 * Preferências de análise. A régua vive na URL de propósito, para que um link
 * de evidência reabra a mesma leitura, e os padrões são do `config.py`,
 * anunciados na tela como recomendados (ajuste 3). Um padrão pessoal escondido
 * num painel quebraria as duas coisas.
 *
 * Foto de perfil. As iniciais identificam, e o avatar já está na lateral.
 *
 * Edição de nome e e-mail. Vêm do provedor de identidade; campo editável aqui
 * criaria duas fontes para o mesmo dado.
 *
 * Encerramento de sessão em todos os dispositivos. Depende do provedor e hoje
 * não teria efeito. Entra junto com ele, e com diálogo de confirmação, porque
 * derruba sessões que não são a desta tela.
 */
'use strict';

import { buscar } from '../lib/api.js';
import { el } from '../lib/dom.js';
import { abrirPagina } from '../lib/pagina.js';
import { TELAS } from '../lib/rotas.js';

/**
 * Uma linha de atributo: rótulo, valor, apoio opcional e ação opcional.
 *
 * `valor` aceita texto ou elemento, e é o que deixa a MESMA linha servir a um
 * estado escrito ("Ativa neste navegador") e a um estado etiquetado (a
 * verificação em duas etapas, que se lê de relance por cor e forma).
 */
function linha({ rotulo, valor, apoio, acao }) {
  const l = el('div', 'def-row');
  l.appendChild(el('span', 'def-k', rotulo));
  const v = el('div', 'def-v');
  v.append(typeof valor === 'string' ? document.createTextNode(valor) : valor);
  if (apoio) {
    v.appendChild(el('span', 'sub', apoio));
    l.classList.add('def-topo');
  }
  l.appendChild(v);
  if (acao) {
    const caixa = el('div', 'def-act');
    caixa.appendChild(acao);
    l.appendChild(caixa);
  }
  return l;
}

/** Etiqueta de estado. `.tag-ctx` (verde, com marca) é o estado verificado do
 *  sistema; `.tag-off` é o estado ausente. Cor NUNCA sozinha: o texto diz o
 *  mesmo que a cor (DIRETRIZES §19). */
function etiqueta(texto, ativo) {
  const t = el('span', `tag ${ativo ? 'tag-ctx' : 'tag-off'}`);
  if (ativo) t.appendChild(el('span', 'mk'));
  t.appendChild(document.createTextNode(texto));
  return t;
}

/** Ação que NAVEGA (sair, provedor de identidade): `<a>`, não `<button>`. */
function botaoLink(href, rotulo) {
  const a = el('a', 'btn', rotulo);
  a.href = href;
  return a;
}

/**
 * Seção: título com régua embaixo, e o conteúdo solto sob ela.
 *
 * NÃO é `.tbl`. O cartão das telas de análise envolve uma TABELA, e a moldura
 * dele separa um objeto denso do resto da página. Aqui envolveria três linhas
 * de texto, sobre `--canvas`, que é branco, contra um `.tbl` que também é
 * branco: a borda não separaria figura de fundo, só acrescentaria moldura.
 * DIRETRIZES §8 nomeia os dois defeitos: cartão desnecessário e borda
 * excessiva.
 *
 * `.sec` e `.sec-hd` já existiam no contrato e não eram usados por nenhuma
 * tela. É exatamente o caso deles.
 */
function secao(titulo) {
  const s = el('div', 'sec');
  const cab = el('div', 'sec-hd');
  cab.appendChild(el('h3', null, titulo));
  s.appendChild(cab);
  return s;
}

/* ── os dois estados da tela ─────────────────────────────────────────────── */

/**
 * SEM SESSÃO. Não é erro, e por isso não vai para o banner de falha: é o estado
 * corrente do ambiente enquanto a autenticação não foi ativada. Duas frases,
 * sem pedido de desculpas e sem promessa de data.
 */
function semSessao(col, conta) {
  const sec = secao('Sessão não autenticada');
  const pilha = el('div', 'stack g8');
  pilha.appendChild(el('span', 'sub', conta.motivo));
  pilha.appendChild(el('span', 'note',
    'Identidade, redefinição de senha e verificação em duas etapas ficam '
    + 'disponíveis após a integração com o provedor de identidade.'));
  sec.appendChild(pilha);
  col.appendChild(sec);
}

/** COM SESSÃO: a pessoa no cabeçalho, as ações num bloco só. */
function comSessao(col, conta) {
  const { usuario, seguranca } = conta;

  /* ── identidade: cabeçalho da página, sem moldura ──────────────────────── */
  const ident = el('div', 'row g14');
  ident.appendChild(el('span', 'av av-lg', usuario.iniciais));

  const quem = el('div', 'stack g4');
  const nome = el('div', 'row g8');
  nome.appendChild(el('b', null, usuario.nome));
  /* Papel só aparece se existir: ausência de atributo não vira etiqueta
     (ajuste 1 do CLAUDE.md), e "sem perfil" seria exatamente essa etiqueta. */
  if (usuario.papel) nome.appendChild(el('span', 'tag tag-attr', usuario.papel));
  quem.appendChild(nome);
  quem.appendChild(el('span', 'sub', usuario.email));
  ident.appendChild(quem);
  col.appendChild(ident);

  col.appendChild(el('span', 'note',
    'Nome, e-mail e perfil são fornecidos pelo provedor de identidade. '
    + 'Alterações são tratadas pela administração de acessos.'));

  /* ── acesso e sessão: uma seção, as três linhas que existem ────────────── */
  const sec = secao('Acesso e sessão');
  const lista = el('div', 'deflist');

  if (seguranca?.provedor) {
    /* Senha e segundo fator são do provedor: o Medyx encaminha em vez de
       manter formulário próprio, que seria uma segunda superfície de
       credencial para proteger (DIRETRIZES §22). */
    lista.appendChild(linha({
      rotulo: 'Senha',
      valor: `Gerenciada pelo ${seguranca.provedor}`,
      acao: botaoLink(seguranca.url_senha, 'Redefinir senha'),
    }));
    /* Duas etapas tem TRÊS estados, e o terceiro é a ausência da linha:
         true  -> ativa
         false -> disponível na política de acesso, ainda não configurada
         null  -> FORA da política; a linha não existe.
       `null` não é `false`. Imprimir "Não configurada" com um botão
       "Configurar" onde o segundo fator não faz parte da política ofereceria
       um recurso que o produto não tem, que é o defeito que esta tela evita em
       todo lugar. Ausência de atributo não vira etiqueta (ajuste 1). */
    if (seguranca.duas_etapas !== null && seguranca.duas_etapas !== undefined) {
      lista.appendChild(linha({
        rotulo: 'Verificação em duas etapas',
        valor: etiqueta(seguranca.duas_etapas ? 'Ativa' : 'Não configurada',
                        seguranca.duas_etapas),
        apoio: seguranca.duas_etapas
          ? null
          : 'Segundo fator reduz o risco de acesso indevido a dado assistencial.',
        acao: botaoLink(seguranca.url_duas_etapas,
                        seguranca.duas_etapas ? 'Gerenciar' : 'Configurar'),
      }));
    }
  } else {
    /* Sem provedor: uma linha que declara o estado, e nenhum botão apagado.
       Controles desabilitados anunciariam recursos que a tela não cumpre, e o
       leitor passaria a desconfiar dos que funcionam. */
    lista.appendChild(linha({
      rotulo: 'Autenticação',
      valor: etiqueta('Provedor não conectado', false),
      apoio: 'Redefinição de senha e verificação em duas etapas ficam '
        + 'disponíveis após a integração.',
    }));
  }

  /* Sair funciona com provedor ou sem: a rota encerra a sessão no servidor. */
  lista.appendChild(linha({
    rotulo: 'Sessão',
    valor: 'Ativa neste navegador',
    acao: botaoLink('/sair', 'Sair'),
  }));

  sec.appendChild(lista);
  col.appendChild(sec);
}

/* ── a tela ──────────────────────────────────────────────────────────────── */

await abrirPagina({
  titulo: 'Minha Conta',
  /* O seletor de área é removido nesta tela por `ajustarControlesDaTela`; o
     destino existe porque o contrato de `abrirPagina` o exige. */
  aoTrocarArea: (id) => TELAS.area.caminho(id),
  montar: async ({ conteudo }) => {
    /* Coluna estreita, e não a largura fluida das telas de análise: aqui não há
       tabela nem gráfico para ocupar 1600px, e um rótulo à esquerda com o seu
       botão na outra ponta da tela não se lê como uma linha só. */
    const col = el('div', 'stack leitura');
    conteudo.appendChild(col);

    const topo = el('div', 'stack g6');
    topo.appendChild(el('h2', null, 'Minha conta'));
    topo.appendChild(el('span', 'sub', 'Identidade e segurança do acesso'));
    col.appendChild(topo);

    const conta = await buscar('/api/conta',
                               { anunciarEm: col, rotulo: 'carregando a conta…' });

    if (conta.autenticado) comSessao(col, conta);
    else semSessao(col, conta);

    /* Versão da aplicação: quem relata um problema precisa dizer sobre qual
       versão fala. A proveniência dos DADOS não se repete aqui; ela vive nas
       telas de análise, onde governa a leitura de um número. */
    /* Sem régua acima: `.note-t` usa a MESMA cor e espessura das divisórias
       entre linhas, e colada ao fim da lista ela lia como mais uma linha. A
       versão da aplicação não pertence a "Acesso e sessão"; o espaço em branco
       já separa, e uma régua ali sugeriria parentesco que não existe. */
    const rodape = el('div', 'stack g4');
    rodape.appendChild(el('span', 'note',
      `Aplicação ${conta.app.versao} · classificação ${conta.app.classificacao}`));
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
