"""
bot.py — Telegram Bot Interaktif untuk kelola Watchlist dan trigger ringkasan.

Jalankan bot listener:
    python -m src.bot
"""

import sys
import time
import requests

# Windows encoding fix
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

from src.config import (
    get_telegram_bot_token,
    get_telegram_chat_id,
    load_watchlist,
    add_to_watchlist,
    remove_from_watchlist,
)
from src.main import run_summary
from src.telegram import send_message


def _get_help_text() -> str:
    return (
        "🤖 *BANTUAN & PERINTAH BOT SAHAM IDX*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Gunakan perintah berikut untuk mengelola watchlist:\n\n"
        "📋 `/watchlist` atau `/list`\n"
        "   _Melihat daftar saham yang sedang dipantau_\n\n"
        "➕ `/add <KODE>`\n"
        "   _Menambahkan saham ke watchlist_\n"
        "   _Contoh: `/add BBRI` atau `/add BREN`_\n\n"
        "➖ `/remove <KODE>` atau `/del <KODE>`\n"
        "   _Menghapus saham dari watchlist_\n"
        "   _Contoh: `/remove UNVR`_\n\n"
        "🚀 `/summary` atau `/run`\n"
        "   _Jalankan dan kirim ringkasan saham sekarang juga_\n\n"
        "ℹ️ `/help`\n"
        "   _Menampilkan pesan bantuan ini_"
    )


def handle_command(text: str, chat_id: str) -> None:
    """Proses perintah pesan dari Telegram."""
    parts = text.strip().split()
    if not parts:
        return

    cmd = parts[0].lower().split("@")[0]  # strip bot username jika ada
    args = parts[1:]

    print(f"[INFO] Menerima command: {cmd} {args} dari chat_id {chat_id}")

    if cmd in ("/start", "/help"):
        send_message(_get_help_text())

    elif cmd in ("/watchlist", "/list"):
        current = load_watchlist()
        msg = (
            "📋 *DAFTAR WATCHLIST AKTIF*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join([f"• `{ticker}`" for ticker in current])
            + f"\n\n_Total: {len(current)} saham_"
            + "\n_Gunakan `/add <KODE>` atau `/remove <KODE>` untuk mengubah._"
        )
        send_message(msg)

    elif cmd in ("/add", "/tambah"):
        if not args:
            send_message("⚠️ Format salah. Gunakan: `/add <KODE_SAHAM>`\nContoh: `/add BBRI`")
            return

        ticker = args[0]
        success, msg = add_to_watchlist(ticker)
        send_message(msg)

    elif cmd in ("/remove", "/del", "/hapus"):
        if not args:
            send_message("⚠️ Format salah. Gunakan: `/remove <KODE_SAHAM>`\nContoh: `/remove UNVR`")
            return

        ticker = args[0]
        success, msg = remove_from_watchlist(ticker)
        send_message(msg)

    elif cmd in ("/summary", "/run", "/ringkasan"):
        send_message("⏳ Sedang memproses ringkasan fundamental & berita terbaru... Mohon tunggu 15-30 detik.")
        try:
            success = run_summary()
            if not success:
                send_message("❌ Terjadi kendala saat menghasilkan ringkasan.")
        except Exception as e:
            send_message(f"❌ Terjadi kesalahan: {e}")

    else:
        send_message(
            f"Perintah `{cmd}` tidak dikenali.\nKetik `/help` untuk melihat daftar perintah yang tersedia."
        )


def start_bot_listener() -> None:
    """Menjalankan loop long-polling untuk menerima pesan secara interaktif."""
    token = get_telegram_bot_token()
    allowed_chat_id = str(get_telegram_chat_id()).strip()

    print("=" * 60)
    print("🤖 Telegram Bot Listener Aktif")
    print(f"Target Chat ID: {allowed_chat_id}")
    print("Mendengarkan perintah (/watchlist, /add, /remove, /summary, /help)...")
    print("Tekan Ctrl+C untuk berhenti.")
    print("=" * 60)

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    offset = 0

    while True:
        try:
            params = {
                "offset": offset,
                "timeout": 25,
                "allowed_updates": ["message"],
            }
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json()

            if not data.get("ok"):
                time.sleep(2)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message")
                if not message:
                    continue

                from_chat_id = str(message.get("chat", {}).get("id", ""))
                text = message.get("text", "")

                # Validasi keamanan: hanya proses dari chat_id pemilik
                if from_chat_id != allowed_chat_id:
                    print(f"[SECURITY] Mengabaikan pesan dari ID tidak diizinkan: {from_chat_id}")
                    continue

                if text.startswith("/"):
                    handle_command(text, from_chat_id)

        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.ConnectionError:
            print("[WARN] Koneksi terputus, mencoba kembali dalam 5 detik...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n[INFO] Bot listener dihentikan oleh user.")
            break
        except Exception as e:
            print(f"[ERROR] Error pada loop polling: {e}")
            time.sleep(3)


if __name__ == "__main__":
    start_bot_listener()
