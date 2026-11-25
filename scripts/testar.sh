#!/usr/bin/env bash
# Gera um áudio de teste com a voz treinada, no PC de treino, e traz para testes/.
#
#   scripts/testar.sh <voz> "texto a falar"          texto → voz sintética (Edge TTS) → voz treinada
#   scripts/testar.sh <voz> minha_gravacao.ogg       áudio → voz treinada (mantém ritmo e entonação)
#
# Opções por variável de ambiente:
#   PITCH=0       semitons (+ mais agudo, - mais grave); ajuste se a sua voz for bem diferente da treinada
#   TTS_VOZ=pt-BR-AntonioNeural   voz do Edge TTS (precisa de internet no PC de treino)
#   TTS_VELOCIDADE=0   velocidade da fala no modo texto, em % (-100 a 100; ex.: 20 = 20% mais rápido); padrão: .env
#   INDEX_RATE=0.75  PROTECT=0.33
#   FORMATO=mp3   formato do arquivo final em testes/ (mp3 | ogg | wav); padrão: TESTE_FORMATO do .env
set -euo pipefail
voz="${1:?uso: scripts/testar.sh <voz> \"texto\" | arquivo_de_audio}"
entrada="${2:?informe um texto entre aspas ou um arquivo de áudio}"
cd "$(dirname "$0")/.."
source scripts/config.sh
PITCH="${PITCH:-0}"; TTS_VOZ="${TTS_VOZ:-pt-BR-AntonioNeural}"; TTS_VELOCIDADE="${TTS_VELOCIDADE:-0}"
INDEX_RATE="${INDEX_RATE:-0.75}"; PROTECT="${PROTECT:-0.33}"
FORMATO="${FORMATO:-${TESTE_FORMATO:-mp3}}"
H="$WIN_HOST"; W="$WIN_DIR_BS"; A="$APPLIO_DIR_BS"

# Modelo mais recente da voz (<voz>_<N>e_<passos>s.pth) e índice
pth=$(ssh "$H" "powershell -NoProfile -Command \"Get-ChildItem '$APPLIO_DIR/logs/$voz/${voz}_*e_*s.pth' | Sort-Object LastWriteTime | Select-Object -Last 1 -ExpandProperty FullName\"" | tr -d '\r')
idx="$A\\logs\\$voz\\$voz.index"
[ -n "$pth" ] || { echo "Nenhum modelo treinado de '$voz' encontrado em $APPLIO_DIR/logs/$voz"; exit 1; }

stamp=$(date +%Y%m%d_%H%M%S)
ssh "$H" "if not exist $W\\testes mkdir $W\\testes"
comum="--pth-path \"$pth\" --index-path \"$idx\" --pitch $PITCH --index-rate $INDEX_RATE --protect $PROTECT --f0-method rmvpe --export-format WAV"

if [ -f "$entrada" ]; then
  ext="${entrada##*.}"
  scp -q "$entrada" "$H:$WIN_DIR/testes/entrada_$stamp.$ext"
  saida="${voz}_${stamp}_de_audio.wav"
  ssh "$H" "cd /d $A && env\\python.exe core.py infer --input-path $W\\testes\\entrada_$stamp.$ext --output-path $W\\testes\\$saida $comum" 2>&1 | tr '\r' '\n' | grep -E 'completed|Error|error' || true
else
  # Texto vai por arquivo para não sofrer com aspas e acentos na linha de comando do Windows
  printf '%s' "$entrada" > "/tmp/texto_$stamp.txt"
  scp -q "/tmp/texto_$stamp.txt" "$H:$WIN_DIR/testes/texto_$stamp.txt"; rm -f "/tmp/texto_$stamp.txt"
  saida="${voz}_${stamp}_de_texto.wav"
  ssh "$H" "cd /d $A && env\\python.exe core.py tts --tts-file $W\\testes\\texto_$stamp.txt --tts-text \"\" --tts-voice $TTS_VOZ --tts-rate $TTS_VELOCIDADE --output-tts-path $W\\testes\\tts_$stamp.wav --output-rvc-path $W\\testes\\$saida $comum" 2>&1 | tr '\r' '\n' | grep -E 'completed|Error|error' || true
fi

mkdir -p testes
scp -q "$H:$WIN_DIR/testes/$saida" testes/
final="testes/$saida"
case "$FORMATO" in
  mp3) final="${final%.wav}.mp3"; ffmpeg -nostdin -v error -y -i "testes/$saida" -c:a libmp3lame -b:a 192k "$final" && rm "testes/$saida" ;;
  ogg) final="${final%.wav}.ogg"; ffmpeg -nostdin -v error -y -i "testes/$saida" -c:a libopus -b:a 64k "$final" && rm "testes/$saida" ;;
esac
echo "Pronto: $final"
echo "Ouvir: xdg-open $final"
