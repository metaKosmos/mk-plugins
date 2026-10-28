#!/usr/bin/env bash
# Sincroniza o motor copiado (motor/) com uma versão do plugin vanta-produto.
#
# Uso: scripts/sincronizar-motor.sh <clone do vanta-plugins> <ref>
#   <clone>  pasta de um clone (ou worktree) do repositório 214SS/vanta-plugins
#   <ref>    SHA, tag ou branch daquele clone
#
# Substitui motor/ pelo conteúdo de plugins/vanta-produto naquele ref (sem o
# .claude-plugin, que é o do plugin de origem) e regrava motor/ORIGEM.json.
# Mostra antes a lista de arquivos que mudam. Mesmo SHA: zero mudança.
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "uso: $0 <clone do vanta-plugins> <ref>" >&2
  exit 2
fi

CLONE="$1"
REF="$2"
CAMINHO="plugins/vanta-produto"
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MOTOR="$AQUI/motor"

git -C "$CLONE" rev-parse --git-dir >/dev/null 2>&1 || { echo "erro: $CLONE não é um clone git" >&2; exit 1; }
SHA="$(git -C "$CLONE" rev-parse --verify "$REF^{commit}")" || { echo "erro: ref $REF não existe em $CLONE" >&2; exit 1; }
git -C "$CLONE" cat-file -e "$SHA:$CAMINHO" 2>/dev/null || { echo "erro: $CAMINHO não existe em $SHA" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

git -C "$CLONE" archive "$SHA" "$CAMINHO" | tar -x -C "$TMP"
NOVO="$TMP/$CAMINHO"
rm -rf "$NOVO/.claude-plugin"

VERSAO="$(git -C "$CLONE" show "$SHA:$CAMINHO/.claude-plugin/plugin.json" | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>console.log(JSON.parse(s).version))')"

ANTERIOR="desconhecido"
if [ -f "$MOTOR/ORIGEM.json" ]; then
  ANTERIOR="$(node -e 'console.log(JSON.parse(require("fs").readFileSync(process.argv[1],"utf8")).sha)' "$MOTOR/ORIGEM.json")"
fi
echo "motor atual:  $ANTERIOR"
echo "motor novo:   $SHA (versão $VERSAO)"
echo "--- arquivos que mudam (ORIGEM.json fica de fora desta lista) ---"

# diff -rq do motor atual contra o novo, sem o ORIGEM.json
MUDANCAS=0
if [ -d "$MOTOR" ]; then
  SAIDA="$(diff -rq --exclude=ORIGEM.json "$MOTOR" "$NOVO" || true)"
  if [ -n "$SAIDA" ]; then
    MUDANCAS="$(printf '%s\n' "$SAIDA" | wc -l | tr -d ' ')"
    printf '%s\n' "$SAIDA" | sed -e "s#$MOTOR#motor#g" -e "s#$NOVO#novo#g"
  fi
fi
echo "--- $MUDANCAS arquivo(s) com diferença ---"

rm -rf "$MOTOR"
mkdir -p "$MOTOR"
cp -R "$NOVO/." "$MOTOR/"

node -e '
const fs = require("fs");
const [arq, sha, versao, data] = process.argv.slice(1);
const o = { repo: "214SS/vanta-plugins", caminho: "plugins/vanta-produto", sha, versao, copiado_em: data };
fs.writeFileSync(arq, JSON.stringify(o, null, 2) + "\n");
' "$MOTOR/ORIGEM.json" "$SHA" "$VERSAO" "$(date +%F)"

echo "motor/ORIGEM.json regravado: $SHA"
