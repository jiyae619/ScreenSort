#!/usr/bin/env python3
"""make_triage.py <batch> [calib_batch=auto] [chunk=60] — prep the LLM triage.
Builds a shared rubric (calibrated with the person's REAL past keep/delete decisions
from the most recently labeled batch, or a GENERIC cold-start rubric if there's no
history yet) + splits this batch's non-dup, non-sensitive items into chunk files for
parallel classifier agents. Each writes a part file; the orchestrator merges parts
-> seed.json. Pure stdlib."""
import sys, os, json, glob
sys.path.insert(0, os.path.dirname(__file__))
from lib import paths, CATEGORIES, PROTECT, DELETE, REVIEW, CONFIG, redact

RUBRIC = """# Screenshot triage — classify one person's saved screenshots

For EACH item decide a category + confidence + one-line why. You are mimicking
ONE person's taste; the calibration examples below are their REAL past decisions.

## Categories (pick exactly ONE)
__CATEGORIES__

## keep vs __DELETE__ — the test
KEEP if it carries a durable, reusable idea: a quote, framework, insight, book,
reference, lecture/study note, a substantive saved post/article, goals, self-knowledge.
ALSO KEEP long-form reflection, philosophy, journaling, study notes, and dense personal
essays — if the text is several sentences of ideas or reflection, keep it even if it
isn't obviously "useful." Substantive non-English text (e.g. Korean study/reflection)
is usually a real keeper — never delete it just for being long or hard to skim.
__DELETE__ if transient/operational: app UI/home screens, notifications, receipts/order
confirmations, one-off maps, ads/paywall fragments, chat with no insight, memes/photos
with no meaningful text, error pages, settings screens.

## Rules
- BIAS TOWARD KEEP when unsure (use conf=lo, or __REVIEW__). A wrongly-deleted keeper is
  far worse than junk slipping through — the human still skims the delete pile.
- LONG, DENSE text (many sentences of ideas/reflection) -> lean KEEP. Reserve a
  high-confidence __DELETE__ for clearly transient/operational screens — never for
  substantive writing just because it's hard to parse.
- Anything sensitive (passport/visa/IDs/payment/account numbers) -> __PROTECT__, never __DELETE__.
- conf: hi (clear), med (likely), lo (unsure). Use hi for __DELETE__ only when obviously junk.
- why: <= 8 words (English or Korean).

## Calibration — this person's REAL past decisions (match this taste)
__CALIB__

## Output
You will be told your chunk file and output file. Read the chunk (a JSON array of
{u,f,d,w,o} = uuid, filename, date, wordcount, ocr-snippet). Classify EVERY item.
Write a JSON array to your output file: {"u":<uuid>,"cat":<CATEGORY>,"conf":"hi|med|lo","why":"..."}
— one object per input item, same uuids, no prose, valid JSON only.
"""

def _pick_calib(current):
    """Most recent OTHER batch that has a decisions.json (newest applied = best calibration)."""
    base = os.path.dirname(paths(current)["work"])   # .../Screenshots/pilot
    best, best_m = None, -1.0
    for d in glob.glob(f"{base}/*/decisions.json"):
        b = os.path.basename(os.path.dirname(d))
        if b == str(current):
            continue
        m = os.path.getmtime(d)
        if m > best_m:
            best, best_m = b, m
    return best

def _generic_calib():
    """Cold-start few-shot when there's no labeled history: universal junk → delete.
    (KEEP guidance comes from the category descriptions already in the rubric.)"""
    d = DELETE
    return ["(no personal history yet — these are universal junk examples; KEEP anything that "
            "matches a category description above, and bias toward KEEP when unsure)",
            f'- [{d}] "battery at 20% — low power mode on"',
            f'- [{d}] "you have 3 new notifications"',
            f'- [{d}] "ad: 50% off — sale ends tonight"',
            f'- [{d}] "your order has shipped — track package"',
            f'- [{d}] "settings > display > brightness"']

def _calib_lines(cex, cdec):
    """Few-shot calibration lines from an export map + a {uuid: category} decisions map."""
    per, out = {}, []
    # delete role gets the most few-shot examples; review excluded (no taste to learn)
    caps = {c["name"]: (8 if c.get("role") == "delete" else 0 if c.get("role") == "review" else 3)
            for c in CATEGORIES}
    for u, cat in cdec.items():
        if u not in cex or per.get(cat, 0) >= caps.get(cat, 0):
            continue
        snip = " ".join((cex[u].get("ocr") or "").split())[:120]
        if cat != DELETE and len(snip) < 15:
            continue
        out.append(f'- [{cat}] "{snip}"')
        per[cat] = per.get(cat, 0) + 1
    return out

def build_rubric(calib_year, seed=None, cur_export=None):
    """Assemble the triage rubric. Calibration priority: (1) cold-start `seed` = THIS batch's
    hand-labeled samples (uuid→cat), (2) calib_year's real decisions, (3) generic cold-start.
    Returns (rubric, src, n_examples)."""
    cal_lines, src = [], None
    if seed:
        cal_lines = _calib_lines(cur_export or {}, seed)
        if cal_lines: src = f"your {len(seed)} labeled samples"
    if not cal_lines and calib_year:
        C = paths(calib_year)
        try:
            cex = {x["uuid"]: x for x in json.load(open(C["export"]))["screenshots"]}
            cdec = json.load(open(f"{C['work']}/decisions.json"))["decisions"]
            cal_lines = _calib_lines(cex, cdec)
            if cal_lines: src = f"batch '{calib_year}'"
        except Exception:
            cal_lines = []
    if not cal_lines:
        cal_lines, src = _generic_calib(), "generic (cold start)"
    cat_block = "\n".join(f"- {c['name']} — {c.get('desc','')}" for c in CATEGORIES)
    rubric = (RUBRIC.replace("__CATEGORIES__", cat_block)
                    .replace("__CALIB__", "\n".join(cal_lines))
                    .replace("__PROTECT__", PROTECT).replace("__REVIEW__", REVIEW)
                    .replace("__DELETE__", DELETE))
    return rubric, src, sum(1 for l in cal_lines if l.startswith("- "))

def main():
    if len(sys.argv) < 2: sys.exit("usage: make_triage.py <batch> [calib_batch] [chunk]")
    year = sys.argv[1]
    calib_year = sys.argv[2] if len(sys.argv) > 2 else _pick_calib(year)
    chunk = int(sys.argv[3]) if len(sys.argv) > 3 else 60   # small: classifier agents truncate big JSON output
    P = paths(year)
    if not os.path.exists(P["export"]):
        sys.exit(f"✗ No export for {year}. Run `pilot {year}` in your FDA Terminal first.")
    if CONFIG.get("privacy", {}).get("no_cloud"):
        sys.exit("ⓘ no_cloud mode is ON (config.privacy.no_cloud) — skipping LLM triage.\n"
                 "  Run dedup.py + sensitive.py, then sort in recat.py (keyword-seeded, fully local).")
    tdir = f"{P['work']}/_triage"; os.makedirs(tdir, exist_ok=True)

    items = json.load(open(P["export"]))["screenshots"]
    cur_export = {x["uuid"]: x for x in items}
    # cold-start bootstrap: if the user hand-labeled samples for THIS batch, calibrate from them
    seed = None
    if os.path.exists(P["seed_dl"]):
        try: seed = json.load(open(P["seed_dl"]))["decisions"]
        except Exception: seed = None
    rubric, calib_src, n_examples = build_rubric(calib_year, seed=seed, cur_export=cur_export)
    open(f"{tdir}/rubric.md", "w", encoding="utf-8").write(rubric)

    # --- chunks of items that need the LLM: skip dups (seeded DELETE), sensitive (seeded
    #     PROTECT — text never goes to the LLM), and any items the user already hand-labeled.
    dd = {}
    if os.path.exists(P["dups"]):
        dd = json.load(open(P["dups"])).get("drop", {})
    sens = {}
    if os.path.exists(P["sensitive"]):
        sens = json.load(open(P["sensitive"])).get("items", {})
    skip = set(dd) | set(sens) | set(seed or {})
    redact_on = CONFIG.get("privacy", {}).get("redact_pii", False)
    def _o(x):
        o = " ".join((x["ocr"] or "").split())[:600]
        return redact(o) if redact_on else o
    rows = [{"u":x["uuid"],"f":x["filename"],"d":(x["date"] or "")[:10],"w":x["wc"], "o":_o(x)}
            for x in items if x["uuid"] not in skip]
    for stale in glob.glob(f"{tdir}/chunk_*.json"):   # clear prior run's chunks so none are orphaned
        os.remove(stale)
    n = 0
    for i in range(0, len(rows), chunk):
        json.dump(rows[i:i+chunk], open(f"{tdir}/chunk_{n:02d}.json", "w"), ensure_ascii=False)
        n += 1
    seed_note = f" + {len(seed)} labeled samples" if seed else ""
    print(f"{len(rows)} items to triage ({len(dd)} dups + {len(sens)} sensitive{seed_note} skipped) → {n} chunks in {tdir}")
    if not sens and not os.path.exists(P["sensitive"]):
        print("note: no sensitive.json — run `python3 sensitive.py <batch>` first to keep private text local.")
    print(f"calibration: {calib_src} — {n_examples} examples")

if __name__ == "__main__":
    main()
