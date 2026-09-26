#!/usr/bin/env bash
# Ruang Risiko IDX 1-Command Production Setup Script (Zero-RDC)
# Target Domain: rridx.fadhilrusydi.com
# Usage: curl -sSL https://raw.githubusercontent.com/Fadhilstat/Stock-Prediction/main/deploy/setup_production.sh | bash -s -- --domain rridx.fadhilrusydi.com

set -euo pipefail

DOMAIN="rridx.fadhilrusydi.com"
EMAIL="admin@fadhilrusydi.com"

while [[ $# -gt 0 ]]; do
  case $1 in
    --domain)
      DOMAIN="$2"
      shift 2
      ;;
    --email)
      EMAIL="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

echo "=========================================================="
echo "  Ruang Risiko IDX: Turnkey Zero-RDC Production Setup     "
echo "  Target Domain: ${DOMAIN}                                "
echo "=========================================================="

TARGET_DIR="/opt/ruang-risiko-idx"

# 1. Install Docker if missing
if ! command -v docker &> /dev/null; then
    echo "[1/4] Installing Docker and container tools..."
    apt-get update
    apt-get install -y ca-certificates curl gnupg lsb-release git
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

# 2. Clone or Update Repository
echo "[2/4] Setting up application workspace at ${TARGET_DIR}..."
if [ -d "${TARGET_DIR}/.git" ]; then
    cd "${TARGET_DIR}"
    git pull origin main
else
    git clone https://github.com/Fadhilstat/Stock-Prediction.git "${TARGET_DIR}"
    cd "${TARGET_DIR}"
fi

# 3. Configure Environment
echo "[3/4] Writing production environment for domain ${DOMAIN}..."
cat << EOF > .env
CUSTOM_DOMAIN=${DOMAIN}
TLS_EMAIL=${EMAIL}
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=true
EOF

# 4. Launch Stack
echo "[4/4] Launching containerized application and Caddy TLS proxy..."
docker compose down || true
docker compose up -d --build

echo "Waiting for healthcheck..."
sleep 10
if docker compose exec -T app curl -f -s http://localhost:8501/_stcore/health > /dev/null; then
    echo "SUCCESS: Ruang Risiko IDX is live at https://${DOMAIN}"
else
    echo "WARNING: Service started, awaiting initial model load."
fi
