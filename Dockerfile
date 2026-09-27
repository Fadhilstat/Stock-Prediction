# Ruang Risiko IDX Autonomous Non-RDC Production Container
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8501 \
    HOST=0.0.0.0

WORKDIR /app

# Install system runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy package dependency manifests first for layer caching
COPY pyproject.toml README.md ./
RUN mkdir -p src/ruang_risiko_idx && touch src/ruang_risiko_idx/__init__.py

# Install python package and dependencies (cached unless pyproject.toml changes)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[models]"

# Copy application source code (cached layer above is preserved on code changes)
COPY src/ ./src/

# Ensure required application directory structure exists
RUN mkdir -p data/raw data/processed data/snapshots data/audit reports/risk reports/ml reports/passports reports/audit

# Copy application code, configuration, baseline data, and reports
COPY app/ ./app/
COPY config/ ./config/
COPY data/ ./data/
COPY reports/ ./reports/
COPY scripts/ ./scripts/

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/health || exit 1

ENTRYPOINT ["uvicorn", "ruang_risiko_idx.web_server:app", "--host", "0.0.0.0", "--port", "8501", "--workers", "2"]

