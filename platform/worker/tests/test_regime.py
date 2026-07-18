"""Market-check tests on constructed series. No network — the live fetch is a
separate manual check; this locks the verdict logic against known shapes."""

import numpy as np
import pandas as pd
import pytest

from worker.compute.indicators import add_indicators
from worker.compute.regime import assess_market


def _nifty(closes):
    n = len(closes)
    idx = pd.date_range("2026-01-01", periods=n, freq="D")
    df = pd.DataFrame(
        {"o": closes, "h": [c * 1.005 for c in closes],
         "l": [c * 0.995 for c in closes], "c": closes, "v": [1e6] * n},
        index=idx,
    )
    return add_indicators(df)


def test_clean_uptrend_is_good():
    df = _nifty([20000 + i * 20 for i in range(120)])   # steady rise
    v = assess_market(df)
    assert v.verdict == "good"
    assert v.max_exposure_pct == 100
    assert v.max_risk_pct == 1.0


def test_downtrend_is_bad():
    df = _nifty([25000 - i * 20 for i in range(120)])   # steady fall
    v = assess_market(df)
    assert v.verdict == "bad"
    assert v.max_exposure_pct == 0
    assert v.max_positions == 0


def test_recent_shock_downgrades_to_shaky():
    # long rise, then a sharp drop in the last few sessions that stays above EMAs
    closes = [20000 + i * 30 for i in range(110)]
    closes += [closes[-1] * 0.97, closes[-1] * 0.965, closes[-1] * 0.96]
    df = _nifty(closes)
    v = assess_market(df)
    assert v.verdict in {"shaky", "bad"}      # not "good" despite the long uptrend
    assert any("recent high" in r for r in v.reasons)


def test_low_breadth_forces_bad():
    df = _nifty([20000 + i * 20 for i in range(120)])   # price/EMAs say good
    v = assess_market(df, breadth_pct_above_20=20)       # but breadth is weak
    assert v.verdict == "bad"


def test_needs_enough_history():
    df = _nifty([20000 + i for i in range(30)])
    with pytest.raises(ValueError, match="need >= 50"):
        assess_market(df)
