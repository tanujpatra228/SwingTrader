"""Yahoo/yfinance: history backfill and the reconciliation audit source (ADR-4).

yfinance is split-adjusted by Yahoo, so it seeds history and independently checks
our own numbers — it is NOT the daily source of truth. Version pinned in
pyproject.toml; an unpinned bump can change column names silently.
"""

from __future__ import annotations

import pandas as pd
import yfinance as yf


def fetch_history(symbols: list[str], period: str = "5y") -> dict[str, pd.DataFrame]:
    """Daily adjusted OHLCV per symbol. Keys are bare NSE symbols; the .NS suffix
    lives only here. Symbols with no Yahoo match are omitted, not errored."""
    tickers = [f"{s}.NS" for s in symbols]
    raw = yf.download(tickers, period=period, interval="1d", auto_adjust=True,
                      group_by="ticker", progress=False, threads=True)
    out: dict[str, pd.DataFrame] = {}
    for s in symbols:
        try:
            d = raw[f"{s}.NS"].dropna()
        except (KeyError, TypeError):
            continue
        if d.empty:
            continue
        d = d.rename(columns={"Open": "o", "High": "h", "Low": "l",
                              "Close": "c", "Volume": "v"})
        cols = [c for c in ["o", "h", "l", "c", "v"] if c in d.columns]
        d = d[cols].copy()
        if len(d) >= 60:
            out[s] = d
    return out


def fetch_index(symbol: str = "^NSEI", period: str = "2y") -> pd.DataFrame:
    """NIFTY (or any index) daily. Used by the market check before the universe is
    even ingested — step 1 needs one symbol, not 2,000."""
    raw = yf.download(symbol, period=period, interval="1d", auto_adjust=True,
                      progress=False)
    raw.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in raw.columns]
    df = raw.rename(columns={"open": "o", "high": "h", "low": "l",
                             "close": "c", "volume": "v"})
    return df[["o", "h", "l", "c", "v"]].dropna()
