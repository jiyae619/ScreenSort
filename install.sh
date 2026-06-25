#!/usr/bin/env bash
# install.sh — one-time setup for photos-pilot (macOS).
# Installs Python deps, adds shell aliases, installs the /photos-pilot agent skill,
# runs onboarding, and opens the Full Disk Access pane. Idempotent; safe to re-run.
set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
say() { printf "\n\033[1;36m%s\033[0m\n" "$1"; }
ok()  { printf "  \033[32m✓\033[0m %s\n" "$1"; }
warn(){ printf "  \033[33m!\033[0m %s\n" "$1"; }

say "📷 photos-pilot installer"
[ "$(uname)" = "Darwin" ] || { warn "macOS only (needs Apple Photos + Vision OCR). Aborting."; exit 1; }
command -v python3 >/dev/null || { warn "python3 not found. Install it (e.g. from python.org or Xcode CLT) and re-run."; exit 1; }
ok "macOS + python3 present"

# 1. Python deps — must import from THIS python3 (so: pip, not pipx). -------
say "1/5 · Python dependencies"
DEPS="osxphotos pyobjc-framework-Vision pyobjc-framework-Quartz pyobjc-framework-Cocoa"
if python3 -m pip install --user --upgrade $DEPS 2>/tmp/pp_pip.log; then
  ok "installed: osxphotos + pyobjc (Vision/Quartz/Cocoa)"
elif python3 -m pip install --user --upgrade --break-system-packages $DEPS 2>>/tmp/pp_pip.log; then
  ok "installed (with --break-system-packages)"
else
  warn "pip install failed — see /tmp/pp_pip.log. If you use a venv/conda, activate it and run:"
  warn "  python3 -m pip install $DEPS"
fi

# 2. Shell aliases (idempotent) -------------------------------------------
say "2/5 · Shell aliases (pilot / pilot-tag)"
ZRC="$HOME/.zshrc"; touch "$ZRC"
add_alias() { # name  target
  if grep -q "alias $1=" "$ZRC" 2>/dev/null; then ok "alias $1 already set"; else
    printf "alias %s='python3 %s/%s'\n" "$1" "$DIR" "$2" >> "$ZRC"; ok "added alias $1"; fi
}
add_alias pilot     export.py
add_alias pilot-tag tag.py
warn "run 'source ~/.zshrc' (or open a new terminal) to load the aliases"

# 3. Install the /photos-pilot agent skill --------------------------------
say "3/5 · Claude Code skill (/photos-pilot)"
SKILLS="$HOME/.claude/skills"; mkdir -p "$SKILLS"
if [ -d "$DIR/skills/photos-pilot" ]; then
  ln -sfn "$DIR/skills/photos-pilot" "$SKILLS/photos-pilot"
  ok "linked $SKILLS/photos-pilot → repo (use /photos-pilot in Claude Code)"
  [ -f "$DIR/AGENTS.md" ] && ok "Codex users: see $DIR/AGENTS.md"
else
  warn "skills/photos-pilot not found in repo — skipping skill install"
fi

# 4. Onboarding (languages, output, consent) ------------------------------
say "4/5 · Onboarding"
python3 "$DIR/onboarding.py" || warn "onboarding skipped/failed — re-run: python3 $DIR/onboarding.py"

# 5. Full Disk Access -----------------------------------------------------
say "5/5 · Full Disk Access (required for Photos)"
warn "Opening System Settings → Privacy & Security → Full Disk Access."
warn "Add your terminal app, toggle it ON, then FULLY QUIT & REOPEN the terminal."
open "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles" 2>/dev/null || true

say "Done."
echo "  Next: open a fresh terminal, then  pilot <batch>   (e.g.  pilot 2023)"
echo "  Then in Claude Code:  /photos-pilot <batch>         (drives dedup → triage → sorter)"
echo "  Home base (all batches): python3 $DIR/dashboard.py    ·    one batch: python3 $DIR/status.py <batch>"
