# Phase 2 Implementation Plan

## Milestone 2.1: Data foundation

Status: started

Deliverables:

- yfinance provider dengan schema long-form yang stabil
- validasi struktural dan aturan harga
- incremental overlap selama tujuh hari kalender
- audit perubahan pada data lama
- snapshot Parquet
- dashboard shell untuk memeriksa data
- unit test untuk normalisasi, validasi, dan rekonsiliasi

Acceptance criteria:

- Semua ticker awal dapat diproses tanpa perubahan manual pada schema.
- Data yang gagal validasi tidak boleh masuk ke snapshot terbaru.
- Perubahan pada tanggal lama tercatat dalam audit.
- Dashboard tetap menampilkan pesan yang jelas saat data belum tersedia.
- Semua file teks lulus pemeriksaan karakter em dash.

## Milestone 2.2: Return and feature layer

Planned deliverables:

- log return dari adjusted close
- rolling volatility dan drawdown
- fitur pasar berbasis IHSG
- tabel analitik DuckDB
- feature tests yang mencegah look-ahead

## Milestone 2.3: Econometrics

Planned deliverables:

- ARCH LM test
- GARCH, EGARCH, dan GJR-GARCH
- residual diagnostics
- walk-forward volatility forecast
- QLIKE dan VaR backtest

## Milestone 2.4: Foundation models

Planned deliverables:

- Kronos-small zero-shot adapter
- TTM R2.1 multivariate adapter
- offline artifact generation
- evaluation against naive and econometric baselines

## Milestone 2.5: Dashboard completion

Planned deliverables:

- market overview
- stock explorer
- GARCH lab
- foundation model comparison
- risk dashboard
- learning page
