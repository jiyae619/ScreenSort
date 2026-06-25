#!/usr/bin/env python3
"""onboarding.py — first-run setup (pure stdlib). Run once by install.sh, or anytime
to reconfigure. Picks languages (installs their i18n packs: OCR code + sensitive
lexicon), the notes output folder/format, and prints the privacy consent summary.
Categories are preserved — edit those directly in config.json.

Non-interactive (for scripting/tests):
  onboarding.py --yes --languages en,ko --output "~/Notes/screens" --format markdown --no-obsidian
Interactive (default): prompts for each choice, English always on."""
import sys, os, json, glob, copy, argparse
sys.path.insert(0, os.path.dirname(__file__))
import lib

PACKS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "packs")

def available_packs():
    """lang -> pack dict, from packs/*.json."""
    out = {}
    for f in sorted(glob.glob(os.path.join(PACKS_DIR, "*.json"))):
        try:
            p = json.load(open(f, encoding="utf-8"))
            out[p["lang"]] = p
        except Exception as e:
            print(f"  ⚠ skipping bad pack {os.path.basename(f)}: {e}")
    return out

def load_config():
    """Existing config.json if present, else a copy of the built-in default."""
    if os.path.exists(lib.CONFIG_PATH):
        try:
            return json.load(open(lib.CONFIG_PATH, encoding="utf-8"))
        except Exception:
            pass
    return copy.deepcopy(lib.DEFAULT_CONFIG)

def ask(prompt, default):
    try:
        r = input(f"{prompt} [{default}]: ").strip()
    except EOFError:
        r = ""
    return r or default

def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--languages", help="comma list, e.g. en,ko (en always added)")
    ap.add_argument("--output", help="notes output folder")
    ap.add_argument("--format", choices=["markdown", "html", "both"])
    ap.add_argument("--obsidian", dest="obsidian", action="store_true")
    ap.add_argument("--no-obsidian", dest="obsidian", action="store_false")
    ap.add_argument("--yes", action="store_true", help="non-interactive; use flags/defaults")
    ap.set_defaults(obsidian=None)
    a = ap.parse_args()

    packs = available_packs()
    if "en" not in packs:
        sys.exit("✗ packs/en.json missing — the English base pack is required.")
    cfg = load_config()
    interactive = not a.yes

    print("\n📷 Photos Pilot — setup\n" + "─" * 40)

    # 1. languages -------------------------------------------------------
    if a.languages:
        chosen = [l.strip() for l in a.languages.split(",") if l.strip()]
    elif interactive:
        opts = [l for l in packs if l != "en"]
        print("Languages in your screenshots? English is always on. Available extras:")
        for l in opts:
            print(f"   {l}  — {packs[l]['name']}")
        raw = ask("Add which (comma list, blank for none)", ",".join(cfg.get("languages", ["en"])[1:]))
        chosen = [l.strip() for l in raw.split(",") if l.strip()]
    else:
        chosen = cfg.get("languages", ["en"])[1:]
    langs = ["en"] + [l for l in chosen if l != "en"]
    missing = [l for l in langs if l not in packs]
    if missing:
        sys.exit(f"✗ no pack for: {missing}. Add packs/<lang>.json or drop the language.")

    cfg["languages"] = langs
    cfg["ocr_languages"] = [packs[l]["ocr"] for l in langs]
    cfg.setdefault("sensitive_packs", {})
    for l in langs:
        cfg["sensitive_packs"][l] = packs[l].get("sensitive", [])

    # 2. output ----------------------------------------------------------
    out = cfg.get("output", {})
    if a.output:
        out["folder"] = a.output
    elif interactive:
        out["folder"] = ask("Notes output folder", out.get("folder", "~/Notes/screenshots"))
    if a.format:
        out["format"] = a.format
    elif interactive:
        out["format"] = ask("Output format (markdown/html/both)", out.get("format", "markdown"))
    if a.obsidian is not None:
        out["obsidian_links"] = a.obsidian
    elif interactive:
        out["obsidian_links"] = ask("Use Obsidian [[wikilinks]]? (y/n)",
                                    "y" if out.get("obsidian_links", False) else "n").lower().startswith("y")
    cfg["output"] = out

    # 3. validate + write ------------------------------------------------
    probs = lib._validate(cfg)
    if probs:
        print("⚠ config problems: " + "; ".join(probs))
    json.dump(cfg, open(lib.CONFIG_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("─" * 40)
    print(f"✓ languages   : {', '.join(langs)}   (OCR: {', '.join(cfg['ocr_languages'])})")
    print(f"✓ notes → {out.get('folder')}  ({out.get('format')}, "
          f"{'obsidian links' if out.get('obsidian_links') else 'portable links'})")
    print(f"✓ wrote {lib.CONFIG_PATH}")
    print("\n🔒 Privacy: screenshots are OCR'd locally; sensitive items are filtered out before")
    print("   any AI step; no photo is ever auto-deleted (you delete by hand in Photos).")
    print("Next: grant Full Disk Access to your terminal, then  `pilot <batch>`  to export.")

if __name__ == "__main__":
    main()
