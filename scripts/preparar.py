"""Converte os áudios de Audios/<voz>/ para o dataset de treino, removendo duplicatas.

Uso: .venv/bin/python scripts/preparar.py <voz> [--simular]

- Aceita qualquer formato que o ffmpeg leia (.opus, .ogg, .mp3, .m4a, .wav...).
- Gera dataset/<voz>/<voz>_NNN.wav (mono, 16-bit, DATASET_SR do .env) e dataset/<voz>_mapa.csv.
- Incremental: só processa originais que ainda não estão no mapa; a numeração continua.
- Duplicatas (mesmo arquivo, ou o mesmo áudio reencaminhado/reencodado) e áudios mais
  longos que MAX_DURACAO (geralmente junções de vários áudios) vão para Audios/_descartados/<voz>/.
- --simular mostra o que seria feito, sem mudar nada.
"""
import csv
import hashlib
import io
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CFG, ROOT  # noqa: E402

EXTENSOES = {".opus", ".ogg", ".oga", ".mp3", ".m4a", ".aac", ".wav", ".flac", ".webm", ".amr"}
SR_CMP = 8000          # taxa usada só para comparar áudios
LIMIAR_CORR = 0.98     # correlação acima disso = mesmo áudio
TOL_DURACAO = 0.15     # segundos de diferença tolerada entre duplicatas


def duracao_e_bitrate(f):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,bit_rate", "-of", "csv=p=0", str(f)],
        capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout.strip().split(",")
    dur = float(out[0]) if out and out[0] not in ("", "N/A") else 0.0
    br = int(out[1]) if len(out) > 1 and out[1].isdigit() else 0
    return dur, br


def pcm(f):
    b = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(f), "-ac", "1", "-ar", str(SR_CMP),
                        "-f", "s16le", "-"], capture_output=True, stdin=subprocess.DEVNULL).stdout
    return np.frombuffer(b, np.int16).astype(np.float32)


def mesmo_audio(a, b):
    n = min(len(a), len(b)) - SR_CMP // 4
    if n <= SR_CMP // 2:
        return False
    melhor = 0.0
    for s in range(0, SR_CMP // 4, 20):       # tolera até 250 ms de deslocamento
        for x, y in ((a[s:s + n], b[:n]), (a[:n], b[s:s + n])):
            if x.std() and y.std():
                melhor = max(melhor, abs(float(np.corrcoef(x, y)[0, 1])))
        if melhor > LIMIAR_CORR:
            return True
    return False


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    voz, simular = sys.argv[1], "--simular" in sys.argv
    origem = ROOT / "Audios" / voz
    destino = ROOT / "dataset" / voz
    descarte = ROOT / "Audios" / "_descartados" / voz
    mapa_csv = ROOT / "dataset" / f"{voz}_mapa.csv"
    sr = CFG["DATASET_SR"]
    max_dur = float(CFG["MAX_DURACAO"])

    mapa = []
    if mapa_csv.exists():
        mapa = [r for r in csv.reader(io.StringIO(mapa_csv.read_text(encoding="utf-8")))][1:]
    ja_mapeados = {r[1] for r in mapa if len(r) > 1}
    prox = max([int(r[0].rsplit("_", 1)[1].split(".")[0]) for r in mapa] or [0]) + 1

    arquivos = sorted(f for f in origem.iterdir() if f.is_file() and f.suffix.lower() in EXTENSOES)
    novos = [f for f in arquivos if f.name not in ja_mapeados]
    print(f"{len(arquivos)} áudios em {origem.relative_to(ROOT)}, {len(novos)} novos")

    # Áudios já no dataset entram na comparação (para não aceitar de novo algo já convertido)
    existentes = [(destino / r[0], None) for r in mapa if (destino / r[0]).exists()]
    info = {}
    for f, _ in existentes:
        info[f] = (duracao_e_bitrate(f)[0], 10**9, hashlib.md5(f.read_bytes()).hexdigest())
    for f in novos:
        d, br = duracao_e_bitrate(f)
        info[f] = (d, br, hashlib.md5(f.read_bytes()).hexdigest())

    descartar = {}
    # Maior bitrate primeiro: entre duplicatas, fica a de melhor qualidade
    candidatos = sorted(novos, key=lambda f: -info[f][1])
    aceitos = [f for f, _ in existentes]
    cache = {}
    for f in candidatos:
        d, br, h = info[f]
        if d <= 0.3:
            descartar[f] = "vazio ou ilegível"
            continue
        if d > max_dur:
            descartar[f] = f"longo demais ({d:.0f}s > MAX_DURACAO), provável junção de áudios"
            continue
        dup = None
        for g in aceitos:
            dg, _, hg = info[g]
            if h == hg:
                dup = g
                break
            if abs(d - dg) <= TOL_DURACAO:
                if f not in cache:
                    cache[f] = pcm(f)
                if g not in cache:
                    cache[g] = pcm(g)
                if mesmo_audio(cache[f], cache[g]):
                    dup = g
                    break
        if dup:
            descartar[f] = f"duplicata de {dup.name}"
        else:
            aceitos.append(f)

    converter = [f for f in novos if f not in descartar]
    for f, motivo in descartar.items():
        print(f"  descartar: {f.name}  ({motivo})")
    print(f"  converter: {len(converter)} áudios")
    if simular:
        return

    destino.mkdir(parents=True, exist_ok=True)
    for f in sorted(converter):
        nome = f"{voz}_{prox:03d}.wav"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(f), "-ac", "1", "-ar", sr,
                        "-c:a", "pcm_s16le", str(destino / nome)], check=True, stdin=subprocess.DEVNULL)
        mapa.append([nome, f.name])
        prox += 1
    if descartar:
        descarte.mkdir(parents=True, exist_ok=True)
        for f in descartar:
            shutil.move(str(f), str(descarte / f.name))

    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["arquivo_wav", "original"])
    w.writerows(mapa)
    mapa_csv.write_text(out.getvalue(), encoding="utf-8")
    total = sum(duracao_e_bitrate(p)[0] for p in destino.glob("*.wav"))
    print(f"OK: {len(list(destino.glob('*.wav')))} áudios, {total / 60:.1f} min em {destino.relative_to(ROOT)}")
    if total < 600:
        print("Aviso: menos de 10 min de áudio. O ideal para RVC é 10 a 30 min.")


if __name__ == "__main__":
    main()
