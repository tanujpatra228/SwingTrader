"""Trade-math tests against hand-computed answers. No DB, no network."""

import pandas as pd
import pytest

from worker.compute.trade_math import (
    ChargeConfig,
    compute_levels,
    position_size,
    trade_forecast,
    zerodha_delivery_charges,
)


def _series(vals):
    return pd.Series(vals, dtype=float)


# ── levels ──────────────────────────────────────────────────────────────────

def test_levels_basic_arithmetic():
    # window high 520, low 490 over last 10
    highs = _series([500, 505, 510, 515, 520, 512, 508, 514, 511, 509])
    lows = _series([490, 495, 498, 500, 502, 496, 493, 499, 497, 495])
    lv = compute_levels(highs, lows, lookback=10,
                        entry_buffer_pct=0.5, stop_buffer_pct=1.0, reward_multiple=2.0)
    assert lv.pivot == 520.0
    assert lv.base_low == 490.0
    assert lv.entry == round(520 * 1.005, 2)      # 522.60
    assert lv.stop == round(490 * 0.99, 2)        # 485.10
    assert lv.risk_per_share == round(lv.entry - lv.stop, 2)
    assert lv.target == round(lv.entry + 2 * lv.risk_per_share, 2)
    assert lv.is_estimate is True                 # proxy, not a detected base


def test_levels_reward_is_two_r():
    highs = _series([100] * 9 + [110])
    lows = _series([90] * 10)
    lv = compute_levels(highs, lows, lookback=10)
    assert lv.reward_per_share == pytest.approx(2 * lv.risk_per_share, abs=0.01)


def test_levels_rejects_short_history():
    with pytest.raises(ValueError, match="need >="):
        compute_levels(_series([1, 2, 3]), _series([1, 2, 3]), lookback=10)


def test_levels_rejects_degenerate_window():
    # flat prices -> base_low == pivot after buffers can invert; caught explicitly
    with pytest.raises(ValueError):
        compute_levels(_series([100] * 10), _series([100] * 10), lookback=10)


# ── position size ───────────────────────────────────────────────────────────

def test_position_size_floors_and_caps_risk():
    highs = _series([100] * 9 + [110])   # pivot 110
    lows = _series([100] * 10)           # base_low 100
    lv = compute_levels(highs, lows, lookback=10)
    # entry 110.55, stop 99.0, risk/share 11.55
    pos = position_size(lv, account=100_000, risk_pct=1.0)   # max risk 1000
    assert pos.qty == int(1000 // lv.risk_per_share)          # floored
    assert pos.risk_amount <= 1000                            # never over the cap
    assert pos.risk_pct_actual <= 1.0


def test_position_size_rejects_bad_account():
    lv = compute_levels(_series([100] * 9 + [110]), _series([100] * 10), lookback=10)
    with pytest.raises(ValueError):
        position_size(lv, account=0)


# ── charges ─────────────────────────────────────────────────────────────────

def test_charges_zero_brokerage_and_components():
    cfg = ChargeConfig()
    # ₹37,500 buy, sell same for a clean component check
    ch = zerodha_delivery_charges(37_500, 37_500, cfg)
    b = ch.breakdown
    assert b["brokerage"] == 0.0                              # Zerodha delivery = free
    assert b["stt"] == pytest.approx(0.001 * 75_000, abs=0.01)   # 0.1% of turnover
    assert b["stamp"] == pytest.approx(0.00015 * 37_500, abs=0.01)  # buy side only
    assert b["dp"] == cfg.dp_charge_flat
    # gst on (brokerage + exch + sebi), not on stt/stamp
    exp_gst = 0.18 * (b["brokerage"] + b["exchange_txn"] + b["sebi"])
    assert b["gst"] == pytest.approx(exp_gst, abs=0.01)
    assert ch.total == pytest.approx(sum(b.values()), abs=0.02)


def test_charges_breakeven_shrinks_with_size():
    cfg = ChargeConfig()
    small = zerodha_delivery_charges(5_000, 5_000, cfg)
    big = zerodha_delivery_charges(100_000, 100_000, cfg)
    # flat DP fee dominates small positions -> higher breakeven %
    assert small.breakeven_move_pct > big.breakeven_move_pct
    assert big.breakeven_move_pct < 0.3     # large trades ~0.24%


# ── full forecast ───────────────────────────────────────────────────────────

def test_trade_forecast_shape():
    highs = _series([500, 505, 510, 515, 520, 512, 508, 514, 511, 509])
    lows = _series([490, 495, 498, 500, 502, 496, 493, 499, 497, 495])
    f = trade_forecast(highs, lows, account=500_000, risk_pct=1.0)
    assert f["tradeable"] is True
    assert f["levels"]["is_estimate"] is True
    assert f["position"]["qty"] > 0
    assert f["charges"]["total"] > 0
    assert "min_amount_ok" in f
    assert f["forecast_profit_pre_tax"] > 0
    assert f["forecast_loss_if_stopped"] > 0


def test_trade_forecast_untradeable_when_risk_too_big():
    # tiny account, wide risk -> no whole share fits
    highs = _series([1000] * 9 + [2000])
    lows = _series([1000] * 10)
    f = trade_forecast(highs, lows, account=1_000, risk_pct=1.0)
    assert f["tradeable"] is False
    assert f["charges"] is None
