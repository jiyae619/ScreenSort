#!/usr/bin/env python3
"""recat.py <year> — build the interactive recategorize HTML (no Photos access).
Thumbnail + bilingual OCR + a category dropdown per screenshot, a click-to-zoom
lightbox with one-key filing (A/P/D/M/C/E/B/L/S/V/X), a 'blanks only' filter, and
a Download button that saves pilot-<year>-decisions.json for Claude to apply."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from lib import paths, classify, CATEGORIES, PROTECT, DELETE, REVIEW

def main():
    if len(sys.argv) < 2: sys.exit("usage: recat.py <batch>")
    year = sys.argv[1]; P = paths(year)
    if not os.path.exists(P["export"]):
        sys.exit(f"✗ No export for {year}. Run `screensort {year}` in your Terminal with Photos access first.")
    items = json.load(open(P["export"]))["screenshots"]
    def load(p):
        try: return json.load(open(p)) if os.path.exists(p) else {}
        except Exception: return {}
    prior = load(P["decisions"]).get("decisions", {})   # your last Download — manual wins
    seedlbl = load(P["seed_dl"]).get("decisions", {})   # cold-start: your ~15 hand labels
    seed  = load(P["seed"]).get("items", {})            # LLM triage: uuid -> {cat, conf, why}
    dd    = load(P["dups"]).get("drop", {})             # dedup: uuid -> representative uuid
    sens  = load(P["sensitive"]).get("items", {})       # privacy pre-filter: uuid -> {cat:PROTECT, why}
    seeded = bool(seed) or bool(dd) or bool(sens) or bool(seedlbl)
    def decide(x):
        u = x["uuid"]
        if u in prior:   return prior[u], "manual", ""                        # your own past edit
        if u in seedlbl: return seedlbl[u], "manual", "you labeled this (seed)"  # cold-start hand label
        if u in sens:    return PROTECT, "sens", sens[u].get("why","")         # sensitive — never auto-delete
        if u in dd:      return DELETE, "dup", f"copy of {dd[u][:8]}"          # near-duplicate
        if u in seed:    s = seed[u]; return s.get("cat",REVIEW), s.get("conf","med"), s.get("why","")
        return classify(x), "heur", ""                                        # keyword fallback
    data = []
    for x in items:
        c, cf, why = decide(x)
        data.append({"u":x["uuid"],"d":(x["date"] or "")[:10],"f":x["filename"],"w":x["wc"],
                     "fav":x.get("favorite",False),"o":" ".join((x["ocr"] or "").split())[:220],
                     "c":c,"cf":cf,"why":why[:90]})
    cats_js = json.dumps([[c["name"], c["color"]] for c in CATEGORIES], ensure_ascii=False)
    keys_js = json.dumps({c["hotkey"]: c["name"] for c in CATEGORIES if c.get("hotkey")}, ensure_ascii=False)
    html = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False)) \
                   .replace("__YEAR__", str(year)).replace("__THUMBS__", P["thumbs_rel"]) \
                   .replace("__SEEDED__", "1" if seeded else "") \
                   .replace("__CATS__", cats_js).replace("__KEYS__", keys_js) \
                   .replace("__DELNAME__", DELETE)
    open(P["recat"], "w", encoding="utf-8").write(html)
    try:   # emit the category editor next to the sorter so the "⚙ Edit categories" link resolves
        import config_editor; config_editor.generate()
    except Exception:
        pass
    nd = sum(1 for r in data if r["c"] == DELETE)
    print(f"{len(data)} rows ({nd} pre-marked DELETE{' — seeded' if seeded else ''}) → {P['recat']}")

TEMPLATE = r"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><title>__YEAR__ Screenshots — Re-categorize</title><style>
body{margin:0;background:#0f1115;color:#e8ebf0;font:14px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI','Apple SD Gothic Neo',sans-serif}
.bar{position:sticky;top:0;z-index:20;background:#11141b;border-bottom:1px solid #2a2f3a;padding:11px 16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.bar h1{font-size:16px;margin:0 12px 0 0} .bar input{background:#1b1f28;border:1px solid #2a2f3a;color:#e8ebf0;border-radius:7px;padding:6px 10px;font-size:13px;width:200px}
button{background:#2563eb;color:#fff;border:0;border-radius:7px;padding:7px 13px;font-size:13px;font-weight:600;cursor:pointer} button.sec{background:#2a2f3a;color:#cdd3dd}
.editcats{background:#2a2f3a;color:#cdd3dd;border-radius:7px;padding:7px 12px;font-size:13px;font-weight:600;text-decoration:none;white-space:nowrap}
.chg{color:#ffd454;font-size:13px;font-weight:600} .wrap{max-width:1180px;margin:0 auto;padding:16px} .legend{color:#9aa3b2;font-size:12.5px;margin:0 0 12px}
h2{font-size:14px;margin:20px 0 6px;padding:5px 10px;border-radius:6px;color:#0f1115;display:inline-block}
.it{display:flex;gap:10px;align-items:center;padding:5px 8px;border-top:1px solid #181c24;border-left:4px solid transparent} .it.moved{background:#161b16;border-left-color:#ffd454}
.th{height:80px;max-width:160px;object-fit:cover;border-radius:5px;border:1px solid #2a2f3a;background:#1a1d24;flex:0 0 auto;cursor:zoom-in} .th:hover{outline:2px solid #2563eb}
.d{color:#7f8895;font-size:11.5px;flex:0 0 68px} .f{color:#5f6773;font-size:11px;flex:0 0 112px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fav{color:#ffd454;flex:0 0 12px} .sn{color:#d4d9e2;font-size:12.5px;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cfd{flex:0 0 9px;width:9px;height:9px;border-radius:50%;cursor:help}
select{background:#1b1f28;color:#fff;border:1px solid #3a4150;border-radius:6px;padding:5px 6px;font-size:12px;flex:0 0 132px;font-weight:600}
.del{flex:0 0 auto;background:#3a2326;color:#ff8b8b;border:1px solid #5a2d30;border-radius:6px;padding:5px 8px;font-size:12px;cursor:pointer} .del.on{background:#ff5d5d;color:#0f1115}
#lb{position:fixed;inset:0;background:rgba(0,0,0,.94);display:none;align-items:center;justify-content:center;z-index:100;cursor:zoom-out} #lb.on{display:flex}
#lb img{max-width:94vw;max-height:76vh;object-fit:contain;border-radius:6px} .lbbar{position:fixed;top:0;left:0;right:0;padding:9px 14px;display:flex;gap:8px;align-items:center;justify-content:center;flex-wrap:wrap;color:#cdd3dd;font-size:12px;background:linear-gradient(#000d,#0000);pointer-events:none}
.lbbar b{color:#fff} .lbcat{padding:2px 11px;border-radius:999px;font-weight:700;color:#0f1115} .kk{margin:0 4px;white-space:nowrap}
.kbd{display:inline-block;border:1px solid #3a4150;border-radius:4px;padding:0 5px;margin-right:3px;background:#1b1f28;font-weight:700;font-size:11px}
#lbtoast{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);font-size:40px;font-weight:800;padding:8px 30px;border-radius:14px;color:#0f1115;opacity:0;transition:.12s;pointer-events:none} #lbtoast.show{opacity:.96}
#done{position:fixed;inset:0;background:rgba(0,0,0,.66);display:none;align-items:center;justify-content:center;z-index:200;padding:20px}
#done.on{display:flex}
#done .box{background:#11141b;border:1px solid #2a2f3a;border-radius:14px;padding:22px 24px;max-width:470px;box-shadow:0 24px 70px #000b}
#done h3{margin:0 0 4px;font-size:18px}
#done .step{background:#0f1115;border:1px solid #2a2f3a;border-radius:9px;padding:12px 14px;margin:14px 0;font-size:14px}
#done .cmd{font-family:"SF Mono",ui-monospace,Menlo,monospace;background:#1b2a4a;color:#9ad1ff;padding:3px 9px;border-radius:6px;font-weight:700;font-size:13px}
</style></head><body>
<div class="bar"><h1>Re-categorize __YEAR__</h1><input id="q" placeholder="filter text / filename…">
<select id="cf" style="flex:0 0 auto"><option value="">all categories</option></select>
<label style="color:#7aa2ff;font-size:12px;cursor:pointer"><input type="checkbox" id="needs"> 🔎 needs review only</label>
<label style="color:#ffd454;font-size:12px;cursor:pointer"><input type="checkbox" id="blanks"> ⚠ blanks only (w&lt;12)</label>
<span class="chg" id="chg">0 changed</span><button class="sec" id="regroup">Regroup</button><button id="dl">⬇ Download decisions</button><button class="sec" id="reset">Reset</button><a class="editcats" href="photos-pilot-config-editor.html" target="_blank" title="Add, rename or recolor categories — takes effect on your next run">⚙ Edit categories</a></div>
<div class="wrap"><p class="legend">Rows are <b>pre-sorted by triage</b>; the colored dot = confidence (<span style="color:#5fd3a3">●</span> high · <span style="color:#ffb454">●</span> med · <span style="color:#9aa3b2">●</span> low · <span style="color:#ff8b8b">●</span> duplicate · <span style="color:#ff5d5d">●</span> sensitive (kept local) · <span style="color:#7aa2ff">●</span> your edit) — hover it for the reason. <b>🔎 needs review only</b> hides high-confidence keepers so you only verify the uncertain ones + the delete pile; untick to see everything. Change a <b>dropdown</b>, hit <b>🗑</b>, or zoom a thumbnail and file with one key. Auto-saves here. When done → <b>Download decisions</b> and tell Claude. <b>To actually delete in Photos later: select in the album → <code>⌘⌫</code> (Delete from Library), not plain Delete.</b></p><div id="list"></div></div>
<div id="lb"><div class="lbbar"><span id="lbpos"></span><span class="lbcat" id="lbcat"></span><span id="lbkeys"></span></div><img><div id="lbtoast"></div></div>
<div id="done"><div class="box"><h3>✓ Decisions downloaded</h3><div id="donesum" style="color:#9aa3b2;font-size:13px"></div><div class="step">Next, back in <b>Claude Code</b>, just say &nbsp;<span class="cmd">apply</span><div style="color:#9aa3b2;font-size:12.5px;margin-top:7px">Claude folds your kept items into topic notes, archives the text losslessly, and stages the junk in a Photos album — you delete it yourself with <b>⌘⌫</b> (30‑day undo). No photo is ever deleted automatically.</div></div><div style="color:#7f8895;font-size:12px">Saved to Downloads as <b>pilot-__YEAR__-decisions.json</b> — just re-download if you change anything.</div><div style="text-align:right;margin-top:10px"><button onclick="document.getElementById('done').classList.remove('on')">Got it</button></div></div></div>
<script>
const DATA=__DATA__, THUMBS="__THUMBS__", YEAR="__YEAR__", SEEDED="__SEEDED__", DELNAME="__DELNAME__";
const CONF={hi:'#5fd3a3',med:'#ffb454',lo:'#9aa3b2',heur:'#6b7280',dup:'#ff8b8b',manual:'#7aa2ff',sens:'#ff5d5d'};
function needsReview(x,c){return c===DELNAME||(x.cf!=='hi'&&x.cf!=='manual');}
const CATS=__CATS__;
const COLOR=Object.fromEntries(CATS), ORDER=CATS.map(c=>c[0]);
const orig=Object.fromEntries(DATA.map(x=>[x.u,x.c])); let ov=JSON.parse(localStorage.getItem('recat'+YEAR)||'{}');
const eff=u=>ov[u]||orig[u], save=()=>localStorage.setItem('recat'+YEAR,JSON.stringify(ov));
const cf=document.getElementById('cf'); ORDER.forEach(c=>{let o=document.createElement('option');o.value=c;o.textContent=c;cf.appendChild(o)});
function nChanged(){return DATA.filter(x=>eff(x.u)!==orig[x.u]).length}
function opts(s){return ORDER.map(c=>`<option ${c===s?'selected':''}>${c}</option>`).join('')}
function setCat(u,c){if(c===orig[u])delete ov[u];else ov[u]=c;save();}
function render(){const q=(document.getElementById('q').value||'').toLowerCase(),fc=cf.value,bl=document.getElementById('blanks').checked,nr=document.getElementById('needs').checked;
 const list=document.getElementById('list');list.innerHTML='';const g={};ORDER.forEach(c=>g[c]=[]);DATA.forEach(x=>g[eff(x.u)].push(x));
 ORDER.forEach(c=>{let rows=g[c].filter(x=>(!fc||c===fc)&&(!bl||x.w<12)&&(!nr||needsReview(x,c))&&(!q||x.o.toLowerCase().includes(q)||x.f.toLowerCase().includes(q)));if(!rows.length)return;
  let h=document.createElement('h2');h.style.background=COLOR[c];h.textContent=`${c} (${rows.length}${rows.length!==g[c].length?' / '+g[c].length:''})`;list.appendChild(h);
  rows.forEach(x=>{const mv=eff(x.u)!==orig[x.u],del=eff(x.u)===DELNAME;let r=document.createElement('div');r.className='it'+(mv?' moved':'');
   r.innerHTML=`<img class="th" loading="lazy" src="${THUMBS}/${x.u}.jpg">`+`<span class="d">${x.d}</span><span class="f">${x.f}</span>`+(x.fav?'<span class="fav">★</span>':'')+`<span class="cfd" title="${((x.why||x.cf)||'').replace(/"/g,'&quot;')}" style="background:${CONF[x.cf]||'#6b7280'}"></span>`+`<span class="sn">${(x.o||'—').replace(/</g,'&lt;')}</span><select data-u="${x.u}">${opts(eff(x.u))}</select><span class="del ${del?'on':''}" data-u="${x.u}">🗑</span>`;list.appendChild(r);});});
 document.getElementById('chg').textContent=nChanged()+' changed';}
document.addEventListener('change',e=>{if(e.target.matches('select[data-u]')){setCat(e.target.dataset.u,e.target.value);render();}});
document.addEventListener('click',e=>{if(e.target.matches('.del[data-u]')){const u=e.target.dataset.u;setCat(u,eff(u)===DELNAME?orig[u]:DELNAME);render();}});
document.getElementById('q').addEventListener('input',render);document.getElementById('blanks').addEventListener('change',render);document.getElementById('needs').addEventListener('change',render);cf.addEventListener('change',render);
if(SEEDED)document.getElementById('needs').checked=true;
document.getElementById('regroup').addEventListener('click',render);
document.getElementById('reset').addEventListener('click',()=>{if(confirm('Clear changes?')){ov={};save();render();}});
document.getElementById('dl').addEventListener('click',()=>{const out={year:YEAR,decisions:Object.fromEntries(DATA.map(x=>[x.u,eff(x.u)]))};
 const cockpit=location.protocol==='http:';  // served by the cockpit → save straight to it, no Downloads round-trip
 if(cockpit){fetch('/api/decisions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(out)}).catch(()=>{});}
 const b=new Blob([JSON.stringify(out,null,1)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='pilot-'+YEAR+'-decisions.json';try{a.click();}catch(e){}showDone(cockpit);});
function showDone(cockpit){const del=DATA.filter(x=>eff(x.u)===DELNAME).length;document.getElementById('donesum').textContent=DATA.length+' decisions saved · '+del+' to delete · '+nChanged()+' changed by you';if(cockpit){const s=document.querySelector('#done .step');if(s)s.innerHTML='Saved to the cockpit. Switch back to the <b>Photos Pilot</b> tab and click <span class="cmd">Apply</span> on this batch.';}document.getElementById('done').classList.add('on');}
// lightbox + one-key filing
const lb=document.getElementById('lb'),li=lb.querySelector('img');let L=[],i=0;
const KEYS=__KEYS__;
document.getElementById('lbkeys').innerHTML=Object.entries(KEYS).map(([k,c])=>`<span class="kk"><span class="kbd" style="color:${COLOR[c]}">${k.toUpperCase()}</span>${c[0]+c.slice(1).toLowerCase()}</span>`).join('')+`<span class="kk"><span class="kbd">←→</span>nav</span><span class="kk"><span class="kbd">Esc</span>close</span>`;
function lbShow(){const u=L[i];li.src=THUMBS+'/'+u+'.jpg';const x=DATA.find(z=>z.u===u),c=eff(u);document.getElementById('lbpos').innerHTML=`<b>${i+1}</b>/${L.length}&nbsp; ${x?x.f:''}${x&&x.why?` &nbsp;<span style="color:#9aa3b2">· ${x.why.replace(/</g,'&lt;')}</span>`:''}`;const bd=document.getElementById('lbcat');bd.textContent=c;bd.style.background=COLOR[c];lb.classList.add('on');}
function toast(c){const t=document.getElementById('lbtoast');t.textContent='→ '+c;t.style.background=COLOR[c];t.classList.add('show');clearTimeout(t._t);t._t=setTimeout(()=>t.classList.remove('show'),420);}
document.addEventListener('click',e=>{if(e.target.matches('img.th')){L=[...document.querySelectorAll('#list img.th')].map(z=>z.src.split('/').pop().replace('.jpg',''));i=Math.max(0,L.indexOf(e.target.src.split('/').pop().replace('.jpg','')));lbShow();}else if(e.target===lb){lb.classList.remove('on');render();}});
document.addEventListener('keydown',e=>{if(!lb.classList.contains('on'))return;if(e.key==='Escape'){lb.classList.remove('on');render();return;}if(e.key==='ArrowRight'){i=(i+1)%L.length;lbShow();return;}if(e.key==='ArrowLeft'){i=(i-1+L.length)%L.length;lbShow();return;}if(e.metaKey||e.ctrlKey||e.altKey)return;const lt=(e.code&&/^Key[A-Z]$/.test(e.code))?e.code.slice(3).toLowerCase():(e.key&&e.key.length===1?e.key.toLowerCase():'');const c=KEYS[lt];if(c){e.preventDefault();setCat(L[i],c);toast(c);document.getElementById('chg').textContent=nChanged()+' changed';if(i<L.length-1)i++;lbShow();}});
render();
</script></body></html>"""

if __name__ == "__main__":
    main()
