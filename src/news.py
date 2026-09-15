"""
news.py — Fetch dan ringkas berita saham via Gemini API.

Menggunakan Gemini API dengan tools google_search dan url_context
untuk mencari berita 24 jam terakhir tentang saham di watchlist.
"""

from google import genai
from google.genai import types

from src.config import get_gemini_api_key

# Model Gemini yang digunakan (ganti jika perlu)
GEMINI_MODEL = "gemini-3.7-flash"


def _build_news_prompt(watchlist: list[str], fundamentals: list[dict]) -> str:
    """
    Bangun prompt terstruktur untuk Gemini agar mencari dan merangkum:
    1. Sentimen Pasar Umum (IHSG)
    2. Sentimen & Dinamika Industri per Sektor (Umum, tanpa sebut saham tertentu)
    3. Highlights Berita Spesifik per Saham di Watchlist
    """
    # Buat konteks fundamental per saham
    fundamental_context = ""
    fund_map = {f["ticker"]: f for f in fundamentals}

    sectors = []
    for ticker in watchlist:
        data = fund_map.get(ticker)
        if data:
            sec = data.get("sector")
            if sec and sec != "Lainnya" and sec not in sectors:
                sectors.append(sec)
            fundamental_context += (
                f"- {ticker} ({sec or 'N/A'}): Rp {data['price']:,.0f} ({data['change_pct']:+.2f}%), "
                f"PER: {data['per'] or 'N/A'}, PBV: {data['pbv'] or 'N/A'}, "
                f"Volume: {data['volume'] or 'N/A'}\n"
            )
        else:
            fundamental_context += f"- {ticker}: data fundamental tidak tersedia\n"

    sectors_list_str = ", ".join(sectors) if sectors else "Financial Services, Communication Services, Industrials, Consumer Defensive"

    prompt = f"""Kamu adalah analis riset pasar saham Indonesia (IDX/BEI). Tugasmu merangkum sentimen pasar, dinamika industri, dan berita emiten.

ATURAN KETAT:
1. HANYA rangkum FAKTA dan sentimen industri yang objektif. JANGAN memberi rekomendasi aksi seperti "beli", "jual", "hold", "entry", "exit", atau saran trading.
2. Pada bagian SENTIMEN SEKTOR INDUSTRI: buat narasi murni secara UMUM mengenai kondisi, tren, atau katalis sektor tersebut. JANGAN menyebut atau mengacu pada satu saham tertentu.
3. Pada bagian SAHAM WATCHLIST: fokuskan pada fakta berita spesifik per saham yang ada di watchlist.
4. Sertakan link sumber untuk poin berita penting jika tersedia.
5. Gunakan bahasa Indonesia yang lugas dan profesional.

DATA WATCHLIST:
{fundamental_context}

TUGAS:
1. MARKET UMUM: Sentimen IHSG & arah makroekonomi hari ini (1-2 kalimat).
2. SENTIMEN SEKTOR INDUSTRI: Untuk sektor-sektor berikut [{sectors_list_str}], tulis narasi ringkas (1-2 kalimat) tentang dinamika pasar, tren bisnis, atau katalis umum industri tersebut saat ini (TANPA menyebut kode saham).
3. WATCHLIST SAHAM: Untuk masing-masing saham [{', '.join(watchlist)}], berikan 2 poin berita penting terkini beserta sumber. Jika tidak ada berita signifikan, tulis "Tidak ada berita signifikan dalam 24 jam terakhir."

FORMAT OUTPUT (ikuti struktur ini secara persis):
===MARKET_UMUM===
[1-2 kalimat ringkasan sentimen IHSG & makro]
Sumber: [link jika ada]

===SEKTOR:[NAMA_SEKTOR]===
[1-2 kalimat narasi sentimen & dinamika industri secara umum tanpa menyebut nama emiten]

===SAHAM:[KODE]===
- [poin berita #1] (Sumber: [link])
- [poin berita #2] (Sumber: [link])

===END===
"""
    return prompt


def fetch_news_summary(watchlist: list[str], fundamentals: list[dict]) -> dict:
    """
    Panggil Gemini API untuk mencari dan merangkum berita saham.
    Mendukung retry/fallback jika kuota search tools habis atau model sedang overload.

    Return dict:
    {
        "market_umum": "...",
        "per_saham": {
            "BBCA": "...",
            "TLKM": "...",
        },
        "raw_response": "..."  # untuk auditability
    }
    """
    api_key = get_gemini_api_key()
    client = genai.Client(api_key=api_key)
    prompt = _build_news_prompt(watchlist, fundamentals)

    # Urutan model dan strategi yang dicoba:
    # 1. gemini-3.7-flash dengan google_search
    # 2. gemini-3.7-flash tanpa tools (jika kuota grounding habis)
    # 3. gemini-3.5-flash sebagai fallback jika 3.7 overload
    # 4. gemini-3.5-flash-lite sebagai fallback terakhir
    configs_to_try = [
        (
            GEMINI_MODEL,
            types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.3,
            ),
            "dengan Google Search",
        ),
        (
            GEMINI_MODEL,
            types.GenerateContentConfig(temperature=0.3),
            "tanpa Google Search (fallback kuota)",
        ),
        (
            "gemini-3.5-flash",
            types.GenerateContentConfig(temperature=0.3),
            "fallback model gemini-3.5-flash",
        ),
        (
            "gemini-3.5-flash-lite",
            types.GenerateContentConfig(temperature=0.3),
            "fallback terakhir gemini-3.5-flash-lite",
        ),
    ]

    last_error = None
    for model_name, cfg, desc in configs_to_try:
        try:
            print(f"[INFO] Memanggil {model_name} ({desc})...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=cfg,
            )
            raw_text = response.text or ""
            if not raw_text.strip():
                print(f"[WARN] Respon dari {model_name} ({desc}) kosong, mencoba fallback berikutnya...")
                continue

            print(f"[INFO] Gemini response berhasil diterima via {model_name} ({len(raw_text)} chars)")
            result = _parse_news_response(raw_text, watchlist)
            result["raw_response"] = raw_text
            return result
        except Exception as e:
            last_error = e
            error_str = str(e)
            if "429" in error_str:
                print(f"[WARN] Quota limit pada {model_name} ({desc}): mencoba fallback berikutnya...")
            elif "503" in error_str:
                print(f"[WARN] Model {model_name} sedang overload (503): mencoba fallback berikutnya...")
            else:
                print(f"[WARN] Error saat memanggil {model_name} ({desc}): {e}")

    print(f"[ERROR] Semua opsi Gemini gagal dipanggil. Error terakhir: {last_error}")
    return {
        "market_umum": "Gagal mengambil ringkasan berita dari Gemini. Silakan cek manual.",
        "per_saham": {ticker: "Berita tidak tersedia saat ini." for ticker in watchlist},
        "raw_response": f"ERROR: {last_error}",
    }


def _parse_news_response(raw_text: str, watchlist: list[str]) -> dict:
    """
    Parse response Gemini yang terformat ke dalam dict:
    - market_umum: ringkasan IHSG & makro
    - per_sektor: narasi sentimen industri per sektor (umum)
    - per_saham: poin berita spesifik per emiten
    """
    result = {
        "market_umum": "",
        "per_sektor": {},
        "per_saham": {},
    }

    # Parse market umum
    if "===MARKET_UMUM===" in raw_text:
        try:
            market_section = raw_text.split("===MARKET_UMUM===")[1]
            end_markers = ["===SEKTOR:", "===SAHAM:", "===END==="]
            for marker in end_markers:
                if marker in market_section:
                    market_section = market_section.split(marker)[0]
                    break
            result["market_umum"] = market_section.strip()
        except (IndexError, ValueError):
            result["market_umum"] = "Ringkasan market tidak tersedia."

    # Parse per sektor (narasi umum tanpa acuan saham tunggal)
    import re
    sektor_blocks = re.findall(r"===SEKTOR:(.*?)===\s*([\s\S]*?)(?====SEKTOR:|===SAHAM:|===END===|$)", raw_text)
    for sec_name, sec_content in sektor_blocks:
        sec_name = sec_name.strip()
        sec_content = sec_content.strip()
        if sec_name and sec_content:
            result["per_sektor"][sec_name] = sec_content

    # Parse per saham
    for ticker in watchlist:
        marker = f"===SAHAM:{ticker}==="
        if marker in raw_text:
            try:
                section = raw_text.split(marker)[1]
                end_markers = ["===SAHAM:", "===SEKTOR:", "===END==="]
                for end_marker in end_markers:
                    if end_marker in section:
                        section = section.split(end_marker)[0]
                        break
                result["per_saham"][ticker] = section.strip()
            except (IndexError, ValueError):
                result["per_saham"][ticker] = "Berita tidak tersedia."
        else:
            result["per_saham"][ticker] = "Tidak ada berita signifikan dalam 24 jam terakhir."

    return result
