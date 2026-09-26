#!/usr/bin/env bash
# Ruang Risiko IDX Autonomous End-of-Day Ingestion & Model Pipeline
# Triggered autonomously at 16:30 WIB (09:30 UTC) Monday to Friday

set -euo pipefail

echo "=========================================================="
echo "  Ruang Risiko IDX: Autonomous EOD Pipeline Routine       "
echo "  Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")            "
echo "=========================================================="

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${APP_DIR}"

# 1. Update Market Data
echo "[1/4] Ingesting latest daily market prices..."
if [ -f "/opt/ruang-risiko-idx/.venv/bin/python" ]; then
    PYTHON="/opt/ruang-risiko-idx/.venv/bin/python"
else
    PYTHON="python3"
fi

${PYTHON} scripts/update_market_data.py

# 2. Build Analytics Parquet
echo "[2/4] Rebuilding analytics features..."
${PYTHON} scripts/build_analytics_dataset.py
${PYTHON} scripts/build_ml_dataset.py

# 3. Fit GARCH and Direction Models
echo "[3/4] Estimating GARCH volatility and machine learning direction snapshots..."
${PYTHON} scripts/build_latest_risk_snapshot.py
${PYTHON} scripts/build_latest_direction_snapshot.py

# 4. Verify Quality Gate
echo "[4/4] Verifying text style and test integrity..."
${PYTHON} scripts/check_text_rules.py

echo "EOD Autonomous pipeline completed successfully."
