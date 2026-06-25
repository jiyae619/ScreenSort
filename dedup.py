#!/usr/bin/env python3
"""dedup.py <year> — RUN BY CLAUDE (pure stdlib, no Photos access).
Find near-duplicate screenshots by OCR-text similarity — scroll-captures of the
same article, re-saves, the same image in two formats — and write dups.json
mapping each redundant uuid -> the representative it duplicates. recat.py then
seeds those as DELETE so you never hand-delete copies. Favorites are never dropped.
Runs before the LLM triage; the triage skips anything already marked a dup."""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(__file__))
from lib import paths

_WORD = re.compile(r"[0-9a-z가-힣]+")
# strip subscription/nav boilerplate that otherwise inflates similarity
_BOILER = {"longblack", "long", "black", "오전", "오후", "요일", "무료로", "시작하기",
           "www", "com", "co", "kr", "https", "http", "the", "and", "you", "that"}

def toks(ocr):
    ws = _WORD.findall((ocr or "").lower())
    return set(w for w in ws if len(w) > 1 and not w.isdigit() and w not in _BOILER)

def near(a, b):
    inter = len(a & b)
    if not inter: return False
    # high Jaccard (same content) OR strong containment (one screen is a subset of another)
    return (inter / len(a | b)) >= 0.82 or (inter / min(len(a), len(b))) >= 0.90

def main():
    if len(sys.argv) < 2: sys.exit("usage: dedup.py <batch>")
    year = sys.argv[1]; P = paths(year)
    if not os.path.exists(P["export"]):
        sys.exit(f"✗ No export for {year}. Run `pilot {year}` in your FDA Terminal first.")
    items = sorted(json.load(open(P["export"]))["screenshots"], key=lambda x: x.get("date") or "")
    reps = []           # [uuid, tokenset]
    index = {}          # rare-ish token -> [rep idx]  (prefilter to avoid O(n^2))
    drop, groups = {}, {}
    for x in items:
        u = x["uuid"]; ts = toks(x.get("ocr"))
        match = None
        if not x.get("favorite") and ts:                       # never dedupe a favorite away
            cand = set()
            for t in sorted(ts, key=len, reverse=True)[:6]:
                cand.update(index.get(t, []))
            for ri in cand:
                rts = reps[ri][1]
                if len(ts) < 5 and ts != rts: continue         # short text: require exact token match
                if near(ts, rts): match = ri; break
        if match is None:
            ri = len(reps); reps.append([u, ts]); groups[u] = [u]
            for t in sorted(ts, key=len, reverse=True)[:6]:
                index.setdefault(t, []).append(ri)
        else:
            ru = reps[match][0]; drop[u] = ru; groups[ru].append(u)
            reps[match][1] = reps[match][1] | ts               # widen rep so scroll-series chain
    multi = {k: v for k, v in groups.items() if len(v) > 1}
    json.dump({"year": str(year), "n_items": len(items), "n_drop": len(drop),
               "drop": drop, "groups": multi},
              open(P["dups"], "w"), ensure_ascii=False, indent=1)
    print(f"{len(items)} items → {len(drop)} near-dups across {len(multi)} groups → {P['dups']}")

if __name__ == "__main__":
    main()
