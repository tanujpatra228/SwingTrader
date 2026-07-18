"""Step 3 — remove the junk. Pure, config-driven.

step-3-filter-the-junk.md: price > Rs.100, volume > 1 lakh, market cap > Rs.1000cr,
real listed company. The 'can you Google it' check becomes 'is it in the master with
a known sector and a real market cap' (mvp.md) — same intent, no ambiguity.

Returns kept rows AND a per-drop reason, because a filter you can't inspect is one
the user stops trusting (user-flow.md §Step 3).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class FilterConfig:
    min_price: float = 100.0
    min_volume: float = 100_000.0
    min_mcap_cr: float = 1_000.0
    require_sector: bool = True


@dataclass(frozen=True)
class FilterResult:
    kept: pd.DataFrame
    dropped: pd.DataFrame          # same rows + a `drop_reason` column
    summary: dict[str, int]        # reason -> count, for the "what got dropped" line


def _drop_reason(row: dict, cfg: FilterConfig) -> str | None:
    """First failing check, in plain words, or None if the row survives."""
    if row.get("close", 0) < cfg.min_price:
        return "too cheap"
    if row.get("volume", 0) < cfg.min_volume:
        return "barely traded"
    mcap = row.get("mcap_cr")
    if mcap is not None and not pd.isna(mcap) and mcap < cfg.min_mcap_cr:
        return "too small"
    sector = row.get("sector")
    # pandas string dtype coerces None -> nan (truthy), so test null explicitly
    if cfg.require_sector and (sector is None or (not isinstance(sector, str)) or pd.isna(sector) or not sector):
        return "unknown company"
    return None


def filter_junk(snapshot: pd.DataFrame, cfg: FilterConfig | None = None) -> FilterResult:
    """Split a snapshot into kept vs dropped with reasons.

    Missing market cap does NOT drop a row (mcap refreshes monthly and may lag a new
    listing) — only a present-and-too-small mcap drops it. Silently dropping on
    absent data would hide good stocks and the user would never know why.
    """
    cfg = cfg or FilterConfig()
    reasons = snapshot.apply(lambda r: _drop_reason(r.to_dict(), cfg), axis=1)

    kept = snapshot[reasons.isna()].copy()
    dropped = snapshot[reasons.notna()].copy()
    dropped["drop_reason"] = reasons[reasons.notna()]

    summary = dropped["drop_reason"].value_counts().to_dict() if not dropped.empty else {}
    return FilterResult(kept=kept, dropped=dropped, summary={str(k): int(v) for k, v in summary.items()})
