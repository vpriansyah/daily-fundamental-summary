"""
news.py — Fetch dan ringkas berita saham via Gemini API dengan Grounding Berita Real-Time.

Menggunakan kombinasi live RSS feed berita finansial terkini (24-48 jam terakhir)
yang diinjeksi langsung ke prompt Gemini, memastikan berita SELALU bertanggal HARI INI
dan tidak mengalami halusinasi tanggal lampau (misal: Mei 2024).
"""

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from google import genai
from google.genai import types

from src.config import get_gemini_api_key

# Model Gemini yang digunakan
GEMINI_MODEL = "gemini-3.7-flash"


def fetch_rss_news(query: str, max_items: int = 3) -> list[dict]:
    """
    Ambil artikel berita terkini (24-48 jam terakhir) via Google News RSS Indonesia.
    Mengembalikan list berisi title, link asli, dan pubDate.
    """
    encoded_query = urllib.parse.quote(query)
    # Gunakan parameter when:2d untuk membatasi berita 48 jam terakhir
    url = f"https://news.google.com/rss/search?q={encoded_query}+when:2d&hl=id&gl=ID&ceid=ID:id"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        xml_data = urllib.request.urlopen(req, timeout=8).read()
        root = ET.fromstring(xml_data)
        items = root.findall("./channel/item")

        articles = []
        for item in items[:max_items]:
            title = item.find("title").text if item.find("title") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
            if title and link:
                articles.append({
                    "title": title.strip(),
                    "link": link.strip(),
                    "pub_date": pub_date.strip(),
                })
        return articles
    except Exception as e:
        print(f"[WARN] Gagal fetch RSS untuk query '{query}': {e}")
        return []


def _collect_live_news(watchlist: list[str]) -> dict[str, list[dict]]:
    """
    Kumpulkan berita real-time untuk pasar IHSG dan setiap saham di watchlist.
    """
    print("[INFO] Mengambil feed berita real-time 24-48 jam terakhir...")
    news_bundle = {}

    # Berita makro / IHSG
    news_bundle["IHSG"] = fetch_rss_news("IHSG hari ini", max_items=3)

    # Berita per saham di watchlist
    for ticker in watchlist:
        news_bundle[ticker] = fetch_rss_news(f"saham {ticker}", max_items=3)

    total_articles = sum(len(v) for v in news_bundle.values())
    print(f"[INFO] Feed berita real-time berhasil dihimpun: {total_articles} artikel.")
    return news_bundle


def _build_news_prompt(
    watchlist: list[str],
    fundamentals: list[dict],
    live_news: dict[str, list[dict]],
) -> str:
    """
    Bangun prompt terstruktur dengan grounding berita real-time hari ini.
    """
    # 1. Konteks Fundamental
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

    # 2. Konteks Berita Terkini (Ground Truth)
    news_context = ""
    for topic, articles in live_news.items():
        if articles:
            news_context += f"\n[{topic}]:\n"
            for a in articles:
                news_context += f"- Judul: {a['title']}\n  Tgl: {a['pub_date']}\n  Link: {a['link']}\n"
        else:
            news_context += f"\n[{topic}]: Tidak ada artikel berita baru dalam 24-48 jam terakhir.\n"

    prompt = f"""Kamu adalah analis riset pasar saham Indonesia (IDX/BEI). Tugasmu merangkum sentimen pasar, dinamika industri, dan berita emiten berbasis data aktual.

ATURAN KETAT (WAJIB DIPATUHI):
1. HANYA rangkum FAKTA dari artikel BERITA TERKINI yang telah disediakan di bawah ini.
2. DILARANG KERAS MENGARANG BERITA LAMA ATAU LINK DARI TAHUN-TAHUN LAMPAU (seperti 2024 atau sebelumnya). Seluruh artikel yang disediakan di bawah bertanggal hari ini.
3. Gunakan tautan (link) asli yang tertera pada bagian artikel di bawah.
4. JANGAN memberi rekomendasi aksi seperti "beli", "jual", "hold", "entry", "exit", atau saran trading.
5. Pada bagian SENTIMEN SEKTOR INDUSTRI: buat narasi murni secara UMUM mengenai kondisi, tren, atau katalis sektor tersebut. JANGAN menyebut atau mengacu pada satu saham tertentu.
6. Pada bagian SAHAM WATCHLIST: fokuskan pada fakta berita spesifik per saham yang ada di watchlist. Jika tidak ada artikel relevan, tulis: "Tidak ada berita signifikan dalam 24 jam terakhir."
7. Gunakan bahasa Indonesia yang lugas dan profesional.

DATA FUNDAMENTAL TERKINI:
{fundamental_context}

ARTIKEL BERITA TERKINI (GROUND TRUTH TERVERIFIKASI):
{news_context}

TUGAS:
1. MARKET UMUM: Sentimen IHSG & arah makroekonomi hari ini (1-2 kalimat), sertakan link sumber dari artikel IHSG di atas.
2. SENTIMEN SEKTOR INDUSTRI: Untuk sektor-sektor berikut [{sectors_list_str}], tulis narasi ringkas (1-2 kalimat) tentang dinamika pasar, tren bisnis, atau katalis umum industri tersebut saat ini (TANPA menyebut nama/kode saham).
3. WATCHLIST SAHAM: Untuk masing-masing saham [{', '.join(watchlist)}], berikan 2 poin berita penting berdasarkan artikel di atas beserta link sumber.

FORMAT OUTPUT (ikuti struktur ini secara persis):
===MARKET_UMUM===
[1-2 kalimat ringkasan sentimen IHSG & makro]
Sumber: [link dari artikel IHSG di atas]

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
    Dilengkapi live RSS feed sebagai ground truth untuk mencegah halusinasi tanggal lama.
    """
    api_key = get_gemini_api_key()
    client = genai.Client(api_key=api_key)

    # Ambil artikel berita real-time terkini terlebih dahulu
    live_news = _collect_live_news(watchlist)
    prompt = _build_news_prompt(watchlist, fundamentals, live_news)

    # Urutan model fallback
    configs_to_try = [
        (
            GEMINI_MODEL,
            types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.2,
            ),
            "dengan Google Search",
        ),
        (
            GEMINI_MODEL,
            types.GenerateContentConfig(temperature=0.2),
            "tanpa Google Search (grounding live RSS)",
        ),
        (
            "gemini-3.5-flash",
            types.GenerateContentConfig(temperature=0.2),
            "fallback model gemini-3.5-flash",
        ),
        (
            "gemini-3.5-flash-lite",
            types.GenerateContentConfig(temperature=0.2),
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
        "per_sektor": {},
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
