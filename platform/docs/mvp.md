# MVP — Steps 1–3 + trade numbers

**This is the current build target.** It supersedes the phased roadmap as the *near-term* plan — the roadmap still describes where this grows to. Everything here is a subset already specified in `user-flow.md`; this doc just draws the line around what ships first.

## What ships

```
[Check the market]   → Good / Shaky / Bad          (step 1)
        ↓
[Search for stocks]  → raw list                    (step 2)
        ↓
[Remove the junk]    → clean list                   (step 3)
        ↓
each surviving stock shows:  entry · target · stop · charges
```

Three buttons, one table, per-row trade numbers. Nothing else.

## What is explicitly NOT in the MVP

| Deferred | Why it's safe to defer |
|---|---|
| Step 4 base engine (real resting-zone detection) | The MVP uses a labeled proxy — see below. This is the one honesty risk; it's handled by being loud about it. |
| Charts / Lightweight Charts | A table carries entry/target/stop/charges without a chart. Chart is how you *verify* the pick — comes with step 4. |
| "Ask Claude" buttons | Nothing to assist until there are charts to read. |
| Tradable table, "I took the trade", GTT slips, journal, tax reports | All post-decision. MVP stops at "here are the numbers." |
| The plain-language `<Term>` layer | **Kept.** It's cheap now and expensive to retrofit (ADR-6). Real terms in code, plain on screen, from day one. |
| Nightly scheduler | MVP is button-driven. A manual "refresh data" button is enough; the scheduler is a convenience added later. |

## The one honest compromise: entry/target/stop without a base engine

The guide's numbers come from the **resting zone** (`step-6-plan-your-exit.md`): entry at its top, stop below its bottom. Detecting that zone properly *is* step 4, which is deferred. So the MVP computes a **proxy** and says so on screen:

```
pivot proxy     = highest high of the last 10 sessions
base-low proxy  = lowest  low  of the last 10 sessions

entry   = pivot proxy + 0.5%          (Ankur's "buy above the range")
stop    = base-low proxy − 1%          (his 0.5–1% buffer below pivot low)
risk    = entry − stop
target  = entry + 2 × risk             (his 1:2 minimum reward)
```

Every row that uses this carries a visible tag: **"quick estimate — from the last 10 days, not a confirmed resting zone."** When the base engine lands, the proxy is swapped for real boundaries and the tag goes away. The numbers are honest arithmetic on real prices; only the *zone* is approximate, and the user is told exactly that.

This is deliberately the simplest thing that isn't misleading. It is **not** a claim that these are good entries — it's a claim that these are the entries *the rules produce from a 10-day window*, clearly marked as provisional.

## Charges (this part is exact, not a proxy)

Zerodha delivery, per `user-flow.md` §Step 5. All rates in `settings.broker_charges`, dated, never hardcoded:

- STT 0.1% buy + 0.1% sell
- Exchange transaction ~0.00297%, SEBI ₹10/cr, stamp 0.015% buy
- GST 18% on (brokerage + txn + SEBI)
- DP charge ~₹18 on sell · brokerage ₹0
- Output per row: total charges, as %, breakeven move, and the min-amount verdict (below ~₹20k the flat fee bites)

## Scans in the MVP

The watchlist-role scans only, from `ankur-patel-swing-trading-learnings.md` §67–116:

- **RC1** (`ema-scan-2-7`), **RC2** (`new-daily-2045`), **20 EMA pullback**, **3-week tight close**, **flag**, **52-week-high zone**

Dropped for the MVP: momentum and volume-spike (background-only, `role: watchlist`-input not tradable — ADR-10), the two reversals (different setup), `5d-range-bo` (needs intraday — ADR-11). Start with **RC1 + RC2 + 20 EMA pullback**; add the rest once the three prove out.

**Substitution stands (ADR-5):** no free tick data, so `buyer/seller initiated trades ≥ 200` becomes `delivery_pct` + turnover + volume. Our lists won't exactly match Chartink; that's known and acceptable for the MVP.

## Build order inside the MVP

Still phase 0 first — the data spine is the prerequisite for all three steps, and none of this works on wrong prices.

1. **Data spine** (`phase-0-data-spine.md`, tasks 0.1–0.9) — unchanged, still the foundation. `verify` green is still the gate.
2. **Market check** — regime engine (`platform-plan.md` §4.2) + a `/market` endpoint + the button.
3. **Scans** — the three RC/pullback clauses + `/scan` + the search screen.
4. **Junk filter** — config-driven + shown-what-dropped.
5. **Trade numbers** — the proxy above + the exact charges + the row display.
6. **`<Term>` layer** — built alongside 2–5, not after.

Steps 2–5 are the old phases 1–2 plus the phase-5 charge forecast, minus charts and everything post-decision. Roughly 2 weeks after the data spine.

## Definition of done

```
✅ data spine verify passes (phase 0 gate)
✅ [Check the market] → Good/Shaky/Bad with the reason and the day it's from
✅ [Search] → clean list from ≥3 scans, each row tagged with which scan hit it
✅ [Remove junk] → filtered list + what-was-dropped, clickable
✅ each row shows entry · target · stop, tagged "quick estimate"
✅ each row shows charges, breakeven %, and min-amount verdict
✅ every real term on screen carries its plain-English label
✅ stale-data honesty: says which session the data is from, refuses nothing silently
```
