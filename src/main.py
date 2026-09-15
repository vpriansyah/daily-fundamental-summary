"""
main.py — Entry point untuk Ringkasan Saham IDX Harian.

Jalankan: python -m src.main
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Fix encoding untuk Windows console (cp1252 tidak support emoji)
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

from src.config import load_watchlist, PROJECT_ROOT
from src.fundamental import fetch_all_fundamentals
from src.news import fetch_news_summary
from src.composer import compose_bubbles
from src.telegram import send_bubbles


# Timezone WIB (UTC+7)
WIB = timezone(timedelta(hours=7))


def save_audit_log(data: dict) -> None:
    """
    Simpan raw data (fundamental + berita) untuk auditability.
    File disimpan di folder audit_data/ dengan nama file berdasarkan tanggal.
    """
    audit_dir = PROJECT_ROOT / "audit_data"
    audit_dir.mkdir(exist_ok=True)

    now = datetime.now(WIB)
    filename = f"audit_{now.strftime('%Y-%m-%d_%H%M%S')}.json"
    audit_path = audit_dir / filename

    try:
        with open(audit_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        print(f"[INFO] Audit log disimpan: {audit_path}")
    except Exception as e:
        print(f"[WARN] Gagal simpan audit log: {e}")

    # Cleanup: hapus file audit lebih dari 7 hari
    _cleanup_old_audits(audit_dir, max_days=7)


def _cleanup_old_audits(audit_dir: Path, max_days: int = 7) -> None:
    """Hapus file audit yang lebih tua dari max_days."""
    now = datetime.now(WIB)
    cutoff = now - timedelta(days=max_days)

    for file in audit_dir.glob("audit_*.json"):
        try:
            date_str = file.stem.replace("audit_", "")[:10]  # YYYY-MM-DD
            file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=WIB)
            if file_date < cutoff:
                file.unlink()
                print(f"[INFO] Audit log lama dihapus: {file.name}")
        except (ValueError, OSError):
            pass


def run_summary() -> bool:
    """
    Eksekusi alur penuh pembuatan & pengiriman ringkasan saham IDX.
    Dapat dipanggil oleh cron job maupun command bot Telegram (/summary).

    Return True jika semua proses dan pengiriman ke Telegram sukses.
    """
    now = datetime.now(WIB)
    print("=" * 60)
    print(f"📊 Ringkasan Saham IDX — {now.strftime('%Y-%m-%d %H:%M:%S WIB')}")
    print("=" * 60)

    # 1. Load watchlist
    print("\n[STEP 1/5] Loading watchlist...")
    watchlist = load_watchlist()

    # 2. Fetch data fundamental
    print("\n[STEP 2/5] Fetching data fundamental via yfinance...")
    fundamentals = fetch_all_fundamentals(watchlist)

    if not fundamentals:
        print("[WARN] Tidak ada data fundamental yang berhasil diambil.")
        print("       Ringkasan akan tetap dikirim dengan data berita saja.")

    # 3. Fetch & ringkas berita via Gemini
    print("\n[STEP 3/5] Fetching & meringkas berita via Gemini API...")
    news = fetch_news_summary(watchlist, fundamentals)

    # 4. Compose pesan multi-bubble
    print("\n[STEP 4/5] Composing pesan multi-bubble...")
    bubbles = compose_bubbles(fundamentals, news)

    print(f"[INFO] {len(bubbles)} bubble pesan berhasil disiapkan:")
    for idx, b in enumerate(bubbles, start=1):
        preview_title = b.splitlines()[0] if b.splitlines() else "Bubble"
        print(f"       Bubble #{idx}: {preview_title} ({len(b)} chars)")

    # 5. Kirim ke Telegram
    print("\n[STEP 5/5] Mengirim multi-bubble ke Telegram...")
    success = send_bubbles(bubbles, delay_seconds=0.7)

    # 6. Simpan audit log
    audit_data = {
        "timestamp": now.isoformat(),
        "watchlist": watchlist,
        "fundamentals": fundamentals,
        "news_raw_response": news.get("raw_response", ""),
        "news_parsed": {
            "market_umum": news.get("market_umum", ""),
            "per_saham": news.get("per_saham", {}),
        },
        "bubbles_count": len(bubbles),
        "telegram_success": success,
    }
    save_audit_log(audit_data)

    print("\n" + "=" * 60)
    if success:
        print("✅ Ringkasan berhasil dikirim ke Telegram (semua bubble tersampaikan)!")
    else:
        print("❌ Terjadi kendala saat mengirim salah satu bubble ke Telegram.")

    return success


def main() -> None:
    """Entry point CLI / cron."""
    success = run_summary()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
