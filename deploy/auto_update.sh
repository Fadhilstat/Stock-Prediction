#!/usr/bin/env bash
# Ruang Risiko IDX Autonomous Auto-Updater Daemon
# Periodically checks GitHub origin/main for new commits and auto-deploys without manual intervention.

set -euo pipefail

TARGET_DIR="/opt/ruang-risiko-idx"
LOG_FILE="/var/log/rridx-autoupdate.log"

log() {
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*" | tee -a "${LOG_FILE}" 2>/dev/null || echo "$*"
}

if [ ! -d "${TARGET_DIR}/.git" ]; then
    log "ERROR: ${TARGET_DIR} is not a valid git repository."
    exit 0
fi

cd "${TARGET_DIR}"

# Fetch remote changes silently
git fetch origin main --quiet 2>/dev/null || exit 0

LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse origin/main)

if [ "${LOCAL_HASH}" = "${REMOTE_HASH}" ]; then
    # Already up to date
    exit 0
fi

log "=========================================================="
log "NEW UPDATE DETECTED on origin/main!"
log "Current HEAD: ${LOCAL_HASH}"
log "Target HEAD:  ${REMOTE_HASH}"
log "Synchronizing workspace..."

git reset --hard origin/main

# Resolve docker compose binary
DOCKER_COMPOSE="docker compose"
if ! docker info &> /dev/null; then
    if sudo docker info &> /dev/null; then
        DOCKER_COMPOSE="sudo docker compose"
    fi
fi

log "Rebuilding and restarting app container..."
${DOCKER_COMPOSE} up -d --build app

# Reconnect to edge Caddy network if Caddy is present
if docker ps | grep -q ' caddy$'; then
    docker network connect ruang-risiko-idx_rridx_network caddy 2>/dev/null || true
fi

NEW_HASH=$(git rev-parse HEAD)
log "SUCCESS: Auto-update complete. Ruang Risiko IDX is running commit ${NEW_HASH}."
log "=========================================================="
