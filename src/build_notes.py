#!/usr/bin/env python3
"""build_notes.py <batch> [output_folder] [format] — turn a batch's KEPT items into
consistent, portable per-category notes. Deterministic structure: frontmatter, an auto
TL;DR (count + date span + top keywords), auto Keywords, and a dated Items list; the
"Key insights" section is left for you / Claude to fill. Writes to
<output_folder>/<batch>/ — never clobbers your consolidated notes. No [[wikilinks]] are
generated, so output is portable regardless of obsidian_links. format: markdown | html |
both (default from config.output.format). Read-only on the batch. Pure stdlib."""
import sys, os, re, json, datetime
sys.path.insert(0, os.path.dirname(__file__))
from lib import paths, CONFIG, CATEGORIES, PROTECT, DELETE, REVIEW, SS

_WORD = re.compile(r"[0-9a-z가-힣]+")
_STOP = set("the a an and or of to in for on with is are be this that it as at by from "
            "your you we our will can not but if so do does has have they them he she".split()) | {
    "오전", "오후", "요일", "www", "com", "co", "kr", "https", "http", "그리고", "하는", "있는",
    "것", "수", "등", "및", "이", "그", "저", "에", "를", "은", "는", "가", "로", "의", "page", "break",
    # common Korean function-word tokens (frequency extraction has no morphology, so filter the worst)
    "있다", "없다", "내가", "네가", "우리", "그것", "이것", "저것", "것이다", "것을", "것이", "것은", "것도",
    "지금", "너무", "정말", "그냥", "매우", "가장", "모든", "어떤", "무슨", "이런", "그런", "저런", "때문",
    "통해", "위해", "대해", "하지만", "그러나", "그래서", "또한", "또는", "일을", "일이", "사람", "사람들",
    "생각", "한다", "하고", "해서", "된다", "같은", "같이", "많은", "많이", "좋은", "좋다", "나는", "나의",
    "당신", "여기", "거기", "아니라", "에서", "에게", "으로", "라고", "하지", "한다는",
    "lte", "longblack", "long", "black", "무료로", "가입하기", "시작하기", "보세요", "우리는",
    "자신의", "새로운", "어떻게", "다른", "우리가", "내가는"}

def keywords(texts, n=10):
    cnt = {}
    for t in texts:
        for w in _WORD.findall((t or "").lower()):
            if len(w) < 2 or w.isdigit() or w in _STOP:
                continue
            cnt[w] = cnt.get(w, 0) + 1
    return [w for w, _ in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[:n]]

def _note_filter():
    note_names = {c["name"] for c in CATEGORIES if c.get("role") == "note"}
    nonnote = {PROTECT, DELETE, REVIEW} | {c["name"] for c in CATEGORIES if c.get("role") == "places"}
    return lambda c: c in note_names or c not in nonnote   # unknown (sorter-coined) → treated as note

def build_md(cat, items, batch):
    items = sorted(items, key=lambda x: x.get("date") or "")
    dates = [x["date"][:10] for x in items if x.get("date")]
    span = f"{dates[0]}–{dates[-1]}" if dates else batch
    kw = keywords([x.get("ocr") for x in items])
    clean = lambda s: " ".join((s or "").split())
    L = ["---", f"title: {cat} — {batch}", f"tags: [{cat.lower()}]", f"items: {len(items)}",
         f"updated: {datetime.date.today().isoformat()}", "---", "",
         f"# {cat} — {batch}", "",
         f"> **TL;DR** — {len(items)} screenshots kept ({span}). "
         "Ask Claude to summarize this note for a real synopsis.", "",
         "## Key insights", "*Ask Claude to summarize this note, or write your own.*", "",
         "## Keywords", "*auto-extracted, rough — ask Claude to refine*", "",
         (" ".join(f"`{w}`" for w in kw) or "*(none)*"), "",
         f"## Items ({len(items)})"]
    for x in items:
        snip = clean(x.get("ocr"))[:90] or "(no text)"
        L.append(f"- **{(x.get('date') or '')[:10]}** — {snip} — `{x.get('filename','')}`")
    return "\n".join(L) + "\n"

def main():
    if len(sys.argv) < 2:
        sys.exit("usage: build_notes.py <batch> [output_folder] [format]")
    batch = sys.argv[1]; P = paths(batch)
    out_root = os.path.expanduser(sys.argv[2]) if len(sys.argv) > 2 else \
        os.path.expanduser(CONFIG.get("output", {}).get("folder", "") or f"{SS}/summary")
    fmt = sys.argv[3] if len(sys.argv) > 3 else CONFIG.get("output", {}).get("format", "markdown")
    snap = f"{P['work']}/decisions.json"
    dec_path = snap if os.path.exists(snap) else P["decisions"]
    if not os.path.exists(dec_path) or not os.path.exists(P["export"]):
        sys.exit(f"✗ need applied decisions + export for {batch} (run apply.py first).")
    dec = json.load(open(dec_path))["decisions"]
    items = {x["uuid"]: x for x in json.load(open(P["export"]))["screenshots"]}
    is_note = _note_filter()
    groups = {}
    for u, c in dec.items():
        if u in items and is_note(c):
            groups.setdefault(c, []).append(items[u])
    if not groups:
        sys.exit(f"✗ no kept note-items for {batch}.")
    folder = f"{out_root}/{batch}"; os.makedirs(folder, exist_ok=True)
    written = []
    for cat, its in sorted(groups.items()):
        open(f"{folder}/{cat}.md", "w", encoding="utf-8").write(build_md(cat, its, batch))
        written.append((cat, len(its)))
    html_path = None
    if fmt in ("html", "both"):
        import summary_viewer
        page, _ = summary_viewer.render(folder)
        html_path = f"{folder}/index.html"
        open(html_path, "w", encoding="utf-8").write(page)
    print(f"built {len(written)} notes ({fmt}) → {folder}")
    for cat, k in written:
        print(f"  {cat}: {k} items")
    if html_path:
        print(f"  view: {html_path}")
    print("  (TL;DR + keywords are auto; fill 'Key insights' yourself or ask Claude)")

if __name__ == "__main__":
    main()
