#!/bin/bash
# Double-click to launch the ScreenSort cockpit (opens in your browser).
# Grant this Terminal Full Disk Access once (System Settings → Privacy & Security
# → Full Disk Access) so Export / Group-deletes can read Photos.
#
# Self-locating: works wherever the repo lives. Uses the osxphotos venv if you set
# one up, else the system python3 that install.sh installs into.
DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$HOME/.osxphotos-venv/bin/python"
[ -x "$PY" ] || PY="python3"
exec "$PY" "$DIR/serve.py"
