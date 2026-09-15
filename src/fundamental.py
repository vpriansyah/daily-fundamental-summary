"""
fundamental.py — Fetch data fundamental saham via yfinance.
"""

import yfinance as yf


def fetch_fundamental(ticker: str) -> dict | None:
    """
    Ambil data fundamental dasar untuk satu saham.
    Mengembalikan dict berisi harga, perubahan %, PER, PBV, volume.
    Return None jika gagal fetch (saham di-skip, bukan crash).
    """
    symbol = f"{ticker}.JK"

    try:
        stock = yf.Ticker(symbol)
        info = stock.info

        if not info or info.get("regularMarketPrice") is None:
            print(f"[WARN] Data tidak tersedia untuk {symbol}, skip.")
            return None

        # Hitung perubahan % harian
        current_price = info.get("regularMarketPrice", 0)
        previous_close = info.get("regularMarketPreviousClose", 0)

        if previous_close and previous_close > 0:
            change_pct = ((current_price - previous_close) / previous_close) * 100
        else:
            change_pct = 0.0

        result = {
            "ticker": ticker,
            "name": info.get("shortName") or ticker,
            "symbol": symbol,
            "sector": info.get("sector") or "Lainnya",
            "industry": info.get("industry") or "Lainnya",
            "price": current_price,
            "previous_close": previous_close,
            "change_pct": round(change_pct, 2),
            "per": info.get("trailingPE"),
            "pbv": info.get("priceToBook"),
            "volume": info.get("regularMarketVolume"),
            "market_cap": info.get("marketCap"),
            "currency": info.get("currency", "IDR"),
        }

        print(f"[INFO] Fundamental {ticker}: Rp {current_price:,.0f} ({change_pct:+.2f}%)")
        return result

    except Exception as e:
        print(f"[WARN] Gagal fetch fundamental untuk {symbol}: {e}")
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
