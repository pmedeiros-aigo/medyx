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

── quando o Cognito entrar ─────────────────────────────────────────────────

O middleware valida o token e escreve o usuário em `request.state.usuario`.
`usuario_da_requisicao` já procura ali primeiro, então nada mais muda: nem a
API, nem a tela, nem este contrato.
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
