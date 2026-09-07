"""cognito, o protocolo de identidade e nada além dele.

Este módulo fala OAuth com o Cognito: monta a URL de autorização, troca o
código por tokens e confere que o token recebido é legítimo. Ele NÃO decide
quem está na sessão, não escreve cookie e não conhece rota: entrega um
`sessao.Usuario` e sai de cena.

A fronteira importa. `sessao.py` continua sendo a única resposta para "quem
está usando o Medyx agora", e é ele que a API consulta. Se amanhã a
cooperativa trocar o provedor de identidade, este arquivo é substituído e
nenhum outro muda.

── por que o fluxo é o de código de autorização ────────────────────────────

Porque o token nunca passa pelo navegador. No fluxo implícito, o `id_token`
viajaria na barra de endereço: ficaria no histórico, no log do proxy e no
`Referer`. Aqui o navegador carrega apenas um código de uso único, e a troca
por token acontece de servidor para servidor (DIRETRIZES §22: credencial não
chega ao navegador em forma utilizável).

── por que PKCE ────────────────────────────────────────────────────────────

O app client do portal é PÚBLICO: não tem segredo. Sem segredo, o código de
autorização sozinho autentica quem o apresentar, e quem interceptasse o
retorno poderia trocá-lo por um token. O PKCE fecha isso: quem inicia o login
guarda um segredo efêmero (`code_verifier`) e manda só o hash dele; na troca,
o Cognito exige o segredo original. Interceptar o código deixa de bastar.

── configuração ────────────────────────────────────────────────────────────

Tudo por variável de ambiente, nada aqui e nada no `config.py`. O `config.py`
é dono dos valores da METODOLOGIA (Lei 2), e endereço de provedor não é
método: muda entre ambientes e não pode viajar no repositório.

    export MEDYX_COGNITO_REGIAO="sa-east-1"
    export MEDYX_COGNITO_POOL_ID="sa-east-1_ylgQdMTxL"
    export MEDYX_COGNITO_CLIENT_ID="6mk459t02pdg53v3ss816d2h86"
    export MEDYX_COGNITO_DOMINIO="entrar.medyx.com.br"
    export MEDYX_URL_BASE="http://localhost:8770"

O domínio é o PRÓPRIO, e não o de prefixo da AWS. Os dois funcionam e os dois
continuam de pé, mas quem digita a senha precisa reconhecer onde está: uma URL
`amazoncognito.com` no meio do login de um portal médico parece desvio, e
desconfiança na hora da senha é o pior lugar para ela aparecer.

Faltando qualquer uma, `configurado()` é `False` e o app se comporta como se
comporta hoje: sem sessão, com o estado declarado na tela. Um provedor mal
configurado NÃO derruba o servidor, porque servidor no chão é pior que app
sem login.
"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
import urllib.parse
from dataclasses import dataclass

import httpx
import jwt
from jwt import PyJWKClient

import sessao

# Tolerância de relógio na conferência de expiração. Existe porque o relógio do
# servidor e o da AWS não são o mesmo, e uma diferença de segundos rejeitaria
# um token perfeitamente válido.
FOLGA_DE_RELOGIO_SEGUNDOS = 30

# Tempo máximo de espera ao falar com o Cognito. Sem limite, uma indisponi-
# bilidade do provedor viraria requisição pendurada e worker ocupado.
TEMPO_LIMITE_SEGUNDOS = 10

# Os escopos que o portal pede. `openid` é obrigatório no OIDC; `email` e
# `profile` são o que a tela de conta exibe (e-mail e nome). Nada além:
# escopo que não é usado é dado pedido sem motivo.
ESCOPOS = ("openid", "email", "profile")

# O idioma da tela do provedor. Viaja em TODA URL que leva alguém até lá, e não
# é opcional: sem ele o Cognito responde em inglês, e o CLAUDE.md proíbe inglês
# em interface de usuário.
#
# Tem de ser `pt-BR` com a região. Verificado em set/2026: `pt` sozinho devolve
# a tela em inglês, e o cabeçalho `Accept-Language` do navegador é ignorado.
IDIOMA = "pt-BR"


class ErroDeIdentidade(Exception):
    """Falha no diálogo com o provedor.

    Existe para que a rota saiba a diferença entre "o Cognito recusou" e "o
    Python quebrou". A primeira é um estado tratável (volta para a porta de
    entrada); a segunda é defeito e tem de aparecer no log como defeito.
    """


@dataclass(frozen=True)
class Config:
    """O endereço do provedor, montado uma vez e conferido inteiro."""

    regiao: str
    pool_id: str
    client_id: str
    dominio: str
    url_base: str

    @property
    def emissor(self) -> str:
        """O `iss` que todo token legítimo deste pool carrega."""
        return f"https://cognito-idp.{self.regiao}.amazonaws.com/{self.pool_id}"

    @property
    def jwks(self) -> str:
        """Onde ficam as chaves públicas que assinam o token."""
        return f"{self.emissor}/.well-known/jwks.json"

    @property
    def url_autorizacao(self) -> str:
        return f"https://{self.dominio}/oauth2/authorize"

    @property
    def url_token(self) -> str:
        return f"https://{self.dominio}/oauth2/token"

    @property
    def url_logout(self) -> str:
        return f"https://{self.dominio}/logout"

    @property
    def url_senha(self) -> str:
        """A tela de redefinição de senha do provedor.

        A tela de conta encaminha para cá em vez de ter campo próprio: senha é
        do provedor, e um formulário aqui criaria uma segunda porta para a
        mesma credencial.
        """
        return (f"https://{self.dominio}/forgotPassword"
                f"?client_id={self.client_id}"
                f"&response_type=code"
                f"&lang={IDIOMA}"
                f"&redirect_uri={urllib.parse.quote(self.retorno, safe='')}")

    @property
    def retorno(self) -> str:
        """O endereço para onde o Cognito devolve o navegador.

        Precisa estar cadastrado nas callback URLs do app client, idêntico até
        a barra final. Divergência aqui é o erro mais comum do fluxo, e o
        Cognito o reporta como `redirect_mismatch` antes mesmo da tela de senha.
        """
        return f"{self.url_base.rstrip('/')}/auth/callback"


def _do_ambiente() -> Config | None:
    """Lê a configuração do ambiente. Incompleta devolve `None`, nunca uma
    configuração pela metade: provedor meio configurado falha no meio do
    login, que é o pior lugar para falhar."""
    valores = {
        "regiao": os.environ.get("MEDYX_COGNITO_REGIAO", "").strip(),
        "pool_id": os.environ.get("MEDYX_COGNITO_POOL_ID", "").strip(),
        "client_id": os.environ.get("MEDYX_COGNITO_CLIENT_ID", "").strip(),
        "dominio": os.environ.get("MEDYX_COGNITO_DOMINIO", "").strip(),
        "url_base": os.environ.get("MEDYX_URL_BASE", "").strip(),
    }
    if not all(valores.values()):
        return None
    return Config(**valores)


def configuracao() -> Config | None:
    """A configuração desta execução, ou `None` se o provedor não foi ligado.

    Sem memoização de propósito: o custo é ler cinco variáveis, e um valor
    guardado obrigaria a reiniciar o servidor para trocar de ambiente.
    """
    return _do_ambiente()


def configurado() -> bool:
    """Há provedor de identidade neste ambiente?

    A API pergunta isto antes de oferecer qualquer caminho de login. Botão que
    não leva a lugar nenhum é pior que a ausência do botão.
    """
    return configuracao() is not None


# ─────────────────────────────────────────────────────────────────────────────
# Ida: a URL para onde mandamos o navegador
# ─────────────────────────────────────────────────────────────────────────────

def _desafio_pkce(verificador: str) -> str:
    """O hash que viaja na ida. SHA-256 em base64url sem preenchimento, que é
    o único método que o Cognito aceita além do inseguro `plain`."""
    resumo = hashlib.sha256(verificador.encode("ascii")).digest()
    return base64.urlsafe_b64encode(resumo).decode("ascii").rstrip("=")


def iniciar(cfg: Config) -> tuple[str, str, str]:
    """Monta o convite de login. Devolve (url, verificador, estado).

    O verificador e o estado voltam para quem chamou porque precisam sobreviver
    até o retorno do Cognito: sem eles a troca não se completa e o retorno não
    se prova legítimo. Quem os guarda é a rota, na sessão do navegador.

    `nonce` não entra: ele defende o fluxo implícito, em que o token chega pelo
    navegador. Aqui o token vem por canal direto e o PKCE já amarra a troca ao
    navegador que iniciou.
    """
    verificador = secrets.token_urlsafe(64)
    estado = secrets.token_urlsafe(32)
    parametros = {
        "client_id": cfg.client_id,
        "response_type": "code",
        "scope": " ".join(ESCOPOS),
        "redirect_uri": cfg.retorno,
        "state": estado,
        "code_challenge": _desafio_pkce(verificador),
        "code_challenge_method": "S256",
        "lang": IDIOMA,
    }
    url = f"{cfg.url_autorizacao}?{urllib.parse.urlencode(parametros)}"
    return url, verificador, estado


# ─────────────────────────────────────────────────────────────────────────────
# Volta: o código vira token, e o token vira usuário
# ─────────────────────────────────────────────────────────────────────────────

def _trocar_codigo(cfg: Config, codigo: str, verificador: str) -> str:
    """Troca o código de uso único pelo `id_token`, de servidor para servidor.

    Só o `id_token` interessa: ele diz QUEM entrou, que é a única pergunta que
    o Medyx faz ao provedor. O `access_token` serviria para chamar APIs do
    Cognito em nome da pessoa, e o portal não chama nenhuma; guardá-lo seria
    manter uma credencial sem uso, que é superfície de ataque de graça.
    """
    try:
        resposta = httpx.post(
            cfg.url_token,
            data={
                "grant_type": "authorization_code",
                "client_id": cfg.client_id,
                "code": codigo,
                "redirect_uri": cfg.retorno,
                "code_verifier": verificador,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=TEMPO_LIMITE_SEGUNDOS,
        )
    except httpx.HTTPError as erro:
        raise ErroDeIdentidade(f"o provedor não respondeu: {erro}") from erro

    if resposta.status_code != 200:
        # O corpo do erro do Cognito é curto e não traz segredo, mas também não
        # vai para a tela: fica no log, e quem está no navegador recebe o
        # estado, não o diagnóstico.
        raise ErroDeIdentidade(
            f"troca recusada pelo provedor ({resposta.status_code}): {resposta.text}")

    token = resposta.json().get("id_token")
    if not token:
        raise ErroDeIdentidade("o provedor respondeu sem id_token")
    return token


def _conferir(cfg: Config, id_token: str) -> dict:
    """Confere que o token é deste pool, para este cliente, e ainda vale.

    A assinatura é conferida contra as chaves públicas do pool, e não apenas
    confiada ao TLS da troca. O OIDC permite pular isso quando o token vem por
    canal direto, e aqui ele vem; a escolha de conferir mesmo assim é
    deliberada, porque num produto de auditoria "quem entrou" é parte da
    trilha, e trilha que se apoia em premissa de transporte é difícil de
    defender numa revisão de segurança.
    """
    try:
        chave = PyJWKClient(cfg.jwks).get_signing_key_from_jwt(id_token)
        return jwt.decode(
            id_token,
            chave.key,
            algorithms=["RS256"],
            audience=cfg.client_id,
            issuer=cfg.emissor,
            leeway=FOLGA_DE_RELOGIO_SEGUNDOS,
            options={"require": ["exp", "iss", "aud"]},
        )
    except Exception as erro:
        raise ErroDeIdentidade(f"token recusado na conferência: {erro}") from erro


def _usuario_das_claims(claims: dict) -> sessao.Usuario:
    """Traduz o token no `Usuario` que a tela conhece.

    Só nome e e-mail atravessam. `sub`, `exp` e o resto das claims ficam para
    trás: o que não é exibido não cruza a fronteira (DIRETRIZES §22).

    `papel` sai `None` porque o pool ainda não tem grupos (decisão de set/2026,
    MVP sem perfis). A tela OMITE a linha quando é `None`, então não há buraco
    visível. No dia em que houver grupos, o valor vem de `cognito:groups`.
    """
    email = (claims.get("email") or "").strip()
    if not email:
        # Sem e-mail não há identidade exibível, e o pool está configurado para
        # exigi-lo. Chegar aqui significa provedor mudado por fora.
        raise ErroDeIdentidade("o token não trouxe e-mail")
    return sessao.Usuario(
        nome=(claims.get("name") or "").strip() or email.split("@")[0],
        email=email,
        papel=None,
    )


def concluir(cfg: Config, codigo: str, verificador: str) -> sessao.Usuario:
    """O retorno inteiro: código vira token, token é conferido, token vira
    usuário. Levanta `ErroDeIdentidade` em qualquer tropeço do caminho."""
    return _usuario_das_claims(_conferir(cfg, _trocar_codigo(cfg, codigo, verificador)))


def url_de_saida(cfg: Config) -> str:
    """Onde encerrar a sessão DO PROVEDOR, depois de encerrar a nossa.

    Sem esta parada, "Sair" sai pela metade: o cookie do Medyx some, mas a
    sessão do Cognito continua de pé, e o próximo clique em Entrar devolve a
    pessoa ao app sem pedir senha. Em máquina compartilhada isso é um defeito
    de segurança, não um detalhe de fluxo.
    """
    parametros = {
        "client_id": cfg.client_id,
        "logout_uri": f"{cfg.url_base.rstrip('/')}/",
        "lang": IDIOMA,
    }
    return f"{cfg.url_logout}?{urllib.parse.urlencode(parametros)}"
