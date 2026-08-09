#!/usr/bin/env bash
# Update the hosted apps.json on the VPS.
# Runs hourly via cron (installed by install.sh). Safe to run manually.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$DIR/vps/vps.env" ]]; then
    # shellcheck disable=SC1091
    source "$DIR/vps/vps.env"
else
    echo "ERROR: $DIR/vps/vps.env not found (run install.sh first)" >&2
    exit 1
fi

mkdir -p "$WEBROOT"
python3 "$DIR/generate.py" --source-url "$SOURCE_URL/apps.json" --out "$DIR/apps.json"
cp "$DIR/apps.json" "$WEBROOT/apps.json"
echo "OK: updated $WEBROOT/apps.json"
