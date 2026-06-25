#!/usr/bin/env python3
"""verify_deleted.py [year ...] — did the pilot DELETE-candidates actually leave the library?

Reads each batch's decisions.json (the DELETE-marked Photos UUIDs) and asks the live
Photos library, via osxphotos, which of them are: still ACTIVE in the library, sitting in
Recently Deleted (TRASH, 30-day undo), or GONE (deleted+purged or otherwise absent).
Also reports whether the `📦 Delete (<year> pilot)` album exists and how many items it holds.

Run in your Full Disk Access Terminal:
    ~/.osxphotos-venv/bin/python ~/photos-pilot/verify_deleted.py 2022 2023
"""
import sys, os, json
import osxphotos

VAULT = os.path.expanduser("~/Documents/Obsidian Vault")
PILOT = os.path.join(VAULT, "Screenshots", "pilot")


def delete_uuids(year):
    path = os.path.join(PILOT, year, "decisions.json")
    if not os.path.exists(path):
        return None
    dec = json.load(open(path))["decisions"]
    out = []
    for uuid, val in dec.items():
        cat = val if isinstance(val, str) else (val.get("cat") or val.get("category"))
        if cat == "DELETE":
            out.append(uuid)
    return out


def main():
    years = sys.argv[1:] or ["2021", "2022", "2023"]
    print("opening Photos library …")
    db = osxphotos.PhotosDB()
    album_titles = set(db.albums)

    for y in years:
        uu = delete_uuids(y)
        print("\n" + "=" * 60)
        if uu is None:
            print(f"{y}: no decisions.json found — skipping")
            continue
        uset = set(uu)
        # targeted queries; default excludes trash, intrash=True returns only trash
        active = {p.uuid for p in db.photos(uuid=uu)} & uset
        trash = {p.uuid for p in db.photos(uuid=uu, intrash=True)} & uset
        gone = uset - active - trash

        alb = next((a for a in album_titles if a.endswith(f"Delete ({y} pilot)") or
                    a == f"\U0001F4E6 Delete ({y} pilot)"), None)
        alb_count = None
        if alb:
            ai = next((a for a in db.album_info if a.title == alb), None)
            alb_count = len(ai.photos) if ai else None

        print(f"{y}: {len(uset)} DELETE-candidates")
        print(f"   ✓ still ACTIVE in library : {len(active)}")
        print(f"   🗑  in Recently Deleted     : {len(trash)}")
        print(f"   ⌫  GONE (purged/absent)    : {len(gone)}")
        print(f"   album '📦 Delete ({y} pilot)': "
              + (f"EXISTS ({alb_count} items)" if alb else "does NOT exist"))

        if len(active) == 0 and len(uset) > 0:
            print(f"   → VERDICT: 2-stage delete COMPLETE — none remain in the active library.")
        elif len(active) == len(uset):
            print(f"   → VERDICT: NOT deleted — all {len(uset)} still in the library "
                  f"({'album exists, so tagged but not ⌘⌫-deleted' if alb else 'pilot-tag never ran'}).")
        else:
            print(f"   → VERDICT: PARTIAL — {len(active)} still active, "
                  f"{len(trash)+len(gone)} removed.")


if __name__ == "__main__":
    main()
