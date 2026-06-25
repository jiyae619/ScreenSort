#!/usr/bin/env python3
"""apply.py <year> — fold the downloaded decisions into working files (no Photos access).
Snapshots decisions, dumps bilingual fulltext per note-category for Claude to write
notes from, and writes the delete list. Run after you Download decisions from the sorter."""
import sys, os, json, re, collections
sys.path.insert(0, os.path.dirname(__file__))
from lib import paths, CATEGORIES, DELETE

def main():
    if len(sys.argv) < 2: sys.exit("usage: apply.py <batch>")
    year = sys.argv[1]; P = paths(year)
    if not os.path.exists(P["export"]):
        sys.exit(f"✗ No export for {year}. Run `pilot {year}` in your FDA Terminal first.")
    if not os.path.exists(P["decisions"]):
        sys.exit(f"✗ No decisions for {year}. Download them from the sorter first (recat → ⬇ Download decisions).")
    items = {x["uuid"]: x for x in json.load(open(P["export"]))["screenshots"]}
    dec = json.load(open(P["decisions"]))["decisions"]
    json.dump({"decisions": dec}, open(f"{P['work']}/decisions.json", "w"))  # stable snapshot
    g = collections.defaultdict(list)
    for u, c in dec.items():
        if u in items: g[c].append(items[u])
    NOTE = [c["name"] for c in CATEGORIES if c.get("role") == "note"]
    clean = lambda s: re.sub(r"[ \t]+", " ", s or "").strip()
    L = []
    for c in NOTE:
        v = [x for x in sorted(g.get(c, []), key=lambda z: z["date"]) if x["wc"] >= 12]
        L.append(f"\n{'='*70}\n{c} ({len(v)} with text)\n{'='*70}")
        for x in v: L.append(f"\n[{x['filename']} | {x['date'][:10]} | w{x['wc']}]\n{clean(x['ocr'])}")
    open(P["fulltext"], "w", encoding="utf-8").write("\n".join(L) + "\n")
    D = [f"# {year} delete-candidates (favorites auto-excluded at tag time)\n"]
    for x in sorted(g.get(DELETE, []), key=lambda z: z["date"][:10]):
        D.append(f"{x['uuid']}\t{x['date'][:10]}\t{x['filename']}")
    open(P["delete"], "w", encoding="utf-8").write("\n".join(D) + "\n")
    print("counts:", {c: len(g[c]) for c in sorted(g)})
    print(f"fulltext → {P['fulltext']}  ({sum(len(g[c]) for c in NOTE)} note items)")
    print(f"delete   → {P['delete']}  ({len(g.get(DELETE, []))} items)")

if __name__ == "__main__":
    main()
