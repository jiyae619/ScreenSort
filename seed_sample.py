#!/usr/bin/env python3
"""seed_sample.py <batch> [n=15] — COLD-START bootstrap for brand-new users (no history).
Picks ~n diverse sample screenshots and builds a tiny labeler so you can teach the triage
your taste in ~2 minutes. Label them → Download → ~/Downloads/pilot-<batch>-seed.json, which
make_triage uses as calibration (and recat seeds as your manual labels). No Photos access."""
import sys, os, json, webbrowser
sys.path.insert(0, os.path.dirname(__file__))
from lib import paths, PREV, CATEGORIES

def pick(items, n, dd, sens):
    """~n items with text, non-dup, non-sensitive, spread evenly across date order."""
    pool = [x for x in sorted(items, key=lambda z: z.get("date") or "")
            if x["uuid"] not in dd and x["uuid"] not in sens and x.get("wc", 0) >= 8]
    if len(pool) <= n:
        return pool
    step = len(pool) / n
    return [pool[int(i * step)] for i in range(n)]

def main():
    if len(sys.argv) < 2: sys.exit("usage: seed_sample.py <batch> [n]")
    batch = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    P = paths(batch)
    if not os.path.exists(P["export"]):
        sys.exit(f"✗ no export for {batch}. Run `pilot {batch}` first.")
    items = json.load(open(P["export"]))["screenshots"]
    dd = json.load(open(P["dups"]))["drop"] if os.path.exists(P["dups"]) else {}
    sens = json.load(open(P["sensitive"]))["items"] if os.path.exists(P["sensitive"]) else {}
    sample = pick(items, n, dd, sens)
    rows = [{"u": x["uuid"], "d": (x.get("date") or "")[:10], "f": x["filename"],
             "o": " ".join((x["ocr"] or "").split())[:240]} for x in sample]
    cats = [c["name"] for c in CATEGORIES]
    out = f"{PREV}/pilot-{batch}-seed-labeler.html"
    html = (TEMPLATE.replace("__ROWS__", json.dumps(rows, ensure_ascii=False))
                    .replace("__CATS__", json.dumps(cats, ensure_ascii=False))
                    .replace("__BATCH__", str(batch)).replace("__N__", str(len(sample))))
    os.makedirs(PREV, exist_ok=True)
    open(out, "w", encoding="utf-8").write(html)
    print(f"seed labeler ({len(sample)} samples) → {out}")
    print(f"label them → Download → ~/Downloads/pilot-{batch}-seed.json, then run make_triage.py {batch}")
    try: webbrowser.open("file://" + out)
    except Exception: pass

TEMPLATE = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Seed labeler — __BATCH__</title><style>
body{margin:0;background:#0f1115;color:#e8ebf0;font:14px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI','Apple SD Gothic Neo',sans-serif}
.bar{position:sticky;top:0;z-index:10;background:#11141b;border-bottom:1px solid #2a2f3a;padding:12px 18px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.bar h1{font-size:16px;margin:0} button{background:#2563eb;color:#fff;border:0;border-radius:7px;padding:8px 14px;font-size:13px;font-weight:700;cursor:pointer}
.wrap{max-width:860px;margin:0 auto;padding:16px}
.legend{color:#9aa3b2;font-size:13px;margin:0 0 14px}
.it{display:flex;gap:12px;align-items:flex-start;padding:11px 12px;border-top:1px solid #181c24}
.idx{color:#5f6773;font-size:12px;flex:0 0 22px;padding-top:7px} .meta{flex:0 0 86px;color:#7f8895;font-size:11px;padding-top:6px}
.sn{flex:1;font-size:13px;color:#d4d9e2} select{background:#1b1f28;color:#fff;border:1px solid #3a4150;border-radius:6px;padding:6px 8px;font-size:12.5px;flex:0 0 130px;font-weight:600}
#done{position:fixed;inset:0;background:rgba(0,0,0,.66);display:none;align-items:center;justify-content:center;z-index:50}
#done.on{display:flex} #done .box{background:#11141b;border:1px solid #2a2f3a;border-radius:14px;padding:22px 24px;max-width:460px}
.cmd{font-family:'SF Mono',ui-monospace,Menlo,monospace;background:#1b2a4a;color:#9ad1ff;padding:3px 9px;border-radius:6px;font-weight:700;font-size:12.5px}
</style></head><body>
<div class="bar"><h1>🌱 Seed labeler — __BATCH__</h1><span id="prog" style="color:#9aa3b2;font-size:13px"></span><button id="dl">⬇ Download seed</button></div>
<div class="wrap"><p class="legend">New here? Label these <b>__N__ sample screenshots</b> the way you'd want them filed (or <b>DELETE</b> for junk). This teaches the AI your taste, then it sorts the rest. ~2 minutes. When done → <b>Download seed</b>, then run <span class="cmd">make_triage</span>.</p>
<div id="list"></div></div>
<div id="done"><div class="box"><h3>✓ Seed downloaded</h3><div style="color:#9aa3b2;font-size:13px" id="dsum"></div>
<p style="font-size:13.5px">Next: <span class="cmd">python3 make_triage.py __BATCH__</span> — it calibrates the triage from your labels.</p>
<div style="text-align:right"><button onclick="document.getElementById('done').classList.remove('on')">Got it</button></div></div></div>
<script>
const ROWS=__ROWS__, CATS=__CATS__, BATCH="__BATCH__";
const list=document.getElementById('list');
const opts=sel=>CATS.map(c=>`<option ${c===sel?'selected':''}>${c}</option>`).join('');
const def=CATS.includes('REVIEW')?'REVIEW':CATS[0];
ROWS.forEach((r,i)=>{const d=document.createElement('div');d.className='it';
 d.innerHTML=`<span class="idx">${i+1}</span><span class="meta">${r.d}<br>${r.f}</span><span class="sn">${(r.o||'—').replace(/</g,'&lt;')}</span><select data-u="${r.u}">${opts(def)}</select>`;list.appendChild(d);});
function prog(){const sel=[...document.querySelectorAll('select')];const done=sel.filter(s=>s.value!==def).length;document.getElementById('prog').textContent=`${done}/${sel.length} labeled`;}
list.addEventListener('change',prog); prog();
document.getElementById('dl').addEventListener('click',()=>{const dec={};document.querySelectorAll('select').forEach(s=>dec[s.dataset.u]=s.value);
 const out={batch:BATCH,decisions:dec};const b=new Blob([JSON.stringify(out,null,1)],{type:'application/json'});
 const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='pilot-'+BATCH+'-seed.json';try{a.click();}catch(e){}
 document.getElementById('dsum').textContent=Object.keys(dec).length+' samples labeled → saved to your Downloads';
 document.getElementById('done').classList.add('on');});
</script></body></html>"""

if __name__ == "__main__":
    main()
