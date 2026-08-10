# Ruang Risiko IDX

Ruang Risiko IDX adalah dashboard edukasi untuk membantu orang membaca risiko saham Indonesia dengan lebih jernih. Proyek ini membahas return, volatilitas, drawdown, Value at Risk, probabilitas arah, dan batas kemampuan model tanpa mengubah hasil analitik menjadi sinyal transaksi.

**Live dashboard:** https://fadhil-stockprediction.streamlit.app/

Proyek ini tidak memberikan rekomendasi beli, jual, atau target harga. Angka yang tampil dipakai untuk belajar membaca ketidakpastian pasar, bukan untuk memberi kesan bahwa harga berikutnya bisa diketahui dengan pasti.

## Kenapa proyek ini dibuat

Banyak dashboard pasar berhenti pada harga, indikator, atau prediksi. Padahal pertanyaan yang lebih penting sering kali justru sederhana: seberapa besar risikonya, apakah kondisi sekarang lebih bergejolak dari biasanya, seberapa dalam penurunan yang sedang terjadi, dan seberapa yakin kita boleh membaca sebuah model.

Ruang Risiko IDX dibuat untuk menjawab pertanyaan itu dengan cara yang dapat diperiksa. Hasil yang kurang bagus tidak disembunyikan. Model yang kalah dari baseline tetap dicatat karena kegagalan model juga memberi informasi tentang batas pendekatan yang sedang diuji.

Target pengguna utamanya adalah investor ritel yang ingin belajar, mahasiswa yang ingin melihat penerapan statistik dan machine learning pada data pasar, serta recruiter atau reviewer yang ingin menilai proses analisis dari data sampai deployment.

## Yang bisa dipelajari di dashboard

Dashboard publik saat ini memiliki tujuh bagian:

- **Gambaran pasar** untuk melihat adjusted close, return harian, volatilitas historis 21 hari, dan drawdown terbaru pada seluruh ticker.
- **Jelajah saham** untuk membaca riwayat harga dan kondisi satu ticker secara lebih dekat.
- **Risiko dan GARCH** untuk melihat forecast volatilitas satu hari serta VaR 95% dan 99% dari model yang dipilih per ticker.
- **Probabilitas arah** untuk melihat estimasi probabilitas naik pada hari perdagangan berikutnya tanpa mengubahnya menjadi label BUY atau SELL.
- **Ringkasan risiko** untuk membandingkan risk output antar ticker tanpa mencampurnya menjadi satu skor sintetis.
- **Bukti model** untuk menunjukkan model yang dipilih, model yang tidak dipilih, dan alasan keputusan tersebut.
- **Belajar** untuk menjelaskan return, volatilitas, drawdown, VaR, walk-forward evaluation, dan baseline dengan bahasa yang lebih mudah diikuti.

Ticker awal yang dipakai adalah `BBCA.JK`, `BBRI.JK`, `TLKM.JK`, `ASII.JK`, `ANTM.JK`, dan benchmark `^JKSE`.

## Status proyek

Phase 1 sampai Phase 6 sudah selesai. Dashboard sudah berjalan di Streamlit Community Cloud dan membaca deployment bundle yang dibangun secara offline.

Pipeline deployment melakukan pembaruan pada hari kerja pukul 18.00 Asia/Jakarta. Urutannya adalah pengambilan data pasar, pembangunan analytics, estimasi risiko GARCH dan VaR, direction inference, validasi deployment bundle, lalu commit hasil yang sudah lolos pemeriksaan ke `main`. Streamlit membaca perubahan repository tersebut untuk memperbarui aplikasi publik.

Dashboard tidak melakukan fitting GARCH, retraining classical model, atau inference foundation model ketika pengguna membuka halaman. Perhitungan model dilakukan sebelum artifact dipublikasikan.

Tanggal data terakhir selalu ditampilkan di dashboard agar pengguna dapat menilai sendiri apakah informasi yang sedang dilihat masih segar.

## Cara model dipakai

Tidak ada satu model yang dianggap terbaik untuk semua pertanyaan. Model dipisahkan berdasarkan tugasnya karena target dan metrik evaluasinya berbeda.

| Tugas | Peran model | Status |
| --- | --- | --- |
| Volatilitas dan tail risk | GARCH, EGARCH, atau GJR-GARCH per ticker | Provisional out-of-sample selection |
| Probabilitas arah | Logistic Regression, Random Forest, atau constant-probability baseline per ticker | Dipilih dari validation set |
| Forecast OHLCV | Kronos | Experimental benchmark, tidak dipilih untuk production |
| Forecast return | IBM Granite TTM R2.1 | Experimental benchmark, tidak dipilih untuk production |

Registry final ada di `reports/model_registry/final_model_registry.json`. GARCH tetap berstatus `provisional_out_of_sample_selection`; status ini tidak dinaikkan hanya demi membuat dashboard terlihat lebih kuat.

### Classical direction models

Pemilihan model arah menggunakan validation log loss sebagai metrik utama dan Brier score sebagai tie-breaker. Test set tidak dipakai untuk memilih model.

Model yang dipakai saat ini:

| Ticker | Model |
| --- | --- |
| ANTM.JK | Logistic Regression |
| ASII.JK | Random Forest |
| BBCA.JK | Random Forest |
| BBRI.JK | Constant probability baseline |
| TLKM.JK | Random Forest |
| ^JKSE | Constant probability baseline |

Keberadaan baseline sebagai model terpilih untuk sebagian ticker sengaja dipertahankan. Model yang lebih kompleks tidak otomatis dianggap lebih baik.

### Foundation model experiments

Kronos dan Granite TTM tetap ditampilkan karena hasil negatifnya penting untuk memahami proyek.

Pada evaluasi rolling zero-shot Kronos, random walk menghasilkan close MAE dan log-return MAE yang lebih rendah pada seluruh enam market series yang diuji. Karena itu Kronos tidak dipromosikan menjadi production forecaster.

Granite TTM R2.1 mengalahkan persistence baseline pada return MAE untuk lima saham yang diuji, tetapi tidak mengalahkan zero-return random-walk baseline pada satu pun dari lima saham tersebut. Hasil ini juga tidak cukup untuk memilih Granite sebagai production return model.

Tidak ada fine-tuning atau tuning ulang yang dilakukan menggunakan frozen evaluation set hanya untuk mengejar hasil yang lebih bagus setelah evaluasi terlihat.

## Arsitektur singkat

```text
Yahoo Finance melalui yfinance
        |
        v
validasi dan penyimpanan market data
        |
        v
return, volatility historis, drawdown, benchmark features
        |
        +------------------------+
        |                        |
        v                        v
GARCH / EGARCH / GJR-GARCH   Classical direction models
        |                        |
        v                        v
risk snapshot                direction snapshot
        |                        |
        +------------+-----------+
                     |
                     v
           validated deployment bundle
                     |
                     v
             Streamlit dashboard
```

Kronos dan Granite berada di jalur eksperimen terpisah dan hanya masuk dashboard sebagai model evidence. Keduanya tidak dijalankan saat pengguna membuka aplikasi.

## Data dan pembaruan

Data pasar MVP diambil melalui `yfinance`. Arsitektur ingestion memakai provider abstraction agar sumber data dapat diganti di masa depan tanpa menulis ulang seluruh analytics layer.

Raw market data tidak dipublikasikan sebagai dataset di repository. Deployment hanya menyimpan analytics yang dibutuhkan antarmuka, risk snapshot, direction snapshot, dan manifest integritas.

Manifest deployment menyimpan tanggal perdagangan terakhir, jumlah baris, jumlah ticker, serta SHA-256 setiap runtime artifact. Loader memeriksa bahwa artifact masih cocok dengan manifest sebelum data diteruskan ke Streamlit.

Jika refresh gagal karena sumber data, jaringan, fitting, atau validation error, workflow berhenti sebelum bundle baru di-commit. Dashboard tetap menggunakan bundle tervalidasi terakhir yang sudah tersedia.

Detail operasional ada di `docs/deployment.md`.

## Menjalankan proyek secara lokal

Python 3.11 digunakan untuk menjaga environment lokal tetap dekat dengan CI dan deployment.

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

Untuk Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Runtime data dan latest snapshots tertentu memang tidak disimpan sebagai source artifact biasa. Pipeline offline membangunnya sebelum dashboard lokal menggunakan hasil terbaru.

## Pemeriksaan kualitas

Setiap perubahan yang akan masuk ke `main` melewati quality gate berikut:

```bash
ruff check app scripts src tests
pytest -q
python scripts/check_text_rules.py
```

GitHub Actions menjalankan gate yang sama pada pull request dan push ke `main`.

Project guideline juga melarang karakter em dash dalam file Python, termasuk komentar, docstring, error message, label, dan teks dashboard. Kalimat tidak diperbaiki dengan sekadar mengganti karakter menjadi hyphen. Penulisan disusun ulang agar tetap alami sesuai konteks.

## Batasan yang sengaja ditampilkan

Ruang Risiko IDX adalah proyek edukasi, bukan sistem trading dan bukan alat penilaian kelayakan investasi.

Beberapa batasan penting:

- sumber data MVP masih bergantung pada ketersediaan `yfinance`;
- registry GARCH masih provisional dan tidak boleh dibaca sebagai model final untuk semua kondisi pasar;
- probabilitas arah tetap dapat salah dan bukan prediksi deterministik;
- model foundation belum menunjukkan evidence yang cukup untuk digunakan sebagai production forecaster;
- exact reproduction metrik Phase 4 dari fresh clone tidak diklaim karena raw input historis asli dan exact dependency environment saat eksperimen tersebut tidak dikunci;
- update otomatis bergantung pada keberhasilan GitHub Actions dan ketersediaan data sumber saat workflow berjalan.

Keterbatasan ini dipertahankan karena proyek akan lebih berguna ketika pengguna memahami apa yang tidak diketahui model, bukan hanya melihat angka yang terlihat meyakinkan.

## Sumber utama

Sumber eksternal dicek sebelum dicatat sebagai `verified_live`. Pemeriksaan terbaru disimpan di `references/source_registry.yaml`.

Beberapa sumber primer yang menjadi acuan proyek:

- [yfinance documentation](https://ranaroussi.github.io/yfinance/)
- [Kronos official repository](https://github.com/shiyu-coder/Kronos)
- [IBM Granite Time Series TTM R2 model card](https://huggingface.co/ibm-granite/granite-timeseries-ttm-r2)
- [Robert F. Engle Nobel Prize Lecture](https://www.nobelprize.org/prizes/economic-sciences/2003/engle/lecture/)
- [Basel Framework market risk terminology](https://www.bis.org/basel_framework/chapter/MAR/10.htm)
- [Streamlit Community Cloud documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud)
- [GitHub Actions workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)

## Struktur repository

```text
app/                                Streamlit application
config/                             Model deployment and risk registries
deployment/                         Validated public dashboard bundle
src/ruang_risiko_idx/data/         Ingestion, validation, and storage
src/ruang_risiko_idx/analytics/    Return and descriptive analytics
src/ruang_risiko_idx/eda/          Exploratory analysis helpers
src/ruang_risiko_idx/econometrics/ GARCH, VaR, and walk-forward evaluation
src/ruang_risiko_idx/ml/           Classical ML and direction inference
src/ruang_risiko_idx/foundation/   Kronos and Granite adapters and backtests
src/ruang_risiko_idx/dashboard/    Dashboard data access and presentation helpers
scripts/                            Offline pipelines and quality checks
tests/                              Automated tests
reports/                            Committed evidence and model decisions
docs/                               Project plans and technical notes
references/                         Verified source registry
.github/workflows/                  CI and deployment refresh automation
```

## Prinsip kerja proyek

Ruang Risiko IDX tidak dibangun untuk terlihat canggih sebanyak mungkin. Keputusan teknis, baseline, model yang ditolak, masalah provenance, dan hasil eksperimen yang tidak sesuai harapan tetap didokumentasikan ketika relevan.

Tidak ada impact metric yang dibuat-buat untuk mempercantik portfolio. Nilai proyek datang dari fungsi yang benar-benar dapat dipakai: membantu orang memahami risiko saham, melihat evidence model, dan belajar bahwa ketidakpastian adalah bagian dari analisis, bukan sesuatu yang perlu disembunyikan.

Guideline lengkap proyek ada di `docs/project_guidelines.md`.
