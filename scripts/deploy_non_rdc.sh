#!/usr/bin/env bash
# Ruang Risiko IDX Autonomous Non-RDC Deployment Script
# Deploys headless container stack with automatic TLS reverse proxy

set -euo pipefail

echo "=========================================================="
echo "  Ruang Risiko IDX: Autonomous Non-RDC Deployment Routine "
echo "=========================================================="

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${APP_DIR}"

# 1. Environment Verification
echo "[1/5] Verifying environment and dependencies..."
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    DEPLOY_MODE="docker"
    echo "Found Docker and Docker Compose. Using containerized stack."
else
    DEPLOY_MODE="native"
    echo "Docker not detected. Falling back to native systemd/venv deployment."
fi

# 2. Pre-Flight Verification
echo "[2/5] Running pre-flight quality gates..."
if command -v python3 &> /dev/null; then
    python3 scripts/check_text_rules.py
    echo "Text rules passed (zero em dash violations)."
fi

# 3. Stack Deployment
if [ "${DEPLOY_MODE}" = "docker" ]; then
    echo "[3/5] Building and launching Docker container stack..."
    docker compose down --remove-orphans || true
    docker compose build --pull
    docker compose up -d

    # 4. Healthcheck Polling
    echo "[4/5] Polling health status on container..."
    MAX_ATTEMPTS=20
    ATTEMPT=1
    HEALTHY=0

    while [ ${ATTEMPT} -le ${MAX_ATTEMPTS} ]; do
        if docker compose exec -T app curl -s -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
            HEALTHY=1
            break
        fi
        echo "Waiting for Streamlit server to report healthy (attempt ${ATTEMPT}/${MAX_ATTEMPTS})..."
        sleep 2
        ATTEMPT=$((ATTEMPT + 1))
    done

    if [ ${HEALTHY} -eq 1 ]; then
        echo "[5/5] Deployment Successful!"
        echo "Ruang Risiko IDX is live and serving traffic."
        echo "Upstream: http://localhost:8501"
        echo "Proxy: http://localhost:80 / https://localhost:443"
    else
        echo "ERROR: Health check failed after ${MAX_ATTEMPTS} attempts."
        docker compose logs --tail=50 app
        exit 1
    fi
else
    echo "[3/5] Starting native systemd service..."
    if command -v systemctl &> /dev/null; then
        sudo systemctl restart ruang-risiko-idx.service
        sudo systemctl status ruang-risiko-idx.service --no-pager
    else
        echo "Starting background streamlit process..."
        nohup streamlit run app/app.py --server.port 8501 --server.address 0.0.0.0 > /tmp/rridx.log 2>&1 &
    fi
    echo "[5/5] Native deployment triggered."
fi
