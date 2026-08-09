#!/usr/bin/env bash
# One-time VPS setup: clone the repo, install hourly auto-update cron,
# and run a tiny static file server for the source JSON.
#
# Usage:
#   sudo ./vps/install.sh <repo-url> [base-url] [port]
#
# Examples:
#   sudo ./vps/install.sh https://github.com/you/dopamine-repo.git
#   sudo ./vps/install.sh https://github.com/you/dopamine-repo.git http://123.45.67.89:8080 8080
#
# The base-url is what SideStore/AltStore will be pointed at. The default
# is http://<first-ip-of-the-machine>:8080 - change it if you have a domain.
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
    echo "ERROR: run with sudo" >&2
    exit 1
fi

REPO_URL="${1:?Usage: sudo ./vps/install.sh <repo-url> [base-url] [port]}"
DEFAULT_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
BASE_URL="${2:-http://${DEFAULT_IP:-127.0.0.1}:8080}"
PORT="${3:-8080}"

DEST="/opt/dopamine-repo"
WEBROOT="/var/www/dopamine-repo"

echo "==> Installing python3 and git"
apt-get update -y
apt-get install -y python3 git

echo "==> Cloning $REPO_URL into $DEST"
rm -rf "$DEST"
git clone --depth 1 "$REPO_URL" "$DEST"

mkdir -p "$WEBROOT"

echo "==> Writing vps.env"
cat > "$DEST/vps/vps.env" <<EOF
WEBROOT="$WEBROOT"
SOURCE_URL="$BASE_URL"
EOF

echo "==> Generating initial apps.json"
"$DEST/vps/update.sh"

echo "==> Installing hourly cron job"
cat > /etc/cron.d/dopamine-repo <<EOF
0 * * * * root $DEST/vps/update.sh >/dev/null 2>&1
EOF

echo "==> Installing static file server (port $PORT)"
cat > /etc/systemd/system/dopamine-repo.service <<EOF
[Unit]
Description=Dopamine AltStore source static server
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 -m http.server $PORT --directory $WEBROOT
DynamicUser=yes
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable dopamine-repo.service
systemctl restart dopamine-repo.service

echo
echo "Done. Your source URL is:  $BASE_URL/apps.json"
echo "Add it in SideStore/AltStore (Sources -> +)."
if command -v ufw >/dev/null 2>&1; then
    echo "NOTE: allow the port through the firewall:  sudo ufw allow $PORT/tcp"
fi
