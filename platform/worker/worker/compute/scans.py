"""Step 2 — the scanners. Ankur's Chartink clauses reimplemented on our own data.

Pure. Two layers:
  snapshot_features(frame)  -> one row of scan inputs from a symbol's indicator frame
  SCANS[name].matches(row)  -> does this symbol pass this scan today?

Clauses transcribed from ankur-patel-swing-trading-learnings.md §67-116. The
`buyer/seller initiated trades >= 200` clause has no free-data equivalent (ADR-5),
so it's substituted by delivery_pct + turnover + volume. Our hits will not exactly
match Chartink; that's known and accepted for the MVP (mvp.md).

Each scan carries a `role` (ADR-10). MVP ships only `watchlist`-role scans — the
momentum / volume-spike scans are watchlist *inputs*, never tradable directly, and
are excluded here entirely.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd


def snapshot_features(frame: pd.DataFrame) -> dict:
    """Collapse a symbol's full indicator history to the fields the scans read.

    `frame` must be ascending, indicator-bearing (add_indicators applied), with a
    `delivery_pct` column (may be NaN when bhavcopy lacked it). Returns the latest
    session's scan inputs, including the recent-low ladder Ankur reuses across scans.
    """
    if len(frame) < 50:
        raise ValueError(f"need >= 50 sessions, got {len(frame)}")

    last = frame.iloc[-1]
    close = float(last["c"])
    prev_close = float(frame["c"].iloc[-2])

    def low_over(n: int) -> float:
        return float(frame["l"].iloc[-n:].min()) if len(frame) >= n else float(frame["l"].min())

    # tightness / contraction — the thing that separates a base from noise.
    # rng_10d = high-low over the last 10 sessions as % of price; normalise by ADR so
    # a "tight" 6%-ADR stock isn't judged the same as a tight 1.5%-ADR stock.
    hi10, lo10 = float(frame["h"].iloc[-10:].max()), float(frame["l"].iloc[-10:].min())
    rng_10d_pct = (hi10 - lo10) / close * 100 if close else 999.0
    adr = float(last["adr_pct"]) if pd.notna(last.get("adr_pct")) else None
    tightness = (rng_10d_pct / adr) if adr else None

    # 3-week tight close: last 3 weekly closes within a tight band (Ankur's 3WTC).
    wk = frame["c"].resample("W").last().dropna()
    if len(wk) >= 3:
        w3 = wk.iloc[-3:]
        wk_tight_pct = (float(w3.max()) / float(w3.min()) - 1) * 100
    else:
        wk_tight_pct = 999.0

    # distance from the 1-year high (near highs = genuine strength, Ankur's 52wh zone)
    hi_52w = float(frame["c"].iloc[-250:].max())
    dist_52wh_pct = (close / hi_52w - 1) * 100 if hi_52w else -999.0

    # volume dry-up: last-5-day avg volume vs 50-day avg — under 1 means sellers quiet
    v = frame["v"]
    vol_dry = float(v.iloc[-5:].mean()) / float(v.iloc[-50:].mean()) if float(v.iloc[-50:].mean()) else 999.0

    return {
        "close": close,
        "day_change_pct": (close / prev_close - 1) * 100 if prev_close else 0.0,
        "ema20": float(last["ema20"]),
        "ema50": float(last["ema50"]),
        "ema200": float(last["ema200"]) if pd.notna(last.get("ema200")) else None,
        "ema200_slope": float(last["ema200_slope"]) if pd.notna(last.get("ema200_slope")) else None,
        "volume": float(last["v"]),
        "vol_sma50": float(last["vol_sma50"]) if pd.notna(last["vol_sma50"]) else 0.0,
        "delivery_pct": float(last["delivery_pct"]) if "delivery_pct" in frame and pd.notna(last.get("delivery_pct")) else None,
        "turnover": close * float(last["v"]),
        "adr_pct": adr,
        "rng_10d_pct": round(rng_10d_pct, 2),
        "tightness": round(tightness, 2) if tightness is not None else None,
        "wk_tight_pct": round(wk_tight_pct, 2),
        "dist_52wh_pct": round(dist_52wh_pct, 2),
        "vol_dry": round(vol_dry, 2),
        "low_5d": low_over(5),
        "low_10d": low_over(10),
        "low_30d": low_over(30),
        "low_90d": low_over(90),
        "low_6m": low_over(126),
        "low_11m": low_over(231),
    }


def _liquid(r: dict) -> bool:
    """Shared liquidity floor, and the delivery/turnover substitute for the
    buyer/seller-initiated-trades clause we can't get free (ADR-5)."""
    if r["close"] <= 30 or r["volume"] < 50_000 or r["vol_sma50"] < 25_000:
        return False
    # substitute: require real delivery when we have it; otherwise fall back to turnover
    if r["delivery_pct"] is not None:
        return r["delivery_pct"] >= 30
    return r["turnover"] >= 1_000_000   # ₹10L turnover floor when delivery is unknown


def _momentum_ladder(r: dict) -> bool:
    """His reused 'rose recently' test: close above a rising ladder of recent lows
    (1.1x 5-day low ... 1.9x 11-month low)."""
    c = r["close"]
    return (
        c >= r["low_5d"] * 1.1 or c >= r["low_10d"] * 1.2 or c >= r["low_30d"] * 1.2
        or c >= r["low_90d"] * 1.3 or c >= r["low_6m"] * 1.8 or c >= r["low_11m"] * 1.9
    )


@dataclass(frozen=True)
class Scan:
    key: str
    label: str          # plain-language name for the UI
    role: str           # "watchlist" — MVP ships only these
    source: str | None  # chartink slug for the cross-check, or None if we have no source
    matches: Callable[[dict], bool]


def _rc1(r: dict) -> bool:
    # close > ema20 AND day-change within +/-4.5 AND liquid
    return _liquid(r) and r["close"] > r["ema20"] and -4.5 <= r["day_change_pct"] <= 4.5


def _rc2(r: dict) -> bool:
    # day-change within +/-4.5 AND momentum ladder AND liquid
    return _liquid(r) and -4.5 <= r["day_change_pct"] <= 4.5 and _momentum_ladder(r)


def _ema20_pullback(r: dict) -> bool:
    # close within +/-5% of ema20 AND momentum ladder AND volume>100k AND liquid
    near_ema = r["ema20"] * 0.95 <= r["close"] <= r["ema20"] * 1.05
    return _liquid(r) and near_ema and r["volume"] > 100_000 and _momentum_ladder(r)


def _stage2(r: dict) -> bool:
    """Minervini's Stage 2 trend template (adapted to our EMAs): a confirmed uptrend.
    Weekend prep scan — established leaders to build a watchlist from, not entries.

      close > 50-line > 200-line   (uptrend stack)
      200-line rising             (long-term trend up)
      >= 30% above the 1-year low  (real advance, not just off the floor)
      within 25% of the 1-year high (near highs = leadership)
    """
    e200 = r.get("ema200")
    slope = r.get("ema200_slope")
    if e200 is None or slope is None:
        return False
    return (
        _liquid(r)
        and r["close"] > r["ema50"] > e200
        and slope > 0
        and r["close"] >= r["low_11m"] * 1.30
        and r.get("dist_52wh_pct", -999) >= -25.0
    )


def _three_week_tight_close(r: dict) -> bool:
    # Ankur's 3WTC — his most selective scan, the one the guide says to start with.
    # Last 3 weekly closes within ~3%, up 30% from the 3-month low, liquid.
    return (
        _liquid(r)
        and r.get("wk_tight_pct", 999) <= 3.01
        and r["close"] >= r["low_90d"] * 1.3
    )


# Daily scans — these feed the evening screen (run_all iterates exactly these).
SCANS: dict[str, Scan] = {
    "three_week_tight": Scan("three_week_tight", "Resting tight for 3 weeks", "watchlist",
                             "3-week-tight-close-19", _three_week_tight_close),
    "rc1": Scan("rc1", "Quietly contracting (RC1)", "watchlist", "ema-scan-2-7", _rc1),
    "rc2": Scan("rc2", "Quietly contracting (RC2)", "watchlist", "new-daily-2045", _rc2),
    "ema20_pullback": Scan("ema20_pullback", "Pulled back to its trend line", "watchlist",
                           "ankur-patel-s-20-ema-scan", _ema20_pullback),
}

# Weekend prep scans — run on demand, NOT part of the daily chain.
WEEKEND_SCANS: dict[str, Scan] = {
    "stage2": Scan("stage2", "Established uptrend (Stage 2)", "watchlist", None, _stage2),
}

ALL_SCANS: dict[str, Scan] = {**SCANS, **WEEKEND_SCANS}

# Tightness gate — the contraction that turns a broad scan list into a reviewable
# shortlist. This is the numeric stand-in for step-4 chart reading (base quality),
# and it's what makes the output land at the guide's 5-12, not 200+.
#
# Ankur's daily RC scans are deliberately broad (they fire 100-200/day on Chartink,
# per backtest/REPORT.md) — they narrow the universe, they don't select. The SELECTION
# is a genuine tight setup: 3 weekly closes within ~2%, near the 1-year high, volume
# drying up, above both EMAs. On 500 large-caps in a strong market this yields ~12;
# in a weak market, fewer. Thresholds were tuned against the live universe, not picked
# to hit a number — see the sweep in the commit that introduced this.
#
# When the real base engine (step 4) lands, it replaces this with detected boundaries.
WK_TIGHT_MAX_PCT = 2.0       # last 3 weekly closes within this band
NEAR_52WH_MIN_PCT = -15.0    # within 15% of the 1-year high
VOL_DRY_MAX = 1.0            # recent volume at/below its average (sellers quiet)


def is_tight_setup(r: dict) -> bool:
    """A genuine, reviewable tight setup — the shortlist a person would chart-read.
    Faithful to Ankur's tight-range-near-highs-with-dry-volume base."""
    return (
        _liquid(r)
        and r.get("wk_tight_pct", 999) <= WK_TIGHT_MAX_PCT
        and r["close"] >= r["low_90d"] * 1.3                 # rose into the base (3WTC leg)
        and r.get("dist_52wh_pct", -999) >= NEAR_52WH_MIN_PCT
        and r.get("vol_dry", 999) <= VOL_DRY_MAX
        and r["close"] > r["ema20"]
        and r["close"] > r["ema50"]                          # uptrend, above both lines
    )


def run_scan(snapshot: pd.DataFrame, scan_key: str) -> pd.DataFrame:
    """Apply one scan to a universe snapshot (one row per symbol, snapshot_features
    fields as columns, `symbol` column present). Returns the passing subset,
    annotated with which scan matched."""
    if scan_key not in ALL_SCANS:
        raise ValueError(f"unknown scan {scan_key!r}; have {list(ALL_SCANS)}")
    scan = ALL_SCANS[scan_key]
    mask = snapshot.apply(lambda row: scan.matches(row.to_dict()), axis=1)
    hit = snapshot[mask].copy()
    hit["scan"] = scan_key
    return hit


def run_all(snapshot: pd.DataFrame) -> pd.DataFrame:
    """Every MVP scan, unioned. A symbol hit by several scans appears once with the
    matching scans collected — that overlap is itself signal."""
    frames = [run_scan(snapshot, k) for k in SCANS]
    allhits = pd.concat(frames) if frames else snapshot.iloc[0:0]
    if allhits.empty:
        return allhits
    grouped = (
        allhits.groupby("symbol")
        .agg(scans=("scan", lambda s: sorted(set(s))))
        .reset_index()
    )
    base = snapshot.merge(grouped, on="symbol", how="inner")
    base["scan_count"] = base["scans"].apply(len)
    return base.sort_values("scan_count", ascending=False)
