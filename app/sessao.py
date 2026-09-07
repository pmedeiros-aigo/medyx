"""sessao, a fronteira de autenticação do app.

É o ÚNICO lugar que responde "quem está usando o Medyx agora". A API e as telas
perguntam aqui; nenhuma delas lê cookie, token ou variável de ambiente por
conta própria. Quando o Cognito entrar, ele entra SÓ neste arquivo.

── por que existe antes de haver login ─────────────────────────────────────

Porque "sem sessão" é um estado do produto, não a ausência dele. A tela de
conta precisa saber a diferença entre "ninguém está autenticado" e "falhou ao
descobrir", e o chassi precisa decidir se mostra o bloco de conta ou não. Sem
uma fonte única, cada tela inventaria a sua resposta.

A regra que este módulo protege é a mesma que manteve o bloco de conta fora do
`shell.html` até agora: **nome fixo na tela é ficção, e ficção em produto de
auditoria custa confiança.** Nada aqui inventa um usuário. Sem sessão real e
sem override explícito de desenvolvimento, a resposta é `None`.

── o Cognito entrou (set/2026) ─────────────────────────────────────────────

Como estava previsto: `hidratar` lê a sessão do cookie e escreve o usuário em
`request.state.usuario`, e `usuario_da_requisicao` já procurava ali primeiro.
Nada mais mudou: nem a API, nem a tela, nem este contrato.

A divisão com o `cognito.py` é de assunto, não de camada. Lá mora o PROTOCOLO
(falar OAuth, conferir token); aqui mora a IDENTIDADE (quem está na sessão, e
por quanto tempo). Trocar de provedor substitui aquele arquivo e não toca
neste.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

# Nome do cookie de sessão. HttpOnly, escrito pelo servidor no retorno do
# provedor de identidade e nunca legível pelo JavaScript (DIRETRIZES §22:
# credencial não chega ao navegador em forma utilizável).
COOKIE_SESSAO = "medyx_sessao"

# Override de DESENVOLVIMENTO. Existe para que a tela de conta possa ser
# construída e conferida antes do Cognito, e é deliberadamente chato de ligar:
# precisa ser exportado à mão, tem "DEV" no nome e não tem valor padrão.
#
#     export MEDYX_SESSAO_DEV="Pedro Medeiros <pedro.hmdo@live.com>"
#
# Some sozinho: assim que `request.state.usuario` existir, ele tem precedência.
VAR_SESSAO_DEV = "MEDYX_SESSAO_DEV"

# A chave que assina o cookie. Sem ela não há sessão: quem tem a chave forja
# identidade, então ela não tem valor padrão e não viaja no repositório.
VAR_CHAVE = "MEDYX_CHAVE_SESSAO"

# Quanto tempo a sessão do Medyx dura. Oito horas é um turno de trabalho: cobre
# o dia de quem está analisando sem obrigar a entrar de novo no meio de uma
# leitura, e expira antes que a máquina passe para o turno seguinte.
#
# Não é o tempo do token do Cognito (60 minutos), e a diferença é deliberada.
# O token responde "esta pessoa provou quem é agora"; a sessão responde "esta
# pessoa continua trabalhando". Amarrar as duas expulsaria o analista a cada
# hora, no meio da tela, sem que nada tivesse acontecido.
DURACAO_SESSAO_SEGUNDOS = 8 * 60 * 60


@dataclass(frozen=True)
class Usuario:
    """Quem está na sessão. Só o que a tela precisa mostrar, nada além.

    Sem id interno, sem token, sem claim bruta do provedor: o que não é exibido
    não atravessa a fronteira (DIRETRIZES §22).
    """

    nome: str
    email: str
    papel: str | None = None

    @property
    def iniciais(self) -> str:
        """Duas letras para o avatar. Primeiro e último nome; um nome só, uma
        letra. Nunca vazio: sem nome, a inicial vem do e-mail."""
        partes = [p for p in self.nome.replace(".", " ").split() if p]
        if not partes:
            return (self.email[:1] or "?").upper()
        if len(partes) == 1:
            return partes[0][:1].upper()
        return (partes[0][:1] + partes[-1][:1]).upper()

    def para_tela(self) -> dict[str, str | None]:
        """O formato que a API entrega. `papel` viaja como está: ausente é
        `None`, e a tela OMITE a linha (ajuste 1 do CLAUDE.md, ausência de
        atributo não vira etiqueta)."""
        return {
            "nome": self.nome,
            "email": self.email,
            "iniciais": self.iniciais,
            "papel": self.papel,
        }


def _do_ambiente() -> Usuario | None:
    """Lê o override de desenvolvimento. Formato: `Nome <email>`, ou só o
    e-mail. Valor malformado devolve `None`, nunca um usuário parcial."""
    bruto = os.environ.get(VAR_SESSAO_DEV, "").strip()
    if not bruto:
        return None
    if "<" in bruto and bruto.endswith(">"):
        nome, _, resto = bruto.partition("<")
        email = resto[:-1].strip()
        nome = nome.strip()
    else:
        nome, email = "", bruto
    if "@" not in email:
        return None
    return Usuario(nome=nome or email.split("@")[0], email=email,
                   papel="Sessão de desenvolvimento")


def usuario_da_requisicao(request) -> Usuario | None:
    """O usuário desta requisição, ou `None` se não há sessão.

    Ordem de precedência, e ela importa: sessão real primeiro, override de
    desenvolvimento depois. Assim que o Cognito estiver no ar, a variável de
    ambiente deixa de ter efeito mesmo se alguém esquecer de removê-la.
    """
    usuario = getattr(request.state, "usuario", None)
    if isinstance(usuario, Usuario):
        return usuario
    return _do_ambiente()


# ─────────────────────────────────────────────────────────────────────────────
# A sessão no cookie — escrita, leitura e fim
# ─────────────────────────────────────────────────────────────────────────────

def chave_de_assinatura() -> str | None:
    """A chave que assina o cookie, ou `None` se não foi definida.

    `None` desliga a sessão inteira em vez de improvisar uma chave. Chave
    gerada na subida do servidor pareceria funcionar e derrubaria todo mundo a
    cada reinício; chave fixa no código autenticaria qualquer um que lesse o
    repositório.
    """
    return os.environ.get(VAR_CHAVE, "").strip() or None


def registrar(request, usuario: Usuario) -> None:
    """Grava o usuário na sessão do navegador, no fim de um login bem-sucedido.

    Só os três campos que a tela mostra. O token do provedor NÃO é guardado: o
    Medyx não chama nenhuma API em nome da pessoa, e credencial guardada sem
    uso é superfície de ataque de graça (DIRETRIZES §22).
    """
    request.session.update({
        "nome": usuario.nome,
        "email": usuario.email,
        "papel": usuario.papel,
    })


def encerrar(request) -> None:
    """Esvazia a sessão. O cookie em si morre com a resposta, por conta do
    middleware; aqui se apaga o conteúdo, que é o que dá acesso.

    Nunca levanta. Sair é a saída de emergência do produto: se ela falhar
    porque não havia sessão para encerrar, a pessoa fica presa numa tela de
    erro sem conseguir sair, que é o oposto do que a rota existe para fazer.
    """
    try:
        request.session.clear()
    except AssertionError:
        pass  # ambiente sem middleware de sessão: não há o que limpar


async def hidratar(request, chamar_proximo):
    """Middleware: transforma a sessão do cookie em `request.state.usuario`.

    É o ponto exato que o cabeçalho deste arquivo prometia. Vale para TODA
    requisição, inclusive as que não exigem sessão: quem decide o que fazer com
    a ausência é a rota, não este middleware. Sessão malformada é tratada como
    ausência, nunca como usuário parcial.
    """
    try:
        dados_da_sessao = request.session or {}
    except AssertionError:
        # Sem o middleware de sessão instalado (ambiente sem chave), `session`
        # não existe. Isso é "não há sessão", não é defeito.
        dados_da_sessao = {}
    email = (dados_da_sessao.get("email") or "").strip()
    if email:
        request.state.usuario = Usuario(
            nome=dados_da_sessao.get("nome") or email.split("@")[0],
            email=email,
            papel=dados_da_sessao.get("papel"),
        )
    return await chamar_proximo(request)
