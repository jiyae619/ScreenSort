#!/usr/bin/env python3
"""sensitive.py <year> — privacy pre-filter, runs BEFORE LLM triage (no Photos access).

Scans each screenshot's LOCAL OCR text for sensitive content — the language-pack
lexicon (English base + the languages in config) plus an always-on structural PII
pass (SSN / IBAN / Luhn-checked card number / email+digits). Matches are routed to
PROTECT and written to sensitive.json, which make_triage.py reads to EXCLUDE them
from the chunks sent to the LLM. Net effect: nothing flagged sensitive ever leaves
the Mac. Pure stdlib; safe to re-run."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from lib import paths, sensitive_match, PROTECT

def main():
    if len(sys.argv) < 2: sys.exit("usage: sensitive.py <batch>")
    year = sys.argv[1]; P = paths(year)
    if not os.path.exists(P["export"]):
        sys.exit(f"✗ No export for {year}. Run `screensort {year}` in your Terminal with Photos access first.")
    items = json.load(open(P["export"]))["screenshots"]
    out = {}
    for x in items:
        why = sensitive_match(x.get("ocr") or "")
        if why:
            out[x["uuid"]] = {"cat": PROTECT, "why": why}
    json.dump({"items": out}, open(P["sensitive"], "w"), ensure_ascii=False)
    print(f"{len(out)} of {len(items)} flagged sensitive → {PROTECT} "
          f"(excluded from LLM triage) → {P['sensitive']}")

if __name__ == "__main__":
    main()
