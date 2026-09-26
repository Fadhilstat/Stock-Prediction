# Ruang Risiko IDX Autonomous Non-RDC Production Container
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Install system runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy package dependency manifests first for layer caching
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install python package and dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e . && \
    pip install --no-cache-dir \
    streamlit==1.64.0 \
    duckdb==1.5.5 \
    xgboost==3.2.0 \
    statsmodels==0.15.0 \
    arch==8.0.0 \
    plotly==7.1.0 \
    pyarrow==25.0.1 \
    yfinance==0.2.57

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
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
