"""The evening pipeline: market check -> scan -> filter -> trade numbers.

Reads candles from Mongo, runs the pure compute chain, stores one screen document
the API serves. This is steps 1-3 + the trade numbers, assembled (mvp.md).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from worker.config import ACCOUNT_SIZE, RISK_PCT
from worker.compute.filters import filter_junk
from worker.compute.indicators import add_indicators
from worker.compute.regime import assess_market, verdict_to_dict
from worker.compute.scans import run_all, snapshot_features
from worker.compute.trade_math import trade_forecast
from worker.repo import load_all_recent, record_job, save_screen, symbol_meta
from worker.sources import yahoo

MIN_PRICE = 99.0            # drop anything priced below this, before any scan


def _market() -> dict:
    """Step 1 — from NIFTY via yfinance (one symbol, no universe needed)."""
    nifty = yahoo.fetch_index("^NSEI", period="2y")
    ind = add_indicators(nifty)
    v = assess_market(ind, as_of=str(nifty.index[-1].date()))
    return verdict_to_dict(v)


def _breadth(snapshot: pd.DataFrame) -> float | None:
    if "close" not in snapshot or "ema20" not in snapshot or snapshot.empty:
        return None
    return round((snapshot["close"] > snapshot["ema20"]).mean() * 100, 1)


def run_screen(account: float = ACCOUNT_SIZE, risk_pct: float = RISK_PCT,
               universe_limit: int | None = None) -> dict:
    started = datetime.now(timezone.utc)
    meta = symbol_meta()

    # one batched read, not 500 round-trips (repo.load_all_recent)
    all_frames = load_all_recent(limit=400)
    rows, frames = [], {}
    excl_large = excl_price = 0
    for sym, df in all_frames.items():
        if sym not in meta or len(df) < 60:
            continue
        if universe_limit and len(frames) >= universe_limit:
            break
        # universe pre-filter, BEFORE any scan:
        #  - drop large caps (NIFTY 100) — swing trading targets faster mid/small caps
        #  - drop anything priced below MIN_PRICE (penny/near-penny)
        if meta[sym].get("tier") == "large":
            excl_large += 1
            continue
        if float(df["c"].iloc[-1]) < MIN_PRICE:
            excl_price += 1
            continue
        try:
            ind = add_indicators(df)
            feat = snapshot_features(ind)
        except ValueError:
            continue
        feat["symbol"] = sym
        feat["sector"] = meta[sym].get("sector")
        feat["mcap_cr"] = meta[sym].get("mcap_cr")
        feat["name"] = meta[sym].get("name")
        rows.append(feat)
        frames[sym] = df

    snapshot = pd.DataFrame(rows)
    market = _market()
    market["metrics"]["breadth_pct_above_20"] = _breadth(snapshot)

    # step 2 + 3
    hits = run_all(snapshot) if not snapshot.empty else snapshot
    if hits.empty:
        result = {"market": market, "candidates": [], "dropped_summary": {},
                  "universe_size": len(snapshot), "excluded_largecap": excl_large,
                  "excluded_price": excl_price, "min_price": MIN_PRICE,
                  "scan_hits": 0, "after_junk": 0,
                  "account": account, "risk_pct": risk_pct}
        save_screen(result)
        record_job("screen", "ok", {"universe": len(snapshot), "candidates": 0}, started=started)
        return result

    filtered = filter_junk(hits)

    # NOTE: tightness gate (is_tight_setup) intentionally NOT applied — the full
    # post-junk list is shown so the user judges tightness themselves via the
    # tightness / near-high / volume columns. Re-enable by filtering `kept` here.
    kept = filtered.kept
    after_scan_filter = len(kept)

    # step 6 numbers per survivor
    candidates = []
    for _, r in kept.iterrows():
        sym = r["symbol"]
        try:
            f = trade_forecast(frames[sym]["h"], frames[sym]["l"],
                               account=account, risk_pct=risk_pct)
        except (ValueError, KeyError):
            continue
        candidates.append({
            "symbol": sym,
            "name": r.get("name"),
            "sector": r.get("sector"),
            "scans": r.get("scans", []),
            "scan_count": int(r.get("scan_count", 1)),
            "close": round(float(r["close"]), 2),
            "delivery_pct": r.get("delivery_pct"),
            # the "why it's tight" signals, for the UI to show
            "wk_tight_pct": r.get("wk_tight_pct"),
            "dist_52wh_pct": r.get("dist_52wh_pct"),
            "vol_dry": r.get("vol_dry"),
            "tightness": r.get("tightness"),
            **f,
        })
    # best setups first: tightest weekly close, then nearest the high
    candidates.sort(key=lambda c: (c.get("wk_tight_pct", 999), -(c.get("dist_52wh_pct") or -999)))

    result = {
        "market": market,
        "candidates": candidates,
        "dropped_summary": filtered.summary,
        "universe_size": len(snapshot),
        "excluded_largecap": excl_large,
        "excluded_price": excl_price,
        "min_price": MIN_PRICE,
        "scan_hits": len(hits),
        "after_junk": after_scan_filter,
        "account": account,
        "risk_pct": risk_pct,
    }
    save_screen(result)
    record_job("screen", "ok",
               {"universe": len(snapshot), "excl_large": excl_large, "excl_price": excl_price,
                "hits": len(hits), "after_junk": after_scan_filter, "candidates": len(candidates)},
               started=started)
    print(f"screen: excluded {excl_large} large-cap + {excl_price} under Rs{MIN_PRICE:.0f} "
          f"-> universe {len(snapshot)} -> scans {len(hits)} -> junk {after_scan_filter} "
          f"-> candidates {len(candidates)} | market {market['verdict'].upper()}")
    return result


if __name__ == "__main__":
    run_screen()
