#!/usr/bin/env python3
"""apply_config.py [path] — install a config.json edited in the browser category editor.
Validates it (unique hotkeys + the 4 reserved roles), backs up the current config to
config.json.bak, then installs it. Default source: ~/Downloads/config.json. Pure stdlib."""
import sys, os, json, shutil
sys.path.insert(0, os.path.dirname(__file__))
import lib

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Downloads/config.json")
    if not os.path.exists(src):
        sys.exit(f"✗ not found: {src}\n  (download it from config_editor.py first, or pass the path)")
    try:
        cfg = json.load(open(src, encoding="utf-8"))
    except Exception as e:
        sys.exit(f"✗ {src} isn't valid JSON: {e}")
    if not cfg.get("categories"):
        sys.exit(f"✗ {src} has no categories — refusing to install.")
    probs = lib._validate(cfg)
    if probs:
        sys.exit("✗ invalid config, not installing: " + "; ".join(probs))
    if os.path.exists(lib.CONFIG_PATH):
        shutil.copy(lib.CONFIG_PATH, lib.CONFIG_PATH + ".bak")
    json.dump(cfg, open(lib.CONFIG_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    names = [c["name"] for c in cfg["categories"]]
    print(f"✓ installed {len(names)} categories → {lib.CONFIG_PATH}")
    print(f"  {' · '.join(names)}")
    print(f"  backup: {lib.CONFIG_PATH}.bak")
    print("  next: re-run  recat.py <batch>  to rebuild the sorter with the new set.")

if __name__ == "__main__":
    main()
