"""Indicators from an adjusted OHLCV DataFrame. Pure — no I/O, no clock.

Input contract: a DataFrame indexed by date (ascending), columns o, h, l, c, v
(adjusted). Output: the same frame with indicator columns added. Names are the real
domain terms (ADR-6): ema20, rvol, adr_pct, vol_class.

EMA seeding note (phase-0-data-spine.md task 0.6): pandas ewm(adjust=False) seeds
from the first value, which differs from an SMA-seed for the first ~N bars but
converges. TradingView uses an SMA seed. Disagreement on OLD bars = seeding, harmless;
disagreement on RECENT bars = a real bug. Know which before trusting scans.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

EMA_LENGTHS = (10, 20, 50, 200)


def ema(series: pd.Series, length: int) -> pd.Series:
    """Exponential moving average, ewm(adjust=False) — the standard recursive EMA."""
    return series.ewm(span=length, adjust=False).mean()


def slope_pct_per_day(series: pd.Series, window: int = 5) -> pd.Series:
    """Slope of a line fit to the last `window` points, as % of the series value per day.
    Positive = rising. Used to answer 'are the average lines pointing up?' (step 1)."""
    def _fit(vals: np.ndarray) -> float:
        if len(vals) < window or np.isnan(vals).any():
            return np.nan
        x = np.arange(len(vals))
        m = np.polyfit(x, vals, 1)[0]
        base = vals[-1]
        return float(m / base * 100) if base else np.nan

    return series.rolling(window).apply(lambda w: _fit(w.to_numpy()), raw=False)


def average_daily_range_pct(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """ADR% — mean of (high-low)/close over `window` days, as a percent.
    A base that's 'tight' for a 6% ADR stock is not tight for a 1.5% ADR stock, so
    tightness thresholds scale by this later (platform-plan.md §4.1)."""
    daily = (df["h"] - df["l"]) / df["c"] * 100
    return daily.rolling(window).mean()


def volume_class(df: pd.DataFrame) -> pd.Series:
    """Per-bar volume character (ankur-patel-swing-trading-learnings.md §136-141):
        blue   up-day and volume > highest down-day volume of last 10 days (pocket pivot)
        red    down-day and volume > 50-day average (supply overhead)
        green  up-day and volume > 50-day average
        orange volume < 20% of average (dry-up)
        neutral otherwise
    """
    c, v = df["c"], df["v"]
    up = c > c.shift(1)
    down = c < c.shift(1)
    vol_sma50 = v.rolling(50).mean()

    # highest down-day volume over the trailing 10 sessions
    down_vol = v.where(down)
    max_down_vol_10 = down_vol.rolling(10, min_periods=1).max()

    out = pd.Series("neutral", index=df.index, dtype=object)
    out[(v < 0.2 * vol_sma50)] = "orange"
    out[up & (v > vol_sma50)] = "green"
    out[down & (v > vol_sma50)] = "red"
    out[up & (v > max_down_vol_10)] = "blue"   # pocket pivot wins over green
    return out


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Attach every MVP indicator. Expects ascending date index and o/h/l/c/v columns.

    Raises on missing columns rather than producing a frame with silent NaN gaps —
    a wrong indicator here becomes a wrong scan hit becomes a wrong trade.
    """
    required = {"o", "h", "l", "c", "v"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    if not df.index.is_monotonic_increasing:
        raise ValueError("index must be ascending by date")

    out = df.copy()
    for n in EMA_LENGTHS:
        out[f"ema{n}"] = ema(out["c"], n)
    out["ema20_slope"] = slope_pct_per_day(out["ema20"])
    out["ema50_slope"] = slope_pct_per_day(out["ema50"])
    out["ema200_slope"] = slope_pct_per_day(out["ema200"])  # Stage 2: long-term line rising
    out["vol_sma50"] = out["v"].rolling(50).mean()
    out["rvol"] = out["v"] / out["vol_sma50"]
    out["adr_pct"] = average_daily_range_pct(out)
    out["vol_class"] = volume_class(out)
    return out
