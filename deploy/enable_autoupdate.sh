#!/usr/bin/env bash
# Turnkey Auto-Updater Installer for Ruang Risiko IDX
# Configures systemd timer to pull and deploy git updates every 60 seconds.

set -euo pipefail

TARGET_DIR="/opt/ruang-risiko-idx"
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo &> /dev/null; then
        SUDO="sudo"
    else
        echo "ERROR: Root privileges required." >&2
        exit 1
    fi
fi

echo "=========================================================="
echo "  Ruang Risiko IDX: Enabling 60s Auto-Update Timer"
echo "=========================================================="

if [ ! -d "${TARGET_DIR}" ]; then
    echo "ERROR: Target directory ${TARGET_DIR} does not exist." >&2
    exit 1
fi

chmod +x "${TARGET_DIR}/deploy/auto_update.sh"

echo "[1/3] Registering systemd service..."
cat << SYSTEMD_SERVICE | $SUDO tee /etc/systemd/system/rridx-autoupdate.service > /dev/null
[Unit]
Description=Ruang Risiko IDX Autonomous Git Auto-Updater
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=oneshot
User=root
WorkingDirectory=${TARGET_DIR}
ExecStart=/bin/bash ${TARGET_DIR}/deploy/auto_update.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SYSTEMD_SERVICE

echo "[2/3] Registering systemd timer (interval: 60s)..."
cat << SYSTEMD_TIMER | $SUDO tee /etc/systemd/system/rridx-autoupdate.timer > /dev/null
[Unit]
Description=Ruang Risiko IDX Continuous Auto-Update Check Timer (Every 60s)

[Timer]
OnBootSec=20s
OnUnitActiveSec=60s
AccuracySec=5s

[Install]
WantedBy=timers.target
SYSTEMD_TIMER

echo "[3/3] Activating systemd timer..."
$SUDO systemctl daemon-reload
$SUDO systemctl enable --now rridx-autoupdate.timer

echo "=========================================================="
echo "SUCCESS: Auto-updater is ACTIVE on the VPS."
echo "Every git push to origin/main will deploy within 60 seconds."
echo "Log file: /var/log/rridx-autoupdate.log"
echo "=========================================================="
