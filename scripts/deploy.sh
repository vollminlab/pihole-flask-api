#!/bin/bash
set -euo pipefail

TARGET="${1:?Usage: $0 <host>}"
APP_DIR="/opt/pihole-flask-api"
VENV_DIR="/opt/pihole-flask-api-venv"
ENV_DIR="/etc/pihole-flask-api"
REPO_URL="https://github.com/svollmi1/pihole-flask-api.git"

read -rsp "PIHOLE_API_KEY for ${TARGET}: " API_KEY
echo

# Prevent Git Bash from mangling Linux paths before they reach SSH
export MSYS_NO_PATHCONV=1

ssh "$TARGET" sudo bash -s -- "$APP_DIR" "$VENV_DIR" "$ENV_DIR" "$REPO_URL" "$API_KEY" <<'ENDSSH'
set -euo pipefail
APP_DIR="$1"; VENV_DIR="$2"; ENV_DIR="$3"; REPO_URL="$4"; API_KEY="$5"

echo "==> Installing system dependencies"
DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv inotify-tools > /dev/null

echo "==> Deploying app to ${APP_DIR}"
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull --ff-only
elif [ -d "$APP_DIR" ]; then
    echo "    ${APP_DIR} exists but is not a git repo — backing up to ${APP_DIR}.bak"
    mv "$APP_DIR" "${APP_DIR}.bak"
    git clone "$REPO_URL" "$APP_DIR"
else
    git clone "$REPO_URL" "$APP_DIR"
fi

echo "==> Setting up virtualenv"
python3 -m venv --clear "$VENV_DIR"
"$VENV_DIR/bin/pip" install -q -r "$APP_DIR/requirements.txt"

echo "==> Creating log file"
touch /opt/pihole-api.log
chown www-data:www-data /opt/pihole-api.log

echo "==> Writing env file"
mkdir -p "$ENV_DIR"
printf 'PIHOLE_API_KEY=%s\n' "$API_KEY" > "$ENV_DIR/.env"
chown root:www-data "$ENV_DIR/.env"
chmod 640 "$ENV_DIR/.env"

echo "==> Installing scripts and services"
cp "$APP_DIR/scripts/fix-pihole-perms.sh" /usr/local/bin/fix-pihole-perms.sh
chmod +x /usr/local/bin/fix-pihole-perms.sh

sed "s|{{VENV}}|$VENV_DIR|g; s|{{APP}}|$APP_DIR|g" \
    "$APP_DIR/services/pihole-flask-api.service.tpl" \
    > /etc/systemd/system/pihole-flask-api.service
cp "$APP_DIR/services/fix-pihole-perms.service.tpl" \
    /etc/systemd/system/fix-pihole-perms.service

echo "==> Enabling and starting services"
systemctl daemon-reload
systemctl enable --now pihole-flask-api fix-pihole-perms

echo "==> Done: $(hostname)"
ENDSSH
