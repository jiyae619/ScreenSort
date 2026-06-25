#!/usr/bin/env python3
"""export.py <batch> — RUN IN FDA TERMINAL.
Reads a batch of screenshots from Photos, copies each preview thumbnail, and OCRs
it bilingually (ko-KR + en-US, accurate). Writes export.json. Read-only on Photos.

How to pick the batch (the default mode comes from config.batch_unit):
  export.py 2023                              # year  (default — backward compatible)
  export.py year 2023
  export.py date-range 2023-01-01 2023-06-30  # inclusive ISO dates
  export.py album "Travel 2023"               # every image in that Photos album
  export.py folder "Research"                 # every image in albums under that Photos folder
year/date-range select screenshots by date; album/folder take everything you curated."""
import sys, os, json, shutil
from datetime import date
sys.path.insert(0, os.path.dirname(__file__))
from lib import paths, CONFIG, parse_batch, ocr_langs
import osxphotos, Vision, Quartz
from Foundation import NSURL

OCR_LANGS = ocr_langs()   # from config (e.g. ["en-US","ko-KR"]); see lib.ocr_langs()

USAGE = (
    "usage: export.py <batch>\n"
    "  export.py 2023                              (year — default)\n"
    "  export.py year 2023\n"
    "  export.py date-range 2023-01-01 2023-06-30\n"
    "  export.py album \"Travel 2023\"\n"
    "  export.py folder \"Research\""
)

def ocr(path):
    url = NSURL.fileURLWithPath_(path)
    src = Quartz.CGImageSourceCreateWithURL(url, None)
    if not src: return ""
    img = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
    if not img: return ""
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(0); req.setUsesLanguageCorrection_(True)
    req.setRecognitionLanguages_(OCR_LANGS)
    h = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img, {})
    h.performRequests_error_([req], None)
    obs = list(req.results() or [])
    obs.sort(key=lambda o: (round(-o.boundingBox().origin.y, 2), round(o.boundingBox().origin.x, 2)))
    return " ".join(o.topCandidates_(1)[0].string() for o in obs)

def select(db, mode, sel):
    """Resolve (mode, selector) to a list of PhotoInfo. Raises ValueError on bad input.
    year/date-range = screenshots by date; album/folder = all images in the container."""
    def is_shot(p): return getattr(p, "screenshot", False) and getattr(p, "date", None)
    if mode == "year":
        y = int(sel[0])
        return [p for p in db.photos() if is_shot(p) and p.date.year == y]
    if mode == "date-range":
        s, e = date.fromisoformat(sel[0]), date.fromisoformat(sel[1])
        return [p for p in db.photos() if is_shot(p) and s <= p.date.date() <= e]
    if mode == "album":
        return [p for p in db.photos(albums=[sel[0]]) if p.isphoto and getattr(p, "date", None)]
    if mode == "folder":
        return [p for p in db.photos()
                if p.isphoto and getattr(p, "date", None)
                and any(sel[0] in (a.folder_names or []) for a in p.album_info)]
    raise ValueError(f"unknown mode {mode!r}")

def main():
    parsed = parse_batch(sys.argv[1:], CONFIG.get("batch_unit", "year"))
    if not parsed: sys.exit(USAGE)
    mode, sel, label = parsed
    P = paths(label)
    os.makedirs(P["work"], exist_ok=True); os.makedirs(P["thumbs"], exist_ok=True)
    print("Loading Photos library… (read-only)")
    db = osxphotos.PhotosDB()
    try:
        shots = select(db, mode, sel)
    except ValueError as e:
        sys.exit(f"✗ bad selector for '{mode}': {e}")
    if not shots:
        sys.exit(f"✗ no matching images for {mode} {' '.join(sel)}. "
                 f"(album/folder names are case-sensitive; check they exist in Photos.)")
    shots.sort(key=lambda p: p.date)
    print(f"{mode} {' '.join(sel)} → batch '{label}': {len(shots)} items. "
          f"Copying thumbnails + bilingual OCR (a few min)…")
    out, fail = [], 0
    for i, p in enumerate(shots, 1):
        dst = os.path.join(P["thumbs"], p.uuid + ".jpg")
        derivs = p.path_derivatives or []
        srcimg = derivs[0] if derivs else (p.path if p.path and os.path.exists(p.path) else None)
        txt = ""
        if srcimg and os.path.exists(srcimg):
            try: shutil.copy(srcimg, dst)
            except Exception: pass
            if os.path.exists(dst):
                try: txt = " ".join((ocr(dst)).split())
                except Exception: txt = ""
        if not txt: fail += 1
        out.append({"uuid": p.uuid, "date": p.date.isoformat(timespec="seconds"),
                    "filename": p.original_filename, "favorite": bool(getattr(p, "favorite", False)),
                    "wc": len(txt.split()), "ocr": txt})
        if i % 50 == 0: print(f"  …{i}/{len(shots)}")
    json.dump({"meta": {"batch": label, "mode": mode, "selector": sel, "count": len(out),
                        "languages": OCR_LANGS, "ocr_empty": fail},
               "screenshots": out}, open(P["export"], "w"), ensure_ascii=False, indent=1)
    print(f"\nDone. {len(out)} exported ({fail} no-text). → {P['export']}")
    print(f"Thumbnails → {P['thumbs']}")
    print(f"Next: tell Claude  “Run the screenshot pilot for {label}”  (it builds the sorter).")

if __name__ == "__main__":
    main()
