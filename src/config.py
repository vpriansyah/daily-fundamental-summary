"""
config.py — Load watchlist dan environment variables.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env file jika ada (untuk development lokal)
load_dotenv()

# Path root project (parent dari folder src/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_watchlist() -> list[str]:
    """
    Baca watchlist saham dari watchlist.json.
    Return list kode saham (tanpa suffix .JK).
    """
    watchlist_path = PROJECT_ROOT / "watchlist.json"

    if not watchlist_path.exists():
        print(f"[ERROR] File watchlist tidak ditemukan: {watchlist_path}")
        sys.exit(1)

    try:
        with open(watchlist_path, "r", encoding="utf-8") as f:
            watchlist = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Format watchlist.json tidak valid: {e}")
        sys.exit(1)

    if not isinstance(watchlist, list) or len(watchlist) == 0:
        print("[ERROR] watchlist.json harus berisi array kode saham, minimal 1 item.")
        sys.exit(1)

    # Normalisasi: uppercase, strip whitespace
    watchlist = [ticker.strip().upper() for ticker in watchlist if isinstance(ticker, str)]

    print(f"[INFO] Watchlist loaded: {watchlist}")
    return watchlist


def save_watchlist(watchlist: list[str]) -> bool:
    """
    Simpan daftar kode saham ke watchlist.json.
    """
    watchlist_path = PROJECT_ROOT / "watchlist.json"
    try:
        # Bersihkan & pastikan unik berurutan
        clean_list = []
        for ticker in watchlist:
            sym = ticker.strip().upper().replace(".JK", "")
            if sym and sym not in clean_list:
                clean_list.append(sym)

        with open(watchlist_path, "w", encoding="utf-8") as f:
            json.dump(clean_list, f, indent=2)
        print(f"[INFO] Watchlist berhasil diperbarui: {clean_list}")
        return True
    except Exception as e:
        print(f"[ERROR] Gagal menyimpan watchlist.json: {e}")
        return False


def add_to_watchlist(ticker: str) -> tuple[bool, str]:
    """
    Tambah 1 kode saham ke watchlist.
    Mengembalikan (sukses: bool, pesan: str).
    """
    clean_ticker = ticker.strip().upper().replace(".JK", "")
    if not clean_ticker.isalpha() or len(clean_ticker) not in (4, 5):
        return False, f"Kode saham '{clean_ticker}' tidak valid (format 4-5 huruf, contoh: BBRI)."

    current = load_watchlist()
    if clean_ticker in current:
        return False, f"Saham {clean_ticker} sudah ada dalam watchlist."

    current.append(clean_ticker)
    if save_watchlist(current):
        return True, f"✅ Saham {clean_ticker} berhasil ditambahkan ke watchlist.\nWatchlist sekarang: {', '.join(current)}"
    return False, "Gagal menyimpan perubahan ke watchlist.json."


def remove_from_watchlist(ticker: str) -> tuple[bool, str]:
    """
    Hapus 1 kode saham dari watchlist.
    Mengembalikan (sukses: bool, pesan: str).
    """
    clean_ticker = ticker.strip().upper().replace(".JK", "")
    current = load_watchlist()

    if clean_ticker not in current:
        return False, f"Saham {clean_ticker} tidak ditemukan di watchlist."

    if len(current) <= 1:
        return False, "Watchlist minimal harus memiliki 1 saham."

    current.remove(clean_ticker)
    if save_watchlist(current):
        return True, f"🗑️ Saham {clean_ticker} berhasil dihapus dari watchlist.\nWatchlist sekarang: {', '.join(current)}"
    return False, "Gagal menyimpan perubahan ke watchlist.json."


def get_env_var(name: str) -> str:
    """
    Ambil environment variable, raise error jika tidak ada.
    """
    value = os.environ.get(name)
    if not value:
        print(f"[ERROR] Environment variable '{name}' tidak ditemukan atau kosong.")
        print(f"        Pastikan sudah diset di .env (lokal) atau GitHub Actions Secrets.")
        sys.exit(1)
    return value


def get_gemini_api_key() -> str:
    return get_env_var("GEMINI_API_KEY")


def get_telegram_bot_token() -> str:
    return get_env_var("TELEGRAM_BOT_TOKEN")


def get_telegram_chat_id() -> str:
    return get_env_var("TELEGRAM_CHAT_ID")
