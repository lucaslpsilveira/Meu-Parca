#!/usr/bin/env bash
# Mostra o andamento do treino de uma voz no PC de treino.
# Uso: scripts/status.sh <voz>          (uma vez)
#      watch -n 30 scripts/status.sh <voz>   (atualizando a cada 30 s)
set -euo pipefail
voz="${1:?uso: scripts/status.sh <voz>}"
cd "$(dirname "$0")/.."
source scripts/config.sh

log="$WIN_DIR/logs/${voz}_treino.log"
saida=$(ssh "$WIN_HOST" "powershell -NoProfile -Command \"Get-Content '$log' -Tail 4\"" 2>/dev/null | tr '\r' '\n' | grep -v '^\s*$' || true)
ultima=$(echo "$saida" | grep -o 'epoch=[0-9]*' | tail -1 | cut -d= -f2 || true)
gpu=$(ssh "$WIN_HOST" "nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu --format=csv,noheader" 2>/dev/null | tr -d '\r')
treinando=$(ssh "$WIN_HOST" "powershell -NoProfile -Command \"@(Get-CimInstance Win32_Process -Filter \\\"name='python.exe'\\\" | Where-Object { \$_.CommandLine -match 'core.py (preprocess|extract|train|index)' }).Count\"" 2>/dev/null | tr -d '\r')

echo "Voz: $voz"
if echo "$saida" | grep -q "CONCLUIDO"; then
  echo "Status: CONCLUÍDO ✓"
elif echo "$saida" | grep -q "ERRO"; then
  echo "Status: ERRO, veja o log: $log"
elif [ "${treinando:-0}" = "0" ]; then
  echo "Status: PARADO (nenhum treino rodando; se não concluiu, use continuar.bat $voz)"
else
  echo "Status: treinando"
fi
if [ -n "$ultima" ]; then
  echo "Época: $ultima de $EPOCAS ($(( ultima * 100 / EPOCAS ))%)"
  # ~segundos por época, medidos pelo intervalo entre os dois últimos checkpoints salvos
  seg=$(ssh "$WIN_HOST" "powershell -NoProfile -Command \"\$f=Get-ChildItem '$APPLIO_DIR/logs/$voz/G_*.pth' | Sort-Object LastWriteTime | Select-Object -Last 2; if (\$f.Count -eq 2) { [int]((\$f[1].LastWriteTime - \$f[0].LastWriteTime).TotalSeconds / $SALVAR_A_CADA) }\"" 2>/dev/null | tr -d '\r')
  if [ -n "$seg" ] && [ "$seg" -gt 0 ] && [ "$ultima" -lt "$EPOCAS" ]; then
    resta=$(( (EPOCAS - ultima) * seg ))
    echo "Tempo restante: ~$(( resta / 3600 ))h$(printf %02d $(( resta % 3600 / 60 )))min (previsão: $(date -d "+$resta sec" +%H:%M))"
  fi
fi
echo "GPU: ${gpu:-?}  (uso, memória, temperatura °C)"
