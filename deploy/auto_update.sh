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

# Resolve docker binary and compose early
DOCKER_BIN="docker"
DOCKER_COMPOSE="docker compose"
if ! docker info &> /dev/null; then
    if sudo docker info &> /dev/null; then
        DOCKER_BIN="sudo docker"
        DOCKER_COMPOSE="sudo docker compose"
    fi
fi

IS_RUNNING=$(${DOCKER_BIN} ps --filter "name=ruang_risiko_idx_app" --filter "status=running" -q 2>/dev/null || true)

if [ "${LOCAL_HASH}" = "${REMOTE_HASH}" ] && [ "${FORCE_BUILD}" = false ] && [ -n "${IS_RUNNING}" ]; then
    # Already up to date and running healthy
    exit 0
fi

log "=========================================================="
log "DEPLOYMENT TRIGGERED on origin/main!"
log "Current HEAD: ${LOCAL_HASH}"
log "Target HEAD:  ${REMOTE_HASH}"
log "Synchronizing workspace..."

git reset --hard origin/main

log "Recreating app container with FastAPI engine..."
${DOCKER_BIN} rm -f ruang_risiko_idx_app ruang-risiko-idx-app-1 2>/dev/null || true
${DOCKER_COMPOSE} up -d --build app

# Ensure edge Caddy network connection, inject routing block if missing, and flush DNS
if ${DOCKER_BIN} ps | grep -q 'caddy'; then
    # Connect Caddy to RRIDX network
    ${DOCKER_BIN} network connect rridx_network signalflow-production-caddy-1 2>/dev/null || true
    ${DOCKER_BIN} network connect ruang-risiko-idx_rridx_network signalflow-production-caddy-1 2>/dev/null || true

    # Connect RRIDX app container to Caddy networks for bidirectional discovery
    CADDY_NETWORKS=$(${DOCKER_BIN} inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' signalflow-production-caddy-1 2>/dev/null || true)
    for cnet in ${CADDY_NETWORKS}; do
        ${DOCKER_BIN} network connect "${cnet}" ruang_risiko_idx_app 2>/dev/null || true
    done

    CADDY_HOST_FILE=$(${DOCKER_BIN} inspect -f '{{range .Mounts}}{{if eq .Destination "/etc/caddy/Caddyfile"}}{{.Source}}{{end}}{{end}}' signalflow-production-caddy-1 2>/dev/null || true)
    if [ -n "${CADDY_HOST_FILE}" ] && [ -f "${CADDY_HOST_FILE}" ]; then
        if ! grep -q "rridx.fadhilrusydi.com" "${CADDY_HOST_FILE}"; then
            printf "\n\nrridx.fadhilrusydi.com {\n    encode zstd gzip\n    reverse_proxy ruang_risiko_idx_app:8501 172.17.0.1:8501 {\n        lb_try_duration 3s\n    }\n}\n" >> "${CADDY_HOST_FILE}"
        fi
    fi

    ${DOCKER_BIN} exec signalflow-production-caddy-1 caddy reload --config /etc/caddy/Caddyfile 2>/dev/null || ${DOCKER_BIN} exec signalflow-production-caddy-1 caddy reload 2>/dev/null || true
fi

NEW_HASH=$(git rev-parse HEAD)
log "SUCCESS: Auto-update complete. Ruang Risiko IDX is running commit ${NEW_HASH}."
log "=========================================================="
