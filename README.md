# Ruang Risiko IDX

Ruang Risiko IDX adalah dashboard edukasi untuk membantu orang memahami risiko saham Indonesia dengan bahasa yang lebih dekat ke kebutuhan pengguna. Fokusnya bukan menebak harga berikutnya, tetapi membantu membaca return, volatilitas, drawdown, tail risk, probabilitas arah, dan keterbatasan model secara lebih jernih.

Proyek ini tidak memberikan rekomendasi beli, jual, atau target harga. Semua output diposisikan sebagai bahan belajar dan alat bantu memahami ketidakpastian pasar.

## Kenapa proyek ini dibuat

Banyak dashboard pasar berhenti pada harga, indikator, atau sinyal. Ruang Risiko IDX mengambil arah yang berbeda: pengguna perlu tahu bukan hanya apa yang berubah, tetapi juga seberapa besar risikonya, seberapa tidak pasti modelnya, dan kapan sebuah model gagal mengalahkan baseline sederhana.

Karena itu, hasil eksperimen yang tidak unggul tetap ditampilkan. Kronos dan Granite TTM, misalnya, tetap menjadi bagian dari cerita proyek sebagai experimental benchmark. Kegagalan mengalahkan baseline adalah informasi yang berguna, bukan sesuatu yang perlu disembunyikan.

Target pengguna awal adalah investor ritel yang ingin belajar, mahasiswa yang ingin memahami penerapan statistik pasar, serta recruiter yang ingin melihat proses analisis end-to-end yang dapat diperiksa.

## Status proyek

Phase 1 sampai Phase 5 sudah selesai. Phase 6 sedang mengintegrasikan seluruh hasil analitik ke dashboard Streamlit tanpa menjalankan training model ketika halaman dibuka.

Phase 6.1, 6.2, dan 6.3 sudah selesai. Data contract, latest direction snapshot pipeline, dashboard data-access layer, serta automated quality gate sudah tersedia. Pekerjaan berikutnya adalah membangun halaman utama dashboard pada Phase 6.4.

Komponen utama yang sudah tersedia meliputi ingestion harian melalui `yfinance`, analytics return dan drawdown, GARCH family untuk risk analytics, classical ML untuk probabilitas arah, benchmark Kronos dan Granite TTM, serta task-specific model registry.

GARCH tetap memakai status `provisional_out_of_sample_selection`. Kronos dan Granite tetap berstatus experimental benchmark. Status tersebut tidak boleh dinaikkan hanya demi membuat dashboard terlihat lebih kuat.

Rencana Phase 6 dicatat di `docs/phase_6_plan.md`. Prinsip kerja proyek dicatat di `docs/project_guidelines.md`.

## Universe awal

- BBCA.JK
- BBRI.JK
- TLKM.JK
- ASII.JK
- ANTM.JK
- ^JKSE

## Peran model

| Task | Model role |
| --- | --- |
| Risk dan volatility | Ticker-specific GARCH registry |
| Direction probability | Ticker-specific classical validation registry |
| OHLCV forecasting | Kronos experimental benchmark |
| Return forecasting | Granite TTM experimental benchmark |

Tidak ada satu leaderboard lintas task. Setiap kelompok model menjawab pertanyaan yang berbeda dan dinilai dengan metrik yang sesuai dengan targetnya.

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

Runtime market data dan latest snapshot tertentu sengaja tidak disimpan di Git karena merupakan generated artifacts. Pipeline offline membangunnya sebelum dashboard menggunakan hasil terbaru.

## Pemeriksaan kualitas

```bash
ruff check app scripts src tests
pytest -q
python scripts/check_text_rules.py
```

Quality gate yang sama dijalankan otomatis oleh GitHub Actions pada pull request dan push ke `main`.

Aturan teks melarang karakter em dash dalam file Python dan file teks proyek yang diperiksa. Kalimat tidak sekadar mengganti karakter tersebut dengan hyphen. Penulisan diusahakan tetap alami dengan menyusun ulang kalimat atau memakai tanda baca yang sesuai konteks.

## Kebijakan data dan sumber

`yfinance` digunakan untuk riset, pembelajaran, dan portfolio. Arsitektur data tetap memakai provider abstraction agar sumber dapat diganti tanpa menulis ulang seluruh analytics layer.

Sumber eksternal yang dipakai untuk keputusan teknis diperiksa sebelum dicatat sebagai `verified_live`. Prioritas diberikan kepada dokumentasi resmi, repository resmi, model card resmi, paper asli, dan sumber primer lain yang relevan. Catatan pemeriksaan berada di `references/source_registry.yaml`.

Proyek tidak menyediakan endpoint untuk mendistribusikan ulang seluruh data mentah.

## Cara proyek ini menjaga sisi manusianya

Keputusan model, keterbatasan, model yang ditolak, masalah provenance, dan hasil yang tidak sesuai harapan tetap didokumentasikan. Tidak ada impact metric yang dibuat hanya untuk mempercantik portfolio.

Komentar kode diarahkan untuk menjelaskan alasan atau risiko implementasi. Dokumentasi ditulis untuk membantu pembaca memahami keputusan, bukan sekadar mencatat daftar fitur.

Semua probabilitas, forecast volatility, dan VaR adalah output analitik untuk edukasi risiko. Nilai tersebut tidak boleh ditampilkan sebagai rekomendasi transaksi.

## Struktur proyek

```text
app/                                Streamlit application
config/                             Model deployment and risk registries
src/ruang_risiko_idx/data/         Ingestion, validation, and storage
src/ruang_risiko_idx/analytics/    Return and descriptive analytics
src/ruang_risiko_idx/eda/          Exploratory analysis helpers
src/ruang_risiko_idx/econometrics/ GARCH, VaR, and walk-forward evaluation
src/ruang_risiko_idx/ml/           Classical ML and direction inference
src/ruang_risiko_idx/foundation/   Kronos and Granite adapters and backtests
src/ruang_risiko_idx/dashboard/    Validated dashboard data access
scripts/                            Offline pipelines and quality checks
tests/                              Automated tests
reports/                            Committed evidence and model decisions
docs/                               Project plans and technical notes
references/                         Verified source registry
```
