#!/usr/bin/env bash
# Turnkey Auto-Updater Installer for Ruang Risiko IDX
# Configures systemd timer to pull and deploy git updates every 60 seconds.

set -euo pipefail

TARGET_DIR="/opt/ruang-risiko-idx"
REPO_URL="https://github.com/Fadhilstat/Stock-Prediction.git"

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

# 1. Ensure repository exists and is synchronized to origin/main
if [ ! -d "${TARGET_DIR}/.git" ]; then
    echo "[1/4] Cloning repository to ${TARGET_DIR}..."
    $SUDO mkdir -p "${TARGET_DIR}"
    $SUDO git clone "${REPO_URL}" "${TARGET_DIR}"
else
    echo "[1/4] Synchronizing existing repository at ${TARGET_DIR}..."
    cd "${TARGET_DIR}"
    $SUDO git fetch origin main --quiet
    $SUDO git reset --hard origin/main
fi

cd "${TARGET_DIR}"
$SUDO chmod +x "${TARGET_DIR}/deploy/auto_update.sh"

# 2. Register systemd service
echo "[2/4] Registering systemd service..."
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

# 3. Register systemd timer (every 60 seconds)
echo "[3/4] Registering systemd timer (interval: 60s)..."
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

# 4. Activate timer and trigger initial update
echo "[4/4] Activating systemd timer and running deployment..."
if command -v systemctl &> /dev/null; then
    $SUDO systemctl daemon-reload
    $SUDO systemctl enable --now rridx-autoupdate.timer
fi

# Run auto-update with force to ensure the latest FastAPI container is up immediately
/bin/bash "${TARGET_DIR}/deploy/auto_update.sh" --force || true

echo "=========================================================="
echo "SUCCESS: Auto-updater is ACTIVE on the VPS."
echo "Every git push to origin/main will deploy within 60 seconds."
echo "Timer status: systemctl status rridx-autoupdate.timer"
echo "Log file: /var/log/rridx-autoupdate.log"
echo "=========================================================="
