# PRD: Ringkasan Saham IDX Harian via Telegram

## 1. Latar Belakang & Masalah
Butuh ringkasan singkat tiap pagi berisi hal-hal yang perlu diperhatikan hari itu terkait watchlist saham IDX — supaya tidak perlu baca berita manual dari banyak sumber sebelum jam bursa buka. Tool ini adalah **alat bantu observasi/informasi, bukan alat rekomendasi beli/jual**.

## 2. Tujuan
- Kirim ringkasan otomatis ke Telegram tiap hari jam 08:00 WIB.
- Ringkasan berisi: berita terbaru (24 jam terakhir) + perubahan fundamental relevan untuk watchlist saham.
- Ringkasan bersifat informasional (netral), bukan sinyal aksi (beli/jual/hold).

## 3. Target Pengguna
Personal use — 1 pengguna (pemilik project), bukan produk multi-user.

## 4. Scope

### In-scope (v1)
- Watchlist tetap, bisa diedit lewat file konfigurasi (`watchlist.json`), berisi 5–10 kode saham (format `.JK`).
- Ambil berita 24 jam terakhir terkait tiap saham di watchlist + berita umum IHSG/market, menggunakan Gemini API dengan tools `google_search` + `url_context`.
- Ambil snapshot data fundamental dasar per saham via `yfinance` (harga terakhir, perubahan %, PER, PBV, volume).
- Gabungkan data berita + fundamental, kirim ke Gemini untuk diringkas jadi bahasa natural per saham.
- Kirim hasil ringkasan ke Telegram (via Bot API) jam 08:00 WIB, dijadwalkan lewat GitHub Actions (cron).
- Setiap ringkasan menyertakan sumber/link berita asli untuk verifikasi.
- Disclaimer otomatis di akhir tiap pesan: bahwa ini ringkasan informasi, bukan rekomendasi transaksi.

### Out-of-scope (v1)
- Sinyal beli/jual/hold eksplisit.
- Analisis teknikal (RSI, MACD, dll).
- Notifikasi real-time intraday (cuma sekali per hari, pagi).
- Multi-user / multi-channel distribusi.
- Auto-trading / eksekusi order apa pun.

## 5. Alur Sistem (High-level)
1. **Trigger**: GitHub Actions cron job jalan tiap hari jam 08:00 WIB (01:00 UTC).
2. **Fetch fundamental**: script Python narik data harga & rasio dasar tiap saham di watchlist via `yfinance`.
3. **Fetch & ringkas berita**: panggil Gemini API (model `gemini-3.7-flash`) dengan tools `google_search` + `url_context`, prompt terstruktur per saham + market umum, batasi ke berita 24 jam terakhir.
4. **Compose pesan**: gabungkan hasil fundamental + ringkasan berita jadi satu pesan terformat (Markdown Telegram).
5. **Kirim ke Telegram**: via Bot API (`sendMessage`), pakai `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_CHAT_ID`.
6. **Logging**: simpan log run (sukses/gagal, timestamp) untuk debugging, bisa cukup di GitHub Actions log.

## 6. Format Output (contoh)

```
📊 Ringkasan Pagi — [Tanggal]

🔎 Market Umum
- [1-2 kalimat ringkasan sentimen/berita IHSG hari ini]

📌 [KODE_SAHAM_1] (harga: Rp X, ±Y%)
- [poin berita/fundamental penting #1]
- [poin berita/fundamental penting #2]
- Sumber: [link]

📌 [KODE_SAHAM_2] (harga: Rp X, ±Y%)
- ...

⚠️ Ini ringkasan informasi otomatis, bukan rekomendasi beli/jual. Selalu verifikasi ke sumber resmi sebelum ambil keputusan.
```

## 7. Non-Functional Requirements
- **Keamanan**: semua API key (Gemini, Telegram) disimpan sebagai GitHub Actions Secrets, tidak pernah hardcode di kode.
- **Biaya**: pantau token usage Gemini (URL context dihitung per token konten yang diambil) — dengan 5-10 saham/hari, estimasi biaya harus tetap rendah (cek dashboard billing tiap minggu di awal).
- **Reliability**: kalau salah satu sumber gagal diambil (misal yfinance timeout untuk 1 saham), skip saham itu di ringkasan tapi tetap kirim sisanya — jangan sampai satu error bikin seluruh notifikasi gagal terkirim.
- **Grounding**: larang model menambahkan opini/analisis dari pengetahuan internalnya sendiri soal harga saham — instruksikan eksplisit di prompt untuk hanya merangkum dari hasil pencarian/URL yang diambil.
- **Auditability**: simpan raw response (berita + fundamental mentah) minimal 7 hari terakhir untuk bisa ditelusuri kalau ringkasan terasa aneh/salah.

## 8. Guardrail Konten (penting)
- Dilarang keras output berisi kalimat imperatif aksi seperti "beli", "jual", "hold", "entry", "exit".
- Fokus pada: apa yang terjadi (fakta), bukan apa yang harus dilakukan (aksi).
- Setiap klaim penting yang cuma berasal dari satu sumber kecil/tidak terverifikasi harus ditandai eksplisit sebagai "belum terkonfirmasi luas".
- Disclaimer wajib ada di setiap pesan.

## 9. Metrik Keberhasilan (v1)
- Notifikasi terkirim tiap hari kerja tanpa gagal (target >95% uptime dalam sebulan pertama).
- Waktu baca ringkasan < 2 menit (ringkasan padat, bukan berita mentah).
- Subjektif: setelah 2-4 minggu, apakah ringkasan ini benar-benar dipakai untuk "memperhatikan hal penting", bukan cuma dibaca sekilas lalu diabaikan.

## 10. Asumsi & Pertanyaan Terbuka
- Asumsi: watchlist statis dulu di v1, belum ada fitur tambah/hapus saham dari Telegram langsung (bisa jadi v2).
- Belum diputuskan: apakah perlu retry otomatis kalau Telegram API gagal kirim (v1 cukup log error saja, v2 bisa tambah retry).
- Belum diputuskan: bahasa pesan (default Bahasa Indonesia, sesuaikan sendiri jika perlu).

---

# Prompt untuk Vibe Coding

Salin prompt di bawah ini ke Claude Code / Cursor / AI coding assistant pilihanmu:

```
Saya ingin membuat automation script Python yang mengirim ringkasan saham IDX harian ke Telegram, dijalankan otomatis via GitHub Actions cron job jam 08:00 WIB (01:00 UTC) setiap hari kerja.

KONTEKS & TUJUAN:
Tool ini alat bantu informasi personal (1 pengguna), BUKAN alat rekomendasi trading. Tujuannya memberi gambaran hal-hal yang perlu diperhatikan hari itu, bukan sinyal beli/jual.

SCOPE:
1. Baca watchlist saham dari file config `watchlist.json` (list kode saham format IDX, contoh: ["BBCA", "TLKM", "ASII"]).
2. Untuk tiap saham, ambil data fundamental dasar via library `yfinance` (tambahkan suffix .JK otomatis): harga terakhir, perubahan % harian, PER, PBV, volume. Handle error per-saham (kalau satu saham gagal fetch, skip saham itu, jangan bikin seluruh script gagal).
3. Untuk berita, gunakan Gemini API (model `gemini-3.7-flash`) dengan tools `google_search` dan `url_context` diaktifkan. Buat prompt yang:
   - Meminta model mencari berita 24 jam terakhir untuk tiap saham di watchlist + berita umum IHSG/market Indonesia.
   - Eksplisit melarang model memberi rekomendasi aksi (beli/jual/hold) — instruksikan hanya merangkum FAKTA dari berita yang ditemukan, bukan opini atau analisis dari pengetahuan internal model.
   - Meminta model menyertakan link sumber untuk tiap poin penting.
   - Kalau ada gap informasi (tidak ada berita signifikan hari itu), boleh bilang "tidak ada berita signifikan" alih-alih mengarang.
4. Gabungkan hasil fundamental + ringkasan berita jadi satu pesan terformat Markdown Telegram, dengan struktur:
   - Header tanggal
   - Ringkasan market umum (1-2 kalimat)
   - Per saham: harga & perubahan %, 2-3 poin berita/fundamental penting, link sumber
   - Disclaimer wajib di akhir: "Ini ringkasan informasi otomatis, bukan rekomendasi beli/jual. Selalu verifikasi ke sumber resmi sebelum ambil keputusan."
5. Kirim pesan ke Telegram via Bot API (`sendMessage`), pakai environment variable `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_CHAT_ID`.
6. Buat GitHub Actions workflow (`.github/workflows/daily-summary.yml`) yang:
   - Jalan cron tiap hari jam 01:00 UTC (= 08:00 WIB), hari kerja Senin-Jumat saja.
   - Install dependencies dari `requirements.txt`.
   - Jalankan script utama.
   - Ambil `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` dari GitHub Actions Secrets, JANGAN hardcode.
7. Tambahkan error handling menyeluruh: kalau Gemini API atau Telegram API gagal, log error dengan jelas (print ke stdout supaya muncul di GitHub Actions log), tapi jangan crash tanpa pesan yang jelas.
8. Buat `requirements.txt` dengan semua dependency yang dipakai.
9. Buat `README.md` singkat berisi cara setup: bikin bot Telegram via BotFather, cara dapat chat ID, cara isi GitHub Actions Secrets, dan cara test manual sebelum diaktifkan cron-nya.

OUTPUT YANG DIHARAPKAN:
Struktur project lengkap siap deploy, dengan kode yang clean, ada komentar secukupnya, dan mudah saya modifikasi watchlist-nya nanti tanpa ubah kode inti.

Mulai dengan menjelaskan struktur file/folder yang akan dibuat, baru tulis kodenya satu per satu.
```

## Cara Pakai
1. Copy bagian "Prompt untuk Vibe Coding" di atas.
2. Paste ke Claude Code, Cursor, atau AI coding assistant pilihanmu.
3. Review tiap file yang dihasilkan — jangan langsung deploy tanpa dibaca, terutama bagian yang menyentuh API key dan logic ringkasan berita.
4. Test manual dulu (jalankan script sekali secara lokal) sebelum mengaktifkan jadwal cron di GitHub Actions.
