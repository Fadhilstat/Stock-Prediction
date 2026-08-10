# Ruang Risiko IDX

Ruang Risiko IDX adalah dashboard edukasi untuk memahami return, volatilitas, drawdown, tail risk, dan ketidakpastian saham Indonesia. Proyek ini tidak memberikan rekomendasi beli, jual, atau target harga.

## Status proyek

Phase 1 sampai Phase 5 sudah selesai. Phase 6 sedang mengintegrasikan seluruh hasil analitik ke dashboard Streamlit tanpa menjalankan training model saat halaman dibuka.

Komponen yang sudah tersedia:

- ingestion harian Yahoo Finance melalui `yfinance`, dengan validasi, audit perubahan, dan snapshot;
- analytics layer untuk return, benchmark, rolling volatility, drawdown, dan time under water;
- GARCH, EGARCH, dan GJR-GARCH dengan evaluasi walk-forward, QLIKE, VaR, serta registry model provisional;
- Logistic Regression, Random Forest, XGBoost, baseline probabilitas, dan registry model arah berbasis validation;
- benchmark zero-shot Kronos untuk OHLCV dan Granite TTM R2.1 untuk return forecasting;
- final task-specific model registry yang memisahkan risk, direction probability, OHLCV forecasting, dan return forecasting;
- latest GARCH risk snapshot dan registry-driven direction probability snapshot;
- automated quality checks melalui GitHub Actions.

Kronos dan Granite tetap berstatus experimental benchmark karena keduanya tidak mengalahkan baseline utama pada target produksi masing-masing. GARCH tetap memakai status `provisional_out_of_sample_selection` sesuai registry sumber.

Rencana integrasi dashboard saat ini dicatat di `docs/phase_6_plan.md`.

## Universe awal

- BBCA.JK
- BBRI.JK
- TLKM.JK
- ASII.JK
- ANTM.JK
- ^JKSE

## Model roles

| Task | Model role |
| --- | --- |
| Risk dan volatility | Ticker-specific GARCH registry |
| Direction probability | Ticker-specific classical validation registry |
| OHLCV forecasting | Kronos experimental benchmark |
| Return forecasting | Granite TTM experimental benchmark |

Tidak ada satu leaderboard lintas task karena setiap kelompok model memiliki target dan metrik yang berbeda.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,models]"
python scripts/update_market_data.py
python scripts/build_analytics_dataset.py
python scripts/build_latest_risk_snapshot.py
python scripts/build_latest_direction_snapshot.py
streamlit run app/app.py
```

Untuk Windows PowerShell, aktifkan environment dengan:

```powershell
.venv\Scripts\Activate.ps1
```

Runtime market data dan latest snapshot tertentu sengaja tidak disimpan di Git karena merupakan generated artifacts. Pipeline offline harus membangunnya sebelum dashboard menggunakan hasil terbaru.

## Pemeriksaan kualitas

```bash
ruff check app scripts src tests
pytest -q
python scripts/check_text_rules.py
```

Quality gate yang sama dijalankan otomatis oleh GitHub Actions pada pull request dan push ke `main`.

## Kebijakan data dan penggunaan

`yfinance` dipakai untuk riset, pembelajaran, dan portfolio. Proyek menyimpan sumber dan audit perubahan, serta tidak menyediakan endpoint untuk mendistribusikan ulang seluruh data mentah.

Semua probabilitas, forecast volatility, dan VaR adalah output analitik untuk edukasi risiko. Nilai tersebut tidak boleh ditampilkan sebagai rekomendasi transaksi.

## Struktur proyek

```text
app/                              Streamlit application
config/                           Model deployment and risk registries
src/ruang_risiko_idx/data/       Ingestion, validation, and storage
src/ruang_risiko_idx/analytics/  Return and descriptive analytics
src/ruang_risiko_idx/eda/        Exploratory analysis helpers
src/ruang_risiko_idx/econometrics/ GARCH, VaR, and walk-forward evaluation
src/ruang_risiko_idx/ml/         Classical ML and direction inference
src/ruang_risiko_idx/foundation/ Kronos and Granite adapters and backtests
src/ruang_risiko_idx/dashboard/  Validated dashboard data access
scripts/                          Offline pipelines and quality checks
tests/                            Automated tests
reports/                          Committed evidence and model decisions
docs/                             Project plans and technical notes
references/                       Source registry
```
