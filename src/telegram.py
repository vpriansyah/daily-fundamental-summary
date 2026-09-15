"""
telegram.py — Kirim pesan ke Telegram via Bot API.
"""

import time
import requests

from src.config import get_telegram_bot_token, get_telegram_chat_id


# Telegram API base URL
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

# Timeout untuk request ke Telegram (detik)
REQUEST_TIMEOUT = 30


def send_message(text: str, parse_mode: str = "Markdown") -> bool:
    """
    Kirim pesan tunggal ke Telegram chat.

    Return True jika sukses, False jika gagal.
    """
    token = get_telegram_bot_token()
    chat_id = get_telegram_chat_id()

    url = TELEGRAM_API_URL.format(token=token)

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        response_data = response.json()

        if response.status_code == 200 and response_data.get("ok"):
            print("[INFO] Pesan berhasil dikirim ke Telegram ✓")
            return True

        # Jika gagal karena parsing error Markdown, coba kirim tanpa parse_mode (plain text)
        error_desc = response_data.get("description", "Unknown error")
        if "can't parse entities" in error_desc.lower() and parse_mode:
            print("[WARN] Gagal parse Markdown, mencoba fallback kirim plain text...")
            payload.pop("parse_mode", None)
            retry_resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            if retry_resp.status_code == 200 and retry_resp.json().get("ok"):
                print("[INFO] Pesan plain text berhasil dikirim ✓")
                return True

        print(f"[ERROR] Telegram API error: {error_desc}")

        # Handle pesan terlalu panjang jika ada
        if "message is too long" in error_desc.lower():
            print("[INFO] Mencoba kirim pesan yang dipotong...")
            return _send_truncated(text, url, chat_id)

        return False

    except requests.exceptions.Timeout:
        print(f"[ERROR] Telegram API timeout setelah {REQUEST_TIMEOUT}s")
        return False
    except requests.exceptions.ConnectionError:
        print("[ERROR] Gagal konek ke Telegram API. Cek koneksi internet.")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error saat kirim ke Telegram: {e}")
        return False


def send_bubbles(bubbles: list[str], delay_seconds: float = 0.5) -> bool:
    """
    Kirim sekumpulan pesan dalam bubble-bubble terpisah.
    Memberi jeda singkat antar bubble agar urutan pesan tetap konsisten di aplikasi Telegram.
    """
    if not bubbles:
        print("[WARN] Tidak ada bubble pesan yang hendak dikirim.")
        return False

    all_success = True
    total = len(bubbles)

    for idx, bubble in enumerate(bubbles, start=1):
        if not bubble.strip():
            continue

        print(f"[INFO] Mengirim bubble [{idx}/{total}] ({len(bubble)} chars)...")
        success = send_message(bubble)
        if not success:
            all_success = False

        # Beri jeda kecil agar urutan bubble di Telegram rapi
        if idx < total:
            time.sleep(delay_seconds)

    return all_success


def _send_truncated(text: str, url: str, chat_id: str) -> bool:
    """
    Kirim pesan yang dipotong jika terlalu panjang.
    """
    chunk_size = 3800
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    success = True
    for i, chunk in enumerate(chunks):
        if i > 0:
            chunk = f"(lanjutan {i + 1}/{len(chunks)})\n\n{chunk}"

        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "disable_web_page_preview": True,
        }

        try:
            resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                print(f"[ERROR] Gagal kirim chunk {i + 1}: {resp.text}")
                success = False
        except Exception as e:
            print(f"[ERROR] Error kirim chunk {i + 1}: {e}")
            success = False

    return success
