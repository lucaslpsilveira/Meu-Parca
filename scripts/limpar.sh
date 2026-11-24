#!/usr/bin/env bash
# Separa a voz do ruído/música com Demucs (CPU) e gera dataset/<voz>_limpo/ no mesmo
# formato do dataset (WAV mono 48 kHz 16-bit, mesmos nomes). Não mexe no dataset original.
# Uso: scripts/limpar.sh joao
set -euo pipefail
voz="${1:?uso: scripts/limpar.sh <voz>}"
cd "$(dirname "$0")/.."
src="dataset/$voz"
dst="dataset/${voz}_limpo"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$dst"

pendentes=()
for f in "$src"/*.wav; do
  [ -f "$dst/$(basename "$f")" ] || pendentes+=("$f")
done
echo "${#pendentes[@]} arquivos para limpar"
[ ${#pendentes[@]} -eq 0 ] && exit 0

.venv/bin/python -m demucs --two-stems vocals -n htdemucs -o "$tmp" "${pendentes[@]}"

for f in "${pendentes[@]}"; do
  n="$(basename "$f" .wav)"
  ffmpeg -nostdin -v error -y -i "$tmp/htdemucs/$n/vocals.wav" -ac 1 -ar 48000 -c:a pcm_s16le "$dst/$n.wav"
done
echo "OK -> $dst ($(ls "$dst" | wc -l) arquivos)"
