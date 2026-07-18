# Data Model

MongoDB, database `stokebroker`. Full collection list is in `platform-plan.md` §10; this doc specifies the **phase 0 collections** concretely and leaves the rest sketched until their phase arrives.

Per ADR-3, collections fall into three tiers, and the tier decides how you're allowed to treat them:

| Tier | Collections | Rule |
|---|---|---|
| **Raw** — expensive to reacquire | `candles`, `corporate_actions`, `symbols` | Write once. Never mutate. Re-derivable only by re-downloading years of files. |
| **Derived** — cheap to rebuild | `indicators`, `regime`, `bases`, `scan_hits` | Delete and rebuild freely. Never the source of anything. |
| **Owned** — irreplaceable | `trades`, `journal`, `plans`, `settings`, `tax_lots` | User's own work. Cannot be re-derived from anything, at any price. **Back these up.** |

That last row is the one that matters most and gets forgotten: if `indicators` is lost, a job rebuilds it in seconds. If `candles` is lost, it's a bad afternoon of re-downloading. If `trades` is lost, your tax filing has no basis and your journal history is gone forever. Treat the tiers differently.

---

## Phase 0 collections

### `symbols`
```js
{
  _id: "TITAN",                    // NSE symbol, uppercase — natural key
  name: "Titan Company Limited",
  isin: "INE280A01028",
  series: "EQ",                    // only EQ is ingested
  listing_date: ISODate,
  sector: "Consumer Durables",     // from index constituent CSVs; null if unmapped
  indices: ["NIFTY 50", "NIFTY 500"],
  mcap_cr: 285400,                 // monthly refresh
  mcap_as_of: ISODate,
  active: true,                    // false when it leaves the master (delisted)
  updated_at: ISODate
}
```
Index: `{sector: 1}`, `{active: 1}`.

**`active`, not deletion.** A delisted symbol must keep its candles and its trades — you may have traded it, and the tax record needs it. Dropping the row would orphan real history.

### `candles` — raw, immutable
```js
{
  symbol: "TITAN",
  date: ISODate("2026-07-15T00:00:00Z"),   // UTC midnight of IST session date
  o: 3390.5, h: 3425.0, l: 3381.2, c: 3412.8,
  v: 1284000,                               // traded quantity
  delivery_qty: 642000,
  delivery_pct: 50.0,                       // null when bhavcopy omits it
  turnover: 4380000000,
  trades: 48210,
  source: "bhavcopy",                       // or "yfinance" for backfilled rows
  ingested_at: ISODate
}
```
Index: `{symbol: 1, date: 1}` **unique** — this is what makes re-running a day idempotent. Plus `{date: 1}` for universe-wide queries (a scan reads one date across 2,000 symbols; that's the hot path).

**Unadjusted, always.** These are the numbers the exchange printed that day. A split does not touch this collection.

**`source` matters.** Backfilled rows come from yfinance and are already split-adjusted by Yahoo; bhavcopy rows are raw. Mixing them without a marker means the adjustment layer cannot know what it's looking at, and the seam sits at whatever date the backfill ended — invisible, and wrong in exactly one direction. See the "backfill seam" note in the phase 0 doc; this field is how it gets handled.

### `corporate_actions`
```js
{
  symbol: "TITAN",
  ex_date: ISODate,
  type: "split",                   // split | bonus | dividend
  ratio: 5.0,                      // price divisor from ex_date backwards
  raw: "Face value split 10 to 2", // original text, kept for auditing the parse
  source: "nse_ca_api",
  ingested_at: ISODate
}
```
Index: `{symbol: 1, ex_date: 1}` unique on `{symbol, ex_date, type}`.

Dividends are recorded but **not applied** — they don't move price the way a split does, and adjusting for them makes our prices disagree with every chart you'll compare against. Recorded because tax and reconciliation will eventually want them.

### `indicators` — derived, disposable
```js
{
  symbol: "TITAN",
  date: ISODate,
  adj_c: 3412.8, adj_o: ..., adj_h: ..., adj_l: ..., adj_v: ...,
  ema10: 3380.1, ema20: 3352.4, ema50: 3298.7, ema200: 3105.2,
  ema20_slope: 0.42,               // 5-day linear fit, % per day
  ema50_slope: 0.31,
  vol_sma50: 610000,
  rvol: 2.10,                      // v / vol_sma50
  adr_pct: 3.2,                    // 20-day average daily range, % of price
  dist_52wh_pct: -8.0,
  dist_ema20_pct: 1.8,
  range_5w_pct: 6.4,
  vol_class: "blue",               // blue|red|green|orange|neutral — §4.1 of plan
  bull_snort: false,
  rs_rank: 94,                     // percentile vs universe; needs full-universe pass
  computed_at: ISODate
}
```
Index: `{symbol: 1, date: 1}` unique, `{date: 1, rs_rank: -1}`.

Rebuilt per symbol whenever its candles or corporate actions change. `rs_rank` is cross-sectional, so it's a second pass after all symbols have their own numbers — it cannot be computed inside the per-symbol loop.

### `job_runs` — observability
```js
{
  job: "daily",
  started_at: ISODate, finished_at: ISODate, duration_ms: 184000,
  status: "ok",                    // ok | failed | partial
  counts: { symbols: 1943, candles_upserted: 1943, indicators_rebuilt: 1943,
            ca_applied: 2, reconcile_flags: 3 },
  errors: [{ symbol: "XYZ", stage: "yahoo_reconcile", msg: "..." }],
  triggered_by: "scheduler"        // scheduler | api | cli
}
```
Index: `{job: 1, started_at: -1}`.

`status: "partial"` exists because "12 of 2,000 symbols failed" is neither success nor failure, and collapsing it to either one is how you end up trading on data with a hole in it.

### `reconcile_flags`
```js
{
  symbol: "TITAN", date: ISODate,
  ours: 3412.8, theirs: 3350.1, drift_pct: 1.87,
  likely_cause: "unrecorded_split",   // or "unknown"
  resolved: false, resolved_note: null,
  flagged_at: ISODate
}
```
The nightly yfinance audit (ADR-4) writes here. Unresolved flags surface in the UI — **a silent reconciliation is not a reconciliation.**

---

## Later phases — sketched only

Field-level specs land with their phase. Shapes are in `platform-plan.md` §10. Two decisions are already locked because they're structural (ADR-7) and cheap to honour now, expensive to retrofit:

**`trades.stop_history` is append-only.**
```js
stop_history: [
  { price: 318700, at: ISODate, reason: "initial — 1% below base low" },
  { price: 341200, at: ISODate, reason: "moved to entry at halfway to target" }
]
```
Stored in **paise as integers**. The API validates that each appended price is ≥ the last. There is no update path and no delete path. Mistake 4 is not a warning in this system; it's a schema property.

**`tax_lots.remaining_qty`** — FIFO consumption is a decrement on the lot, never a recomputation from trade history. Recomputing FIFO from scratch on every read means the answer can change as history is edited; decrementing means a sold lot stays sold. Tax records must be stable across time, or last year's filed return stops matching what the system says today.

---

## Indexes, all at once

```js
symbols:            {_id}, {sector:1}, {active:1}
candles:            {symbol:1, date:1} UNIQUE, {date:1}
corporate_actions:  {symbol:1, ex_date:1, type:1} UNIQUE
indicators:         {symbol:1, date:1} UNIQUE, {date:1, rs_rank:-1}
job_runs:           {job:1, started_at:-1}
reconcile_flags:    {symbol:1, date:1}, {resolved:1}
```

Created idempotently in `worker/db.py` at startup. `createIndex` is a no-op when the index exists, so this is safe to run every time and removes "did anyone create the index on the new machine" as a category of problem.
