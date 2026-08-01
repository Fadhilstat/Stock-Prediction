# Ruang Risiko IDX

Ruang Risiko IDX adalah dashboard edukasi yang membantu pengguna memahami return, volatilitas, drawdown, dan ketidakpastian saham Indonesia. Proyek ini tidak memberikan rekomendasi beli atau jual.

## Status proyek

Phase 1 sudah dikunci. Starter ini membuka Phase 2 dengan tiga bagian awal:

1. Pengambilan data harian dari Yahoo Finance melalui `yfinance`.
2. Validasi, rekonsiliasi, audit perubahan, dan penyimpanan snapshot.
3. Dashboard Streamlit sederhana untuk memeriksa data yang sudah masuk.

Model GARCH, Kronos-small, dan TTM R2.1 akan ditambahkan setelah data layer lulus acceptance criteria.

## Saham awal

- BBCA.JK
- BBRI.JK
- TLKM.JK
- ASII.JK
- ANTM.JK
- ^JKSE

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,models]"
python scripts/update_market_data.py
streamlit run app/app.py
```

Untuk Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev,models]"
python scripts/update_market_data.py
streamlit run app/app.py
```

## Pemeriksaan kualitas

```bash
pytest
ruff check .
python scripts/check_text_rules.py
```

## Kebijakan data

`yfinance` dipakai untuk riset, pembelajaran, dan portfolio. Proyek menyimpan waktu pembaruan, sumber, serta audit perubahan. Dashboard tidak menyediakan endpoint untuk mengunduh ulang seluruh data mentah.

## Struktur awal

```text
app/                         Streamlit shell
src/ruang_risiko_idx/data/  Ingestion, validation, dan storage
scripts/                     Pipeline harian dan quality checks
tests/                       Unit tests
docs/                        Keputusan teknis dan acceptance criteria
references/                  Registry sumber yang telah diperiksa
```
