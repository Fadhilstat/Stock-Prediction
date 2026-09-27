#!/usr/bin/env bash
# Ruang Risiko IDX Autonomous Auto-Updater Daemon
# Periodically checks GitHub origin/main for new commits and auto-deploys without manual intervention.

set -euo pipefail

TARGET_DIR="/opt/ruang-risiko-idx"
LOG_FILE="/var/log/rridx-autoupdate.log"
FORCE_BUILD=false

if [ "${1:-}" = "--force" ]; then
    FORCE_BUILD=true
fi

log() {
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*" | tee -a "${LOG_FILE}" 2>/dev/null || echo "$*"
}

if [ ! -d "${TARGET_DIR}/.git" ]; then
    log "ERROR: ${TARGET_DIR} is not a valid git repository."
    exit 0
fi

git config --global --add safe.directory "${TARGET_DIR}" 2>/dev/null || true

cd "${TARGET_DIR}"

# Fetch remote changes
git fetch origin main --quiet 2>/dev/null || exit 0

LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse origin/main)

if [ "${LOCAL_HASH}" = "${REMOTE_HASH}" ] && [ "${FORCE_BUILD}" = false ]; then
    # Already up to date
    exit 0
fi

log "=========================================================="
log "DEPLOYMENT TRIGGERED on origin/main!"
log "Current HEAD: ${LOCAL_HASH}"
log "Target HEAD:  ${REMOTE_HASH}"
log "Synchronizing workspace..."

git reset --hard origin/main

# Resolve docker binary and compose
DOCKER_BIN="docker"
DOCKER_COMPOSE="docker compose"
if ! docker info &> /dev/null; then
    if sudo docker info &> /dev/null; then
        DOCKER_BIN="sudo docker"
        DOCKER_COMPOSE="sudo docker compose"
    fi
fi

log "Recreating app container with FastAPI engine..."
${DOCKER_BIN} rm -f ruang_risiko_idx_app ruang-risiko-idx-app-1 2>/dev/null || true
${DOCKER_COMPOSE} up -d --build app

# Ensure edge Caddy network connection
if ${DOCKER_BIN} ps | grep -q 'caddy'; then
    ${DOCKER_BIN} network connect rridx_network signalflow-production-caddy-1 2>/dev/null || true
    ${DOCKER_BIN} network connect ruang-risiko-idx_rridx_network signalflow-production-caddy-1 2>/dev/null || true
fi

NEW_HASH=$(git rev-parse HEAD)
log "SUCCESS: Auto-update complete. Ruang Risiko IDX is running commit ${NEW_HASH}."
log "=========================================================="
