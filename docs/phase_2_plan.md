# Phase 2 Implementation Plan

> Historical planning document. Phase 2 through Phase 5 have since been completed. Current dashboard integration work is tracked in `docs/phase_6_plan.md`.

## Milestone 2.1: Data foundation

Status: complete

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

Status: complete

Historical deliverables:

- log return dari adjusted close
- rolling volatility dan drawdown
- fitur pasar berbasis IHSG
- processed analytics dataset
- feature tests yang mencegah look-ahead

## Milestone 2.3: Econometrics

Status: complete

Historical deliverables:

- ARCH LM test
- GARCH, EGARCH, dan GJR-GARCH
- residual diagnostics
- walk-forward volatility forecast
- QLIKE dan VaR backtest

## Milestone 2.4: Foundation models

Status: complete

Historical deliverables:

- Kronos zero-shot adapter dan rolling evaluation
- Granite TTM R2.1 zero-shot adapter dan rolling evaluation
- offline artifact generation
- evaluation against naive baselines

## Milestone 2.5: Dashboard completion

Status: superseded by Phase 6

Dashboard integration is now tracked as a dedicated Phase 6 so runtime data access, model evidence, UX, and deployment can be validated separately.
