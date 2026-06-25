#!/usr/bin/env python3
"""dashboard.py — one HTML home base across ALL your batches: pipeline progress, the
next action for each, and links to its sorter, the category editor, and the notes viewer.
Read-only on your data; writes only the dashboard HTML. Pure stdlib."""
import sys, os, glob, html, webbrowser
sys.path.insert(0, os.path.dirname(__file__))
from lib import paths, SS, PREV
import status

OUT = f"{PREV}/photos-pilot-dashboard.html"
SHORT = ["export", "dedup", "privacy", "triage", "categorize", "saved", "applied", "archived"]

def list_batches():
    bs = []
    for d in glob.glob(f"{SS}/pilot/*/"):
        b = os.path.basename(d.rstrip("/"))
        if os.path.exists(os.path.join(d, "export.json")):
            bs.append(b)
    return sorted(bs, reverse=True)   # most recent (years) first

def main():
    bs = list_batches()
    has_editor = os.path.exists(f"{PREV}/photos-pilot-config-editor.html")
    has_viewer = os.path.exists(f"{PREV}/photos-pilot-summary.html")
    cards = []
    for b in bs:
        steps, nxt = status.step_status(b)
        total = len(steps)
        done = sum(1 for _, ok, _ in steps if ok)
        oks = [i for i, (_, ok, _) in enumerate(steps) if ok]
        last = max(oks) if oks else -1
        complete = last == total - 1          # archived (last stage) reached → effectively done
        next_idx = (last + 1) if not complete else -1
        P = paths(b)
        pills = []
        for i, ((label, ok, _), short) in enumerate(zip(steps, SHORT)):
            cls = "ok" if ok else ("next" if i == next_idx else "todo")
            pills.append(f'<span class="pill {cls}" title="{html.escape(label)}">{"✓ " if ok else ""}{short}</span>')
        links = []
        if os.path.exists(P["recat"]):
            links.append(f'<a href="{html.escape(os.path.basename(P["recat"]))}" target="_blank">Open sorter →</a>')
        prog = "✓ done" if complete else f"{done}/{total}"
        cards.append(
            f'<div class="card{" done" if complete else ""}">'
            f'<div class="chead"><b>{html.escape(b)}</b><span class="prog">{html.escape(prog)}</span></div>'
            f'<div class="pills">{"".join(pills)}</div>'
            f'<div class="next"><span class="lbl">next</span> {html.escape(nxt)}</div>'
            f'<div class="links">{" · ".join(links) or "<span class=muted>(open in Finder)</span>"}</div>'
            f'</div>')
    glinks = []
    if has_editor: glinks.append('<a href="photos-pilot-config-editor.html" target="_blank">⚙ Edit categories</a>')
    if has_viewer: glinks.append('<a href="photos-pilot-summary.html" target="_blank">📚 View notes</a>')
    body = "\n".join(cards) or '<p class="muted">No batches yet — run <code>pilot &lt;batch&gt;</code> in a Terminal with Photos access to start.</p>'
    page = (TEMPLATE.replace("__CARDS__", body)
                    .replace("__GLINKS__", " · ".join(glinks))
                    .replace("__N__", str(len(bs))))
    os.makedirs(PREV, exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(page)
    print(f"dashboard → {OUT}  ({len(bs)} batches)")
    try: webbrowser.open("file://" + OUT)
    except Exception: pass

TEMPLATE = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Photos Pilot — Dashboard</title><style>
*{box-sizing:border-box}
body{margin:0;background:#f6f7f9;color:#1f2328;font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI','Apple SD Gothic Neo',sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:860px;margin:0 auto;padding:26px 22px 60px}
header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:6px}
h1{font-size:22px;margin:0} .glinks a{color:#4f46e5;text-decoration:none;font-weight:600;font-size:14px;margin-left:16px}
.sub{color:#57606a;font-size:13px;margin:0 0 18px}
.card{background:#fff;border:1px solid #e6e9ef;border-radius:14px;padding:15px 18px;margin:12px 0;box-shadow:0 1px 2px #0000000a}
.card.done{border-color:#bfe3cf;background:#fcfffd}
.chead{display:flex;justify-content:space-between;align-items:baseline}
.chead b{font-size:17px} .prog{color:#57606a;font-size:12.5px;font-weight:700}
.pills{display:flex;gap:6px;flex-wrap:wrap;margin:11px 0 4px}
.pill{font-size:11.5px;font-weight:700;padding:4px 9px;border-radius:999px;background:#eef1f5;color:#9aa3b2;border:1px solid transparent;white-space:nowrap}
.pill.ok{background:#e6f6ec;color:#1a7f47} .pill.next{background:#eaf1ff;color:#2563eb;border-color:#b9d0ff}
.next{font-size:13.5px;margin-top:9px} .next .lbl{font-size:10.5px;font-weight:800;letter-spacing:.04em;text-transform:uppercase;color:#9aa3b2;margin-right:8px}
.links{margin-top:9px;font-size:13px} .links a{color:#4f46e5;text-decoration:none;font-weight:600}
.muted{color:#9aa3b2} code{background:#eef1f5;padding:1px 6px;border-radius:5px;font-size:.9em;font-family:'SF Mono',ui-monospace,Menlo,monospace}
.legend{color:#9aa3b2;font-size:12px;margin-top:20px}
.legend .pill{font-size:10.5px}
</style></head><body><div class="wrap">
<header><h1>📷 Photos Pilot — Dashboard</h1><div class="glinks">__GLINKS__</div></header>
<p class="sub">__N__ batch(es). Each shows pipeline progress and the next action. Read-only.</p>
__CARDS__
<p class="legend">Stages: <span class="pill ok">✓ done</span> <span class="pill next">next</span> <span class="pill todo">todo</span> &nbsp;·&nbsp; export → scan → triage → categorize → save → apply → notes, then group &amp; delete in Photos.</p>
</div></body></html>"""

if __name__ == "__main__":
    main()
