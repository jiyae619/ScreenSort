#!/bin/bash
# Double-click to launch the Photos Pilot cockpit (opens in your browser).
# Grant this Terminal Full Disk Access once (System Settings → Privacy & Security
# → Full Disk Access) so Export / Group-deletes can read Photos.
#
# Uses the osxphotos venv if you set one up; otherwise the system python3 that
# `install.sh` installs into. Whichever has osxphotos + pyobjc.
PY="$HOME/.osxphotos-venv/bin/python"
[ -x "$PY" ] || PY="python3"
exec "$PY" "$HOME/photos-pilot/serve.py"
