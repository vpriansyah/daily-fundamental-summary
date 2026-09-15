"""
composer.py — Format data fundamental + berita jadi pesan Telegram (multi-bubble terstruktur).
Menyajikan:
- Bubble 1: Kilas Pasar Makro & Sentimen IHSG (Ringkas & Berjarak)
- Bubble 2: Fundamental per Sektor Industri (Ringkas seperti Bubble 1)
- Bubble 3: Highlights Emiten & Sorotan Berita Watchlist (Spacious, Ber-margin)
- Bubble 4: Catatan Disclaimer & Panduan Operasional
"""

import re
from collections import defaultdict
from datetime import datetime, timezone, timedelta

# Timezone WIB (UTC+7)
WIB = timezone(timedelta(hours=7))

# Limit karakter per bubble untuk kenyamanan membaca di mobile Telegram
TELEGRAM_CHAR_LIMIT = 3200

# Mapping hari & bulan Bahasa Indonesia
HARI_MAP = {
    "Monday": "Senin",
    "Tuesday": "Selasa",
    "Wednesday": "Rabu",
    "Thursday": "Kamis",
    "Friday": "Jumat",
    "Saturday": "Sabtu",
    "Sunday": "Minggu",
}

BULAN_MAP = {
    "January": "Januari",
    "February": "Februari",
    "March": "Maret",
    "April": "April",
    "May": "Mei",
    "June": "Juni",
    "July": "Juli",
    "August": "Agustus",
    "September": "September",
    "October": "Oktober",
    "November": "November",
    "December": "Desember",
}

# Mapping translasi sektor & ikon
SEKTOR_TRANSLATION = {
    "Financial Services": ("🏦", "Keuangan & Perbankan"),
    "Communication Services": ("📡", "Telekomunikasi"),
    "Industrials": ("🏭", "Perindustrian & Konglomerasi"),
    "Consumer Defensive": ("🛒", "Konsumer Primer"),
    "Consumer Cyclical": ("🛍️", "Konsumer Siklikal"),
    "Energy": ("⚡", "Energi & Tambang"),
    "Basic Materials": ("🧱", "Material Dasar & Kimia"),
    "Healthcare": ("💊", "Kesehatan & Farmasi"),
    "Technology": ("💻", "Teknologi & Digital"),
    "Real Estate": ("🏢", "Properti & Real Estat"),
    "Utilities": ("💡", "Utilitas"),
}


def _format_date_id(dt: datetime) -> str:
    """Format tanggal ke Bahasa Indonesia (contoh: Selasa, 15 September 2026)."""
    day_en = dt.strftime("%A")
    month_en = dt.strftime("%B")
    day_id = HARI_MAP.get(day_en, day_en)
    month_id = BULAN_MAP.get(month_en, month_en)
    return f"{day_id}, {dt.day} {month_id} {dt.year}"


def _format_volume(val: float | int | None) -> str:
    """Format volume ke format ringkas (K, M, B)."""
    if val is None:
        return "-"
    try:
        val = float(val)
        if val >= 1_000_000_000:
            return f"{val / 1_000_000_000:.1f}B"
        if val >= 1_000_000:
            return f"{val / 1_000_000:.1f}M"
        if val >= 1_000:
            return f"{val / 1_000:.1f}K"
        return f"{val:,.0f}"
    except (ValueError, TypeError):
        return str(val)


def _get_status_icon(change_pct: float) -> tuple[str, str]:
    """Return icon status dan prefix tanda plus/minus."""
    if change_pct > 0:
        return "🟢", "+"
    elif change_pct < 0:
        return "🔴", ""
    return "⚪", ""


def _compose_bubble_market(now: datetime, news: dict) -> str:
    """Bubble 1: Ringkasan Pasar Makro & IHSG."""
    tanggal_str = _format_date_id(now)
    market_text = news.get("market_umum", "Data kondisi pasar saat ini belum tersedia.").strip()

    lines = [
        "📊 *KILAS PASAR IHSG & MAKRO*",
        f"📅 {tanggal_str}  •  ⏰ {now.strftime('%H:%M')} WIB",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "🌐 *Sentimen & Dinamika Pasar:*",
        "",
        f"{market_text}",
    ]
    return "\n".join(lines)


def _get_sector_display(raw_key: str) -> tuple[str, str]:
    """Helper untuk mencocokkan nama sektor bahasa Inggris/Indonesia dengan icon & label resmi."""
    for eng_sec, (icon, id_name) in SEKTOR_TRANSLATION.items():
        if (
            eng_sec.lower() in raw_key.lower()
            or id_name.lower() in raw_key.lower()
            or raw_key.lower() in id_name.lower()
        ):
            return icon, id_name
    return "📁", raw_key.replace("Sektor", "").strip()


def _compose_bubble_sectors(now: datetime, fundamentals: list[dict], news: dict) -> str:
    """
    Bubble 2: Sentimen & Dinamika Fundamental per Sektor Industri.
    Narasi makro & sentimen industri secara umum (tanpa mengacu pada saham tertentu).
    Format dibuat ringkas, elegan, dan sepadan dengan Bubble 1 IHSG.
    """
    tanggal_str = _format_date_id(now)
    per_sektor = news.get("per_sektor", {})

    # Kumpulkan sektor unik yang relevan dari watchlist
    unique_sectors = []
    for item in fundamentals:
        sec = item.get("sector")
        if sec and sec != "Lainnya" and sec not in unique_sectors:
            unique_sectors.append(sec)

    lines = [
        "🏢 *SENTIMEN PER SEKTOR INDUSTRI*",
        f"📅 {tanggal_str}  •  ⏰ {now.strftime('%H:%M')} WIB",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "Dinamika & katalis industri yang mempengaruhi pasar hari ini:",
        "",
    ]

    if per_sektor:
        for sec_name, narrative in per_sektor.items():
            icon, id_sec = _get_sector_display(sec_name)
            lines.append(f"{icon} *Sektor {id_sec}*")
            lines.append(f"• {narrative.strip()}")
            lines.append("")
    else:
        # Fallback narasi umum industri jika data sektor AI belum terisi
        for sec in unique_sectors:
            icon, id_sec = SEKTOR_TRANSLATION.get(sec, ("📁", sec))
            lines.append(f"{icon} *Sektor {id_sec}*")
            lines.append("• Sentimen industri bergerak dinamis mengikuti rilis laporan keuangan dan respon pasar terhadap arah kebijakan makroekonomi.")
            lines.append("")

    return "\n".join(lines).strip()


def _compose_bubbles_watchlist(fundamentals: list[dict], news: dict) -> list[str]:
    """
    Bubble 3: Card Detail Emiten & Sorotan Berita.
    Diberikan MARGIN yang lega dan lapang agar tidak tumpuk menumpuk.
    """
    fund_map = {f["ticker"]: f for f in fundamentals}
    per_saham = news.get("per_saham", {})

    all_tickers = list(dict.fromkeys(
        [f["ticker"] for f in fundamentals] + list(per_saham.keys())
    ))

    cards = []
    header_intro = [
        "📌 *HIGHLIGHTS EMITEN & BERITA*",
        f"Daftar Pantauan: `{', '.join(all_tickers)}`",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    current_bubble_lines = list(header_intro)

    for i, ticker in enumerate(all_tickers):
        data = fund_map.get(ticker)
        news_text = per_saham.get(ticker, "Tidak ada berita signifikan 24 jam terakhir.").strip()

        card_lines = []

        if data:
            icon, sign = _get_status_icon(data["change_pct"])
            company_name = data.get("name", ticker)
            price_str = f"Rp {data['price']:,.0f}"
            pct_str = f"{sign}{data['change_pct']:.2f}%"

            # Header Card
            card_lines.append(f"{icon} *{ticker}* — _{company_name}_")
            card_lines.append("")

            # Metrik Harga & Valuasi (Diberi spasi agar tidak tumpuk)
            card_lines.append(f"💵 *Harga:* {price_str} ({pct_str})")

            val_items = []
            if data.get("per") is not None:
                val_items.append(f"PER {data['per']:.1f}x")
            if data.get("pbv") is not None:
                val_items.append(f"PBV {data['pbv']:.2f}x")
            if data.get("volume") is not None:
                val_items.append(f"Vol {_format_volume(data['volume'])}")

            if val_items:
                card_lines.append(f"📊 *Valuasi:* {'  •  '.join(val_items)}")

            # Sektor
            sec = data.get("sector")
            if sec:
                _, id_sec = SEKTOR_TRANSLATION.get(sec, ("", sec))
                card_lines.append(f"🏢 *Sektor:* {id_sec}")

        else:
            card_lines.append(f"⚪ *{ticker}* (Data fundamental tidak tersedia)")

        card_lines.append("")

        # Poin Berita
        card_lines.append("📰 *Sorotan Berita:*")
        for line in news_text.split("\n"):
            clean_l = line.strip()
            if clean_l:
                # Parse format: "- [teks] (Sumber: URL)" -> "• [teks] 🔗 Baca Berita (URL)"
                source_match = re.search(r'\(Sumber:\s*(.+?)\)\s*$', clean_l)
                if source_match:
                    url = source_match.group(1).strip()
                    base_text = clean_l[:source_match.start()].strip()
                    if base_text.startswith("- ") or base_text.startswith("• "):
                        base_text = base_text[2:]
                    clean_l = f"• {base_text} 🔗 Baca Berita ({url})"
                elif not clean_l.startswith("-") and not clean_l.startswith("•"):
                    clean_l = f"• {clean_l}"
                card_lines.append(f"{clean_l}")

        card_str = "\n".join(card_lines)

        # Cek batas karakter per bubble
        if len("\n".join(current_bubble_lines)) + len(card_str) > TELEGRAM_CHAR_LIMIT:
            cards.append("\n".join(current_bubble_lines).strip())
            current_bubble_lines = [
                "📌 *HIGHLIGHTS EMITEN (Lanjutan)*",
                "━━━━━━━━━━━━━━━━━━━━━━",
                "",
                card_str,
            ]
        else:
            current_bubble_lines.append(card_str)

        # Tambahkan divider berjarak jika bukan emiten terakhir
        if i < len(all_tickers) - 1:
            current_bubble_lines.append("")
            current_bubble_lines.append("──────────────────────")
            current_bubble_lines.append("")

    if current_bubble_lines:
        cards.append("\n".join(current_bubble_lines).strip())

    return cards


def _compose_bubble_disclaimer() -> str:
    """Bubble 4: Disclaimer & Panduan Operasional."""
    lines = [
        "⚠️ *CATATAN & DISCLAIMER RESMI*",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "• Ringkasan ini disusun otomatis dari data pasar dan berita publik terbuka.",
        "",
        "• BUKAN merupakan anjuran, rekomendasi, atau ajakan jual/beli saham (DYOR).",
        "",
        "• Seluruh keputusan investasi adalah tanggung jawab pribadi investor.",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "💡 *Akses Cepat Bot:*",
        "• `/watchlist` — Lihat daftar saham aktif",
        "• `/add <KODE>` — Tambah saham (misal: `/add BBRI`)",
        "• `/remove <KODE>` — Hapus saham (misal: `/remove UNVR`)",
        "• `/summary` — Minta update ringkasan sekarang",
    ]
    return "\n".join(lines)


def compose_bubbles(fundamentals: list[dict], news: dict) -> list[str]:
    """
    Menghasilkan urutan bubble pesan:
    1. Kilas Pasar Makro & IHSG
    2. Fundamental per Sektor Industri (Ringkas & Rapi)
    3. Highlights Detail Emiten & Berita (Spacious dengan Margin yang Nyaman)
    4. Catatan Disclaimer & Panduan Bot
    """
    now = datetime.now(WIB)
    bubbles = []

    # 1. Bubble Pasar Makro & IHSG
    bubbles.append(_compose_bubble_market(now, news))

    # 2. Bubble Fundamental per Sektor Industri (Ringkas)
    bubbles.append(_compose_bubble_sectors(now, fundamentals, news))

    # 3. Bubble Highlights Emiten & Berita (Ber-margin)
    bubbles.extend(_compose_bubbles_watchlist(fundamentals, news))

    # 4. Bubble Disclaimer & Panduan
    bubbles.append(_compose_bubble_disclaimer())

    return bubbles


def compose_message(fundamentals: list[dict], news: dict) -> str:
    """Fallback kompatibilitas: gabungkan semua bubble menjadi 1 pesan teks."""
    bubbles = compose_bubbles(fundamentals, news)
    return "\n\n".join(bubbles)
