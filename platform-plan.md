# Swing Trading Platform — Plan

A single-user platform to run the whole evening routine in one place: check the market, search for stocks, filter, read charts, watch for breakouts, plan trades, track them, and compute tax. Execution stays outside (you place orders in your broker app); everything else lives here.

Everything below uses free data and free libraries. Paid options are flagged only where no free path exists.

**Two conventions for this document.** It is a build plan, so §2–§4 and §10 use the precise technical terms — that's what the code and database use, and what the reference docs and formulas assume. **What the user actually sees on screen is plain English**, spec'd in §5 and applied throughout §6. The translation happens at the rendering layer, exactly once.

---

## 1. The one design principle

The backtest in `backtest/REPORT.md` is the most important input to this plan:

> Mechanically auto-trading the scans lost money over 9 months. No scan produced a positive edge as a rules-only system. The scans do their stated job — compress 2,000 stocks to 10–40 candidates. The edge sits in what happens *after* the scan: base quality, sector strength, volume character, entry timing, position size.

So the platform is **not** a signal generator. It is a **funnel with brakes**:

```
2000 stocks
  → [Market gate]     regime decides how much you're allowed to risk at all
  → [Scan]            10-40 raw candidates
  → [Junk filter]     5-12 survivors
  → [Base engine]     scored, ranked; you make the call on the chart
  → [Watchlist]       nothing is buyable yet
  → [Trigger]         only a confirmed breakout unlocks a trade plan
  → [Trade plan]      stop + size + target computed before you can log an entry
  → [Position]        trailing rules, climax alert, time stop
  → [Journal + Tax]
```

Each arrow is a gate. You cannot jump from a scan hit straight to a trade plan — that is Mistake 3 in `beginners-guide/common-mistakes.md`, and the backtest measured it at −0.88% average. The software should make that transition physically impossible, not just discouraged.

---

## 2. Architecture

The folder is `mern/StokeBroker`, so: **React + Node/Express + MongoDB**, plus a **Python worker** for anything numeric. Python is not optional here — the existing backtest code is pandas/yfinance, and rewriting EMA/base math in JS buys nothing.

```
┌─────────────────────────────────────────────────┐
│  React (Vite) + Lightweight Charts              │
│  Dashboard · Scanner · Candidates · Chart       │
│  Watchlist · Planner · Positions · Journal · Tax│
└───────────────┬─────────────────────────────────┘
                │ REST + SSE (live job progress)
┌───────────────▼─────────────────────────────────┐
│  Node / Express  — API, auth, rules engine,     │
│  trade + journal + tax logic, alert dispatch    │
└───────┬───────────────────────┬─────────────────┘
        │ reads/writes          │ POST /jobs (on-demand run)
┌───────▼───────────┐   ┌───────▼─────────────────┐
│  MongoDB          │◄──┤  Python worker (FastAPI)│
│  timeseries:      │   │  ingest · indicators ·  │
│   candles         │   │  scans · base engine ·  │
│  docs: symbols,   │   │  regime · RS · backtest │
│   scans, watch,   │   └───────┬─────────────────┘
│   trades, tax     │           │ Windows Task Scheduler
└───────────────────┘           │ 18:45 IST daily
                                ▼
                     NSE bhavcopy · yfinance · (optional broker API)
```

**Why this split:** Node owns state and rules (things you edit through the UI). Python owns math (things recomputed from price data). They meet only in MongoDB and one job endpoint. Either can be rewritten later without touching the other.

**Runs locally** on your machine (matches the XAMPP setup). No hosting cost, no data leaving the box, no auth complexity. A ₹500/month VPS becomes worth it only if you want alerts when your PC is off — defer that decision.

---

## 3. Data layer

### 3.1 Sources (all free)

| Need | Source | Notes |
|---|---|---|
| Daily prices, all NSE stocks | **NSE bhavcopy** (`sec_bhavdata_full_DDMMYYYY.csv`) | Official, free, published ~18:00–18:30 IST. Includes **delivery quantity/%**, which yfinance does not have. Primary source. |
| History backfill (3–5 years) | **yfinance** | Free, split/bonus-adjusted. Used once to seed, then bhavcopy takes over daily. Already proven in `backtest/`. |
| Symbol master, sector | NSE `EQUITY_L.csv` + index constituent CSVs (`ind_nifty*list.csv`) | Free. Sector comes from index membership, which is also exactly how you check sector strength. |
| Market cap | NSE monthly `MCAP*.csv` | Free, monthly. Between updates, scale by price change. Accurate enough for a ₹1,000cr cutoff. |
| Corporate actions | NSE corporate actions CSV | Free. Needed — see gotcha below. |
| Index data (NIFTY, sector indices) | NSE index bhavcopy / yfinance | Free. |
| Intraday candles (optional, later) | **Free broker API** — Dhan / Upstox / Fyers / Angel One | All free with an account. Needed only for the 15-min breakout scan. You can pull data from one broker and still execute manually at another. |

**Paid alternatives, and when they'd be justified:** TrueData or Global Datafeeds (~₹500–2,000/month) for realtime streaming; Kite Connect (₹2,000/month). None are needed for an evening-routine platform — every step you described works on end-of-day data. Revisit only if you move to intraday entries.

### 3.2 Gotchas that will bite if ignored

1. **Bhavcopy is unadjusted.** A 1:5 split makes a stock look like it fell 80%, which corrupts every EMA and every scan. Ingest must apply corporate actions retroactively and recompute indicators for that symbol. Nightly reconciliation: compare our adjusted close against yfinance's adjusted close, flag any symbol drifting >0.5%.
2. **"Buyer/seller initiated trades ≥ 200"** appears in his Chartink clauses. That comes from tick data nobody gives away free. Substitute: `delivery_pct` + turnover + `volume > 50000`. Our scan output will therefore **not exactly match Chartink's**. That's fine — but the platform should be honest about it, so:
3. **Keep a Chartink import path as a cross-check.** Chartink is free to use in a browser. Support pasting/importing its result list next to our native scan output, and show the diff. Native engine is the source of truth (we control it, no terms-of-service question, works offline); Chartink is the sanity check.
4. **Trading holidays** — NSE holiday list, otherwise the scheduler chases missing files.
5. **Series filter** — keep `EQ` only. Drop `BE`/`BZ`/`SM` (trade-to-trade and SME segments are exactly the manipulated names Step 3 tells you to avoid).

### 3.3 Ingest jobs

| Job | When | Does |
|---|---|---|
| `backfill` | once | 5y of daily candles for ~2,000 symbols via yfinance → ~2.5M rows. Minutes, not hours. |
| `daily_ingest` | 18:45 IST, weekdays | Download bhavcopy → upsert candles → apply corporate actions → recompute indicators → recompute regime → run daily scans → run base engine on hits → check watchlist triggers → dispatch alerts. One chained job, ~2–5 min. |
| `weekly_ingest` | Sunday 19:00 | 3-week tight close + the 6 weekend scans + RS ranks + sector strength refresh. |
| `mcap_refresh` | monthly | NSE MCAP file. |

---

## 4. Compute layer

### 4.1 Indicators (recomputed nightly, cached per symbol/date)

All of these are formulas, implemented from their public descriptions in `ankur-patel-swing-trading-learnings.md`. We are **not** copying his Pine scripts — those are his, and they only run inside TradingView anyway. We reimplement the same measurements.

- **EMA 10 / 20 / 50 / 200**, and slope of each (5-day linear fit → rising/flat/falling).
- **RVOL** = today's volume ÷ 50-day average volume.
- **ADR%** = average daily range over 20 days, as % of price. Drives position sizing sanity and base-tightness thresholds (a tight base for a 6% ADR stock is not tight for a 1.5% ADR stock — thresholds must scale by ADR or every low-volatility name scores high).
- **Distance from 52-week high**, distance from EMA10/20/50.
- **5-week range %**, turnover (₹).
- **Volume character** (per bar, drives chart colouring):
  - **Blue — pocket pivot:** up-day and volume > highest down-day volume of last 10 days.
  - **Red:** down-day and volume > 50-day average → supply overhead. Platform notes the high of that day as a level to overcome.
  - **Green:** up-day and volume > 50-day average.
  - **Orange:** volume < 20% of average → dry, supply exhausted.
  - **Bull snort:** volume ≥ 3× average, close in top 35% of the day's range, close above previous close.
- **Relative strength rank** — percentile of 3/6/12-month return against the full universe. Not in the scan clauses, but it's what "leading stock" means, and it's cheap to compute.

### 4.2 Market regime engine (Step 1)

Per day, on NIFTY 50 daily:

```
price_above_ema20, ema20_above_ema50, both_slopes_rising
breadth       = % of universe above its own 20 EMA, and above 50 EMA
recent_shock  = drawdown from 20-day high  (catches the Jul-15 case:
                numbers look fine but it just fell hard from 24,547)
distribution  = count of high-volume down days in last 10 sessions
```

→ verdict `GREEN` / `CAUTION` / `RED`, plus a **max exposure %**, which is his 0%→100% invested idea made concrete:

| Verdict | Condition | Max exposure | Max open positions | Max risk/trade |
|---|---|---|---|---|
| GREEN | above 20 EMA, 20>50, both rising, breadth >55% | 100% | 5 | 1.0% |
| CAUTION | mixed signals, or recent sharp drop, or breadth 35–55% | 25% | 2 | 0.5% |
| RED | below both EMAs, both falling, or breadth <35% | 0% | 0 | — |

The regime verdict is not decoration. It is a **hard input to the rules engine** — in RED, the trade planner won't open. That single wire implements Mistake 1 and Mistake 12.

**Where a rare Claude call earns its keep:** when signals conflict (price above EMAs *and* `recent_shock` > 3%), rules can't judge "is this a warning sign." One CLI call per day at most, fed the last 10 sessions, returning a verdict + one-line reason, stored on the regime record. Clear GREEN/RED days need no call. Budget: 0–1 calls/day.

### 4.3 Scan engine (Step 2)

The exact clauses are already extracted in `ankur-patel-swing-trading-learnings.md` lines 69–116. Each becomes a declarative spec in code:

```python
SCANS = {
  "rc1_ema20": Scan(
    schedule="daily",
    role="watchlist",        # never "signal" — enforced downstream
    where=lambda d: (d.close > d.ema20) & d.day_chg.between(-4.5, 4.5)
                    & (d.volume > 50_000) & (d.close > 30)
                    & (d.vol_sma50 >= 25_000) & (d.delivery_pct > 30),  # proxy
  ),
  ...
}
```

Ship these: RC1, RC2, 20 EMA pullback, volume spike (RE), momentum, flag, 52-week-high zone, 3-week tight close, plus the two reversal scans. Each carries a `role` field (`universe` / `watchlist` / `signal`) — the momentum and volume scans are tagged `watchlist` so the UI physically cannot offer a "plan trade" button on their rows. That's Mistake 3, enforced in the type system rather than in a tooltip.

Each run stores a snapshot of every hit's metrics, so the scan history is itself a dataset — after 6 months you can ask which scan actually fed your winners.

### 4.4 Junk filter (Step 3) — trivial, config-driven

`close > 100`, `volume > 100000`, `mcap > 1000cr`, `series == EQ`, symbol exists in master with a sector. Runs automatically; the UI shows what was dropped and why, with a per-scan override. The "can you Google it" check is replaced by "is it in the NSE master with a known sector and non-zero market cap" — same intent, no ambiguity.

### 4.5 Base engine (Step 4) — the hard part, and the platform's actual value

This is where the edge is, so it gets the most care. Two jobs: **find the base**, then **score it**.

**Find the base boundaries.** For each candidate, walk candidate windows from 5 to 30 sessions ending today. For each window compute range% = `(max(high) − min(low)) / close`, normalised by ADR. Pick the longest window whose normalised range stays under threshold and which is preceded by a rise (his ladder: close ≥ 1.1× 5-day low, or 1.2× 30-day low, etc.). Output: `base_start`, `base_end`, `pivot = max(high) in base`, `base_low = min(low) in base`, `days_in_base`.

If no window qualifies → not a base → the stock never reaches the watchlist. Most candidates die here, which is the point.

**Score it (0–100), components stored separately so they're auditable:**

| Component | Measure | Why |
|---|---|---|
| Tightness | base range% ÷ ADR — smaller is better | The spring |
| Linearity | efficiency ratio of the prior rise = net move ÷ sum of daily absolute moves. Near 1 = clean, near 0 = choppy | This is exactly his linear-vs-choppy distinction, made numeric |
| Base tidiness | std of daily returns inside base ÷ ADR | Choppy bases have fat, erratic candles |
| Volume dry-up | last-5-day avg volume ÷ 50-day avg — under 0.8 is good | Sellers finished |
| Accumulation | count of blue pocket-pivot bars inside the base | His "best indicator of institutional accumulation" |
| Overhead supply | count of red bars inside base, and whether their highs are already taken out | Unconsumed supply |
| Trend context | above 50 EMA, above 200 EMA, EMA stack order, RS rank | Stage 2 |
| Not extended | distance from 20 EMA, distance from 52-week high | Mistake 2 |
| Sector strength | rank of the stock's sector by momentum-scan share + sector index EMA state | Mistake 10 |

Score is a weighted sum, and **the weights live in a config file, not in code**, because they should be retuned against your own journal after a few months. Score is a sort order and a filter — never an auto-buy.

**Linear vs choppy classification:** three buckets from the efficiency ratio — clear-linear (≥0.6), clear-choppy (≤0.35), and a grey band in between. Clear cases are decided in code, no Claude, no human. Only the grey band (realistically 1–3 stocks a night) gets a chart eyeball — yours, or optionally a Claude look via the browser extension on the chart page. This is the second and last place Claude belongs.

### 4.6 Trigger engine (Step 5)

For every watchlist stock, nightly:

```
breakout   = close > pivot  AND  rvol >= 1.5
                             AND  volume > max(volume of last 10 down days)   # pocket pivot
strength   = close in top 35% of day's range
invalidate = close < base_low  →  drop from watchlist, log why
stale      = days_in_base > 45 without trigger  →  drop
chased     = close > pivot * 1.05  →  flag "missed it, do not chase"
```

Only a `breakout` unlocks the trade planner for that symbol, and only for the next session. The `chased` flag is the codification of the guide's own warning and the backtest's −0.88% finding: if you didn't catch the day, the platform says no.

---

## 5. Language

The user of this platform is not an expert trader. Every word on screen is written for that.

### 5.1 The rule: plain leads, real term follows

The tempting move is to strip jargon entirely and invent friendly names. **That's a trap.** Ankur's videos say "base." Chartink says "EMA." Your broker's contract note says "STT." The ITR form says "111A." A platform that only ever says "resting zone" leaves you fluent in a private language and stranded everywhere else — it makes you *more* dependent on it, not less.

So every term renders in two layers:

```
┌──────────────────────────────────────┐
│  Resting zone                        │   ← plain, big, what you read
│  base · consolidation                │   ← real term, small, grey
└──────────────────────────────────────┘
```

You read the plain line. The real term seeps in over months at zero cost. In six months you can watch his videos without subtitles. A **Learn mode** toggle (default on) hides the grey line once you don't need it, and a glossary page maps both directions, each entry linking to the file in `beginners-guide/` that explains it properly.

### 5.2 Never name things by colour

`step-1-check-the-market.md` calls the 20-day line **blue** and the 50-day line **green**. `how-to-screen-stocks.md` calls them **red** and **orange**. Same lines, same project, two vocabularies — that's what happens when a name depends on a paint choice. It also fails outright if you're colourblind, and again the moment you change themes.

Lines are named by **what they measure**, never by colour:

- **Short-term average line** (20 days) — "is the stock healthy right now?"
- **Trend line** (50 days) — "is it in an uptrend?"
- **Long-term line** (200 days) — "is it healthy over years?"
- **Fast line** (10 days) — for tight entries.

The chart still colours them, consistently, and the legend states both name and colour. But no text anywhere says "above the blue line."

### 5.3 Numbers carry their own units

Never print a bare metric name. The unit *is* the explanation:

| Don't | Do |
|---|---|
| `RVOL 2.1` | `Traded 2.1× more than usual today` |
| `ADR 3.2%` | `Typically swings about 3.2% a day` |
| `Dist 52WH −8%` | `8% below its highest price of the past year` |
| `RS rank 94` | `Stronger than 94% of all stocks` |
| `Risk 6.6% / 1R = ₹225` | `If wrong, you lose ₹225 per share (6.6%)` |
| `Target 2R` | `If right, you make ₹450 per share — twice what you risk` |

### 5.4 Blocks explain themselves and offer the fix

A guardrail that says "Blocked: exposure cap exceeded" teaches nothing and just annoys. Every block states what you tried, why it's stopped, and what to do instead:

> **Hold on — this puts too much money in at once.**
> This buy would put **₹1,20,000** into the market. Right now your limit is **₹1,00,000**, because the market is shaky (see today's market check).
> **Options:** buy 18 shares instead of 22 · wait for the market to steady · [override, and tell me why]

### 5.5 The translation table

Plain wording is what ships in the UI. The right column stays visible in Learn mode, and stays authoritative in the code.

| On screen | Real term (grey subtitle, and used in code/DB) |
|---|---|
| Resting zone / rest | base, consolidation |
| Top of the resting zone / breakout price | pivot |
| Bottom of the resting zone | base low |
| Steady rest / jumpy rest | linear base / choppy base |
| How straight the rise was | efficiency ratio |
| Short-term / trend / long-term average line | EMA 20 / 50 / 200 |
| Traded ⨯ more than usual | relative volume (RVOL) |
| Typical daily swing | average daily range (ADR) |
| Stronger than X% of all stocks | relative strength rank |
| Big-buyer day | pocket pivot |
| Huge-buying day | bull snort |
| Sellers waiting above this price | overhead supply |
| Quiet — nobody's selling | volume dry-up |
| Market condition (Good / Shaky / Bad) | regime (green / caution / red) |
| How many stocks are healthy | market breadth |
| Fall from its recent high | drawdown |
| Heavy-selling days | distribution days |
| Already moved too far | extended |
| Buying late | chasing |
| It broke out — price moved above the resting zone | breakout, trigger |
| Exit price if wrong | stop loss |
| How many shares to buy | position size |
| Money you're putting in / your limit | exposure |
| Too many from the same industry | sector concentration |
| Move your exit price up | trail the stop |
| It shot up too fast — consider taking profit | climax / parabolic move |
| It's stuck, freeing the money | time stop |
| Shares actually kept, not day-traded | delivery % |
| Money traded | turnover |
| Normal stocks / restricted stocks | series EQ / BE, BZ, SM |
| Search for stocks | scanner, screener |
| Test on past data | backtest |
| Practice mode — not real money | paper trading |
| Oldest shares are counted as sold first | FIFO |
| Profit already booked / profit on paper | realized / unrealized P&L |
| Average result per trade | expectancy |
| Money made ÷ money lost | profit factor |
| Trade type | setup |

**Tax terms are the exception — they stay literal.** `STCG`, `STT`, `Section 111A`, `Section 87A`, `ITR-2`, `advance tax`, `DP charges`, `GST` all appear verbatim on your contract note, your broker's tax statement, and the ITR form. Renaming them would actively hurt you at filing time. They get a plain-English explanation next to them, never a replacement:

> **Short-term tax — ₹18,400** <sub>STCG, Section 111A</sub>
> You held these for under a year, so profit is taxed at 20%, plus 4% cess.
> **Note:** the ₹12 lakh rebate everyone talks about (Section 87A) does **not** apply to this. Common surprise.

### 5.6 How it's built

One dictionary module, one component:

```jsx
// terms.js — single source of truth, i18n-shaped so it's swappable
ema20: { plain: "Short-term average line", real: "20 EMA",
         help: "beginners-guide/step-1-check-the-market.md#thing-1" }

// usage
<Term id="ema20" />          → renders both layers, respects Learn mode
```

**The database and the Python worker keep the real terms** — `ema20`, `pivot`, `base_low`, `rvol`. Plain wording is a rendering concern only. Mixing "resting_zone_bottom" into the schema would make the code disagree with every reference doc, every formula, and every Stack Overflow answer you'll ever search. Translate at the edge, exactly once.

---

## 6. The screens

### Today — the evening routine, as a wizard
Not a grid of widgets. A **sequential flow that refuses to skip the market check**, because that's the golden rule in `overview.md`:

```
① IS THE MARKET OK?      ✅ Good — you can invest up to 100%, risk ₹5,000 per trade
                         NIFTY 24,068, above its short-term average (24,035),
                         trend rising, 58% of stocks healthy
② SEARCH FOR STOCKS      ✅ 5 searches run at 18:47 · found 34
③ REMOVE THE JUNK        ✅ 34 → 9 left  (dropped: 11 too cheap, 9 barely traded, 5 too small)
④ CHECK THE CHARTS       ⏳ 4 look promising — review now  →
⑤ ANY READY TO BUY?      🔔 TITAN broke out — closed ₹3,412, above its resting zone
                         top of ₹3,390, traded 2.1× more than usual
⑥ YOUR TRADES            2 open · ₹1,840 at risk (1.8% of account) · 26% invested
```

If ① says **Bad**, steps ②–⑤ still run — you keep building the watchlist, which is exactly what the guide says to do in a bad market — but ⑥ is locked shut.

### Chart — the workbench
TradingView **Lightweight Charts** (free, Apache-2.0, made by TradingView themselves). Candles plus volume bars, coloured by the volume-character rules from §4.1. Overlays: the four average lines, resting zone shaded, its top and bottom marked, your exit price and target drawn in.

Side panel carries the same *measurements* the AP AI1 dashboard shows, written per §5.3 — how far from each average line, how much it traded vs usual, its typical daily swing, distance from the past year's high, how tight the last 5 weeks were, money traded, strength vs other stocks, sector strength, shares actually kept.

Manual override always available: drag the top or bottom of the resting zone if the engine picked the wrong boundary. Your edit is stored and **fed back as tuning data** for the scoring weights later.

### Search — *scanner*
Cards per search, each with what it looks for in one plain sentence, when it last ran, and how many it found. A badge says what the results are *for* — **"build a watchlist"** vs **"just for background"** — mirroring the `role` field from §4.3. Results table, sortable, every column captioned in plain words. Diff view against a Chartink import. Run-now button. **No buy button anywhere on this page, by design** — that's Mistake 3, enforced by layout as well as by the API.

### Promising stocks — *candidates*
Card grid, best first. Each card: 90-day sparkline with the resting zone shaded, the score with its reasons spelled out ("tight rest ✓ · steady rise ✓ · quiet volume ✓ · sector strong ✗"), sector, strength rank. Keyboard triage — `j/k` to move, `w` to watch, `x` to reject with a reason. Rejection reasons are stored; in three months they tell you what you keep throwing away, and whether you should have.

### Watchlist
Breakout price, how far away it is (%), how long it's been resting, score, status. Sorted by closeness to breaking out. Drops itself with a plain reason logged ("fell below its resting zone — the setup is dead").

### Plan a trade — the gate
Opens only when a stock has actually broken out. Pre-filled, and every line says what it means:

```
Buy at            ₹3,412    only if it crosses this price (a "buy-stop" order)
Exit if wrong     ₹3,187    1% below the resting zone bottom of ₹3,219
You risk          ₹225 per share (6.6%)
Your account      ₹5,00,000 · market is Good · you may risk up to ₹5,000
Buy               22 shares = ₹75,064 — 15% of your account
Take profit at    ₹3,862    you make ₹450 per share — twice what you risk
```

Then the checklist runs. Every item is a rule from `common-mistakes.md`; each is a hard **stop** or a **heads-up**:

| Check, as the user reads it | Fails when | Result |
|---|---|---|
| Is the market OK? | condition is Bad | **Stop** |
| Are you putting in too much? | pushes past the exposure cap | **Stop** |
| Are you risking too much? | risk > cap for current condition | **Stop** |
| Has it actually broken out? | no confirmed breakout | **Stop** |
| Are you buying late? | buy price > 5% above the resting zone top | **Stop** |
| Has it already run too far? | up >10% in 3 days without a new rest | **Stop** |
| Is your exit price in the right place? | not 0.5–1% below the resting zone bottom | **Stop** |
| Is the reward worth the risk? | target below 2× the risk | **Stop** |
| Is your exit price too far away? | risk/share > 8% of price | Heads-up — "buy fewer shares, or skip" |
| Is the industry doing well? | sector in the bottom half | Heads-up |
| Too many from one industry? | 3rd position in one sector | Heads-up |
| Sticking to one trade type? | differs from your main type this quarter | Heads-up (Mistake 9) |
| Any trade left unreviewed? | closed trade with no journal entry | Heads-up |

Stops are overridable **only by typing a reason**, which is logged and surfaced in the monthly review. In about two months you'll be able to see whether your overrides made or lost money. That's the feature.

### Your trades — *positions*
Per open trade: how much you're up or down (in ₹ and as a multiple of what you risked), distance to your exit price and target, days held, and rule-driven nudges:

- **Move your exit up:** halfway to target → suggest moving it to your buy price ("from here you can't lose money on this one"). Near target → suggest locking in most of the gain. Suggestions only.
- **Your exit price can only move up.** The API rejects any edit that lowers it. Mistake 4 becomes a 400 error.
- **Buying more while it's below your buy price is rejected.** Mistake 8, same treatment.
- **Shot up too fast:** +15–20% in 2–3 days → "these often snap back — consider taking some profit."
- **Market turned bad while you're holding** → review everything.
- **Stuck too long:** 3 weeks, barely moved → "consider freeing the money for a better setup."

### Journal
Auto-filled from the trade record (trade type, score, buy/exit/target, market condition when you bought, sector strength, result, chart snapshot at buy and at sell). You add: what you saw, what went right, what went wrong, mistake tags. Weekly review view. The aggregates that matter: win rate and average result **by trade type, by score band, by market condition at entry, by sector strength, and by whether you overrode a stop**.

This is the loop that eventually retunes the scoring weights. It's the whole reason §4.5 stores the score's reasons separately instead of just a number.

### Tax
See §8.

### Practice & history
Reuses `backtest/ankur_backtest2.py` against local data instead of Chartink's 160-day cap — with 5 years of data you can finally test across a rising market, which `REPORT.md` names as its biggest limitation. Also a **replay tool**: pick a stock and a past date, step the chart forward one day at a time, and practise spotting the rest and the breakout with the ending hidden. That's the "study a past winner" habit from his material, made into a game you can't cheat at.

---

## 7. Rules engine

One config file, one evaluator, referenced by both the planner and the positions screen:

```js
{ id: "no-trade-in-red-market",
  source: "common-mistakes.md#mistake-1",
  severity: "block",
  when: ctx => ctx.regime === "RED",
  message: "NIFTY below both EMAs. Guide says sit in cash. No new positions." }
```

Every rule cites its source doc. The UI links back to the guide file. When you disagree with a rule later, you edit the config — and the change is versioned, so the journal can tell you whether loosening it helped or hurt.

---

## 8. Tax

Straight from `swing-trading-tax-india-2026.md`, plus the charges that document doesn't model:

**Lot matching: FIFO.** Mandatory for Indian equity, and it's the thing people get wrong when they scale into a position. Every buy creates a lot; every sell consumes lots oldest-first, producing realized-gain records with a holding period each.

**Charges model (configurable per broker, defaults for common ones):**

| Charge | Rate |
|---|---|
| Brokerage | configurable (₹0 or ₹20/order flat, delivery) |
| STT | 0.1% on buy + 0.1% on sell |
| Exchange transaction | ~0.00297% of turnover (NSE) |
| SEBI turnover | ₹10 per crore |
| Stamp duty | 0.015% on buy |
| GST | 18% on (brokerage + transaction + SEBI) |
| DP charges | ~₹13–16 per scrip on sell day |

These land in the trade record, so your P&L is net of costs from day one — and the platform can then tell you honestly what the guide asserts: that you need roughly a 6% move before a trade is worth taking.

**Tax computation, per financial year (Apr–Mar):**

- STCG under 111A: **20% flat**, plus **4% cess** → ~20.8% effective.
- **Section 87A rebate does not apply** to 111A gains — the platform states this on the report, because it's the single most common surprise.
- LTCG 112A at 12.5% above ₹1.25L (only if a swing trade accidentally becomes a hold).
- Surcharge 10–15% if total income > ₹50L (configurable input).
- Loss handling: STCG loss sets off against STCG/LTCG only, never against salary. Carry forward 8 years, contingent on filing ITR-2 by the due date — the platform tracks the carry-forward ledger year by year.

**Advance tax planner** — the quarterly schedule (15 Jun 15% / 15 Sep 45% / 15 Dec 75% / 15 Mar 100%), with a live estimate from realized gains to date and a countdown. Missing these costs 1%/month under 234B/234C, and it's pure calendar arithmetic — exactly what software should own.

**Exports:** FY realized P&L statement, ITR-2 capital-gains schedule CSV, and a reconciliation view against your broker's own tax P&L statement so you can catch discrepancies before filing.

---

## 9. Alerts and the Claude boundary

**Alerts:** Telegram bot (free) is the right channel — trigger fired, stop breached, climax move, regime flip, advance-tax date. Email via SMTP as backup. In-app toast for anything while you're at the desk.

**Claude usage, kept deliberately small** — two places only:

1. **Conflicted market read** (§4.2) — max 1 call/day, only when rules disagree with each other.
2. **Grey-band base classification** (§4.5) — 1–3 calls/night, only for stocks the efficiency ratio can't cleanly bucket.

Everything else is deterministic code. The reason isn't cost — it's that a rules engine you can read, version, and backtest is worth more than a model call you can't. Both Claude touchpoints write their verdict *and reasoning* to the record, so you can audit whether they were adding anything. If after three months they aren't, delete them.

---

## 10. Data model

```
symbols        symbol, name, isin, series, sector, industry, mcap, listing_date, active
candles        [timeseries] symbol, date, o, h, l, c, v, delivery_qty, delivery_pct, adj_factor
indicators     symbol, date, ema10/20/50/200 + slopes, vol_sma50, rvol, adr_pct,
               dist_52wh, dist_ema20, vol_class(blue|red|green|orange|neutral),
               bull_snort, rs_rank
regime         date, nifty_close, ema20, ema50, slopes, breadth_20/50, drawdown_20d,
               verdict, max_exposure, max_risk_pct, reason, claude_used
scans          id, name, role, schedule, clause_spec, source_link, enabled
scan_runs      scan_id, run_at, universe_size, hit_count, duration_ms
scan_hits      run_id, symbol, metrics{}, passed_filter, drop_reason
bases          symbol, as_of, base_start, base_end, pivot, base_low, days_in_base,
               score, components{}, linearity_class, manual_override
watchlist      symbol, base_id, added_at, status(watching|triggered|invalidated|stale),
               drop_reason, notes
triggers       watchlist_id, date, close, pivot, rvol, is_pocket_pivot, chased, consumed
plans          symbol, trigger_id, entry, stop, target, r_per_share, qty, risk_amt,
               risk_pct, regime_at_plan, checklist[], overrides[], created_at
trades         plan_id, symbol, setup_type, entries[], exits[], stop_history[] (append-only),
               charges{}, status, r_multiple, net_pnl, opened_at, closed_at
journal        trade_id, chart_snapshot_entry, chart_snapshot_exit, went_right, went_wrong,
               mistake_tags[], reviewed_at
tax_lots       symbol, buy_date, qty, price, charges, remaining_qty
realized       symbol, buy_lot_id, sell_date, qty, buy_price, sell_price, charges,
               holding_days, gain_type(stcg|ltcg), gain, fy
settings       account_size, base_risk_pct, broker_charges{}, regime_caps{}, score_weights{}
rules          id, source_doc, severity, enabled, params, version
alerts         type, symbol, payload, sent_at, channel, acknowledged
```

`stop_history` being append-only and `remaining_qty` on lots are the two schema decisions that carry real weight — the first makes Mistake 4 unrepresentable, the second makes FIFO tax correct under scaling.

---

## 11. Build order

Each phase ends in something you actually use that evening. No phase is a prerequisite you can't see.

| Phase | Ships | Rough |
|---|---|---|
| **0 — Data spine** | Symbol master, 5y backfill, daily bhavcopy ingest, corporate-action adjustment, holiday calendar. Verified: spot-check 10 stocks' closes and EMAs against TradingView. | ~1 wk |
| **1 — Chart + Market gate + words** | Lightweight Charts with the average lines, volume colouring, metrics panel. NIFTY market-condition page with verdict and breadth. Plus the `terms.js` dictionary, `<Term>` component, Learn-mode toggle and glossary page from §5 — **built here, not retrofitted.** Every phase after this one inherits plain wording for free; bolting it on at the end means rewriting every screen. **Step 1 is now automated.** | ~1 wk |
| **2 — Scans + filter** | 10 native scans, junk filter, run history, Chartink diff import. **Steps 2–3 automated.** | ~1 wk |
| **3 — Base engine + candidates** | Base detection, scoring, candidate triage grid, watchlist with pivot capture. **Step 4 assisted.** | ~2 wk |
| **4 — Triggers + alerts** | Nightly trigger detection, invalidation, Telegram. **Step 5 automated.** | ~1 wk |
| **5 — Planner + positions + journal** | Rules engine, trade planner, position monitor, trailing/climax/time alerts, journal. **Step 6 automated.** | ~2 wk |
| **6 — Tax** | FIFO lots, charges, FY report, advance tax planner, ITR-2 export. | ~1 wk |
| **7 — Lab** | Local backtest over 5y, past-winner replay, journal analytics, weight retuning. | ongoing |

**Phases 0–2 alone replace most of the manual evening.** Phase 5 is where the platform starts protecting you from yourself, which is the part that actually pays.

---

## 12. Cost

| Item | Cost |
|---|---|
| NSE bhavcopy, yfinance, symbol/sector/mcap data | ₹0 |
| Lightweight Charts, React, Node, MongoDB, Python | ₹0 |
| Telegram alerts | ₹0 |
| Local hosting | ₹0 |
| Claude calls (~1–4/day, small prompts) | negligible |
| **Total** | **₹0/month** |

Paid, only if you later change what you're doing:

| Trigger | Option | Cost |
|---|---|---|
| Want intraday scans | Free broker API first (Dhan/Upstox/Fyers/Angel) — try this before paying | ₹0 |
| Free broker API insufficient | TrueData / Global Datafeeds | ₹500–2,000/mo |
| Want alerts with PC off | Small VPS | ~₹500/mo |
| Want automated execution | Broker API — free at Upstox/Fyers/Dhan/Angel; Kite Connect ₹2,000/mo | ₹0–2,000/mo |

---

## 13. Honest risks

1. **The strategy is unproven in the tested window.** `backtest/REPORT.md` says so plainly. This platform makes the process fast, disciplined, and measurable — it does not make the edge exist. Phase 7 over 5 years of local data is what will actually tell you, and it should be run before you size up.
2. **Our scans won't exactly match Chartink's** — the buyer/seller-initiated-trades clause has no free equivalent. Expect a few % difference in hit lists. The diff view keeps this visible rather than silent.
3. **The base engine is the platform's biggest assumption.** Efficiency ratio is a reasonable proxy for linear-vs-choppy, not a proof of it. Ship it with manual override on day one, capture every override, and retune from your own data. Do not trust the score before you have ~50 journalled trades to check it against.
4. **Guardrails only work if you don't route around them.** The override-with-reason log is what keeps this honest — review it monthly.
5. **Corporate actions are the most likely source of silent wrong answers.** The nightly yfinance reconciliation is not optional.
6. **Not financial advice.** Paper trade the whole flow for a month before real money — the platform should support a paper mode from Phase 5 (same records, flagged `paper: true`, excluded from tax).
