#!/usr/bin/env python3
"""notes_done.py <batch> [count] — mark a batch's note integration COMPLETE.

Writes a tiny marker (pilot/<batch>/notes.json) that the cockpit reads to show the
'Notes' step as done (the note-writing is a Claude step, so it has no other on-disk
signal). Run this right after the kept items are integrated into Screenshots/summary/*.md
(the 'write the notes' step). Pure stdlib; safe to re-run."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from lib import paths


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: notes_done.py <batch> [count]")
    batch = sys.argv[1]
    count = sys.argv[2] if len(sys.argv) > 2 else None
    P = paths(batch)
    if not os.path.isdir(P["work"]):
        sys.exit(f"✗ no batch dir for {batch} — has it been exported?")
    payload = {"batch": str(batch), "status": "integrated into summary/*.md"}
    if count is not None:
        payload["items"] = count
    json.dump(payload, open(P["notes"], "w"), ensure_ascii=False)
    print(f"✓ notes marked integrated for {batch} → {P['notes']}")


if __name__ == "__main__":
    main()
