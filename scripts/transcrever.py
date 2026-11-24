"""Transcreve os WAVs de dataset/<voz>/ e gera catalogo/<voz>.json.

Uso: .venv/bin/python scripts/transcrever.py <voz> [modelo]   (padrão: WHISPER_MODELO do .env)
Mantém as tags já existentes no catálogo (só transcreve arquivos novos).
"""
import json
import sys
import time
from pathlib import Path

from faster_whisper import WhisperModel

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CFG, ROOT  # noqa: E402

voz = sys.argv[1]
modelo = sys.argv[2] if len(sys.argv) > 2 else CFG["WHISPER_MODELO"]

dataset = ROOT / "dataset" / voz
saida = ROOT / "catalogo" / f"{voz}.json"
saida.parent.mkdir(exist_ok=True)

catalogo = json.loads(saida.read_text(encoding="utf-8")) if saida.exists() else {"voz": voz, "itens": []}
ja = {i["arquivo"] for i in catalogo["itens"]}

mapa = {}
mapa_csv = ROOT / "dataset" / f"{voz}_mapa.csv"
if mapa_csv.exists():
    for linha in mapa_csv.read_text(encoding="utf-8").splitlines()[1:]:
        wav, orig = linha.split(",", 1)
        mapa[wav] = orig.strip('"')

arquivos = [f for f in sorted(dataset.glob("*.wav")) if f.name not in ja]
print(f"{len(arquivos)} arquivos para transcrever com {modelo}", flush=True)
if not arquivos:
    sys.exit(0)

model = WhisperModel(modelo, device="cpu", compute_type="int8")
for n, f in enumerate(arquivos, 1):
    t0 = time.time()
    segs, info = model.transcribe(str(f), language=CFG["IDIOMA"], vad_filter=True, beam_size=5)
    texto = " ".join(s.text.strip() for s in segs).strip()
    catalogo["itens"].append({
        "arquivo": f.name,
        "original": mapa.get(f.name, ""),
        "duracao": round(info.duration, 1),
        "texto": texto,
        "tags": [],
        "notas": "",
    })
    print(f"[{n}/{len(arquivos)}] {f.name} ({time.time()-t0:.0f}s): {texto[:80]}", flush=True)
    saida.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2), encoding="utf-8")

catalogo["itens"].sort(key=lambda i: i["arquivo"])
saida.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"OK -> {saida}")
