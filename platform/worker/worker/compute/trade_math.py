"""Trade numbers: entry, stop, target, position size, and Zerodha delivery charges.

Pure. No I/O. This is the MVP headline — the numbers the user asked to see.

Two honesty boundaries, stated in code because they matter:

1. The resting zone (pivot / base low) is a PROXY here — highest-high / lowest-low
   over a lookback window — NOT a detected base. Real base detection is step 4,
   deferred. Every result carries `is_estimate=True` so the UI can say so. See
   ../../docs/mvp.md "The one honest compromise".

2. Charges are EXACT arithmetic on published Zerodha delivery rates, but the rates
   themselves drift over time. They live in ChargeConfig with a `rates_checked`
   date and must come from settings, never be hardcoded at a call site.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict

import pandas as pd


# ── levels ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Levels:
    """Entry/stop/target for one stock. Money in rupees (float) — this is a forecast,
    not a stored trade record, so paise-integers (structure.md) don't apply yet."""
    pivot: float          # top of the (proxy) resting zone
    base_low: float       # bottom of the (proxy) resting zone
    entry: float          # buy trigger — just above the pivot
    stop: float           # exit-if-wrong — just below the base low
    target: float         # take-profit — entry + reward_multiple * risk
    risk_per_share: float
    reward_per_share: float
    lookback: int
    is_estimate: bool     # True while pivot/base_low come from the proxy, not a base engine


def compute_levels(
    highs: pd.Series,
    lows: pd.Series,
    *,
    lookback: int = 10,
    entry_buffer_pct: float = 0.5,
    stop_buffer_pct: float = 1.0,
    reward_multiple: float = 2.0,
) -> Levels:
    """Entry/stop/target from the last `lookback` sessions.

    Ankur's rules (ankur-patel-swing-trading-learnings.md, step-6-plan-your-exit.md):
      entry  = pivot + buffer            "buy above the range"
      stop   = base_low - 0.5..1% buffer "below the pivot low, buffer against wick-outs"
      target = entry + 2 * risk          "1:2 minimum reward"

    pivot / base_low are the PROXY (window high / low), so is_estimate is True.
    Swap for detected-base boundaries later and the flag flips off.

    Raises ValueError on insufficient or degenerate data — a caller must not get a
    plausible-looking number from garbage input (the whole failure mode of this domain).
    """
    if len(highs) < lookback or len(lows) < lookback:
        raise ValueError(f"need >= {lookback} sessions, got {len(highs)}")

    pivot = float(highs.iloc[-lookback:].max())
    base_low = float(lows.iloc[-lookback:].min())

    if not (pivot > 0 and base_low > 0):
        raise ValueError(f"non-positive prices: pivot={pivot}, base_low={base_low}")
    if base_low >= pivot:
        raise ValueError(f"base_low {base_low} >= pivot {pivot} — degenerate window")

    entry = pivot * (1 + entry_buffer_pct / 100)
    stop = base_low * (1 - stop_buffer_pct / 100)
    risk_per_share = entry - stop

    if risk_per_share <= 0:
        raise ValueError(f"non-positive risk: entry={entry}, stop={stop}")

    reward_per_share = reward_multiple * risk_per_share
    target = entry + reward_per_share

    return Levels(
        pivot=round(pivot, 2),
        base_low=round(base_low, 2),
        entry=round(entry, 2),
        stop=round(stop, 2),
        target=round(target, 2),
        risk_per_share=round(risk_per_share, 2),
        reward_per_share=round(reward_per_share, 2),
        lookback=lookback,
        is_estimate=True,
    )


# ── position size ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Position:
    qty: int
    capital: float          # qty * entry
    risk_amount: float      # qty * risk_per_share — the real "how much can I lose"
    account_pct: float      # capital as % of account
    risk_pct_actual: float  # risk_amount as % of account (<= requested cap)


def position_size(
    levels: Levels,
    *,
    account: float,
    risk_pct: float = 1.0,
) -> Position:
    """Shares to buy so a stop-out loses at most `risk_pct` of the account
    (step-6 "position size" / Mistake 5-7). Floors to a whole share, so actual
    risk is <= requested — never over.
    """
    if account <= 0:
        raise ValueError(f"account must be positive, got {account}")
    max_risk = account * risk_pct / 100
    qty = int(max_risk // levels.risk_per_share)   # floor — never exceed the cap
    capital = qty * levels.entry
    risk_amount = qty * levels.risk_per_share
    return Position(
        qty=qty,
        capital=round(capital, 2),
        risk_amount=round(risk_amount, 2),
        account_pct=round(capital / account * 100, 2) if account else 0.0,
        risk_pct_actual=round(risk_amount / account * 100, 2) if account else 0.0,
    )


# ── charges (Zerodha, delivery / CNC) ─────────────────────────────────────────

@dataclass(frozen=True)
class ChargeConfig:
    """Zerodha delivery-equity rates. VERIFY against the live Zerodha charges page
    before trusting rupee figures; these drift. `rates_checked` is the audit stamp.
    Belongs in settings.broker_charges — a default lives here only so tests and the
    MVP have something to run against.
    """
    brokerage_pct: float = 0.0          # Zerodha: free on delivery
    brokerage_flat: float = 0.0
    stt_pct: float = 0.1                # each side, on turnover
    exchange_txn_pct: float = 0.00297   # NSE
    sebi_per_cr: float = 10.0           # ₹10 per crore
    stamp_buy_pct: float = 0.015        # buy side only
    gst_pct: float = 18.0               # on brokerage + txn + sebi
    dp_charge_flat: float = 18.0        # per scrip on sell (incl GST), approx
    rates_checked: str = "2026-07-17"   # NOT verified against live page — see note above


@dataclass(frozen=True)
class Charges:
    total: float
    pct_of_buy: float          # total charges as % of buy value
    breakeven_move_pct: float  # how far price must rise just to cover charges
    breakdown: dict[str, float]


def zerodha_delivery_charges(buy_value: float, sell_value: float, cfg: ChargeConfig) -> Charges:
    """Round-trip charges for a delivery trade. buy_value / sell_value in rupees.

    breakeven_move_pct = charges / buy_value — the move needed to net zero, which is
    what makes the "minimum sensible amount" verdict real rather than a rule of thumb
    (corrects the ~6% claim in swing-trading-tax-india-2026.md).
    """
    if buy_value < 0 or sell_value < 0:
        raise ValueError("values must be non-negative")

    turnover = buy_value + sell_value
    brokerage = cfg.brokerage_flat * 2 + (cfg.brokerage_pct / 100) * turnover
    stt = (cfg.stt_pct / 100) * turnover
    exch = (cfg.exchange_txn_pct / 100) * turnover
    sebi = (cfg.sebi_per_cr / 1e7) * turnover
    stamp = (cfg.stamp_buy_pct / 100) * buy_value
    gst = (cfg.gst_pct / 100) * (brokerage + exch + sebi)
    dp = cfg.dp_charge_flat  # once, on sell

    total = brokerage + stt + exch + sebi + stamp + gst + dp
    breakdown = {
        "brokerage": round(brokerage, 2),
        "stt": round(stt, 2),
        "exchange_txn": round(exch, 2),
        "sebi": round(sebi, 2),
        "stamp": round(stamp, 2),
        "gst": round(gst, 2),
        "dp": round(dp, 2),
    }
    return Charges(
        total=round(total, 2),
        pct_of_buy=round(total / buy_value * 100, 3) if buy_value else 0.0,
        breakeven_move_pct=round(total / buy_value * 100, 3) if buy_value else 0.0,
        breakdown=breakdown,
    )


# ── the one call the API makes ────────────────────────────────────────────────

# Below this buy value the flat ₹18 DP charge dominates and eats returns
# (user-flow.md §Step 5 "minimum sensible amount"). Advisory, not a block.
MIN_SENSIBLE_BUY_VALUE = 20_000.0


def trade_forecast(
    highs: pd.Series,
    lows: pd.Series,
    *,
    account: float,
    risk_pct: float = 1.0,
    charge_cfg: ChargeConfig | None = None,
    **level_kwargs,
) -> dict:
    """Everything the MVP row shows for one stock: levels, size, charges, verdict.

    Returns a plain dict (JSON-ready for the Node API). Real terms as keys per ADR-6;
    the frontend maps them to plain English.
    """
    cfg = charge_cfg or ChargeConfig()
    levels = compute_levels(highs, lows, **level_kwargs)
    pos = position_size(levels, account=account, risk_pct=risk_pct)

    if pos.qty <= 0:
        return {
            "levels": asdict(levels),
            "position": asdict(pos),
            "charges": None,
            "tradeable": False,
            "note": "risk-per-share too large for the account and risk cap — no whole share fits",
        }

    buy_value = pos.qty * levels.entry
    sell_at_target = pos.qty * levels.target
    charges = zerodha_delivery_charges(buy_value, sell_at_target, cfg)

    return {
        "levels": asdict(levels),
        "position": asdict(pos),
        "charges": {**asdict(charges)},
        "tradeable": True,
        "min_amount_ok": buy_value >= MIN_SENSIBLE_BUY_VALUE,
        "min_amount_hint": (
            f"Position ₹{buy_value:,.0f} is below ~₹{MIN_SENSIBLE_BUY_VALUE:,.0f}; "
            "the flat sell fee starts to eat returns."
            if buy_value < MIN_SENSIBLE_BUY_VALUE else
            f"Position ₹{buy_value:,.0f} — flat fees are negligible at this size."
        ),
        "forecast_profit_pre_tax": round(pos.qty * levels.reward_per_share - charges.total, 2),
        "forecast_loss_if_stopped": round(pos.risk_amount + charges.total, 2),
    }
