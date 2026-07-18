"""Market-condition check — step 1 of the guide, made numeric.

Pure. Takes a NIFTY OHLCV DataFrame (with indicators already attached by
add_indicators) and returns a verdict + the exposure caps the rest of the platform
obeys. Implements step-1-check-the-market.md and platform-plan.md §4.2.

Good / Shaky / Bad maps to regime green / caution / red. The verdict is a hard
input downstream (ADR-7), not decoration: in Bad, planning is blocked.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class MarketVerdict:
    verdict: str            # "good" | "shaky" | "bad"
    max_exposure_pct: int   # how much of the account may be deployed
    max_positions: int
    max_risk_pct: float     # risk cap per trade
    reasons: list[str]      # plain-language, why this verdict
    as_of: str              # the session date this reflects (caller fills)
    metrics: dict


def assess_market(
    df,
    *,
    breadth_pct_above_20: float | None = None,
    as_of: str = "",
) -> MarketVerdict:
    """Verdict from the last row of an indicator-bearing NIFTY frame.

    Three checks from step 1:
      1. price above its short-term average line (20 EMA)?
      2. short-term line above the trend line (20 EMA > 50 EMA)?
      3. both lines pointing up (positive slope)?
    Plus the recent-shock check that catches the Jul-15 case — numbers fine but a
    sharp drop from a recent high — which a naive three-tick pass would miss.

    `breadth_pct_above_20` (share of the universe above its own 20 EMA) is optional;
    when absent, breadth simply doesn't contribute. Everything else works from NIFTY
    alone, so the market check runs before the universe is ingested.
    """
    if len(df) < 50:
        raise ValueError(f"need >= 50 sessions for a market read, got {len(df)}")

    last = df.iloc[-1]
    close = float(last["c"])
    ema20 = float(last["ema20"])
    ema50 = float(last["ema50"])
    slope20 = float(last["ema20_slope"])
    slope50 = float(last["ema50_slope"])

    # drawdown from the highest close of the last 20 sessions
    high_20 = float(df["c"].iloc[-20:].max())
    drawdown_pct = (close / high_20 - 1) * 100

    price_above_20 = close > ema20
    stack_ok = ema20 > ema50
    slopes_up = slope20 > 0 and slope50 > 0
    recent_shock = drawdown_pct <= -3.0

    reasons: list[str] = []
    reasons.append(
        f"Price is {'above' if price_above_20 else 'below'} its short-term average line"
        f" ({close:,.0f} vs {ema20:,.0f})."
    )
    reasons.append(
        f"Short-term line is {'above' if stack_ok else 'below'} the trend line"
        f" ({ema20:,.0f} vs {ema50:,.0f})."
    )
    reasons.append(
        "Both average lines point up." if slopes_up else "The average lines are flat or falling."
    )
    if recent_shock:
        reasons.append(f"Warning: fell {abs(drawdown_pct):.1f}% from its recent high — shaky despite the numbers.")
    if breadth_pct_above_20 is not None:
        reasons.append(f"{breadth_pct_above_20:.0f}% of stocks are healthy (above their own short-term line).")

    # verdict
    breadth_bad = breadth_pct_above_20 is not None and breadth_pct_above_20 < 35
    breadth_shaky = breadth_pct_above_20 is not None and breadth_pct_above_20 < 55

    if (not price_above_20 and not stack_ok) or (not slopes_up and not price_above_20) or breadth_bad:
        verdict, exp, npos, risk = "bad", 0, 0, 0.0
    elif price_above_20 and stack_ok and slopes_up and not recent_shock and not breadth_shaky:
        verdict, exp, npos, risk = "good", 100, 5, 1.0
    else:
        verdict, exp, npos, risk = "shaky", 25, 2, 0.5

    return MarketVerdict(
        verdict=verdict,
        max_exposure_pct=exp,
        max_positions=npos,
        max_risk_pct=risk,
        reasons=reasons,
        as_of=as_of,
        metrics={
            "close": round(close, 2),
            "ema20": round(ema20, 2),
            "ema50": round(ema50, 2),
            "ema20_slope": round(slope20, 4),
            "ema50_slope": round(slope50, 4),
            "drawdown_20d_pct": round(drawdown_pct, 2),
            "breadth_pct_above_20": breadth_pct_above_20,
        },
    )


def verdict_to_dict(v: MarketVerdict) -> dict:
    return asdict(v)
