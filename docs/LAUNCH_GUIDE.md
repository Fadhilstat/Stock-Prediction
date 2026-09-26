# Ruang Risiko IDX: Production Launch and Non-RDC Operational Guide

## 1. Executive Summary & Zero-RDC Mandate
This guide specifies the autonomous, headless release procedure to launch Ruang Risiko IDX on the `fadhilrusydi` domain ecosystem (e.g. `rridx.fadhilrusydi.com` or `fadhilrusydi.com`) without requiring Remote Desktop Connection (RDC).

Remote Desktop protocols introduce friction: connection queues, bandwidth bottlenecks, clipboard failures, and manual GUI overhead. Ruang Risiko IDX replaces RDC entirely with:
1. Headless Linux VPS execution (SSH key authentication, zero GUI).
2. Automated Docker Compose stack with health-monitored containers.
3. Caddy reverse proxy with automatic ACME TLS (Let's Encrypt / ZeroSSL) for `rridx.fadhilrusydi.com`.
4. An integrated browser-based **Web Action Console** allowing full system inspection, model recalculation, and risk parameter management from any mobile or desktop web browser.

---

## 2. Fast Launch Architecture
```
[User Browser: https://rridx.fadhilrusydi.com]
                       │
                       ▼ (HTTPS / 443 with TLS Auto-Certificate)
        [Caddy Reverse Proxy Container]
                       │
                       ▼ (Internal Network / HTTP 8501 + WebSockets)
 [Ruang Risiko IDX Application Container (Streamlit)]
                       │
                       ├── DuckDB & Parquet Data Stores
                       ├── GARCH & XGBoost/RF Model Snapshots
                       ├── Stockbit UI Engine & Orderbook Depth
                       └── Web Action Controller & Audit Ledger
```

---

## 3. Launching on `fadhilrusydi` Domain (15-Minute Blueprint)

### Step 1: Point Your DNS
At your domain registrar or DNS provider (Cloudflare, Namecheap, Niagahoster, Domainesia):
- Create an **A Record**:
  - Name: `rridx` (for `rridx.fadhilrusydi.com`) or `@` (for root domain)
  - Type: `A`
  - Value: `<YOUR_VPS_PUBLIC_IP>`
  - TTL: 60 seconds (or Auto / Proxied)

### Step 2: Connect to VPS via Headless SSH
Open terminal (PowerShell, macOS Terminal, or Linux shell):
```bash
ssh root@<YOUR_VPS_PUBLIC_IP>
```

### Step 3: Run Turnkey 1-Command Setup
Execute the automated setup script directly:
```bash
curl -sSL https://raw.githubusercontent.com/Fadhilstat/Stock-Prediction/main/deploy/setup_production.sh | bash -s -- --domain rridx.fadhilrusydi.com --email admin@fadhilrusydi.com
```

Caddy immediately contacts Let's Encrypt, validates the domain ownership, issues the TLS certificate, and routes incoming HTTPS traffic to Ruang Risiko IDX.

---

## 4. Operating via the Web Action Console (No SSH or RDC Needed)
Once live, routine operational workflows do not require server login:
1. Open your browser: `https://rridx.fadhilrusydi.com` (or your chosen domain).
2. Navigate to tab: **Web Action Console**.
3. Available interactive actions:
   - **Perbarui Data Pasar**: Triggers live data ingestion across the canonical universe.
   - **Hitung Ulang Snapshot Risiko & GARCH**: Refits volatility models and VaR thresholds.
   - **Hitung Ulang Model Direction ML**: Retrains and updates directional classification models.
   - **Radar Bandarmology Seluruh Universe**: Scans and ranks all tickers by smart money accumulation.
   - **Penerbitan Mandiri Pre-Buy Decision Passport**: Issues digitally signed passports with custom invalidation levels.
   - **Pengaturan Parameter Risiko Runtime**: Dynamically tune VaR confidence levels, max portfolio allocation limits, and slippage tolerance thresholds in real time.
   - **Audit Trail & Riwayat Aksi**: Inspect all past automated or operator actions, execution durations, timestamps, and parameters directly in the browser table.

---

## 5. Ongoing Headless Maintenance Commands
To pull code updates or restart services remotely via SSH:
```bash
# Pull latest commits and reload
cd /opt/ruang-risiko-idx
git pull origin main
docker compose up -d --build

# View container logs
docker compose logs -f --tail=100 app
```
