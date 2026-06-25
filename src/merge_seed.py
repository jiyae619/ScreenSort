#!/usr/bin/env python3
"""merge_seed.py <batch> — merge _triage/part_*.json into seed.json (pure stdlib).
Validates categories, ensures EVERY item that was SENT to triage is covered (missing
ones become REVIEW so they surface for human review, never silently dropped), and writes
the list of missing uuids to _triage/missing.json for an optional re-run. Items excluded
from triage on purpose (dups, sensitive, hand-labeled samples) are not expected here."""
import sys, os, json, glob
sys.path.insert(0, os.path.dirname(__file__))
from lib import paths, CATS, REVIEW

def main():
    if len(sys.argv) < 2: sys.exit("usage: merge_seed.py <batch>")
    batch = sys.argv[1]; P = paths(batch); tdir = f"{P['work']}/_triage"
    allow = set(CATS)
    def load(p, key):
        try: return json.load(open(p)).get(key, {}) if os.path.exists(p) else {}
        except Exception: return {}
    # the same set make_triage excluded from the chunks — so they aren't "missing"
    skip = set(load(P["dups"], "drop")) | set(load(P["sensitive"], "items")) | set(load(P["seed_dl"], "decisions"))
    expected = [x["uuid"] for x in json.load(open(P["export"]))["screenshots"] if x["uuid"] not in skip]
    seed, bad = {}, 0
    for pf in sorted(glob.glob(f"{tdir}/part_*.json")):
        try: arr = json.load(open(pf))
        except Exception as e: print(f"  ! {os.path.basename(pf)} unreadable: {e}"); continue
        for o in arr:
            u = o.get("u"); cat = o.get("cat")
            if not u: continue
            if cat not in allow: cat = REVIEW; bad += 1
            seed[u] = {"cat": cat, "conf": o.get("conf", "med"), "why": (o.get("why") or "")[:90]}
    missing = [u for u in expected if u not in seed]
    for u in missing:
        seed[u] = {"cat": REVIEW, "conf": "lo", "why": "unclassified — needs eyes"}
    json.dump({"batch": str(batch), "items": seed}, open(P["seed"], "w"), ensure_ascii=False, indent=1)
    json.dump(missing, open(f"{tdir}/missing.json", "w"))
    from collections import Counter
    c = Counter(v["cat"] for v in seed.values())
    print(f"to-triage items: {len(expected)} | classified: {len(expected)-len(missing)} | missing→{REVIEW}: {len(missing)} | invalid cat→{REVIEW}: {bad}")
    print("seed categories:", dict(c.most_common()))
    print(f"→ {P['seed']}")
    if missing: print(f"missing uuids → {tdir}/missing.json (re-run to recover)")

if __name__ == "__main__":
    main()
