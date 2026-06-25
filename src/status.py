#!/usr/bin/env python3
"""status.py <year> — read-only "you are here → next step" checklist (pure stdlib).
Inspects which screensort artifacts exist for a year and prints the next action, so a
first-time user (or you, months later) always knows what to run next. Writes nothing."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from lib import paths

def step_status(batch):
    """(steps, next_cmd) for a batch. steps = [(label, exists, cmd), ...] in flow order.
    Reused by the CLI and by dashboard.py — single source for 'where am I / what's next'."""
    P = paths(batch); snap = f"{P['work']}/decisions.json"   # stable snapshot apply.py writes
    raw = [
        ("export.json",          P["export"],    f"screensort {batch}  (needs Photos access)"),
        ("dups.json",            P["dups"],      f"dedup.py {batch}"),
        ("sensitive.json",       P["sensitive"], f"sensitive.py {batch}  (privacy pre-filter)"),
        ("seed.json",            P["seed"],      f"triage (make_triage.py {batch} → agents → merge_seed.py {batch})"),
        ("sorter HTML",          P["recat"],     f"recat.py {batch}"),
        ("downloaded decisions", P["decisions"], "review sorter → ⬇ Download decisions"),
        ("fulltext + delete",    P["fulltext"],  f"apply.py {batch}"),
        ("archive notes",        P["archive"],   f"archive.py {batch}"),
    ]
    steps = [(label, os.path.exists(path), cmd) for label, path, cmd in raw]
    # 'next' = first incomplete step AFTER the furthest one reached — so a batch finished
    # via an older flow (missing newer intermediate artifacts) isn't told to redo them.
    oks = [i for i, (_, ok, _) in enumerate(steps) if ok]
    last = max(oks) if oks else -1
    nxt = next((cmd for i, (_, ok, cmd) in enumerate(steps) if not ok and i > last), None)
    if nxt is None:   # progressed to the end → final manual step (or re-apply if no snapshot)
        nxt = (f"screensort-tag {batch}  (needs Photos access) → delete the album with ⌘⌫"
               if os.path.exists(snap) else f"apply.py {batch}")
    return steps, nxt

def main():
    if len(sys.argv) < 2: sys.exit("usage: status.py <batch>")
    batch = sys.argv[1]
    steps, nxt = step_status(batch)
    print(f"screensort status — {batch}")
    for label, ok, _ in steps:
        print(f"  {'✓' if ok else '·'} {label}")
    print(f"\n→ next: {nxt}")

if __name__ == "__main__":
    main()
