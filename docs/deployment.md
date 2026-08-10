# Deployment Guide

Dokumen ini menjelaskan cara Ruang Risiko IDX dipublikasikan tanpa menjalankan fitting model saat pengguna membuka dashboard.

## Prinsip deployment

Streamlit hanya membaca artifact yang sudah dihitung dan divalidasi. Proses pengambilan data, analytics, GARCH, direction inference, dan pembuatan deployment bundle berjalan di GitHub Actions.

Raw market data tetap berada di luar repository. Repository hanya menyimpan bundle publik yang dibutuhkan dashboard, yaitu analytics yang sudah dipangkas ke kolom presentasi, snapshot risiko terbaru, snapshot probabilitas arah terbaru, dan manifest integritas.

## Streamlit Community Cloud

Gunakan repository `Fadhilstat/Stock-Prediction`, branch `main`, dan entrypoint `app/app.py`.

Pilih Python 3.11 agar konsisten dengan CI dan kontrak proyek. `requirements.txt` memasang package lokal beserta dependency dasar dari `pyproject.toml`. Dashboard tidak membutuhkan dependency model untuk membuka halaman karena semua model dijalankan offline.

Saat artifact canonical lokal tersedia, dashboard memakainya terlebih dahulu. Pada Community Cloud, dashboard menggunakan bundle di direktori `deployment/`.

## Bundle deployment

Bundle berisi empat file:

- `deployment/analytics_daily.parquet`
- `deployment/latest_risk_snapshot.json`
- `deployment/latest_direction_snapshot.json`
- `deployment/manifest.json`

Manifest menyimpan schema version, tanggal perdagangan terakhir, jumlah baris analytics, jumlah ticker, dan SHA-256 untuk tiga runtime artifact. Loader memverifikasi checksum serta ringkasan manifest sebelum data diteruskan ke Streamlit.

Bundle yang tidak lengkap atau tidak cocok dengan manifest ditolak. Perilaku ini sengaja dipilih agar dashboard tidak menampilkan kombinasi data yang meragukan hanya demi tetap terlihat aktif.

## Pembaruan otomatis

Workflow `.github/workflows/refresh-deployment.yml` berjalan setiap Senin sampai Jumat pukul 18.00 Asia/Jakarta. Workflow juga berjalan ketika perubahan pipeline yang relevan masuk ke `main`, sehingga perubahan deployment dapat menghasilkan bundle baru tanpa menunggu jadwal berikutnya.

Urutan pembaruan adalah:

1. mengambil data pasar melalui provider yfinance;
2. membangun analytics harian;
3. membangun snapshot GARCH dan VaR;
4. membangun snapshot probabilitas arah;
5. membangun deployment bundle;
6. memuat ulang bundle melalui loader dashboard sebagai validasi akhir;
7. melakukan commit hanya ketika isi bundle berubah.

Commit otomatis memakai `GITHUB_TOKEN` dengan permission `contents: write`. GitHub tidak membuat workflow run baru untuk push yang dihasilkan token tersebut, sehingga commit bundle tidak membentuk loop refresh.

Pada hari tanpa observasi perdagangan baru, workflow dapat selesai tanpa commit jika bundle yang dihasilkan tidak berubah.

## Pembaruan manual

Workflow yang sama menyediakan `workflow_dispatch`. Gunakan pemicu manual setelah perubahan operasional yang perlu diterapkan segera atau ketika refresh terjadwal sebelumnya gagal karena gangguan jaringan atau sumber data.

Jangan mengedit file deployment secara manual. Perubahan manual akan membuat checksum manifest tidak cocok dan loader akan menolak bundle tersebut.

## Batasan operasional

Sumber pasar pada MVP tetap yfinance. Karena data historis mentah tidak disimpan di repository, runner GitHub Actions membangun data runtime dari sumber tersebut pada setiap refresh. Kegagalan sumber data atau jaringan membuat workflow gagal sebelum bundle baru di-commit, sehingga bundle publik terakhir yang sudah tervalidasi tetap tersedia.

Scheduled workflow juga bukan jaminan bahwa data baru selalu tersedia tepat pada jam eksekusi. Dashboard menampilkan tanggal data terakhir agar pengguna dapat melihat freshness secara langsung.

Kronos dan Granite tidak dijalankan dalam workflow deployment. Keduanya tetap menjadi experimental benchmark sesuai registry proyek dan hanya ditampilkan sebagai evidence yang sudah dibekukan.

## Pemeriksaan sebelum rilis

Sebelum perubahan deployment di-merge, jalankan quality gate proyek yang sama seperti fase lain: Ruff, pytest, dan text rules. Review juga final diff untuk memastikan tidak ada raw data, secret, model artifact besar, atau perubahan status model yang ikut masuk tanpa sengaja.
