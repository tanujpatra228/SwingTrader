"""On-demand symbol lookup for a pasted Chartink list (Weekly Prep import).

Enriches raw symbols with name, price, and whether the symbol's industry is
currently trending — computed from the SAME screening universe the evening
routine judges "the market" by (build_universe: liquid mid/small caps, junk
already excluded), not from the pasted batch itself. A pasted list might only
have 1-2 stocks from a sector; the full universe gives a stable sample.
"""

from __future__ import annotations

import pandas as pd

from worker.compute.indicators import add_indicators
from worker.jobs.screen import build_universe
from worker.repo import load_all_recent, symbol_meta

MIN_SECTOR_SAMPLE = 3   # below this, "industry trending" isn't a meaningful stat


def _sector_trend(universe: pd.DataFrame) -> dict[str, dict]:
    """sector -> {pct_above_50, trending, n} from the full screening universe."""
    if universe.empty or "sector" not in universe:
        return {}
    out = {}
    for sector, g in universe.groupby("sector"):
        if not sector:
            continue
        pct = round(float((g["close"] > g["ema50"]).mean() * 100), 1)
        out[sector] = {"pct_above_50": pct, "n": len(g),
                       "trending": pct >= 50.0 if len(g) >= MIN_SECTOR_SAMPLE else None}
    return out


def lookup_symbols(raw: list[str]) -> dict:
    symbols = sorted({s.strip().upper() for s in raw if s.strip()})
    if not symbols:
        return {"requested": 0, "found": 0, "rows": [], "not_found": []}

    universe, _frames, _excl_large, _excl_price = build_universe()
    sector_trend = _sector_trend(universe)
    by_symbol = {r["symbol"]: r for _, r in universe.iterrows()} if not universe.empty else {}

    meta = symbol_meta()
    # symbols the screening universe already excluded (large-cap, illiquid, too
    # cheap, missing history) still get looked up directly — a pasted Chartink
    # list may legitimately include them.
    missing = [s for s in symbols if s not in by_symbol and s in meta]
    extra_frames = load_all_recent(limit=260, symbols=missing) if missing else {}

    rows, not_found = [], []
    for sym in symbols:
        if sym not in meta:
            not_found.append(sym)
            continue
        m = meta[sym]
        sector = m.get("sector")
        trend = sector_trend.get(sector)

        if sym in by_symbol:
            r = by_symbol[sym]
            close = round(float(r["close"]), 2)
            above_ema50 = bool(r["close"] > r["ema50"])
        else:
            df = extra_frames.get(sym)
            if df is None or df.empty:
                not_found.append(sym)
                continue
            close = round(float(df["c"].iloc[-1]), 2)
            above_ema50 = None
            if len(df) >= 60:
                ind = add_indicators(df)
                last = ind.iloc[-1]
                if pd.notna(last.get("ema50")):
                    above_ema50 = bool(last["c"] > last["ema50"])

        rows.append({
            "symbol": sym,
            "name": m.get("name"),
            "sector": sector,
            "close": close,
            "above_ema50": above_ema50,
            "industry_trending": trend["trending"] if trend else None,
            "industry_pct_above_50": trend["pct_above_50"] if trend else None,
            "tier": m.get("tier"),
        })

    return {"requested": len(symbols), "found": len(rows), "not_found": not_found, "rows": rows}
