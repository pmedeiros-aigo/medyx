#!/usr/bin/env bash
#
# deploy.sh — publica o app na instância Lightsail (sa-east-1).
#
# O QUE ELE FAZ, nesta ordem:
#   1. confere que o local está limpo e já empurrado (não se publica o que não
#      está no remoto: senão o servidor fica com código que ninguém revisa);
#   2. `git pull --ff-only` no servidor (fast-forward, nunca merge);
#   3. sincroniza os MARTS que o app lê, e só eles;
#   4. importa o app no servidor SEM tocar no serviço, como ensaio;
#   5. só então reinicia, e verifica que subiu.
#
# ── por que os marts viajam por rsync, e não pelo git ───────────────────────
# O `.gitignore` diz, com todas as letras, que dado de beneficiário ou de
# cooperado não entra no repositório. O fato tem ID_BENEFICIARIO e o histórico
# de utilização de quase um milhão de solicitações; uma vez no histórico do git,
# tirá-lo de lá exige reescrever história e invalidar todos os clones. Parquet
# também não delta-comprime: cada regeração viraria uma cópia inteira nova.
# O que este arquivo versiona é o PROCEDIMENTO, que é o que precisa ser
# revisável e repetível. O dado continua fora.
#
# ── por que a chave SSH é temporária ────────────────────────────────────────
# `aws lightsail get-instance-access-details` devolve um par chave+certificado
# válido por poucos minutos. Não há chave de longa duração para guardar, vazar
# ou rotacionar, e quem roda o deploy é quem já tem credencial AWS do projeto.
#
# ── o ENSAIO antes do restart ───────────────────────────────────────────────
# O unit tem `Restart=always`. Se o app subir quebrado (mart faltando, coluna
# que mudou de nome), o systemd o reinicia em laço e a aplicação fica fora do ar
# até alguém intervir. Importar o app num processo separado custa segundos e
# transforma um incidente em uma mensagem de erro.
#
# Uso:
#     ./deploy.sh                # publica
#     ./deploy.sh --so-codigo    # só o código, sem sincronizar marts
#     ./deploy.sh --ensaio       # faz tudo menos reiniciar (conferência)
#
set -euo pipefail

INSTANCIA="medyx-portal"
REGIAO="sa-east-1"
USUARIO="ubuntu"
DIR_APP="/opt/medyx/medyx"
DIR_MARTS_REMOTO="/opt/medyx/unimed_natal/marts"
PYTHON_REMOTO="/opt/medyx/venv/bin/python"
SERVICO="medyx"
BRANCH="main"

SO_CODIGO=0
ENSAIO=0
for arg in "$@"; do
  case "$arg" in
    --so-codigo) SO_CODIGO=1 ;;
    --ensaio)    ENSAIO=1 ;;
    *) echo "argumento desconhecido: $arg" >&2; exit 2 ;;
  esac
done

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$raiz"

# ATENÇÃO ao usar `erro`: sempre com `if`/`||`, NUNCA com `teste && erro`. Sob
# `set -e`, `[ teste ] && erro` derruba o script quando o teste é FALSO — que é
# justamente o caminho em que está tudo certo.
passo() { printf '\n\033[1m── %s\033[0m\n' "$1"; }
erro()  { printf '\033[31mFALHA: %s\033[0m\n' "$1" >&2; exit 1; }

# ── 1. o local está publicável? ─────────────────────────────────────────────
passo "conferindo o repositório local"
if [ -n "$(git status --porcelain)" ]; then erro "há alterações não commitadas."; fi
atual="$(git branch --show-current)"
[ "$atual" = "$BRANCH" ] || erro "está em '$atual', não em '$BRANCH'."
git fetch --quiet origin "$BRANCH"
atras=$(git rev-list --count "HEAD..origin/$BRANCH")
frente=$(git rev-list --count "origin/$BRANCH..HEAD")
if [ "$frente" -gt 0 ]; then erro "há $frente commit(s) não empurrado(s). Rode 'git push' antes."; fi
if [ "$atras" -gt 0 ]; then erro "o remoto está $atras commit(s) à frente. Rode 'git pull' antes."; fi
alvo="$(git rev-parse --short HEAD)"
echo "local e origin/$BRANCH em $alvo"

# ── 2. acesso temporário ────────────────────────────────────────────────────
passo "obtendo acesso à instância"
tmp="$(mktemp -d)"
# a chave some ao fim, inclusive se o script morrer no meio
trap 'rm -rf "$tmp"' EXIT
aws lightsail get-instance-access-details \
    --instance-name "$INSTANCIA" --region "$REGIAO" --output json > "$tmp/acesso.json" \
  || erro "não foi possível obter acesso (credencial AWS ativa?)."

python3 - "$tmp" <<'PY'
import json, sys
tmp = sys.argv[1]
d = json.load(open(f"{tmp}/acesso.json"))["accessDetails"]
open(f"{tmp}/chave", "w").write(d["privateKey"])
open(f"{tmp}/chave-cert.pub", "w").write(d["certKey"])
# As chaves de host vêm da API, e é por isso que a conferência fica LIGADA:
# `StrictHostKeyChecking=no` aceitaria qualquer servidor no meio do caminho.
with open(f"{tmp}/known_hosts", "w") as f:
    for k in d["hostKeys"]:
        f.write(f"{d['ipAddress']} {k['algorithm']} {k['publicKey']}\n")
open(f"{tmp}/ip", "w").write(d["ipAddress"])
PY
chmod 600 "$tmp/chave"
ip="$(cat "$tmp/ip")"
opc=(-i "$tmp/chave" -o CertificateFile="$tmp/chave-cert.pub"
     -o UserKnownHostsFile="$tmp/known_hosts" -o StrictHostKeyChecking=yes
     -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=15)
remoto() { ssh "${opc[@]}" "$USUARIO@$ip" "$@"; }
echo "conectado a $INSTANCIA ($ip)"

# ── 3. o código ─────────────────────────────────────────────────────────────
passo "atualizando o código"
sujo="$(remoto "cd $DIR_APP && git status --porcelain")"
if [ -n "$sujo" ]; then erro "o servidor tem alterações locais não commitadas:
$sujo"; fi
remoto "cd $DIR_APP && git fetch --quiet origin $BRANCH && git pull --ff-only origin $BRANCH"
no_servidor="$(remoto "cd $DIR_APP && git rev-parse --short HEAD")"
[ "$no_servidor" = "$alvo" ] || erro "servidor em $no_servidor, esperado $alvo."
echo "servidor em $no_servidor"

# ── 4. os marts ─────────────────────────────────────────────────────────────
# A LISTA SAI DO `config.py`, e não escrita aqui: config é a fonte única dos
# caminhos (CLAUDE.md, mapa dos documentos). Um mart novo passa a viajar sozinho
# no dia em que a constante nasce; uma lista à mão aqui envelheceria em silêncio,
# e o sintoma seria o app quebrando no restart por um arquivo que ninguém copiou.
if [ "$SO_CODIGO" -eq 1 ]; then
  passo "marts: pulados (--so-codigo)"
else
  passo "sincronizando os marts que o app lê"
  # `while read` e não `mapfile`: o bash 3.2 que vem no macOS não tem `mapfile`,
  # e um deploy que só roda na máquina de quem o escreveu não é um deploy.
  marts=()
  while IFS= read -r linha; do marts+=("$linha"); done < <(python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, ".")
import config
raiz = Path(config.DIR_MARTS).resolve()
vistos = set()
for nome in sorted(dir(config)):
    if not nome.startswith("CAMINHO_") or nome.startswith("CAMINHO_RAW_"):
        continue
    caminho = Path(getattr(config, nome)).resolve()
    if raiz in caminho.parents and caminho.name not in vistos:
        vistos.add(caminho.name)
        print(caminho)
PY
)
  [ "${#marts[@]}" -gt 0 ] || erro "nenhum mart encontrado a partir do config.py."
  for m in "${marts[@]}"; do
    [ -f "$m" ] || erro "mart ausente no local: $m"
  done
  # `--checksum` e não data de modificação: regerar os marts mexe no mtime de
  # todos, e sem ele o deploy reenviaria 58 MB a cada vez para trocar um CSV.
  rsync -avh --checksum --progress \
        -e "ssh ${opc[*]}" \
        "${marts[@]}" "$USUARIO@$ip:$DIR_MARTS_REMOTO/"
fi

# ── 5. o ensaio ─────────────────────────────────────────────────────────────
passo "ensaiando a carga (sem tocar no serviço)"
remoto "cd $DIR_APP && $PYTHON_REMOTO - <<'PY'
import app.api  # noqa: F401  — sobe a API inteira, com os motores que ela importa
from utils import dados
f = dados.carregar_fato()
print(f'fato: {f.shape[0]:,} linhas · {f[\"AREA_ATUACAO\"].nunique()} áreas')
print(f'classificação: {len(dados.carregar_classificacao()):,} cooperados')
PY" || erro "o app NÃO carrega com este código e estes dados. Serviço intocado."

if [ "$ENSAIO" -eq 1 ]; then
  passo "ensaio concluído: nada foi reiniciado (--ensaio)"
  exit 0
fi

# ── 6. o restart, e a prova de que subiu ────────────────────────────────────
passo "reiniciando o serviço"
remoto "sudo systemctl restart $SERVICO"
sleep 6
estado="$(remoto "systemctl is-active $SERVICO" || true)"
[ "$estado" = "active" ] || erro "o serviço está '$estado'. Veja:
  journalctl -u $SERVICO -n 50"
# `NRestarts` cresce quando o systemd está reerguendo um processo que morre: o
# serviço pode estar "active" no instante da pergunta e em laço de reinício.
reinicios="$(remoto "systemctl show $SERVICO --property=NRestarts --value")"
[ "$reinicios" = "0" ] || erro "o serviço reiniciou $reinicios vez(es) sozinho: está em laço."

passo "verificando a aplicação"
remoto "curl -sf -o /dev/null -m 60 http://127.0.0.1:8000/static/inicio.js" \
  || erro "o app não respondeu."
echo "aplicação no ar em $alvo"
