#!/usr/bin/env python3
"""config_editor.py — generate an HTML editor for your category set (no terminal needed).
Reads config.json and opens a browser page where you add / rename / recolor / re-key /
re-role / remove categories with live validation, then Download an updated config.json.
Apply it with `python3 apply_config.py` (or tell Claude "apply my new categories")."""
import sys, os, json, webbrowser
sys.path.insert(0, os.path.dirname(__file__))
import lib

OUT = f"{lib.PREV}/screensort-config-editor.html"

def generate():
    """Write the editor HTML from the current config; return its path. No browser open
    (so recat.py can emit it alongside the sorter for the in-sorter 'Edit categories' link)."""
    cfg = lib.load_config()
    os.makedirs(lib.PREV, exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(TEMPLATE.replace("__CFG__", json.dumps(cfg, ensure_ascii=False)))
    return OUT

def main():
    path = generate()
    print(f"category editor → {path}")
    try: webbrowser.open("file://" + path)
    except Exception: pass

TEMPLATE = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>screensort — Category Editor</title><style>
body{margin:0;background:#0f1115;color:#e8ebf0;font:14px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI','Apple SD Gothic Neo',sans-serif}
.bar{position:sticky;top:0;z-index:20;background:#11141b;border-bottom:1px solid #2a2f3a;padding:12px 18px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.bar h1{font-size:16px;margin:0 8px 0 0}
button{background:#2563eb;color:#fff;border:0;border-radius:7px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer} button:disabled{opacity:.45;cursor:not-allowed} button.sec{background:#2a2f3a;color:#cdd3dd}
.wrap{max-width:1000px;margin:0 auto;padding:18px}
.legend{color:#9aa3b2;font-size:13px;margin:0 0 14px}
.chips{display:flex;gap:7px;flex-wrap:wrap;margin:6px 0 18px}
.chip{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;font-weight:600;padding:4px 11px;border-radius:999px;border:1px solid #2a2f3a;background:#161a22}
.cdot{width:10px;height:10px;border-radius:50%}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:#7f8895;font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;padding:6px 8px;border-bottom:1px solid #2a2f3a;font-weight:700}
td{padding:5px 8px;border-bottom:1px solid #181c24;vertical-align:middle}
input,select{background:#1b1f28;border:1px solid #2a2f3a;color:#e8ebf0;border-radius:6px;padding:6px 8px;font-size:13px;font-family:inherit}
input[type=color]{padding:2px;width:38px;height:30px;cursor:pointer}
.nm{width:120px;font-weight:600} .key{width:38px;text-align:center;text-transform:lowercase} .desc{width:100%;min-width:150px} .kw{width:100%;min-width:120px}
select{cursor:pointer} .role-note{color:#9ad1ff} .role-protect{color:#ff8b8b} .role-delete{color:#9aa3b2}
.rm{background:#3a2326;color:#ff8b8b;border:1px solid #5a2d30;border-radius:6px;padding:4px 9px;font-size:13px;cursor:pointer;font-weight:700}
.reserved{font-size:11px;color:#7f8895}
#msg{margin:14px 0;padding:0}
#msg .err{background:#3a2326;border:1px solid #5a2d30;color:#ff9b9b;border-radius:8px;padding:9px 13px;font-size:13px;margin:6px 0}
#msg .ok{background:#16271d;border:1px solid #285039;color:#86e0aa;border-radius:8px;padding:9px 13px;font-size:13px}
#done{position:fixed;inset:0;background:rgba(0,0,0,.66);display:none;align-items:center;justify-content:center;z-index:200;padding:20px}
#done.on{display:flex}
#done .box{background:#11141b;border:1px solid #2a2f3a;border-radius:14px;padding:22px 24px;max-width:500px;box-shadow:0 24px 70px #000b}
#done h3{margin:0 0 6px;font-size:18px}
#done .cmd{font-family:'SF Mono',ui-monospace,Menlo,monospace;background:#1b2a4a;color:#9ad1ff;padding:3px 9px;border-radius:6px;font-weight:700;font-size:12.5px}
#done .step{background:#0f1115;border:1px solid #2a2f3a;border-radius:9px;padding:12px 14px;margin:12px 0;font-size:13.5px}
</style></head><body>
<div class="bar"><h1>Category Editor</h1><button class="sec" id="add">＋ Add category</button><button id="dl" disabled>⬇ Download config.json</button><span id="status" style="font-size:13px;color:#9aa3b2"></span></div>
<div class="wrap">
<p class="legend">Edit your categories — rename, recolor, change the one-key shortcut, switch role, or remove. <b>note</b> = becomes a knowledge note; <b>places/protect/review/delete</b> are the reserved roles (one each of protect/review/delete required; places optional). Then <b>Download config.json</b> and apply it.</p>
<div class="chips" id="chips"></div>
<table><thead><tr><th>Name</th><th>Color</th><th>Key</th><th>Role</th><th>Description (guides triage)</th><th>Keywords (comma)</th><th></th></tr></thead><tbody id="rows"></tbody></table>
<div id="msg"></div>
</div>
<div id="done"><div class="box"><h3>✓ config.json downloaded</h3><div style="color:#9aa3b2;font-size:13px" id="donesum"></div>
<div class="step">Apply it — back in <b>Claude Code</b>, say <span class="cmd">apply my new categories</span><br><span style="color:#9aa3b2;font-size:12.5px">(or run <span class="cmd">python3 ~/screensort/src/apply_config.py</span>). It validates &amp; installs to <b>config.json</b> (keeping a backup). Then re-run the sorter to see the new set.</span></div>
<div style="text-align:right"><button onclick="document.getElementById('done').classList.remove('on')">Got it</button></div></div></div>
<script>
const CFG=__CFG__;
const ROLES=["note","places","protect","review","delete"];
const PALETTE=["#7aa2ff","#ffb454","#5fd3a3","#c08af7","#4fd0e0","#f78ad0","#d0b35f","#8fbf7a","#ff5d5d","#9aa3b2","#6b7280","#e06c9f"];
let cats=(CFG.categories||[]).map(c=>({name:c.name||'',hotkey:c.hotkey||'',color:c.color||'#7aa2ff',role:c.role||'note',desc:c.desc||'',keywords:(c.keywords||[]).join(', ')}));
window.cats=cats;
const esc=s=>String(s==null?'':s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;');
function freeKey(){const used=new Set(cats.map(c=>(c.hotkey||'').toLowerCase()));for(const k of "abcdefghijklmnopqrstuvwxyz")if(!used.has(k))return k;return '';}
function nextColor(){const used=new Set(cats.map(c=>c.color));return PALETTE.find(p=>!used.has(p))||PALETTE[cats.length%PALETTE.length];}
function rowHTML(c,i){const opts=ROLES.map(r=>`<option value="${r}" ${r===c.role?'selected':''}>${r}</option>`).join('');
 return `<tr><td><input class="nm" data-i="${i}" data-f="name" value="${esc(c.name)}"></td>`+
  `<td><input type="color" data-i="${i}" data-f="color" value="${esc(c.color)}"></td>`+
  `<td><input class="key" maxlength="1" data-i="${i}" data-f="hotkey" value="${esc(c.hotkey)}"></td>`+
  `<td><select class="role-${c.role}" data-i="${i}" data-f="role">${opts}</select></td>`+
  `<td><input class="desc" data-i="${i}" data-f="desc" value="${esc(c.desc)}"></td>`+
  `<td><input class="kw" data-i="${i}" data-f="keywords" value="${esc(c.keywords)}"></td>`+
  `<td><button class="rm" data-i="${i}" title="remove">✕</button></td></tr>`;}
function renderTable(){document.getElementById('rows').innerHTML=cats.map(rowHTML).join('');refresh();}
function chips(){document.getElementById('chips').innerHTML=cats.map(c=>`<span class="chip" style="border-color:${esc(c.color)}"><span class="cdot" style="background:${esc(c.color)}"></span>${esc(c.name)||'—'}<span class="reserved">${c.role!=='note'?'· '+c.role:''}</span></span>`).join('');}
function validate(){const p=[];const names=cats.map(c=>c.name.trim().toLowerCase());
 if(cats.some(c=>!c.name.trim()))p.push("every category needs a name");
 if(new Set(names).size!==names.length)p.push("category names must be unique");
 const hk=cats.map(c=>(c.hotkey||'').toLowerCase()).filter(Boolean);
 const dh=[...new Set(hk.filter(k=>hk.filter(x=>x===k).length>1))];
 if(dh.length)p.push("duplicate hotkeys: "+dh.join(", "));
 for(const r of ["note","protect","review","delete"])if(!cats.some(c=>c.role===r))p.push("missing a category with role “"+r+"”");
 return p;}
function refresh(){chips();const p=validate();const msg=document.getElementById('msg');
 if(p.length){msg.innerHTML=p.map(x=>`<div class="err">⚠ ${esc(x)}</div>`).join('');document.getElementById('dl').disabled=true;document.getElementById('status').textContent=p.length+" issue"+(p.length>1?"s":"")+" to fix";}
 else{msg.innerHTML=`<div class="ok">✓ valid — ${cats.length} categories. Download &amp; apply.</div>`;document.getElementById('dl').disabled=false;document.getElementById('status').textContent=cats.length+" categories";}}
function buildConfig(){const out=Object.assign({},CFG);
 out.categories=cats.map(c=>{const o={name:c.name.trim(),hotkey:(c.hotkey||'').toLowerCase(),color:c.color,role:c.role,desc:c.desc.trim(),
   keywords:c.keywords.split(',').map(k=>k.trim()).filter(Boolean)};return o;});
 return out;}
window.buildConfig=buildConfig; window.validate=validate;
document.getElementById('rows').addEventListener('input',e=>{const t=e.target;if(t.dataset.i==null)return;cats[t.dataset.i][t.dataset.f]=t.value;
 if(t.dataset.f==='color'){chips();}refresh();});
document.getElementById('rows').addEventListener('change',e=>{const t=e.target;if(t.dataset.f==='role'){t.className='role-'+t.value;}});
document.getElementById('rows').addEventListener('click',e=>{if(e.target.classList.contains('rm')){cats.splice(+e.target.dataset.i,1);renderTable();}});
document.getElementById('add').addEventListener('click',()=>{cats.push({name:'',hotkey:freeKey(),color:nextColor(),role:'note',desc:'',keywords:''});renderTable();
 const ins=document.querySelectorAll('#rows .nm');if(ins.length)ins[ins.length-1].focus();});
document.getElementById('dl').addEventListener('click',()=>{const out=buildConfig();const js=JSON.stringify(out,null,2);window.__lastDownload=js;
 const b=new Blob([js],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='config.json';try{a.click();}catch(e){}
 document.getElementById('donesum').textContent=out.categories.length+' categories saved to config.json in your Downloads';
 document.getElementById('done').classList.add('on');});
renderTable();
</script></body></html>"""

if __name__ == "__main__":
    main()
