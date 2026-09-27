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
    fi
fi

if ${DOCKER_BIN} compose version &>/dev/null; then
    DOCKER_COMPOSE="${DOCKER_BIN} compose"
elif command -v docker-compose &>/dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif sudo command -v docker-compose &>/dev/null; then
    DOCKER_COMPOSE="sudo docker-compose"
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

CHANGES=$(git diff --name-only "${LOCAL_HASH}" "${REMOTE_HASH}" 2>/dev/null || echo "all")
git reset --hard origin/main

if echo "${CHANGES}" | grep -qE "pyproject\.toml|Dockerfile|docker-compose\.yml" || [ -z "${IS_RUNNING}" ] || [ "${FORCE_BUILD}" = true ]; then
    log "Dependencies or Dockerfile changed. Rebuilding container..."
    ${DOCKER_COMPOSE} up -d --build app
else
    log "Code-only update. Performing fast live restart of volume-mounted container..."
    ${DOCKER_BIN} restart ruang_risiko_idx_app || ${DOCKER_COMPOSE} restart app || ${DOCKER_COMPOSE} up -d app
fi

# Ensure edge Caddy network connection and stable upstream routing
if ${DOCKER_BIN} ps | grep -q 'caddy'; then
    CADDY_HOST_FILE=$(${DOCKER_BIN} inspect -f '{{range .Mounts}}{{if eq .Destination "/etc/caddy/Caddyfile"}}{{.Source}}{{end}}{{end}}' signalflow-production-caddy-1 2>/dev/null || true)
    if [ -n "${CADDY_HOST_FILE}" ] && [ -f "${CADDY_HOST_FILE}" ]; then
        python3 -c "
import sys, re
path = sys.argv[1]
try:
    with open(path, 'r') as f:
        content = f.read()
    target_block = '''rridx.fadhilrusydi.com {
    encode zstd gzip
    reverse_proxy 172.17.0.1:8501
}'''
    if 'rridx.fadhilrusydi.com' in content:
        content = re.sub(r'rridx\.fadhilrusydi\.com\s*\{[^}]*\}', target_block, content)
    else:
        content = content.rstrip() + '\n\n' + target_block + '\n'
    with open(path, 'w') as f:
        f.write(content)
except Exception:
    sys.exit(0)
" "${CADDY_HOST_FILE}" 2>/dev/null || true
    fi

    ${DOCKER_BIN} exec signalflow-production-caddy-1 caddy reload --config /etc/caddy/Caddyfile 2>/dev/null || \
    ${DOCKER_BIN} exec signalflow-production-caddy-1 caddy reload 2>/dev/null || \
    ${DOCKER_BIN} restart signalflow-production-caddy-1 2>/dev/null || true
fi

NEW_HASH=$(git rev-parse HEAD)
log "SUCCESS: Auto-update complete. Ruang Risiko IDX is running commit ${NEW_HASH}."
log "=========================================================="
