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

# Auto-detect sudo requirement
if [ "$EUID" -ne 0 ]; then
    if command -v sudo &> /dev/null; then
        SUDO="sudo"
    else
        echo "ERROR: Please run as root or install sudo." >&2
        exit 1
    fi
else
    SUDO=""
fi

# 1. Install Docker if missing
if ! command -v docker &> /dev/null; then
    echo "[1/4] Installing Docker and container tools..."
    $SUDO apt-get update
    $SUDO apt-get install -y ca-certificates curl gnupg lsb-release git
    $SUDO mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | $SUDO gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | $SUDO tee /etc/apt/sources.list.d/docker.list > /dev/null
    $SUDO apt-get update
    $SUDO apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

# 2. Clone or Update Repository
echo "[2/4] Setting up application workspace at ${TARGET_DIR}..."
if [ -d "${TARGET_DIR}/.git" ]; then
    echo "Updating existing Git repository at ${TARGET_DIR}..."
    cd "${TARGET_DIR}"
    $SUDO chown -R "$(id -u):$(id -g)" "${TARGET_DIR}" 2>/dev/null || true
    git fetch origin main
    git reset --hard origin/main
elif [ -d "${TARGET_DIR}" ]; then
    echo "Directory ${TARGET_DIR} exists but is not a valid Git repo. Re-initializing..."
    $SUDO rm -rf "${TARGET_DIR}"
    $SUDO mkdir -p "${TARGET_DIR}"
    $SUDO chown -R "$(id -u):$(id -g)" "${TARGET_DIR}" 2>/dev/null || true
    git clone https://github.com/Fadhilstat/Stock-Prediction.git "${TARGET_DIR}"
    cd "${TARGET_DIR}"
else
    $SUDO mkdir -p "$(dirname "${TARGET_DIR}")"
    $SUDO git clone https://github.com/Fadhilstat/Stock-Prediction.git "${TARGET_DIR}"
    $SUDO chown -R "$(id -u):$(id -g)" "${TARGET_DIR}" 2>/dev/null || true
    cd "${TARGET_DIR}"
fi

# Ensure workspace runtime directories exist
mkdir -p data/raw data/processed data/snapshots data/audit reports/risk reports/ml reports/passports reports/audit

# 3. Configure Environment
echo "[3/4] Writing production environment for domain ${DOMAIN}..."
cat << EOF > .env
CUSTOM_DOMAIN=${DOMAIN}
TLS_EMAIL=${EMAIL}
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=true
EOF

# 4. Resolve Docker Compose command
DOCKER_COMPOSE="docker compose"
if ! docker info &> /dev/null; then
    if $SUDO docker info &> /dev/null; then
        DOCKER_COMPOSE="${SUDO} docker compose"
    fi
fi
if ! ${DOCKER_COMPOSE} version &> /dev/null; then
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    elif $SUDO command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="${SUDO} docker-compose"
    fi
fi

# 5. Launch Stack
echo "[4/4] Launching containerized application and Caddy TLS proxy..."
${DOCKER_COMPOSE} down || true
${DOCKER_COMPOSE} up -d --build

echo "Waiting for healthcheck..."
sleep 10
if ${DOCKER_COMPOSE} exec -T app curl -f -s http://localhost:8501/_stcore/health > /dev/null; then
    echo "SUCCESS: Ruang Risiko IDX is live at https://${DOMAIN}"
else
    echo "NOTICE: Service started. Initial model load may take up to 30 seconds."
    echo "Check logs: ${DOCKER_COMPOSE} logs -f"
fi
