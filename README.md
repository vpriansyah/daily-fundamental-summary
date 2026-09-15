# 📊 Ringkasan Saham IDX Harian via Telegram

Automation script Python dan Telegram Bot interaktif yang menyajikan ringkasan fundamental dan berita saham IDX setiap hari.

> ⚠️ **Disclaimer**: Tool ini adalah alat bantu observasi personal, **bukan** alat rekomendasi investasi (beli/jual/hold).

---

## Fitur Utama

- 📈 **Data Fundamental Terkini**: Harga saham harian, % perubahan dengan indikator visual (🟢/🔴/⚪), rasio PER, PBV, dan volume transaksi via `yfinance`.
- 📰 **Ringkasan Berita AI Berjenjang**:
  - Prioritas 1: `gemini-3.7-flash` (dengan Google Search)
  - Prioritas 2: `gemini-3.7-flash` (tanpa tool jika limit search tercapai)
  - Prioritas 3: `gemini-3.5-flash` (failover jika model overload)
  - Prioritas 4: `gemini-3.5-flash-lite` (**fallback terakhir**)
- 💬 **Pemisahan Pesan Rapi (Multi-Bubble)**:
  - **Bubble 1**: 🌐 *Sentimen IHSG & Pasar Makro* beserta link sumber.
  - **Bubble 2**: 📌 *Watchlist Fundamental & Highlights Berita* per emiten.
  - **Bubble 3**: ⚠️ *Catatan & Disclaimer Resmi*.
- 🤖 **Interaktif via Telegram**: Ubah watchlist langsung dari aplikasi Telegram tanpa edit file manual!
- ⏰ **Otomatisasi Cron**: Terjadwal setiap Senin - Jumat pukul 08:00 WIB via GitHub Actions.
- 📋 **Audit Log Otomatis**: Riwayat output tersimpan dalam format JSON (retensi 7 hari).
- 🐳 **Docker & Compose Ready**: Siap dijalankan baik sebagai cron one-shot maupun bot daemon.

---

## Perintah Bot Telegram

Saat bot listener dijalankan (`python -m src.bot` atau `docker compose up telegram-bot`), Anda dapat mengirim perintah berikut:

| Perintah | Contoh | Keterangan |
|----------|--------|------------|
| `/watchlist` atau `/list` | `/watchlist` | Melihat daftar kode saham yang sedang aktif dipantau |
| `/add <KODE>` | `/add BBRI` | Menambahkan kode saham baru ke watchlist |
| `/remove <KODE>` | `/remove UNVR` | Menghapus kode saham dari watchlist |
| `/summary` atau `/run` | `/summary` | Menjalankan dan mengirim ringkasan saham saat itu juga |
| `/help` | `/help` | Menampilkan petunjuk penggunaan bot |

---

## Struktur Project

```
├── .github/workflows/daily-summary.yml   # GitHub Actions cron workflow
├── src/
│   ├── __init__.py
│   ├── main.py          # Entry point pengiriman ringkasan
│   ├── bot.py           # Daemon bot interaktif (kelola watchlist)
│   ├── config.py        # Load/save config & watchlist CRUD
│   ├── fundamental.py   # Data harga & rasio via yfinance
│   ├── news.py          # Ringkasan berita via Gemini (multi-tier fallback)
│   ├── composer.py      # Format pesan multi-bubble
│   └── telegram.py      # Sender Telegram Bot API (send_bubbles)
├── watchlist.json        # File daftar saham aktif
├── Dockerfile            # Container image
├── docker-compose.yml    # Konfigurasi multi-service
├── requirements.txt      # Python dependencies
├── .env.example          # Template credentials
└── .gitignore
```

---

## Menjalankan Project

### 1. Mengirim Ringkasan Sekali Jalan (CLI / One-shot)
```bash
python -m src.main
```

### 2. Menjalankan Bot Interaktif (Daemon)
```bash
python -m src.bot
```
_Bot akan standby menerima perintah `/add`, `/remove`, `/watchlist`, dan `/summary` secara real-time._

### 3. Menggunakan Docker Compose
```bash
# Menjalankan bot listener di background
docker compose up -d telegram-bot

# Atau eksekusi ringkasan sekali jalan
docker compose run --rm daily-summary
```

---

## Setup Awal

1. Buat bot via **@BotFather** di Telegram dan dapatkan `TELEGRAM_BOT_TOKEN`.
2. Dapatkan Chat ID Anda via `https://api.telegram.org/bot<TOKEN>/getUpdates`.
3. Dapatkan Gemini API Key dari [Google AI Studio](https://aistudio.google.com/apikey).
4. Salin `.env.example` menjadi `.env` dan isi credentials:
   ```env
   GEMINI_API_KEY=your_key
   TELEGRAM_BOT_TOKEN=your_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```
5. Buka bot di Telegram dan klik **Start** (`/start`).
