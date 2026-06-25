#!/usr/bin/env python3
"""serve.py — the ScreenSort COCKPIT. One local web page that drives the whole
pipeline so you stop bouncing between Terminal, the browser, and Claude.

  Export · Prep (dedup+privacy) · Build sorter · Apply · Tag   → buttons here
  Triage · Write notes                                          → the 2 Claude steps
  Delete                                                        → your ⌘⌫ in Photos

Localhost only (127.0.0.1) — nothing leaves your Mac. The two NATIVE steps (Export,
Tag) need this server launched from a Full-Disk-Access Terminal with the osxphotos
venv; everything else runs anywhere.

Launch:
  ~/.osxphotos-venv/bin/python ~/photos-pilot/serve.py
or double-click  ~/photos-pilot/ScreenSort.command
"""
import sys, os, json, glob, threading, subprocess, webbrowser, time, html as _html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib, status

PY = sys.executable                 # whatever launched us (ideally the osxphotos venv)
HOST, PORT = "127.0.0.1", 8765
KNOWN_YEARS = ["2025", "2024", "2023", "2022", "2021"]

# An "action" is one cockpit button → an ordered list of scripts to run as one job.
# fda=True means it needs Photos access (Export / Tag) — only works if the server was
# launched from an FDA Terminal with the venv.
ACTIONS = {
    "export": {"seq": ["export.py"],                 "fda": True},
    "prep":   {"seq": ["dedup.py", "sensitive.py"],  "fda": False},
    "recat":  {"seq": ["recat.py"],                  "fda": False},
    "apply":  {"seq": ["apply.py", "archive.py"],    "fda": False},
    "tag":    {"seq": ["tag.py"],                    "fda": True},
}

_SAFE = lambda b: bool(b) and all(c.isalnum() or c in "-_." for c in str(b)) and ".." not in str(b)

# ---- job registry (in-memory) ---------------------------------------------
_jobs, _lock, _seq = {}, threading.Lock(), [0]

def start_job(action, batch):
    spec = ACTIONS.get(action)
    if not spec or not _SAFE(batch):
        return None
    with _lock:
        _seq[0] += 1
        jid = str(_seq[0])
        _jobs[jid] = {"action": action, "batch": batch, "status": "running", "output": "", "rc": None}

    def run():
        buf = []
        for script in spec["seq"]:
            buf.append(f"$ {script} {batch}\n")
            _jobs[jid]["output"] = "".join(buf)
            try:
                p = subprocess.Popen([PY, os.path.join(HERE, script), batch], cwd=HERE,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            except Exception as e:
                buf.append(f"✗ could not launch {script}: {e}\n")
                _jobs[jid].update(status="error", rc=1, output="".join(buf))
                return
            for line in p.stdout:
                buf.append(line)
                _jobs[jid]["output"] = "".join(buf)
            p.wait()
            if p.returncode != 0:
                buf.append(f"\n✗ {script} exited {p.returncode}"
                           + ("  — Export/Tag need a Terminal with Photos access (Full Disk Access) + the osxphotos venv.\n" if spec["fda"] else "\n"))
                _jobs[jid].update(status="error", rc=p.returncode, output="".join(buf))
                return
            buf.append("\n")
        buf.append("✓ done\n")
        _jobs[jid].update(status="done", rc=0, output="".join(buf))

    threading.Thread(target=run, daemon=True).start()
    return jid

# ---- state ----------------------------------------------------------------
def batch_states():
    found = [os.path.basename(d.rstrip("/")) for d in glob.glob(f"{lib.SS}/pilot/*/")]
    batches = list(dict.fromkeys(KNOWN_YEARS + sorted(found, reverse=True)))
    out = []
    for b in batches:
        steps, nxt = status.step_status(b)          # [(label, ok, cmd)] in flow order
        ok = [s[1] for s in steps]
        P = lib.paths(b)
        out.append({
            "batch": b, "next": nxt,
            "export": ok[0], "dups": ok[1], "sensitive": ok[2], "seed": ok[3],
            "recat": ok[4], "decisions": ok[5], "fulltext": ok[6], "archive": ok[7],
            "snapshot": os.path.exists(f"{P['work']}/decisions.json"),
            "notes": os.path.exists(P["notes"]),
        })
    return out

def native_ok():
    """Soft check: are the native deps importable (i.e. launched with the venv)?
    FDA itself is only proven when the Photos DB opens — see fda_ok()."""
    try:
        import osxphotos, Vision  # noqa: F401
        return True
    except Exception:
        return False

def fda_ok():
    """The REAL Full-Disk-Access test: can this process actually read the Photos
    library DB? True / False, or None if no library is found. native_ok() only checks
    imports; FDA denials surface only when the DB is read — this catches them before
    the user clicks Export and hits a traceback."""
    import glob
    cands = glob.glob(os.path.expanduser("~/Pictures/*.photoslibrary/database/Photos.sqlite"))
    if not cands:
        return None
    try:
        with open(cands[0], "rb") as f:
            f.read(1)
        return True
    except PermissionError:
        return False
    except Exception:
        return None

# ---- http -----------------------------------------------------------------
_CT = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css",
       ".json": "application/json", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
       ".png": "image/png", ".svg": "image/svg+xml"}

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):       # quiet
        pass

    def do_GET(self):
        u = urlparse(self.path)
        path, q = u.path, parse_qs(u.query)
        if path == "/" or path == "/index.html":
            fda = fda_ok()
            page = (COCKPIT.replace("__NATIVE__", "1" if native_ok() else "")
                           .replace("__FDA__", "1" if fda else ("0" if fda is False else "")))
            return self._send(200, page, _CT[".html"])
        if path == "/api/status":
            return self._send(200, {"batches": batch_states(), "native": native_ok(), "fda": fda_ok()})
        if path == "/api/job":
            jid = (q.get("id") or [""])[0]
            j = _jobs.get(jid)
            return self._send(200, j or {"status": "unknown", "output": "", "rc": None})
        if path.startswith("/prev/"):
            return self._serve_prev(path[len("/prev/"):])
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw or b"{}")
        except Exception:
            return self._send(400, {"error": "bad json"})
        u = urlparse(self.path).path
        if u == "/api/run":
            jid = start_job(data.get("action"), data.get("batch"))
            if not jid:
                return self._send(400, {"error": "unknown action or bad batch"})
            return self._send(200, {"job": jid})
        if u == "/api/decisions":
            batch = data.get("batch") or data.get("year")
            dec = data.get("decisions")
            if not _SAFE(batch) or not isinstance(dec, dict):
                return self._send(400, {"error": "bad payload"})
            path = lib.paths(batch)["decisions"]            # ~/Downloads/pilot-<b>-decisions.json
            os.makedirs(os.path.dirname(path), exist_ok=True)
            json.dump({"year": str(batch), "decisions": dec}, open(path, "w"), ensure_ascii=False)
            return self._send(200, {"ok": True, "saved": path, "count": len(dec)})
        return self._send(404, {"error": "not found"})

    def _serve_prev(self, rel):
        rel = rel.split("?")[0]
        full = os.path.normpath(os.path.join(lib.PREV, rel))
        if not full.startswith(os.path.abspath(lib.PREV)) or not os.path.isfile(full):
            return self._send(404, {"error": "not found"})
        ext = os.path.splitext(full)[1].lower()
        with open(full, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", _CT.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def main():
    try:
        srv = ThreadingHTTPServer((HOST, PORT), H)
    except OSError as e:
        sys.exit(f"✗ can't bind {HOST}:{PORT} ({e}). Is the cockpit already running? "
                 f"Open http://{HOST}:{PORT} — or close the other one.")
    url = f"http://{HOST}:{PORT}"
    if not native_ok():
        warn = ("  ⚠ launched without the osxphotos venv — Export/Tag will fail.\n"
                "     relaunch with:  ~/.osxphotos-venv/bin/python ~/photos-pilot/serve.py\n")
    elif fda_ok() is False:
        warn = ("  ⚠ no Full Disk Access — Export/Tag can't read Photos.\n"
                "     System Settings → Privacy & Security → Full Disk Access → enable Terminal, then relaunch from Terminal.\n")
    else:
        warn = ""
    print(f"📷 ScreenSort cockpit → {url}\n{warn}   (Ctrl-C to stop)")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")

# ---------------------------------------------------------------------------
COCKPIT = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ScreenSort — Cockpit</title><style>
:root{--bg:#0f1115;--panel:#11141b;--panel2:#161a22;--line:#2a2f3a;--line2:#181c24;--ink:#e8ebf0;--mut:#9aa3b2;--mut2:#7f8895;--blue:#2563eb;--blue2:#9ad1ff;--ok:#5fd3a3;--you:#ffb454;--claude:#7aa2ff;--warn:#ff5d5d}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14.5px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI','Apple SD Gothic Neo',sans-serif}
code{font-family:"SF Mono",ui-monospace,Menlo,monospace}
.cmd{font-family:"SF Mono",ui-monospace,Menlo,monospace;background:#1b2a4a;color:var(--blue2);padding:1px 7px;border-radius:6px;font-weight:700;font-size:.86em;white-space:nowrap}
.bar{position:sticky;top:0;z-index:30;background:rgba(17,20,27,.93);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:13px 22px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.bar h1{font-size:16px;margin:0;font-weight:700}
.bar .sp{margin-left:auto;display:flex;gap:8px;align-items:center}
.bar a{color:var(--mut);font-size:12.5px;font-weight:600;padding:6px 10px;border-radius:7px}.bar a:hover{background:#1b1f28;color:var(--ink)}
.bar button{background:#2a2f3a;color:#cdd3dd;border:0;border-radius:7px;padding:7px 12px;font-size:12.5px;font-weight:700;cursor:pointer}
.wrap{max-width:980px;margin:0 auto;padding:22px 22px 220px}
.intro{display:flex;gap:9px;flex-wrap:wrap;margin:4px 0 20px;color:var(--mut);font-size:12.5px}
.intro .tag{background:var(--panel);border:1px solid var(--line);border-radius:999px;padding:5px 11px}
.intro .tag b{color:var(--ink)}
.banner{background:rgba(255,93,93,.09);border:1px solid rgba(255,93,93,.32);color:#ffc1c1;border-radius:11px;padding:11px 15px;margin:0 0 18px;font-size:13px;display:none}
.banner.on{display:block}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:15px 17px;margin:12px 0}
.card.done{border-color:#27452f}
.chead{display:flex;align-items:baseline;gap:10px}
.chead b{font-size:18px;letter-spacing:-.01em}.chead .prog{color:var(--mut2);font-size:12px;font-weight:700}
.chead .nx{margin-left:auto;font-size:12px;color:var(--mut)}
/* per-batch: a tracker row + an action row that SHARE the same 8 columns, so each
   tracker node sits directly above its button. The tracker is a connected stepper
   (dots + line) that reads as progress, NOT as clickable chips. */
.stagewrap{margin:15px 0 2px;overflow-x:auto}
.track,.acts{display:grid;grid-template-columns:repeat(8,minmax(76px,1fr))}
.track{margin-bottom:11px;cursor:default}
.tnode{position:relative;display:flex;flex-direction:column;align-items:center;gap:8px;padding-top:3px}
.tnode::before{content:"";position:absolute;top:9px;left:-50%;width:100%;height:2px;background:#2a2f3a;z-index:0}
.tnode:first-child::before{display:none}
.tnode .dot{width:16px;height:16px;border-radius:50%;background:#161a22;border:2px solid #333a48;z-index:1}
.tnode .tlabel{font-size:9.5px;font-weight:800;color:var(--mut2);white-space:nowrap;text-transform:uppercase;letter-spacing:.03em}
.tnode.ok::before{background:var(--ok)}
.tnode.ok .dot{background:var(--ok);border-color:var(--ok)}
.tnode.ok .dot::after{content:"✓";color:#0f1115;font-size:10px;font-weight:900;display:flex;align-items:center;justify-content:center;height:100%;margin-top:-1px}
.tnode.ok .tlabel{color:var(--ok)}
.tnode.next .dot{background:#0f1115;border-color:var(--blue);animation:pulsenode 1.5s infinite}
.tnode.next .tlabel{color:var(--blue2)}
.tnode.claude.next .dot{border-color:var(--claude);animation:pulsenodec 1.5s infinite}
.tnode.claude.next .tlabel{color:var(--claude)}
.tnode.manual .dot{border-style:dashed;border-color:#3a4150;background:transparent}
@keyframes pulsenode{0%,100%{box-shadow:0 0 0 4px rgba(37,99,235,.28)}55%{box-shadow:0 0 0 9px rgba(37,99,235,.04)}}
@keyframes pulsenodec{0%,100%{box-shadow:0 0 0 4px rgba(122,162,255,.26)}55%{box-shadow:0 0 0 9px rgba(122,162,255,.04)}}
/* action row — one control per column, full-width, aligned under its node */
.acell{display:flex;padding:0 3px}
.act{width:100%;border:0;border-radius:9px;padding:8px 6px;font-size:12.5px;font-weight:700;cursor:pointer;background:#222734;color:#cdd3dd;display:inline-flex;align-items:center;justify-content:center;gap:4px;line-height:1.18;text-align:center}
.act:hover:not(:disabled){background:#2b3140}
.act:disabled{opacity:.32;cursor:not-allowed}
.act.go{background:var(--blue);color:#fff;animation:pulsebtn 1.5s infinite}
.act.cl{background:rgba(122,162,255,.12);color:var(--claude);border:1px solid rgba(122,162,255,.3)}
.act.cl.go{background:rgba(122,162,255,.22);border-color:transparent;color:#fff;animation:pulsebtnc 1.5s infinite}
.act.done2{background:rgba(95,211,163,.1);color:var(--ok)}
.act.fda::after{content:"Photos";font-size:8px;font-weight:800;background:rgba(255,180,84,.22);color:var(--you);border-radius:4px;padding:1px 4px;margin-left:2px;letter-spacing:.02em}
.act.ph{background:transparent;color:var(--mut2);font-weight:600;font-size:11px;cursor:default;border:1px dashed #2f3645}
@keyframes pulsebtn{0%{box-shadow:0 0 0 0 rgba(37,99,235,.6)}70%{box-shadow:0 0 0 10px rgba(37,99,235,0)}100%{box-shadow:0 0 0 0 rgba(37,99,235,0)}}
@keyframes pulsebtnc{0%{box-shadow:0 0 0 0 rgba(122,162,255,.55)}70%{box-shadow:0 0 0 10px rgba(122,162,255,0)}100%{box-shadow:0 0 0 0 rgba(122,162,255,0)}}
.kbd{display:inline-block;border:1px solid #3a4150;border-bottom-width:2px;border-radius:5px;padding:0 6px;background:#1b1f28;font-weight:700;font-size:.8em;font-family:Menlo,monospace}
/* log drawer */
#log{position:fixed;left:0;right:0;bottom:0;z-index:40;background:#0b0d12;border-top:1px solid var(--line);transform:translateY(calc(100% - 40px));transition:transform .18s;max-height:48vh;display:flex;flex-direction:column}
#log.open{transform:translateY(0)}
#log .lh{display:flex;align-items:center;gap:10px;padding:9px 16px;cursor:pointer;font-size:12.5px;font-weight:700;color:#cdd3dd}
#log .lh .dot{width:8px;height:8px;border-radius:50%;background:#3a4150}
#log .lh .dot.run{background:var(--you);animation:pulse 1s infinite}#log .lh .dot.done{background:var(--ok)}#log .lh .dot.err{background:var(--warn)}
@keyframes pulse{50%{opacity:.3}}
#log pre{margin:0;padding:10px 16px 18px;overflow:auto;font:12px/1.5 "SF Mono",Menlo,monospace;color:#c8d0dc;white-space:pre-wrap}
.muted{color:var(--mut2)}
</style></head><body>
<div class="bar"><h1>📷 ScreenSort · Cockpit</h1>
<div class="sp"><button id="refresh">↻ Refresh</button>
<a href="/prev/photos-pilot-workflow-guide.html" target="_blank">Guide</a>
<a href="/prev/photos-pilot-config-editor.html" target="_blank">⚙ Categories</a></div></div>
<div class="wrap">
<div class="intro">
  <span class="tag"><b style="color:var(--you)">Run here</b> · Export · Scan · Categorize · Apply · Group deletes</span>
  <span class="tag"><b style="color:var(--claude)">Ask Claude</b> · Triage · Write notes</span>
  <span class="tag"><b>You · Photos</b> · the final <span class="kbd">⌘</span><span class="kbd">⌫</span></span>
</div>
<div class="banner" id="banner"></div>
<div id="cards"></div>
</div>
<div id="log"><div class="lh" id="lh"><span class="dot" id="ldot"></span><span id="ltitle">log</span><span class="muted" id="lhint" style="margin-left:auto;font-weight:400">click to expand</span></div><pre id="lpre"></pre></div>
<script>
const NATIVE="__NATIVE__", FDA="__FDA__";   // FDA: "1" ok · "0" denied · "" unknown
const $=s=>document.querySelector(s);
let polling=null;

// warn BEFORE the user clicks Export — missing venv or missing Full Disk Access
function banner(){
 const b=$('#banner');
 if(!NATIVE){ b.innerHTML='⚠ Launched without the osxphotos venv — <b>Export/Tag</b> will fail. Relaunch: <span class="cmd">~/.osxphotos-venv/bin/python ~/photos-pilot/serve.py</span>'; b.classList.add('on'); return; }
 if(FDA==='0'){ b.innerHTML='⚠ This Terminal doesn’t have <b>Full Disk Access</b>, so <b>Export/Tag</b> can’t read Photos. Fix: System Settings → Privacy &amp; Security → <b>Full Disk Access</b> → enable <b>Terminal</b>, then quit Terminal and relaunch the cockpit from it. (A cockpit started from Claude/another app can’t Export.)'; b.classList.add('on'); return; }
 b.classList.remove('on');
}

// One stage list drives BOTH rows (so the tracker node + its button share a column).
// kind: run = cockpit button · sorter = build+open the categorizer · claude = copy-prompt · photos = ⌘⌫ hint
const STAGES=[
 {k:'export',    label:'Export',    kind:'run',    action:'export', fda:true,  done:s=>s.export},
 {k:'scan',      label:'Scan',      kind:'run',    action:'prep',              done:s=>s.dups&&s.sensitive},
 {k:'triage',    label:'Triage',    kind:'claude', prompt:b=>`run the screenshot pilot triage for ${b}`, done:s=>s.seed},
 {k:'categorize',label:'Categorize',kind:'sorter', action:'recat',             done:s=>s.decisions},
 {k:'apply',     label:'Apply',     kind:'run',    action:'apply',             done:s=>s.fulltext&&s.archive},
 {k:'notes',     label:'Notes',     kind:'claude', prompt:b=>`apply ${b} — write the notes`, done:s=>s.notes},
 {k:'tag',       label:'Group deletes', short:'Group', kind:'run', action:'tag', fda:true, manual:true},
 {k:'delete',    label:'Delete',    kind:'photos',                             manual:true},
];
const CORE=['export','scan','triage','categorize','apply','notes'];   // the stages with real progress markers
const dn=(st,s)=> st.done? !!st.done(s) : false;

// next actionable stage = first incomplete CORE stage *after* the furthest one reached
// (so a batch sorted without triage isn't sent back to triage). null = complete.
function nextKey(s){
 const core=CORE.map(k=>STAGES.find(x=>x.k===k));
 const done=core.map(st=>dn(st,s));
 const oks=done.map((d,i)=>d?i:-1).filter(i=>i>=0);
 const last=oks.length?Math.max(...oks):-1;
 for(let i=0;i<core.length;i++) if(!done[i] && i>last) return core[i].k;
 return null;
}
function reachable(st,s){
 return ({export:true, scan:s.export, triage:s.export, categorize:s.export,
          apply:s.decisions, notes:s.fulltext, tag:s.snapshot, delete:s.snapshot})[st.k];
}

function render(states){
 banner();
 const host=$('#cards'); host.innerHTML='';
 states.forEach(s=>{
  const nextK=nextKey(s);
  const coreDone=CORE.filter(k=>dn(STAGES.find(x=>x.k===k),s)).length;
  const complete=nextK===null;
  const card=document.createElement('div'); card.className='card'+(complete?' done':'');

  // tracker row — read-only stepper, aligned columns
  const nodes=STAGES.map(st=>{
   const d=dn(st,s), nx=st.k===nextK;
   const cls='tnode'+(d?' ok':'')+(nx?' next':'')+(st.manual?' manual':'')+(st.kind==='claude'?' claude':'');
   return `<div class="${cls}"><span class="dot"></span><span class="tlabel">${st.short||st.label}</span></div>`;
  }).join('');

  // action row — one control per column, directly under its node
  const cells=STAGES.map(st=>{
   const d=dn(st,s), nx=st.k===nextK, on=reachable(st,s);
   if(st.kind==='run'||st.kind==='sorter'){
    const cls='act'+(st.fda?' fda':'')+(nx?' go':'')+(d&&!nx?' done2':'');
    const tt=st.fda?' title="Reads your Photos library — your Terminal needs Full Disk Access (a macOS permission)"':'';
    if(st.kind==='sorter'){
      const lbl=(d?'✓ ':'')+'Categorize'+(s.recat?' ↗':'');
      return `<div class="acell"><button class="${cls}" ${on?'':'disabled'} data-cat="${s.batch}" data-built="${s.recat?1:''}">${lbl}</button></div>`;
    }
    return `<div class="acell"><button class="${cls}"${tt} ${on?'':'disabled'} data-action="${st.action}" data-batch="${s.batch}">${d?'✓ ':''}${st.label}</button></div>`;
   }
   if(st.kind==='claude'){
    if(d) return `<div class="acell"><button class="act done2" disabled>✓ ${st.label}</button></div>`;
    const p=st.prompt(s.batch);
    return `<div class="acell"><button class="act cl${nx?' go':''}" ${on?'':'disabled'} data-copy="${p.replace(/"/g,'&quot;')}" title="Copy this prompt → paste to Claude">🤖 ${st.label}</button></div>`;
   }
   return `<div class="acell"><span class="act ph" title="Open 📦 Delete (${s.batch} pilot) in Photos → Select All → ⌘⌫">${on?'<span class="kbd">⌘</span><span class="kbd">⌫</span> Photos':'Delete'}</span></div>`;
  }).join('');

  card.innerHTML=`<div class="chead"><b>${s.batch}</b><span class="prog">${complete?'✓ complete':coreDone+'/6'}</span><span class="nx">next: ${escapeHtml(s.next)}</span></div>
    <div class="stagewrap"><div class="track">${nodes}</div><div class="acts">${cells}</div></div>`;
  host.appendChild(card);
 });
}
function escapeHtml(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}

async function load(){ const r=await fetch('/api/status'); const j=await r.json(); render(j.batches); }

// run an action
async function run(action,batch){
 openLog(); setLog('run','running…',`$ ${action} ${batch}\n`);
 const r=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,batch})});
 const j=await r.json(); if(!j.job){setLog('err','error',JSON.stringify(j));return;}
 clearInterval(polling);
 polling=setInterval(async()=>{
   const jr=await(await fetch('/api/job?id='+j.job)).json();
   setLog(jr.status==='running'?'run':(jr.status==='done'?'done':'err'),
          (action+' '+batch+' · '+jr.status), jr.output||'');
   if(jr.status!=='running'){clearInterval(polling); load();}
 },700);
}
function openLog(){$('#log').classList.add('open');}
function setLog(state,title,text){
 $('#ldot').className='dot '+(state==='run'?'run':state==='done'?'done':state==='err'?'err':'');
 $('#ltitle').textContent=title; const pre=$('#lpre'); pre.textContent=text; pre.scrollTop=pre.scrollHeight;
}

function openSorter(b){window.open('/prev/pilot-'+b+'-recategorize.html','_blank');}
// Categorize = build the sorter (if needed) then open it in a new tab
function categorize(b,built){
 if(built){openSorter(b);return;}
 openLog(); setLog('run','building categorizer…',`$ recat ${b}\n`);
 fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'recat',batch:b})})
  .then(r=>r.json()).then(j=>{ if(!j.job){setLog('err','error',JSON.stringify(j));return;}
   clearInterval(polling);
   polling=setInterval(async()=>{ const jr=await(await fetch('/api/job?id='+j.job)).json();
     setLog(jr.status==='running'?'run':(jr.status==='done'?'done':'err'),'categorize '+b+' · '+jr.status,jr.output||'');
     if(jr.status!=='running'){clearInterval(polling); load(); if(jr.status==='done') openSorter(b);}
   },700);
  });
}
document.addEventListener('click',e=>{
 const cat=e.target.closest('[data-cat]'); if(cat&&!cat.disabled){categorize(cat.dataset.cat, cat.dataset.built==='1');return;}
 const a=e.target.closest('[data-action]'); if(a&&!a.disabled){run(a.dataset.action,a.dataset.batch);return;}
 const c=e.target.closest('[data-copy]'); if(c&&!c.disabled){navigator.clipboard.writeText(c.dataset.copy);const t=c.textContent;c.textContent='✓ copied';setTimeout(()=>c.textContent=t,1200);return;}
 if(e.target.closest('#lh')){$('#log').classList.toggle('open');}
});
$('#refresh').addEventListener('click',load);
// auto-refresh status: when you return to this tab (e.g. after saving in the sorter
// tab) and as a slow backstop — so buttons like Apply enable without a manual refresh
window.addEventListener('focus', load);
document.addEventListener('visibilitychange', ()=>{ if(document.visibilityState==='visible') load(); });
setInterval(()=>{ if(document.visibilityState==='visible') load(); }, 5000);
load();
</script></body></html>"""

if __name__ == "__main__":
    main()
