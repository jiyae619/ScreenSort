#!/usr/bin/env python3
"""summary_viewer.py — render your knowledge notes into ONE standalone, offline HTML
you can read outside Obsidian and EXPORT TO PDF (browser print). Portable: strips YAML
frontmatter, turns [[wikilinks]] into in-page links (or plain text), no CDN / no beacon.
Reads the configured output folder (or Screenshots/summary). Read-only. Pure stdlib."""
import sys, os, re, glob, html, webbrowser
sys.path.insert(0, os.path.dirname(__file__))
from lib import CONFIG, SS, PREV

OUT = f"{PREV}/screensort-summary.html"

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "n"

def _inline(s, names):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*(?!\*)([^*]+?)\*", r"<em>\1</em>", s)
    def wl(m):
        name = m.group(1).split("|")[0].split("#")[0].strip()
        if name.lower() in names:
            return f'<a class="wl" href="#{slug(name)}">{html.escape(name)}</a>'
        return html.escape(name)
    s = re.sub(r"\[\[([^\]]+)\]\]", wl, s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s

def md_to_html(md, names):
    """Minimal Markdown → HTML (headings, lists, blockquote, hr, bold/italic/code,
    [[wikilinks]], links). Strips YAML frontmatter; returns body HTML."""
    lines = md.split("\n")
    if lines and lines[0].strip() == "---":      # YAML frontmatter
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            i += 1
        lines = lines[i + 1:]
    out, para, in_ul = [], [], False
    def flush_p():
        if para:
            out.append("<p>" + _inline(" ".join(para), names) + "</p>"); para.clear()
    def close_ul():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>"); in_ul = False
    for ln in lines:
        s = ln.rstrip()
        if not s.strip():
            flush_p(); close_ul(); continue
        if re.match(r"#{1,6}\s", s):
            flush_p(); close_ul()
            lvl = min(len(s) - len(s.lstrip("#")), 6)
            out.append(f"<h{lvl}>{_inline(s[lvl:].strip(), names)}</h{lvl}>")
        elif s.lstrip()[:2] in ("- ", "* "):
            flush_p()
            if not in_ul: out.append("<ul>"); in_ul = True
            out.append("<li>" + _inline(s.lstrip()[2:], names) + "</li>")
        elif s.startswith(">"):
            flush_p(); close_ul()
            out.append("<blockquote>" + _inline(s.lstrip("> ").strip(), names) + "</blockquote>")
        elif re.match(r"-{3,}$", s.strip()):
            flush_p(); close_ul(); out.append("<hr>")
        else:
            close_ul(); para.append(s.strip())
    flush_p(); close_ul()
    return "\n".join(out)

def render(folder):
    """Render every .md note in `folder` into one standalone HTML string. Returns (html, n)."""
    files = glob.glob(f"{folder}/*.md")
    # INDEX first, then alphabetical by name
    files.sort(key=lambda p: (os.path.basename(p).lower() != "index.md", os.path.basename(p).lower()))
    names = {os.path.splitext(os.path.basename(f))[0].lower() for f in files}
    nav, body = [], []
    for f in files:
        stem = os.path.splitext(os.path.basename(f))[0]
        sid = slug(stem)
        nav.append(f'<a href="#{sid}">{html.escape(stem)}</a>')
        body.append(f'<section id="{sid}">' + md_to_html(open(f, encoding="utf-8").read(), names) + "</section>")
    page = (TEMPLATE.replace("__NAV__", "\n".join(nav))
                    .replace("__BODY__", "\n".join(body))
                    .replace("__FOLDER__", html.escape(folder)))
    return page, len(files)

def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else (CONFIG.get("output", {}).get("folder", "") or f"{SS}/summary")
    folder = os.path.expanduser(folder)
    if not os.path.isdir(folder):
        sys.exit(f"✗ no notes folder: {folder}")
    page, n = render(folder)
    if not n:
        sys.exit(f"✗ no .md notes in {folder}")
    os.makedirs(PREV, exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(page)
    print(f"summary viewer → {OUT}  ({n} notes)")
    try: webbrowser.open("file://" + OUT)
    except Exception: pass

TEMPLATE = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Knowledge Notes</title><style>
:root{--ink:#1f2328;--muted:#57606a;--line:#eaecef;--accent:#4f46e5}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,'Segoe UI','Apple SD Gothic Neo',sans-serif;-webkit-font-smoothing:antialiased}
.topbar{position:sticky;top:0;z-index:10;background:rgba(255,255,255,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:11px 20px;display:flex;align-items:center;justify-content:space-between}
.topbar b{font-size:15px} .topbar .src{color:var(--muted);font-size:12px}
button.pdf{background:var(--accent);color:#fff;border:0;border-radius:8px;padding:8px 15px;font-size:13.5px;font-weight:700;cursor:pointer}
.layout{display:flex;max-width:1080px;margin:0 auto;align-items:flex-start}
nav.toc{position:sticky;top:49px;width:200px;flex:0 0 200px;padding:18px 10px;max-height:calc(100vh - 49px);overflow:auto;border-right:1px solid var(--line);font-size:13.5px}
nav.toc a{display:block;color:var(--muted);text-decoration:none;padding:5px 9px;border-radius:7px;font-weight:600}
nav.toc a:hover{background:#f0f2f5;color:var(--ink)}
main{flex:1;min-width:0;padding:8px 38px 60px}
section{padding:14px 0 26px;border-bottom:1px solid var(--line)}
h1{font-size:27px;letter-spacing:-.01em;margin:18px 0 10px} h2{font-size:19px;margin:26px 0 8px;padding-bottom:5px;border-bottom:1px solid var(--line)} h3{font-size:16px;margin:18px 0 6px}
p{margin:9px 0;max-width:760px} ul{padding-left:22px;max-width:760px} li{margin:6px 0}
blockquote{border-left:3px solid var(--accent);margin:12px 0;padding:7px 16px;color:var(--muted);background:#f7f7ff;border-radius:0 8px 8px 0;max-width:760px}
code{background:#eff1f3;padding:1px 6px;border-radius:5px;font-size:.86em;font-family:'SF Mono',ui-monospace,Menlo,monospace}
a{color:var(--accent)} a.wl{text-decoration:none;font-weight:600}
hr{border:0;border-top:1px solid var(--line);margin:18px 0}
@media print{
  .topbar,nav.toc{display:none} .layout{display:block;max-width:none} main{padding:0}
  section{page-break-before:always;border:0;padding:0} section:first-of-type{page-break-before:auto}
  blockquote{background:#f4f4f4}
}
</style></head><body>
<div class="topbar"><div><b>📚 Knowledge Notes</b> &nbsp;<span class="src">__FOLDER__</span></div>
<button class="pdf" onclick="window.print()">🖨 Export to PDF</button></div>
<div class="layout">
<nav class="toc">__NAV__</nav>
<main>__BODY__</main>
</div></body></html>"""

if __name__ == "__main__":
    main()
