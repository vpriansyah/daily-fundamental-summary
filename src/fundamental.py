"""
fundamental.py — Fetch data fundamental saham via yfinance & direct Yahoo Chart API.
Dirancang tahan banting di VPS (anti-blocking IP data center).
"""

import requests
import yfinance as yf

# Metadata cadangan emiten populer IDX jika endpoint profil Yahoo dibatasi di VPS
IDX_METADATA_FALLBACK = {
    "BBCA": {
        "name": "Bank Central Asia Tbk",
        "sector": "Financial Services",
        "industry": "Banks - Regional",
    },
    "BBRI": {
        "name": "Bank Rakyat Indonesia (Persero) Tbk",
        "sector": "Financial Services",
        "industry": "Banks - Regional",
    },
    "BMRI": {
        "name": "Bank Mandiri (Persero) Tbk",
        "sector": "Financial Services",
        "industry": "Banks - Regional",
    },
    "BBNI": {
        "name": "Bank Negara Indonesia (Persero) Tbk",
        "sector": "Financial Services",
        "industry": "Banks - Regional",
    },
    "TLKM": {
        "name": "Telkom Indonesia (Persero) Tbk.",
        "sector": "Communication Services",
        "industry": "Telecom Services",
    },
    "ASII": {
        "name": "Astra International Tbk",
        "sector": "Industrials",
        "industry": "Conglomerates",
    },
    "UNVR": {
        "name": "Unilever Indonesia Tbk",
        "sector": "Consumer Defensive",
        "industry": "Household & Personal Products",
    },
    "ICBP": {
        "name": "Indofood CBP Sukses Makmur Tbk",
        "sector": "Consumer Defensive",
        "industry": "Packaged Foods",
    },
    "INDF": {
        "name": "Indofood Sukses Makmur Tbk",
        "sector": "Consumer Defensive",
        "industry": "Packaged Foods",
    },
    "GOTO": {
        "name": "GoTo Gojek Tokopedia Tbk",
        "sector": "Technology",
        "industry": "Internet Content & Information",
    },
    "AMMN": {
        "name": "Amman Mineral Internasional Tbk",
        "sector": "Basic Materials",
        "industry": "Copper",
    },
    "BREN": {
        "name": "Barito Renewables Energy Tbk",
        "sector": "Utilities",
        "industry": "Utilities - Renewable",
    },
    "ADRO": {
        "name": "Adaro Energy Indonesia Tbk",
        "sector": "Energy",
        "industry": "Thermal Coal",
    },
    "PTBA": {
        "name": "Bukit Asam Tbk",
        "sector": "Energy",
        "industry": "Thermal Coal",
    },
    "KLBF": {
        "name": "Kalbe Farma Tbk",
        "sector": "Healthcare",
        "industry": "Drug Manufacturers",
    },
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


def _fetch_from_chart_api(ticker: str) -> dict | None:
    """
    Fallback langsung ke Yahoo Finance v8 chart API.
    Endpoint ini sangat andal, tidak diblokir oleh Yahoo pada IP VPS/data center,
    dan tidak memerlukan cookie/crumb yang rumit.
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}.JK?interval=1d&range=5d"
    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None

        data = resp.json()
        results = data.get("chart", {}).get("result")
        if not results:
            return None

        meta = results[0].get("meta", {})
        current_price = meta.get("regularMarketPrice")
        if current_price is None or current_price == 0:
            return None

        previous_close = meta.get("chartPreviousClose") or meta.get("previousClose") or current_price

        if previous_close and previous_close > 0:
            change_pct = ((current_price - previous_close) / previous_close) * 100
        else:
            change_pct = 0.0

        fallback_meta = IDX_METADATA_FALLBACK.get(ticker, {})

        return {
            "ticker": ticker,
            "name": meta.get("shortName") or meta.get("longName") or fallback_meta.get("name", ticker),
            "symbol": f"{ticker}.JK",
            "sector": fallback_meta.get("sector", "Lainnya"),
            "industry": fallback_meta.get("industry", "Lainnya"),
            "price": float(current_price),
            "previous_close": float(previous_close),
            "change_pct": round(change_pct, 2),
            "per": None,
            "pbv": None,
            "volume": meta.get("regularMarketVolume"),
            "market_cap": None,
            "currency": meta.get("currency", "IDR"),
        }
    except Exception as e:
        print(f"[DEBUG] Chart API fallback gagal untuk {ticker}: {e}")
        return None


def fetch_fundamental(ticker: str) -> dict | None:
    """
    Ambil data fundamental dasar untuk satu saham dengan multi-layer fallback.
    Layer 1: yfinance Ticker.info (data lengkap PER, PBV)
    Layer 2: Direct Yahoo Chart API (andal di IP VPS data center)
    Layer 3: yfinance fast_info / history
    """
    symbol = f"{ticker}.JK"
    fallback_meta = IDX_METADATA_FALLBACK.get(ticker, {})

    # Layer 1: Coba yfinance Ticker.info
    try:
        stock = yf.Ticker(symbol)
        info = stock.info

        if info and info.get("regularMarketPrice") is not None:
            current_price = info.get("regularMarketPrice", 0)
            previous_close = info.get("regularMarketPreviousClose", 0)

            if previous_close and previous_close > 0:
                change_pct = ((current_price - previous_close) / previous_close) * 100
            else:
                change_pct = 0.0

            result = {
                "ticker": ticker,
                "name": info.get("shortName") or fallback_meta.get("name", ticker),
                "symbol": symbol,
                "sector": info.get("sector") or fallback_meta.get("sector", "Lainnya"),
                "industry": info.get("industry") or fallback_meta.get("industry", "Lainnya"),
                "price": current_price,
                "previous_close": previous_close,
                "change_pct": round(change_pct, 2),
                "per": info.get("trailingPE"),
                "pbv": info.get("priceToBook"),
                "volume": info.get("regularMarketVolume"),
                "market_cap": info.get("marketCap"),
                "currency": info.get("currency", "IDR"),
            }
            print(f"[INFO] Fundamental {ticker} (via info): Rp {current_price:,.0f} ({change_pct:+.2f}%)")
            return result

    except Exception as e:
        print(f"[WARN] yfinance info gagal untuk {symbol}: {e}")

    # Layer 2: Direct Yahoo Finance Chart API (solusi utama VPS data center)
    print(f"[INFO] Mencoba direct Chart API untuk {ticker} (VPS fallback)...")
    chart_data = _fetch_from_chart_api(ticker)
    if chart_data is not None:
        # Coba lengkapi PER/PBV dari fast_info jika memungkinkan
        try:
            stock = yf.Ticker(symbol)
            fi = stock.fast_info
            if hasattr(fi, "market_cap"):
                chart_data["market_cap"] = fi.market_cap
        except Exception:
            pass

        print(f"[INFO] Fundamental {ticker} (via Chart API): Rp {chart_data['price']:,.0f} ({chart_data['change_pct']:+.2f}%)")
        return chart_data

    # Layer 3: fast_info & history
    try:
        stock = yf.Ticker(symbol)
        fi = stock.fast_info
        last_price = getattr(fi, "last_price", None)
        prev_close = getattr(fi, "previous_close", None)

        if last_price is not None and prev_close is not None and prev_close > 0:
            change_pct = ((last_price - prev_close) / prev_close) * 100
            result = {
                "ticker": ticker,
                "name": fallback_meta.get("name", ticker),
                "symbol": symbol,
                "sector": fallback_meta.get("sector", "Lainnya"),
                "industry": fallback_meta.get("industry", "Lainnya"),
                "price": last_price,
                "previous_close": prev_close,
                "change_pct": round(change_pct, 2),
                "per": None,
                "pbv": None,
                "volume": getattr(fi, "last_volume", None),
                "market_cap": getattr(fi, "market_cap", None),
                "currency": getattr(fi, "currency", "IDR"),
            }
            print(f"[INFO] Fundamental {ticker} (via fast_info): Rp {last_price:,.0f} ({change_pct:+.2f}%)")
            return result
    except Exception as e:
        print(f"[WARN] fast_info gagal untuk {symbol}: {e}")

    print(f"[ERROR] Semua metode fundamental gagal untuk {ticker}.")
    return None


def fetch_all_fundamentals(watchlist: list[str]) -> list[dict]:
    """
    Fetch data fundamental untuk semua saham di watchlist.
    Saham yang gagal di-skip, sisanya tetap dikembalikan.
    """
    results = []

    for ticker in watchlist:
        data = fetch_fundamental(ticker)
        if data is not None:
            results.append(data)

    print(f"[INFO] Fundamental berhasil diambil: {len(results)}/{len(watchlist)} saham")
    return results
