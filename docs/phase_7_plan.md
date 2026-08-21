# Phase 7 Daily Intelligence Layer

## Goal

Menambah lapisan intelligence harian yang membantu pengguna membaca market data, model risk, probabilitas arah, berita, dan kondisi pipeline dari beberapa sudut tanpa mengubah Ruang Risiko IDX menjadi mesin rekomendasi transaksi.

Fitur publik harus tetap dapat berjalan tanpa API AI berbayar. Karena itu OpenAI API tidak menjadi dependency web. ChatGPT dapat dipakai sebagai lapisan review pribadi di luar runtime publik, sementara dashboard menghasilkan ringkasan terstruktur dari data dan aturan yang dapat diperiksa.

## 7.1 Cost and architecture contract

Status: complete.

Public runtime memakai Streamlit Community Cloud, GitHub Actions, project artifacts, dan metadata sumber publik. Tidak ada API key OpenAI yang ditaruh di frontend, repository, atau deployment workflow.

Analyst roles pada web tidak disebut sebagai ChatGPT agents. Mereka adalah modul analisis deterministic dengan kontrak yang bisa diuji. Keputusan ini menjaga biaya tambahan tetap nol pada arsitektur saat ini dan mencegah pengguna mengira narasi yang tampil berasal dari model bahasa ketika sebenarnya berasal dari aturan proyek.

## 7.2 Analyst roles

Status: complete.

Daily Intelligence Layer memiliki lima sudut baca:

1. Analis pasar membaca return terbaru, volatilitas historis 21 dan 63 hari, serta drawdown.
2. Analis risiko membaca forecast volatility, VaR, ranking risiko lintas universe, dan convergence warning.
3. Analis probabilitas arah membaca probability up tanpa mengubahnya menjadi label transaksi.
4. Analis makro dan berita mengelompokkan headline dari source allowlist ke tema makro dan ticker yang relevan.
5. Auditor model dan data memeriksa keselarasan tanggal dan convergence warning secara terpisah dari opini pasar.

Synthesis hanya merangkai evidence dari role di atas. Ia tidak menambahkan klaim yang tidak ada pada input.

## 7.3 News discovery

Status: complete.

GDELT DOC 2.0 dipakai sebagai discovery layer untuk metadata artikel. Hanya domain yang sudah diverifikasi dan masuk allowlist yang dapat diteruskan ke dashboard.

Artikel penuh tidak disalin. Artifact hanya menyimpan judul, URL asli, domain, label sumber, waktu yang dilaporkan discovery provider, ticker terkait, dan tema. Pengguna tetap diarahkan ke halaman sumber untuk membaca konteks lengkap.

Jika discovery gagal untuk satu atau lebih domain, pipeline market dan model tetap boleh selesai. Kegagalan berita dicatat sebagai source availability issue dan tidak diubah menjadi asumsi sentimen.

## 7.4 Dashboard integration

Status: complete.

Halaman `Intel Harian` berdiri terpisah dari dashboard utama. Core dashboard tetap bisa dibuka ketika intelligence artifact belum tersedia.

Intelligence artifact harus memiliki tanggal yang sama dengan latest market data dan ticker universe yang sama. Link berita harus memakai HTTPS. Artifact dengan schema yang tidak dikenali atau tanggal yang stale ditolak.

## 7.5 Deployment automation

Status: complete.

Workflow refresh hari kerja tetap dimulai pukul 18.00 WIB. Setelah market data, analytics, GARCH snapshot, dan direction snapshot selesai, workflow membangun daily intelligence lalu memasukkannya ke validated deployment bundle.

Daily intelligence menjadi file tambahan yang bersifat backward compatible. Bundle lama tanpa file intelligence masih dapat memuat halaman utama, sehingga deployment tidak memiliki jendela kegagalan saat versi baru pertama kali masuk ke `main`.

## 7.6 Private ChatGPT review

Status: product-side automation.

ChatGPT dapat dipakai sebagai reviewer pribadi setelah refresh publik selesai. Perannya berbeda dari analyst modules di web. Review pribadi boleh menggabungkan kondisi dashboard dengan pencarian web terbaru dan menjelaskan apa yang berubah, tetapi tetap tidak membuat rekomendasi transaksi.

Arsitektur repository tidak memanggil OpenAI API untuk fungsi ini. Dengan begitu tidak ada tagihan API per pengunjung atau per refresh dari fitur publik.

## Guardrails

GARCH tetap berstatus `provisional_out_of_sample_selection` sampai evaluasi terpisah mengubahnya secara eksplisit.

Kronos dan Granite tetap experimental benchmark. Daily Intelligence Layer tidak mempromosikan model foundation ke production forecasting.

Headline bukan fakta lengkap. Analyst role hanya menyebut konteks yang dapat diturunkan dari metadata yang tersedia dan selalu mempertahankan link sumber.

Tidak ada BUY, SELL, target price, atau synthetic trading score pada output publik.

Semua Python tetap mengikuti aturan no em dash proyek. Kalimat ditulis ulang secara natural ketika tanda baca perlu diperbaiki.
