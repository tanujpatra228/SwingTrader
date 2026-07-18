"""Indicator tests against hand-computed answers. No DB, no network."""

import numpy as np
import pandas as pd
import pytest

from worker.compute.indicators import add_indicators, ema, volume_class


def _df(closes, highs=None, lows=None, vols=None):
    n = len(closes)
    idx = pd.date_range("2026-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {
            "o": closes,
            "h": highs if highs is not None else [c * 1.01 for c in closes],
            "l": lows if lows is not None else [c * 0.99 for c in closes],
            "c": closes,
            "v": vols if vols is not None else [100_000] * n,
        },
        index=idx,
    )


def test_ema_matches_manual_recursion():
    # ewm(adjust=False): e_t = a*x_t + (1-a)*e_{t-1}, seed = x_0
    x = pd.Series([10.0, 11, 12, 13, 14, 15])
    length = 3
    a = 2 / (length + 1)
    manual = [x.iloc[0]]
    for v in x.iloc[1:]:
        manual.append(a * v + (1 - a) * manual[-1])
    got = ema(x, length)
    assert got.to_numpy() == pytest.approx(np.array(manual), abs=1e-9)


def test_add_indicators_columns_present():
    df = _df([100 + i for i in range(60)])
    out = add_indicators(df)
    for col in ("ema10", "ema20", "ema50", "ema200",
                "ema20_slope", "ema50_slope", "vol_sma50", "rvol", "adr_pct", "vol_class"):
        assert col in out.columns


def test_rising_series_has_positive_slope():
    df = _df([100 + i for i in range(60)])
    out = add_indicators(df)
    assert out["ema20_slope"].iloc[-1] > 0


def test_add_indicators_rejects_missing_columns():
    df = pd.DataFrame({"c": [1, 2, 3]}, index=pd.date_range("2026-01-01", periods=3))
    with pytest.raises(ValueError, match="missing columns"):
        add_indicators(df)


def test_add_indicators_rejects_descending_index():
    df = _df([100, 101, 102]).iloc[::-1]
    with pytest.raises(ValueError, match="ascending"):
        add_indicators(df)


def test_volume_class_blue_on_pocket_pivot():
    # flat then an up-day whose volume tops any recent down-day volume -> blue
    closes = [100, 99, 101, 98, 102, 97, 103, 96, 104, 95, 110]
    vols =   [100, 200, 100, 300, 100, 400, 100, 500, 100, 600, 5000]
    df = _df(closes, vols=vols)
    vc = volume_class(df)
    assert vc.iloc[-1] == "blue"


def test_volume_class_orange_on_dryup():
    closes = [100] * 60
    vols = [100_000] * 59 + [1_000]     # last bar < 20% of average
    df = _df(closes, vols=vols)
    vc = volume_class(df)
    assert vc.iloc[-1] == "orange"
