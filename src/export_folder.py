#!/usr/bin/env python3
"""export_folder.py <folder> [batch] [n] — ingest LOOSE IMAGE FILES (not Apple Photos).

For users whose screenshots live in a folder (e.g. ~/Downloads) instead of the Photos
library. Reads up to n images (random sample), copies a thumbnail (sips), OCRs each
LOCALLY — Apple Vision if available, else tesseract — and writes export.json in the SAME
format the rest of the pipeline reads. No Photos library / no Full Disk Access needed.

Downstream is identical (dedup → sensitive → seed_sample/make_triage → recat → build_notes)
EXCEPT tag.py (Photos albums) doesn't apply: for loose files your DELETE list is delete.txt
— you remove those files yourself. Run on your Mac. OCR stays local either way."""
import sys, os, json, glob, random, hashlib, subprocess
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))
from lib import paths, CONFIG, ocr_langs

EXTS = (".png", ".jpg", ".jpeg", ".heic", ".gif", ".webp", ".tiff", ".bmp")
_TESS = {"en": "eng", "ko": "kor", "ja": "jpn", "es": "spa", "fr": "fra", "de": "deu",
         "zh": "chi_sim", "it": "ita", "pt": "por"}

def _vision_ocr(path, langs):
    import Vision, Quartz
    from Foundation import NSURL
    src = Quartz.CGImageSourceCreateWithURL(NSURL.fileURLWithPath_(path), None)
    if not src: return ""
    img = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
    if not img: return ""
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(0); req.setUsesLanguageCorrection_(True)
    req.setRecognitionLanguages_(langs)
    h = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img, {})
    h.performRequests_error_([req], None)
    obs = list(req.results() or [])
    obs.sort(key=lambda o: (round(-o.boundingBox().origin.y, 2), round(o.boundingBox().origin.x, 2)))
    return " ".join(o.topCandidates_(1)[0].string() for o in obs)

def _tess_langstr():
    try:
        installed = set(subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True).stdout.split())
    except Exception:
        installed = {"eng"}
    use = [_TESS.get(l, l) for l in CONFIG.get("languages", ["en"]) if _TESS.get(l, l) in installed]
    return "+".join(use or ["eng"])

def _tess_ocr(path, langstr):
    try:
        r = subprocess.run(["tesseract", path, "stdout", "-l", langstr], capture_output=True, text=True, timeout=40)
        return " ".join(r.stdout.split())
    except Exception:
        return ""

def main():
    if len(sys.argv) < 2: sys.exit("usage: export_folder.py <folder> [batch] [n]")
    folder = os.path.expanduser(sys.argv[1])
    batch = sys.argv[2] if len(sys.argv) > 2 else (os.path.basename(folder.rstrip("/")).lower() or "folder")
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    if not os.path.isdir(folder): sys.exit(f"✗ not a folder: {folder}")
    files = [f for f in glob.glob(f"{folder}/*") if f.lower().endswith(EXTS) and os.path.isfile(f)]
    if not files: sys.exit(f"✗ no images in {folder}")
    sample = random.sample(files, min(n, len(files)))

    vision = True
    try: import Vision  # noqa: F401
    except Exception: vision = False
    langs = ocr_langs() if vision else _tess_langstr()
    P = paths(batch)
    os.makedirs(P["work"], exist_ok=True); os.makedirs(P["thumbs"], exist_ok=True)
    shown = ",".join(langs) if isinstance(langs, list) else langs
    print(f"ingesting {len(sample)} of {len(files)} images from {folder} → batch '{batch}' "
          f"(OCR: {'Apple Vision' if vision else 'tesseract'} [{shown}])")
    out, fail = [], 0
    for i, src in enumerate(sorted(sample), 1):
        uid = hashlib.md5(os.path.abspath(src).encode()).hexdigest()[:16]
        dst = os.path.join(P["thumbs"], uid + ".jpg")
        try:
            subprocess.run(["sips", "-Z", "400", "-s", "format", "jpeg", src, "--out", dst],
                           capture_output=True, timeout=30)
        except Exception: pass
        try:
            txt = " ".join(((_vision_ocr(src, langs) if vision else _tess_ocr(src, langs)) or "").split())
        except Exception:
            txt = ""
        if not txt: fail += 1
        mt = datetime.fromtimestamp(os.path.getmtime(src)).isoformat(timespec="seconds")
        out.append({"uuid": uid, "date": mt, "filename": os.path.basename(src),
                    "favorite": False, "wc": len(txt.split()), "ocr": txt})
        if i % 10 == 0: print(f"  …{i}/{len(sample)}")
    json.dump({"meta": {"batch": batch, "source": folder, "count": len(out), "ocr_empty": fail},
               "screenshots": out}, open(P["export"], "w"), ensure_ascii=False, indent=1)
    print(f"\nDone. {len(out)} ingested ({fail} no-text). → {P['export']}")
    print(f"Next: dedup.py {batch} → sensitive.py {batch} → seed_sample.py {batch} (cold start) → make_triage → recat.py {batch}")
    print("Loose-file batch: tag.py/Photos albums don't apply — your DELETE list is delete.txt (remove those files yourself).")

if __name__ == "__main__":
    main()
