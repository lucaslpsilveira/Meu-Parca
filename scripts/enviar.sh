#!/usr/bin/env bash
# Envia uma voz para o PC de treino (Windows) e mantém tudo sincronizado.
#   1. Monta dataset/<voz>_treino/ com a versão (original/limpo) escolhida no painel, sem os "ruim".
#   2. Copia os .wav novos para <WIN_DIR>\dataset\<voz>\ e apaga lá os que não existem mais aqui.
#   3. Atualiza os scripts de treino (windows/*.bat, TREINO.md) e gera <WIN_DIR>\config.env a partir do .env.
# Uso: scripts/enviar.sh <voz>
set -euo pipefail
voz="${1:?uso: scripts/enviar.sh <voz>}"
cd "$(dirname "$0")/.."
source scripts/config.sh
H="$WIN_HOST"

.venv/bin/python scripts/montar_treino.py "$voz"
local_dir="dataset/${voz}_treino"

ssh "$H" "if not exist $WIN_DIR_BS\\dataset\\$voz mkdir $WIN_DIR_BS\\dataset\\$voz"
ssh "$H" "if not exist $WIN_DIR_BS\\logs mkdir $WIN_DIR_BS\\logs"

# Compara por nome e tamanho: troca de original para limpo também é reenviada
remoto=$(ssh "$H" "powershell -NoProfile -Command \"Get-ChildItem '$WIN_DIR/dataset/$voz' -Filter *.wav | ForEach-Object { \$_.Name + ' ' + \$_.Length }\"" | tr -d '\r' | sort)
locais=$(cd "$local_dir" && for f in *.wav; do echo "$f $(stat -c %s "$f")"; done | sort)

enviar=$(comm -13 <(echo "$remoto") <(echo "$locais") | awk '{print $1}' | grep . || true)
apagar=$(comm -23 <(echo "$remoto" | awk '{print $1}' | sort -u) <(echo "$locais" | awk '{print $1}' | sort -u) | grep . || true)

for f in $apagar; do
  ssh "$H" "del $WIN_DIR_BS\\dataset\\$voz\\$f" && echo "apagado no Windows: $f"
done
if [ -n "$enviar" ]; then
  (cd "$local_dir" && scp -q $enviar "$H:$WIN_DIR/dataset/$voz/")
  echo "enviados: $(echo "$enviar" | wc -l)"
fi

# Scripts de treino e configuração. Nunca sobrescrever um .bat em execução: o cmd.exe lê o
# arquivo aos poucos e se perde se ele mudar no meio do treino.
treinando=$(ssh "$H" "powershell -NoProfile -Command \"@(Get-CimInstance Win32_Process -Filter \\\"name='python.exe'\\\" | Where-Object { \$_.CommandLine -match 'core.py (preprocess|extract|train|index)' }).Count\"" | tr -d '\r')
if [ "${treinando:-0}" != "0" ]; then
  echo "Treino em andamento no Windows: scripts e config.env NÃO foram atualizados (rode de novo depois)."
  n=$(ssh "$H" "dir /b $WIN_DIR_BS\\dataset\\$voz\\*.wav" | grep -c wav || true)
  echo "Windows: $n wav em $WIN_DIR/dataset/$voz"
  exit 0
fi
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
for f in windows/*.bat; do sed 's/\r*$/\r/' "$f" > "$tmp/$(basename "$f")"; done
cat > "$tmp/config.env" <<EOF
# Gerado por scripts/enviar.sh a partir do .env do notebook. Edite o .env lá, não aqui.
APPLIO=$APPLIO_DIR_BS
SR=$SAMPLE_RATE
EPOCAS_PADRAO=$EPOCAS
BATCH_PADRAO=$BATCH
SALVAR=$SALVAR_A_CADA
EOF
sed -i 's/$/\r/' "$tmp/config.env"
scp -q "$tmp"/*.bat "$tmp/config.env" windows/TREINO.md "$H:$WIN_DIR/"

n=$(ssh "$H" "dir /b $WIN_DIR_BS\\dataset\\$voz\\*.wav" | grep -c wav || true)
echo "Windows: $n wav em $WIN_DIR/dataset/$voz · scripts e config.env atualizados"
echo "Para treinar: no Windows, rode $WIN_DIR_BS\\treinar.bat $voz   (ou peça ao Claude)"
