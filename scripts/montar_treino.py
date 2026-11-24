"""Monta dataset/<voz>_treino/ com a versão escolhida de cada áudio no painel.

Uso: .venv/bin/python scripts/montar_treino.py <voz>

Para cada fala do catálogo: usa o limpo se você escolheu "Limpo" no painel (e ele existe),
senão o original; falas marcadas "ruim" ficam de fora. Sem catálogo, usa todos os originais.
Chamado automaticamente pelo scripts/enviar.sh.
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import ROOT  # noqa: E402

voz = sys.argv[1]
orig = ROOT / "dataset" / voz
limpo = ROOT / "dataset" / f"{voz}_limpo"
saida = ROOT / "dataset" / f"{voz}_treino"
catalogo = ROOT / "catalogo" / f"{voz}.json"

itens = {f.name: {} for f in sorted(orig.glob("*.wav"))}
if catalogo.exists():
    for i in json.loads(catalogo.read_text(encoding="utf-8"))["itens"]:
        if i["arquivo"] in itens:
            itens[i["arquivo"]] = i

if saida.exists():
    shutil.rmtree(saida)
saida.mkdir(parents=True)
n_limpo = n_ruim = 0
for nome, it in itens.items():
    if "ruim" in it.get("tags", []):
        n_ruim += 1
        continue
    src = orig / nome
    if it.get("versao") == "limpo" and (limpo / nome).is_file():
        src = limpo / nome
        n_limpo += 1
    shutil.copy2(src, saida / nome)

total = len(list(saida.glob("*.wav")))
print(f"{saida.relative_to(ROOT)}: {total} áudios ({n_limpo} limpos, {total - n_limpo} originais, {n_ruim} 'ruim' fora)")
