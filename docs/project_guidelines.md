# Ruang Risiko IDX Project Guidelines

Dokumen ini menjadi acuan kerja aktif untuk pengembangan Ruang Risiko IDX. Tujuannya bukan sekadar membuat demo model, tetapi membangun portfolio yang terasa dibuat dengan pertimbangan manusia, dapat diperiksa, dan punya nilai edukasi bagi masyarakat luas.

## 1. Tujuan proyek

Ruang Risiko IDX membantu pengguna memahami risiko pasar saham Indonesia melalui return, volatilitas, drawdown, Value at Risk, probabilitas arah, dan bukti evaluasi model.

Dashboard tidak boleh berubah menjadi alat rekomendasi transaksi. Bahasa seperti BUY, SELL, target price, atau klaim keuntungan tidak digunakan sebagai output analitik.

Nilai utama proyek adalah membantu pengguna membaca ketidakpastian dengan lebih baik, bukan membuat prediksi terlihat lebih pasti daripada kenyataannya.

## 2. Prinsip pengembangan

Setiap fase mengikuti urutan yang sudah disepakati. Perubahan model, data contract, atau status deployment tidak dilakukan diam-diam di tengah fase dashboard.

Keputusan teknis harus punya alasan yang dapat dijelaskan. Catat juga model yang ditolak, keterbatasan data, kegagalan eksperimen, dan kompromi implementasi ketika hal tersebut penting untuk memahami hasil.

Tidak ada impact metric yang dibuat-buat. Manfaat proyek dijelaskan melalui fungsi yang benar-benar tersedia, seperti edukasi risiko, transparansi model, dan akses yang lebih mudah terhadap konsep statistik pasar.

## 3. Gaya penulisan

Bahasa dokumentasi dan dashboard harus terasa manusiawi, mengalir, dan profesional. Hindari kalimat yang terlalu generik, terlalu formal, atau terdengar seperti template AI.

Istilah teknis tetap dipakai ketika memang membantu ketepatan makna, tetapi penjelasannya harus mudah diikuti pembaca yang belum memiliki latar belakang quantitative finance.

Kalimat sebaiknya menjelaskan alasan dan konteks, bukan hanya menyebut fitur.

## 4. Aturan kode Python

Karakter em dash tidak boleh muncul dalam file Python, termasuk komentar, docstring, string error, label, dan teks dashboard yang ditulis di Python.

Larangan ini bukan berarti semua em dash diganti menjadi hyphen. Susun ulang kalimat atau gunakan tanda baca yang lebih alami, seperti koma, titik, titik dua, atau tanda kurung sesuai konteks.

Komentar kode harus menjelaskan alasan atau risiko implementasi. Hindari komentar yang hanya mengulang apa yang sudah jelas dari nama fungsi atau baris kode.

Kode harus lebih mudah dirawat daripada sekadar terlihat canggih. Abstraksi baru hanya ditambahkan ketika benar-benar mengurangi duplikasi, memperjelas kontrak, atau memisahkan tanggung jawab.

## 5. Data dan model

Data pasar utama pada tahap MVP berasal dari yfinance melalui arsitektur provider yang tetap modular.

GARCH, EGARCH, dan GJR-GARCH digunakan untuk volatilitas dan tail risk. Status registry GARCH tetap provisional sampai ada proses evaluasi terpisah yang secara eksplisit mengubahnya.

Model arah klasik mengikuti keputusan registry berbasis validation. Test set tidak digunakan untuk memilih model.

Kronos dan Granite TTM tetap ditampilkan sebagai experimental benchmark selama hasil evaluasi belum mendukung promosi ke production forecasting.

Dashboard membaca hasil yang sudah dihitung sebelumnya. Membuka halaman Streamlit tidak boleh memicu fitting GARCH, training model klasik, atau loading foundation model untuk inference.

## 6. Sumber eksternal

Sumber eksternal yang dipakai untuk keputusan teknis harus dapat diakses saat diperiksa. Utamakan dokumentasi resmi, repository resmi, model card resmi, paper asli, atau sumber primer lain yang relevan.

`references/source_registry.yaml` mencatat kapan sumber terakhir diperiksa dan perannya dalam proyek. Status `verified_live` hanya dipakai setelah sumber benar-benar dapat diakses pada saat pemeriksaan.

Jika sumber tidak lagi tersedia, jangan mempertahankan status tersebut tanpa catatan. Cari sumber primer pengganti atau dokumentasikan keterbatasannya.

## 7. Workflow perubahan

Perubahan dikerjakan dalam branch yang sesuai dengan fase atau tujuan pekerjaan.

Sebelum merge, perubahan harus melewati Ruff, pytest, dan text rules. Untuk perubahan yang memengaruhi model atau data contract, tambahkan test yang mengunci perilaku penting dan mencegah regresi.

Pull request harus menjelaskan apa yang berubah, alasan perubahan, guardrail yang tetap dipertahankan, dan keterbatasan yang masih ada.

Merge dilakukan setelah quality gate hijau. Phase berikutnya tidak dianggap selesai hanya karena file sudah dibuat.

## 8. Standar dashboard

Tampilan harus membantu pengguna memahami risiko, bukan membanjiri pengguna dengan angka.

Setiap metrik penting perlu konteks singkat tentang cara membacanya. Model evidence harus menunjukkan hasil yang baik dan buruk secara seimbang.

Ketidakpastian, keterbatasan data, dan status eksperimental harus terlihat jelas. Hindari bahasa yang menyiratkan kepastian prediksi.

Desain akhir harus tetap berguna bagi investor ritel, mahasiswa, dan pembaca umum yang ingin belajar tentang risiko saham Indonesia.
