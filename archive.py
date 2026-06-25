#!/usr/bin/env python3
"""archive.py <year> — write the lossless raw-text archive (no Photos access).
One note per kept knowledge category under Screenshots/text-extract/<year>-pilot/.
Excludes PROTECT (sensitive; image kept) and DELETE. This is the 'text is the keeper'
record so deleting the images loses nothing."""
import sys, os, json, re, collections
sys.path.insert(0, os.path.dirname(__file__))
from lib import paths

def main():
    if len(sys.argv) < 2: sys.exit("usage: archive.py <year>")
    year = sys.argv[1]; P = paths(year)
    if not os.path.exists(P["export"]):
        sys.exit(f"✗ No export for {year}. Run `pilot {year}` in your FDA Terminal first.")
    if not os.path.exists(f"{P['work']}/decisions.json"):
        sys.exit(f"✗ No decisions snapshot for {year}. Run `apply.py {year}` first.")
    items = {x["uuid"]: x for x in json.load(open(P["export"]))["screenshots"]}
    dec = json.load(open(f"{P['work']}/decisions.json"))["decisions"]
    os.makedirs(P["archive"], exist_ok=True)
    CATS = ["AI","PM","DESIGN","MINDSET","CAREER","EVENTS","READING","PLACES"]  # PROTECT/DELETE excluded
    tagmap = {c: c.lower() for c in CATS}
    g = collections.defaultdict(list)
    for u, c in dec.items():
        if c in CATS and u in items: g[c].append(items[u])
    clean = lambda s: re.sub(r"[ \t]+", " ", s or "").strip()
    made = []
    for c in CATS:
        v = [x for x in sorted(g.get(c, []), key=lambda z: z["date"]) if x["wc"] >= 8]
        if not v: continue
        L = ["---", f'title: "{c.title()} — {year} pilot raw text (bilingual OCR)"', "tags:",
             "  - text-extract", f"  - {tagmap[c]}", f"created: {year}-pilot",
             f'note: "Lossless ko-KR+en-US OCR. Curated summary -> Screenshots/summary/{c.title()}.md"',
             "---", "", f"# {c.title()} — {year} pilot raw text",
             f"*{len(v)} screenshots · verbatim bilingual OCR · lossless record.*", ""]
        for x in v:
            L.append(f"## {x['filename']}  ({x['date'][:10]})"); L.append(clean(x["ocr"])); L.append("")
        open(f"{P['archive']}/{c.title()}.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
        made.append((c, len(v)))
    print(f"archive → {P['archive']}/")
    for c, n in made: print(f"  {c.title()}.md ({n})")

if __name__ == "__main__":
    main()
