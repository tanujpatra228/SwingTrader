"""Scan + filter tests on constructed snapshots. No data download."""

import numpy as np
import pandas as pd
import pytest

from worker.compute.filters import FilterConfig, filter_junk
from worker.compute.scans import SCANS, is_tight_setup, run_all, run_scan, snapshot_features
from worker.compute.indicators import add_indicators


def _frame(closes, vols=None):
    n = len(closes)
    idx = pd.date_range("2025-01-01", periods=n, freq="D")
    df = pd.DataFrame(
        {"o": closes, "h": [c * 1.02 for c in closes], "l": [c * 0.98 for c in closes],
         "c": closes, "v": vols or [500_000] * n},
        index=idx,
    )
    out = add_indicators(df)
    out["delivery_pct"] = 55.0
    return out


def test_snapshot_features_has_ladder():
    f = _frame([100 + i * 0.5 for i in range(120)])
    s = snapshot_features(f)
    for k in ("close", "day_change_pct", "ema20", "low_5d", "low_30d", "low_11m", "delivery_pct"):
        assert k in s


def test_rc1_hits_quiet_stock_above_ema20():
    # long steady rise, tiny last-day move, above ema20
    f = _frame([100 + i * 0.5 for i in range(120)])
    s = snapshot_features(f)
    assert SCANS["rc1"].matches(s) is True


def test_rc1_rejects_illiquid():
    f = _frame([100 + i * 0.5 for i in range(120)], vols=[10_000] * 120)  # below floors
    s = snapshot_features(f)
    assert SCANS["rc1"].matches(s) is False


def test_rc1_rejects_big_move_day():
    closes = [100 + i * 0.5 for i in range(119)] + [200]   # +26% last day
    f = _frame(closes)
    s = snapshot_features(f)
    assert SCANS["rc1"].matches(s) is False


def test_run_all_unions_and_counts_overlap():
    rows = []
    for sym, closes in {
        "AAA": [100 + i * 0.5 for i in range(120)],   # should hit rc1/rc2/pullback-ish
        "BBB": [50 - i * 0.1 for i in range(120)],     # falling, low price -> likely no hit
    }.items():
        s = snapshot_features(_frame(closes))
        s["symbol"] = sym
        rows.append(s)
    snap = pd.DataFrame(rows)
    hits = run_all(snap)
    assert "scan_count" in hits.columns
    assert (hits["scan_count"] >= 1).all()


def test_filter_drops_with_reasons():
    snap = pd.DataFrame([
        {"symbol": "GOOD", "close": 500, "volume": 500_000, "mcap_cr": 5000, "sector": "IT"},
        {"symbol": "CHEAP", "close": 50, "volume": 500_000, "mcap_cr": 5000, "sector": "IT"},
        {"symbol": "THIN", "close": 500, "volume": 10_000, "mcap_cr": 5000, "sector": "IT"},
        {"symbol": "SMALL", "close": 500, "volume": 500_000, "mcap_cr": 200, "sector": "IT"},
        {"symbol": "NOSEC", "close": 500, "volume": 500_000, "mcap_cr": 5000, "sector": None},
    ])
    res = filter_junk(snap)
    assert set(res.kept["symbol"]) == {"GOOD"}
    assert res.summary == {"too cheap": 1, "barely traded": 1, "too small": 1, "unknown company": 1}


def test_snapshot_has_tightness_signals():
    f = _frame([100 + i * 0.5 for i in range(120)])
    s = snapshot_features(f)
    for k in ("wk_tight_pct", "dist_52wh_pct", "vol_dry", "tightness", "rng_10d_pct"):
        assert k in s


def test_tight_setup_gate_rejects_wide_and_falling():
    # a steady riser but NOT tight (big swings) and below EMAs should fail the gate
    base = {"close": 100, "ema20": 105, "ema50": 110, "volume": 500_000, "vol_sma50": 400_000,
            "delivery_pct": 50, "turnover": 5e7, "low_90d": 90, "wk_tight_pct": 8.0,
            "dist_52wh_pct": -30, "vol_dry": 1.5}
    assert is_tight_setup(base) is False


def test_tight_setup_gate_accepts_clean_base():
    good = {"close": 130, "ema20": 125, "ema50": 118, "volume": 500_000, "vol_sma50": 400_000,
            "delivery_pct": 55, "turnover": 6e7, "low_90d": 100, "wk_tight_pct": 1.2,
            "dist_52wh_pct": -3, "vol_dry": 0.6}
    assert is_tight_setup(good) is True


def test_filter_keeps_row_with_missing_mcap():
    snap = pd.DataFrame([
        {"symbol": "NEW", "close": 500, "volume": 500_000, "mcap_cr": None, "sector": "IT"},
    ])
    res = filter_junk(snap)
    assert set(res.kept["symbol"]) == {"NEW"}     # absent mcap must not silently drop
