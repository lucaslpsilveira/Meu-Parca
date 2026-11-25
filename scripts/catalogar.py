"""Tela local para ouvir, corrigir e marcar os áudios transcritos.

Uso: .venv/bin/python scripts/catalogar.py joao
     .venv/bin/python scripts/catalogar.py joao --remover joao_007.wav
Abre http://localhost:8765 — as alterações salvam sozinhas em catalogo/<voz>.json.
Remover um áudio apaga o .wav do dataset, tira do catálogo e do mapa, e move o
original de Audios/<voz>/ para Audios/_descartados/<voz>/ (para não voltar numa
próxima conversão). Depois rode scripts/enviar.sh <voz> para sincronizar o Windows.
"""
import csv
import io
import json
import shutil
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CFG, ROOT  # noqa: E402

if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
    sys.exit("Uso: catalogar.py <voz> [--remover <arquivo>.wav]")
voz = sys.argv[1]
PORTA = int(CFG["PORTA_CATALOGO"])
CATALOGO = ROOT / "catalogo" / f"{voz}.json"
DATASET = ROOT / "dataset" / voz
LIMPO = ROOT / "dataset" / f"{voz}_limpo"
MAPA = ROOT / "dataset" / f"{voz}_mapa.csv"
ORIGINAIS = ROOT / "Audios" / voz
DESCARTE = ROOT / "Audios" / "_descartados" / voz


def ler_catalogo():
    return json.loads(CATALOGO.read_text(encoding="utf-8"))


def gravar_catalogo(cat):
    tmp = CATALOGO.with_suffix(".tmp")
    tmp.write_text(json.dumps(cat, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(CATALOGO)


def remover(arquivo, motivo=""):
    arquivo = Path(arquivo).name
    cat = ler_catalogo()
    item = next((i for i in cat["itens"] if i["arquivo"] == arquivo), None)

    # mapa: descobre o original e tira a linha
    original = ""
    if MAPA.exists():
        linhas = list(csv.reader(io.StringIO(MAPA.read_text(encoding="utf-8"))))
        resto = [l for l in linhas if not (l and l[0] == arquivo)]
        original = next((l[1] for l in linhas if l and l[0] == arquivo), "")
        out = io.StringIO()
        csv.writer(out, lineterminator="\n").writerows(resto)
        MAPA.write_text(out.getvalue(), encoding="utf-8")

    if original and (ORIGINAIS / original).is_file():
        DESCARTE.mkdir(parents=True, exist_ok=True)
        shutil.move(str(ORIGINAIS / original), str(DESCARTE / original))

    (DATASET / arquivo).unlink(missing_ok=True)
    (LIMPO / arquivo).unlink(missing_ok=True)

    cat["itens"] = [i for i in cat["itens"] if i["arquivo"] != arquivo]
    cat.setdefault("removidos", []).append({
        "arquivo": arquivo, "original": original, "motivo": motivo,
        "texto": item["texto"] if item else "",
    })
    gravar_catalogo(cat)
    return original

PAGINA = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Catálogo de falas</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--fg:#1d1d1f;--mut:#6b6b70;--line:#e3e1dc;--acc:#2f6fec;
--piada:#e8883a;--bordao:#7b5ce0;--frase:#1f9d6b;--ruim:#b9b9be}
@media (prefers-color-scheme:dark){:root{--bg:#161618;--card:#1f1f22;--fg:#ececee;--mut:#9a9aa0;--line:#333338}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif}
header{position:sticky;top:0;z-index:2;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 16px}
h1{font-size:18px;margin:0 0 8px}.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.bar input{flex:1;min-width:180px;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg)}
.f{border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:999px;padding:5px 11px;cursor:pointer;font-size:13px}
.f.on{background:var(--fg);color:var(--bg)}#st{color:var(--mut);font-size:13px;margin-left:auto}
main{max-width:860px;margin:0 auto;padding:12px 16px 60px}
.c{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px;margin:10px 0}
.c.ruim{opacity:.55}.top{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.nm{font-weight:600;font-size:13px}.du{color:var(--mut);font-size:12px}audio{height:32px;flex:1;min-width:200px}
textarea{width:100%;margin-top:8px;border:1px solid var(--line);border-radius:8px;padding:8px;font:inherit;background:transparent;color:var(--fg);resize:vertical}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.t{border:1.5px solid var(--line);background:transparent;color:var(--fg);border-radius:999px;padding:4px 10px;cursor:pointer;font-size:13px}
.t.on[data-t=piada]{background:var(--piada);border-color:var(--piada);color:#fff}
.t.on[data-t=bordao]{background:var(--bordao);border-color:var(--bordao);color:#fff}
.t.on[data-t=complemento]{background:var(--frase);border-color:var(--frase);color:#fff}
.t.on[data-t=tocar_original]{background:var(--acc);border-color:var(--acc);color:#fff}
.t.on[data-t=ruim]{background:var(--ruim);border-color:var(--ruim);color:#222}
.notas{margin-top:6px;min-height:34px;font-size:13px}
.ok{margin-left:auto;border:1px solid var(--line);background:transparent;color:var(--frase);border-radius:8px;padding:4px 10px;cursor:pointer;font-size:12px}
.ok.on{background:var(--frase);color:#fff;border-color:var(--frase)}
.del{border:1px solid var(--line);background:transparent;color:#c0392b;border-radius:8px;padding:4px 10px;cursor:pointer;font-size:12px}
.del:hover{background:#c0392b;color:#fff;border-color:#c0392b}
.ver{display:flex;gap:6px;align-items:center;margin-top:8px;font-size:13px;color:var(--mut)}
.v{border:1.5px solid var(--line);background:transparent;color:var(--fg);border-radius:8px;padding:3px 10px;cursor:pointer;font-size:13px}
.v.on{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.ajuda{color:var(--mut);font-size:13px;margin:6px 0 0}
</style></head><body>
<header><h1>Catálogo de falas — <span id="voz"></span></h1>
<div class="bar"><input id="q" placeholder="Buscar no texto…">
<button class="f on" data-f="_nao_avaliados">Não avaliados</button><button class="f" data-f="">Todos</button><button class="f" data-f="_sem">Sem tag</button>
<button class="f" data-f="piada">Piadas</button><button class="f" data-f="bordao">Bordões</button>
<button class="f" data-f="complemento">Complementos</button><button class="f" data-f="tocar_original">Tocar original</button><button class="f" data-f="_comparar">Comparar limpo</button>
<span id="st"></span></div>
<p class="ajuda"><b>Piada</b>: algo engraçado dele · <b>Bordão</b>: expressão que ele repete · <b>Complemento</b>: frase para o assistente usar de vez em quando · <b>Tocar original</b>: o assistente pode tocar este áudio real · <b>Ruim</b>: ruído/ininteligível, não usar (fica fora do treino). · <b>✓ Avaliado</b>: tira a fala da lista "Não avaliados" quando terminar. · <b>Treinar com</b>: ouça os dois players e escolha a versão que vai para o treino (padrão: original).</p>
</header><main id="lista"></main>
<script>
const TAGS=[["piada","Piada"],["bordao","Bordão"],["complemento","Complemento"],["tocar_original","Tocar original"],["ruim","Ruim"]];
let cat,filtro="_nao_avaliados",timer;
const st=document.getElementById("st");
async function carregar(){cat=await (await fetch("api/catalogo")).json();document.getElementById("voz").textContent=cat.voz;render();}
function salvar(){st.textContent="salvando…";clearTimeout(timer);timer=setTimeout(async()=>{
 const r=await fetch("api/catalogo",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(cat)});
 st.textContent=r.ok?"salvo ✓":"ERRO ao salvar";resumo();},400);}
function resumo(){const n=k=>cat.itens.filter(i=>i.tags.includes(k)).length;
 const sem=cat.itens.filter(i=>!i.tags.length).length;
 if(!st.textContent.startsWith("salvando"))st.textContent=`${cat.itens.length} falas · ${cat.itens.filter(i=>!i.avaliado).length} não avaliadas · ${sem} sem tag · ${n("piada")} piadas · ${n("bordao")} bordões · ${cat.itens.filter(i=>i.versao==="limpo").length} limpos · ${cat.itens.filter(i=>i.limpo&&!i.versao).length} p/ comparar`;}
function render(){const q=document.getElementById("q").value.toLowerCase();const L=document.getElementById("lista");L.innerHTML="";
 cat.itens.forEach(it=>{
  if(q&&!(it.texto+" "+it.notas).toLowerCase().includes(q))return;
  if(filtro==="_nao_avaliados"&&it.avaliado)return;
  if(filtro==="_sem"&&it.tags.length)return;
  if(filtro==="_comparar"&&!(it.limpo&&!it.versao))return;
  if(filtro&&filtro!=="_sem"&&!it.tags.includes(filtro))return;
  const c=document.createElement("div");c.className="c"+(it.tags.includes("ruim")?" ruim":"");
  c.innerHTML=`<div class="top"><span class="nm"></span><span class="du">${it.duracao}s</span><audio controls preload="none" src="audio/${encodeURIComponent(it.arquivo)}"></audio>${it.limpo?`<span class="du">limpo:</span><audio controls preload="none" src="limpo/${encodeURIComponent(it.arquivo)}"></audio>`:""}<button class="ok" title="Marca esta fala como avaliada">✓ Avaliado</button><button class="del" title="Apaga do dataset (não é desta voz, ruído…)">Excluir</button></div>
  <textarea rows="2"></textarea><div class="tags"></div>${it.limpo?`<div class="ver">Treinar com: <button class="v" data-v="original">Original</button><button class="v" data-v="limpo">Limpo</button><span class="vst"></span></div>`:""}<textarea class="notas" rows="1" placeholder="Notas (contexto da piada, quando usar…)"></textarea>`;
  c.querySelector(".nm").textContent=it.arquivo;
  const [tx,nt]=c.querySelectorAll("textarea");tx.value=it.texto;nt.value=it.notas||"";
  tx.oninput=()=>{it.texto=tx.value;salvar();};nt.oninput=()=>{it.notas=nt.value;salvar();};
  const ok=c.querySelector(".ok");ok.classList.toggle("on",!!it.avaliado);
  ok.onclick=()=>{it.avaliado=!it.avaliado;ok.classList.toggle("on",it.avaliado);salvar();
   if(it.avaliado&&filtro==="_nao_avaliados"){c.style.transition="opacity .3s";c.style.opacity="0";setTimeout(()=>c.remove(),300);}};
  c.querySelector(".del").onclick=async()=>{
   const motivo=prompt(`Excluir ${it.arquivo} do dataset?\n"${it.texto.slice(0,80)}"\n\nMotivo (opcional), ex.: não é ${cat.voz}, ruído…`,"");
   if(motivo===null)return;
   const r=await fetch("api/remover",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({arquivo:it.arquivo,motivo})});
   if(!r.ok){st.textContent="ERRO ao excluir";return;}
   cat.itens=cat.itens.filter(x=>x!==it);c.remove();st.textContent=`${it.arquivo} excluído ✓`;setTimeout(resumo,1500);};
  c.querySelectorAll(".v").forEach(b=>{b.classList.toggle("on",(it.versao||"original")===b.dataset.v);
   b.onclick=()=>{it.versao=b.dataset.v;const s2=c.querySelector(".vst");if(s2)s2.textContent="";c.querySelectorAll(".v").forEach(x=>x.classList.toggle("on",x===b));salvar();};});
  const vst=c.querySelector(".vst");if(vst&&!it.versao)vst.textContent="(não avaliado)";
  const tg=c.querySelector(".tags");
  TAGS.forEach(([k,lbl])=>{const b=document.createElement("button");b.className="t"+(it.tags.includes(k)?" on":"");b.dataset.t=k;b.textContent=lbl;
   b.onclick=()=>{it.tags=it.tags.includes(k)?it.tags.filter(x=>x!==k):[...it.tags,k];b.classList.toggle("on");c.classList.toggle("ruim",it.tags.includes("ruim"));salvar();};tg.appendChild(b);});
  L.appendChild(c);});
 resumo();}
document.getElementById("q").oninput=render;
document.querySelectorAll(".f").forEach(b=>b.onclick=()=>{document.querySelectorAll(".f").forEach(x=>x.classList.remove("on"));b.classList.add("on");filtro=b.dataset.f;render();});
carregar();
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._send(200, PAGINA.encode(), "text/html; charset=utf-8")
        if self.path == "/api/catalogo":
            cat = ler_catalogo()
            for i in cat["itens"]:
                i["limpo"] = (LIMPO / i["arquivo"]).is_file()
            return self._send(200, json.dumps(cat, ensure_ascii=False).encode(), "application/json; charset=utf-8")
        if self.path.startswith("/limpo/"):
            f = LIMPO / Path(unquote(self.path[7:])).name
            if f.is_file():
                return self._send(200, f.read_bytes(), "audio/wav")
        if self.path.startswith("/audio/"):
            nome = Path(unquote(self.path[7:])).name  # impede sair da pasta
            f = DATASET / nome
            if f.is_file():
                return self._send(200, f.read_bytes(), "audio/wav")
        self._send(404, b"nao encontrado", "text/plain")

    def do_POST(self):
        dados = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/api/remover":
            original = remover(dados["arquivo"], dados.get("motivo", ""))
            return self._send(200, json.dumps({"original": original}).encode(), "application/json")
        if self.path != "/api/catalogo":
            return self._send(404, b"", "text/plain")
        # Uma aba antiga não pode ressuscitar áudios já removidos
        atual = ler_catalogo()
        dados["itens"] = [i for i in dados["itens"] if (DATASET / i["arquivo"]).is_file()]
        marcados = {i["arquivo"]: i["avaliado"] for i in atual["itens"] if "avaliado" in i}
        for i in dados["itens"]:
            i.pop("limpo", None)
            # Aba aberta antes do botão "Avaliado" existir não apaga a marcação
            if "avaliado" not in i and i["arquivo"] in marcados:
                i["avaliado"] = marcados[i["arquivo"]]
        dados["removidos"] = atual.get("removidos", [])
        gravar_catalogo(dados)
        self._send(200, b"ok", "text/plain")


if __name__ == "__main__":
    if not CATALOGO.exists():
        sys.exit(f"Catálogo não encontrado: {CATALOGO}. Rode antes scripts/transcrever.py {voz}")
    if "--remover" in sys.argv:
        alvo = sys.argv[sys.argv.index("--remover") + 1]
        print(f"Removido {alvo} (original: {remover(alvo, 'linha de comando') or '?'})")
        sys.exit(0)
    srv = ThreadingHTTPServer(("127.0.0.1", PORTA), H)
    url = f"http://localhost:{PORTA}"
    print(f"Catálogo de {voz}: {url}  (Ctrl+C para sair)")
    webbrowser.open(url)
    srv.serve_forever()
