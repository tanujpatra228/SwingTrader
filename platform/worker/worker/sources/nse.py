"""NSE data: symbol master, sector map, and the full bhavcopy (with delivery).

VERIFIED 2026-07-17 (see phase-0-data-spine.md):
  - host is nsearchives.nseindia.com; a browser User-Agent is enough for archives.
  - EQUITY_L.csv: SYMBOL, NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE,
    MARKET LOT, ISIN
  - sec_bhavdata_full_DDMMYYYY.csv: SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE,
    HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY,
    TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, DELIV_PER   <- delivery present

Raw files are cached under DATA_CACHE and kept — re-parsing a saved file beats
re-downloading, and a parser bug can be tested against the original (structure.md).
"""

from __future__ import annotations

import io
from datetime import date

import pandas as pd
import requests

from worker.config import DATA_CACHE

ARCHIVE = "https://nsearchives.nseindia.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

# NIFTY 500 constituent list carries an "Industry" column — our sector source.
INDEX_CONSTITUENTS = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
# NIFTY 100 = large-cap (SEBI's top-100-by-mcap definition). Used to EXCLUDE large caps.
NIFTY100_LIST = "https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv"


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "text/csv,*/*"})
    try:                       # warm cookies; archives work even if this 403s
        s.get("https://www.nseindia.com", timeout=15)
    except requests.RequestException:
        pass
    return s


def _get(session: requests.Session, url: str, cache_name: str) -> bytes:
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    (DATA_CACHE / cache_name).write_bytes(resp.content)
    return resp.content


def fetch_symbol_master(session: requests.Session | None = None) -> pd.DataFrame:
    """All EQ symbols with name, ISIN, listing date. Sector merged separately."""
    s = session or _session()
    raw = _get(s, f"{ARCHIVE}/content/equities/EQUITY_L.csv", "EQUITY_L.csv")
    df = pd.read_csv(io.BytesIO(raw))
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={
        "SYMBOL": "symbol", "NAME OF COMPANY": "name", "SERIES": "series",
        "DATE OF LISTING": "listing_date", "ISIN NUMBER": "isin",
    })
    df["symbol"] = df["symbol"].str.strip()
    df["series"] = df["series"].str.strip()
    df = df[df["series"] == "EQ"].copy()      # EQ only (ADR / structure.md)
    return df[["symbol", "name", "series", "listing_date", "isin"]]


def fetch_sector_map(session: requests.Session | None = None) -> dict[str, str]:
    """symbol -> industry, from the NIFTY 500 list. Symbols outside the 500 get no
    sector and will be dropped by the junk filter's require_sector — acceptable for
    the MVP, since the tradable universe is large-cap anyway."""
    s = session or _session()
    try:
        raw = _get(s, INDEX_CONSTITUENTS, "ind_nifty500list.csv")
    except requests.RequestException:
        return {}
    df = pd.read_csv(io.BytesIO(raw))
    df.columns = [c.strip() for c in df.columns]
    if "Symbol" not in df.columns or "Industry" not in df.columns:
        return {}
    return dict(zip(df["Symbol"].str.strip(), df["Industry"].str.strip()))


def fetch_largecap_symbols(session: requests.Session | None = None) -> set[str]:
    """NIFTY 100 members = large-cap (SEBI top-100-by-mcap). Empty set on failure
    so the caller can decide whether to proceed without the exclusion."""
    s = session or _session()
    try:
        raw = _get(s, NIFTY100_LIST, "ind_nifty100list.csv")
    except requests.RequestException:
        return set()
    df = pd.read_csv(io.BytesIO(raw))
    df.columns = [c.strip() for c in df.columns]
    if "Symbol" not in df.columns:
        return set()
    return set(df["Symbol"].str.strip())


def fetch_bhavcopy(day: date, session: requests.Session | None = None) -> pd.DataFrame:
    """Full bhavcopy for one session: OHLC + volume + delivery, EQ series only.

    Returns normalised columns: symbol, date, o, h, l, c, v, turnover, trades,
    delivery_qty, delivery_pct. Raises on a non-trading day (NSE 404s those).
    """
    s = session or _session()
    name = f"sec_bhavdata_full_{day.strftime('%d%m%Y')}.csv"
    raw = _get(s, f"{ARCHIVE}/products/content/{name}", name)
    df = pd.read_csv(io.BytesIO(raw))
    df.columns = [c.strip() for c in df.columns]
    df = df[df["SERIES"].str.strip() == "EQ"].copy()
    df["symbol"] = df["SYMBOL"].str.strip()
    out = pd.DataFrame({
        "symbol": df["symbol"],
        "date": pd.to_datetime(df["DATE1"].str.strip(), format="%d-%b-%Y"),
        "o": pd.to_numeric(df["OPEN_PRICE"], errors="coerce"),
        "h": pd.to_numeric(df["HIGH_PRICE"], errors="coerce"),
        "l": pd.to_numeric(df["LOW_PRICE"], errors="coerce"),
        "c": pd.to_numeric(df["CLOSE_PRICE"], errors="coerce"),
        "v": pd.to_numeric(df["TTL_TRD_QNTY"], errors="coerce"),
        "turnover": pd.to_numeric(df["TURNOVER_LACS"], errors="coerce") * 1e5,
        "trades": pd.to_numeric(df["NO_OF_TRADES"], errors="coerce"),
        "delivery_qty": pd.to_numeric(df["DELIV_QTY"], errors="coerce"),
        "delivery_pct": pd.to_numeric(df["DELIV_PER"], errors="coerce"),
    })
    return out.dropna(subset=["o", "h", "l", "c"])
