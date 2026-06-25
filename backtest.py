#!/usr/bin/env python3
"""backtest.py <batch> — how well did the LLM triage match your REAL decisions?

Read-only: compares files already on disk — seed.json (what triage PROPOSED) vs
decisions.json (what you ACTUALLY chose after review) — so it re-runs nothing.
Reports the keep-vs-delete confusion, the dangerous FALSE-DELETE rate (keepers the
triage wanted to throw away), and category-match accuracy. Use it to decide how far
to trust the auto-delete pile before sharing the tool. Pure stdlib."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from lib import paths, DELETE

def _load_decisions(P):
    snap = f"{P['work']}/decisions.json"          # stable snapshot apply.py writes
    for p in (snap, P["decisions"]):
        if os.path.exists(p):
            return json.load(open(p))["decisions"]
    return None

def main():
    if len(sys.argv) < 2: sys.exit("usage: backtest.py <batch>")
    batch = sys.argv[1]; P = paths(batch)
    if not os.path.exists(P["seed"]):
        sys.exit(f"✗ no seed.json for {batch} — need a batch that was LLM-triaged.")
    dec = _load_decisions(P)
    if dec is None:
        sys.exit(f"✗ no decisions for {batch} — need a batch you've already sorted + applied.")
    seed = json.load(open(P["seed"]))["items"]
    items = {x["uuid"]: x for x in json.load(open(P["export"]))["screenshots"]} if os.path.exists(P["export"]) else {}

    common = [u for u in seed if u in dec]
    cd = ck = fd = fk = 0          # correct-delete, correct-keep, false-delete, false-keep
    cat_hit = cat_tot = 0          # category exact-match among items both kept
    fd_items, fd_conf = [], {"hi": 0, "med": 0, "lo": 0}
    for u in common:
        pred, truth = seed[u].get("cat"), dec[u]
        pd, td = (pred == DELETE), (truth == DELETE)
        if pd and td: cd += 1
        elif not pd and not td:
            ck += 1; cat_tot += 1; cat_hit += (pred == truth)
        elif pd and not td:        # triage said DELETE, you KEPT it — the dangerous error
            fd += 1; fd_conf[seed[u].get("conf", "lo")] = fd_conf.get(seed[u].get("conf", "lo"), 0) + 1
            x = items.get(u, {}); fd_items.append((seed[u].get("conf", "?"), truth, x.get("filename", u[:8]),
                                                   " ".join((x.get("ocr") or "").split())[:80]))
        else: fk += 1             # triage said keep, you deleted — just extra review, not dangerous

    n = len(common); keepers = ck + fd; deletes_pred = cd + fd
    print(f"\nBACKTEST — batch '{batch}'  (seed.json vs decisions.json, read-only)")
    print(f"  {n} LLM-triaged items compared  ({len(dec)-n} more were dedup/sensitive/manual, not LLM keep/delete calls)\n")
    acc = (cd + ck) / n * 100 if n else 0
    print(f"  keep/delete accuracy : {acc:.1f}%   ({cd+ck}/{n} agreed)")
    print(f"  ✓ correct keep       : {ck}")
    print(f"  ✓ correct delete     : {cd}")
    print(f"  ⚠ FALSE DELETE       : {fd}   (you KEPT these; triage wanted to delete)"
          + (f"  → {fd/keepers*100:.1f}% of your {keepers} keepers" if keepers else ""))
    print(f"      by confidence      hi={fd_conf.get('hi',0)} · med={fd_conf.get('med',0)} · lo={fd_conf.get('lo',0)}"
          f"   (hi false-deletes are the scary ones)")
    print(f"  · false keep         : {fk}   (triage kept; you deleted — just extra review, safe)")
    if deletes_pred:
        print(f"  delete precision     : {cd/deletes_pred*100:.1f}%   (of what triage marked delete, this much you also deleted)")
    if cat_tot:
        print(f"  category match       : {cat_hit/cat_tot*100:.1f}%   ({cat_hit}/{cat_tot} kept items filed the same)")
    if fd_items:
        print(f"\n  the {len(fd_items)} false-deletes (skim these — would auto-delete have lost them?):")
        for conf, truth, fn, snip in sorted(fd_items)[:15]:
            print(f"    [{conf:3}] →{truth:8} {fn:20} {snip}")
    print()

if __name__ == "__main__":
    main()
