#!/usr/bin/env python3
"""tag.py <year> — RUN IN FDA TERMINAL. NON-DESTRUCTIVE.
Adds your Delete-marked + Places screenshots to review albums in Photos. Deletes
nothing — you review the '📦 Delete (<year> pilot)' album and swipe (30-day undo).
Allow Photos automation when prompted. Favorites are auto-excluded."""
import sys, os, json, collections
sys.path.insert(0, os.path.dirname(__file__))
from lib import paths
import osxphotos
from osxphotos import PhotosAlbum

def main():
    if len(sys.argv) < 2: sys.exit("usage: tag.py <year>")
    year = sys.argv[1]; P = paths(year)
    if not os.path.exists(P["export"]):
        sys.exit(f"✗ No export for {year}. Run `screensort {year}` in your Terminal with Photos access first.")
    if not os.path.exists(f"{P['work']}/decisions.json"):
        sys.exit(f"✗ No decisions snapshot for {year}. Run `apply.py {year}` first.")
    dec = json.load(open(f"{P['work']}/decisions.json"))["decisions"]
    fav = {x["uuid"] for x in json.load(open(P["export"]))["screenshots"] if x.get("favorite")}
    buckets = collections.defaultdict(list)
    for u, c in dec.items():
        if u in fav: continue
        if c == "DELETE":   buckets[f"📦 Delete ({year} pilot)"].append(u)
        elif c == "PLACES": buckets[f"📍 Places ({year} pilot)"].append(u)
    db = osxphotos.PhotosDB()
    print("Adding to albums (no deletions)…")
    for name, uuids in buckets.items():
        photos = db.photos(uuid=uuids)
        PhotosAlbum(name, verbose=lambda *a, **k: None).extend(photos)
        print(f"  {name}: {len(photos)}")
    print(f"\nDone. In Photos: open '📦 Delete ({year} pilot)' → Select All → delete (Recently Deleted, 30-day undo).")

if __name__ == "__main__":
    main()
