# User Flow — the canonical spec

**This is what the user actually does.** Where a screen in `platform-plan.md` §6 disagrees with this file, this file wins — the plan describes an automated system that reports to you; this describes the one you asked for, where you press buttons and it answers.

Terminology on screen follows [ADR-6](decisions.md) — plain English leads, real term in grey beneath. This doc uses the plain names.

---

## The shape of it

```
[Check the market]     → Good / Shaky / Bad
        ↓
[Search for stocks]    → ~34 found
        ↓
[Remove the junk]      → 9 left
        ↓
Read the charts        → per row: [Ask Claude] · [Mark tradable]
        ↓
TRADABLE table         → entry · exit · stop · charges · tax · min amount
        ↓                 worth-it verdict · forecast profit/loss
        ↓                 → you set the GTT in Kite yourself
        ↓
[I took the trade]     → editable · [Ask Claude for news]
```

Nothing runs on its own except a nightly pre-warm. You press a button, it answers.

---

## Step 1 — Check the market

**Button.** Runs `step-1-check-the-market.md`: NIFTY against its short-term and trend averages, both slopes, breadth, and the drop-from-recent-high check that catches the "numbers look fine but it just fell hard" case.

**Output:** Good / Shaky / Bad, one sentence of why, and what you're allowed to risk today.

> ⚠️ **Market is Shaky** — data from **Thu 16 Jul** (today's isn't published yet)
> NIFTY 24,068, barely above its short-term average (24,035). Fell hard from 24,547 four days ago. 44% of stocks healthy.
> **Today: invest up to ₹1,25,000 · risk up to ₹2,500 per trade · max 2 trades**

### The clock problem

NSE publishes around 18:00–18:30 IST. Click this at 2pm and today's data **does not exist yet** — not slow, not missing, not published. The button always says which session it's showing, and before ~18:30 that's yesterday and it says so.

The nightly job still exists but is demoted to a **pre-warm**: it downloads so your buttons are instant. If the PC was off, the button downloads for itself and takes a few minutes. Same answer either way ([ADR-11](decisions.md)).

### Bad market

You can still run steps 2–4 and build the list — that's what `overview.md` says to do in a bad market. But the tradable table refuses to plan ([ADR-7](decisions.md)), and any pending GTT gets a **cancel these** warning, because a GTT set in a good market will happily fire in a bad one ([ADR-12](decisions.md)).

---

## Step 2 — Search for stocks

**Button** (per search, plus a run-all). The clauses from `ankur-patel-swing-trading-learnings.md` §67–116 against our own data.

Nine searches, not ten — `5d-range-bo` needs 15-minute candles and there's no intraday data ([ADR-11](decisions.md)).

Each result table says what the search is **for**:

- **Build a watchlist** — the resting/pullback searches. These feed step 3.
- **Just for background** — momentum and volume-spike. These tell you which industries are hot. **They have no [Mark tradable] button** — not disabled, absent. Buying from them measured −0.88% in your own `REPORT.md`, and no tooltip beats a missing button ([ADR-10](decisions.md)).

**Output:** ~10–40 rows.

---

## Step 3 — Remove the junk

**Button.** `step-3-filter-the-junk.md`: price above ₹100, volume above 1 lakh, market cap above ₹1,000cr, normal stocks only.

**Output:** ~5–12 rows, and what got dropped and why — *"25 dropped: 11 too cheap, 9 barely traded, 5 too small."* Clickable, because a filter you can't inspect is one you stop trusting.

"Can you Google it" becomes "is it in the NSE master with a known industry and a real market cap" — same intent, no ambiguity.

---

## Step 4 — Read the charts

The main table. Per row: symbol, industry, price, score, and the score's reasons in words — *"tight rest ✓ · steady rise ✓ · quiet volume ✓ · industry strong ✗"*.

Click a row → full chart: candles, the four average lines, volume coloured by character, resting zone shaded with its top and bottom marked.

### Button: **Ask Claude to check**

Per row, on demand. Never automatic — that's what keeps Claude usage minimal: it fires when you click, not 34 times a night.

**It does not open TradingView.** We already have the data — same prices, same averages, same volume that TradingView has; that's what phase 0 built. TradingView is where *you* look, not a source of truth. Driving a browser to read pixels off a chart we could hand over as numbers is the slow, flaky version of a problem we don't have.

Implementation, cheapest first:

1. **Send the numbers** — shell `claude -p` with the last ~40 sessions, our EMAs, the detected resting zone, volume classes. Ask: steady rest or jumpy? Anything the score missed? **Default.**
2. **Send a picture** — render our chart to PNG and hand Claude the image. Add if (1) reads thin.
3. ~~Drive TradingView~~ — fragile, slow, and the browser extension is user-driven; the backend can't invoke it.

The answer and its reasoning are stored on the row, so you can audit later whether Claude was adding anything. If it isn't, delete the button.

### Button: **Mark tradable**

Captures the resting zone's top and bottom **as they are now** and moves the symbol to the tradable table. If the engine drew the zone wrong, drag it first — your correction is stored and is how the scoring gets tuned in phase 7.

---

## Step 5 — the Tradable table

### Where step 5 of the guide went

`step-5-wait-for-trigger.md` isn't a step you do. **The GTT is step 5.** You set a buy at the top of the resting zone; Zerodha's servers wait for the breakout while your laptop is off. This is cleaner than the original plan and it's the right call ([ADR-12](decisions.md)).

Two consequences. You lose the volume confirmation — a GTT knows price only, so it will buy some fake breakouts; the stop is what handles them. And the platform's step-5 job becomes **tracking** the GTT, not waiting for it.

### What the table shows

```
TITAN · Consumer Durables · Resting 14 days · Score 78

  Buy at             ₹3,412     top of resting zone (₹3,390) + 0.65%
  Exit if wrong      ₹3,187     1% below the zone bottom (₹3,219)
  Take profit at     ₹3,862     twice what you risk

  You risk           ₹225/share · 11 shares · ₹37,532 in
  If wrong           −₹2,475    (0.5% of your account)
  If right           +₹4,950 before tax → +₹3,821 in your pocket

  Charges            ₹101       (0.27% — STT ₹80, DP ₹18, stamp ₹6)
  Short-term tax     ₹1,029     (STCG 111A — 20% + 4% cess)
  Breakeven move     0.27%      it must rise this much before you make anything

  ✅ Worth it — ₹37,532 is well above the ~₹20,000 where flat charges start to bite
```

### Minimum sensible amount

Zerodha delivery costs split in two:

- **Percentage** (~0.22% round trip): STT 0.1% each side, stamp 0.015% on buy, exchange/SEBI/GST negligible. **Brokerage is ₹0.**
- **Fixed:** DP charge ~₹18 with GST, per stock, every sell. Flat regardless of size.

The flat one is the whole question:

| Position | Charges | As % | Breakeven move |
|---|---|---|---|
| ₹5,000 | ₹29 | 0.58% | 0.58% |
| ₹20,000 | ₹62 | 0.31% | 0.31% |
| ₹37,500 | ₹101 | 0.27% | 0.27% |
| ₹1,00,000 | ₹238 | 0.24% | 0.24% |

**Below ~₹20,000 the flat ₹18 starts eating you; above ~₹40,000 it stops mattering.** The 1% risk rule with a ~6% stop lands you around ₹37,000 naturally, so this rarely bites — but the table says so instead of leaving you to wonder.

> **Note on `swing-trading-tax-india-2026.md`:** it claims you need a ~6% move for a trade to be worthwhile. The arithmetic doesn't support that — charges are 0.27% and tax takes 20.8% *of the profit*, so a 3% move still nets ~2.2%. Small moves are less worth the risk and effort, which is a fair point, but it isn't a cost floor. The table computes the real number per trade, so the rule of thumb isn't needed.

**Verify before shipping:** exact DP charge, exchange transaction rate, and stamp duty change over time. Put them in `settings.broker_charges` with the date last checked, never hardcode.

### Setting the GTT

The table hands you a copy-ready slip:

```
GTT 1 — BUY, single-leg                          [Copy]
  TITAN · CNC · Qty 11 · Trigger ₹3,412 · Limit ₹3,429
  ⚠ Also set a Kite price alert at ₹3,412

GTT 2 — SELL, OCO — create only AFTER the buy fills
  TITAN · Qty 11
  Stoploss: trigger ₹3,187 · limit ₹3,155
  Target:   trigger ₹3,862 · limit ₹3,850
```

**Why two, and why the alert.** Zerodha's OCO only works on shares you already own, so the exit GTT cannot be pre-set. Between the buy filling and you creating the OCO, you have **no stop loss** — that's Mistake 4, forced by how the broker works. The free Kite price alert fires to your phone within minutes so you can set the OCO from anywhere. A held position with no exit GTT is a loud state on the dashboard until you confirm it ([ADR-12](decisions.md)).

**Stated once, plainly:** a stop-loss GTT does not protect against a gap down. Stock closes ₹3,300, opens ₹2,900 — your stop triggers, the limit order never fills, you're holding well below plan. True of stop orders everywhere; nothing fixes it.

---

## Step 6 — I took the trade

**Button.** Confirms the trade is live, with every value editable — your actual fill won't match the plan exactly, and pretending otherwise makes the tax numbers wrong.

**Typing every fill by hand will not last.** You'll do it for three weeks and stop, and a half-populated trade history is worse than none — it's what phase 6's tax report and phase 7's analytics are built on. **Zerodha Console tradebook CSV** import is the fix: export, drop it in, it matches to your plans. Zerodha has no free API (Kite Connect is ₹2,000/month), so the CSV is the free path. Manual editing stays for corrections.

### Button: **Ask Claude for news**

Per trade, on demand. This one genuinely needs the web, so it's a real use of the CLI:

```
claude -p "Search recent news for <SYMBOL> (NSE, Indian equity), last 3 weeks.
Report anything that would affect the stock: earnings, orders, regulatory,
management changes, sector news, promoter pledging. Say plainly if nothing
material. Cite sources."
```

Stored on the trade, timestamped, and it lands in the journal — so when you review, you can see what you knew when.

### While you hold

Nudges only, at your evening run, never automatic action:

- Halfway to target → move your exit up to your buy price ("from here you can't lose on this one")
- Shot up 15–20% in 2–3 days → these often snap back, consider taking some
- Market turned Bad → review everything
- Stuck 3 weeks → consider freeing the money
- **Try to move your exit down → refused.** Not a warning; a 400 ([ADR-7](decisions.md))

### The GTT tracker

Because a GTT is fire-and-forget and this platform is asleep, tracking is a module, not a nicety. It tells you when to go **cancel**:

- Market flipped to Bad → *"Cancel all 4 pending buy GTTs. You shouldn't be entering now."*
- Resting zone broke down → *"TITAN fell below its zone. The setup is dead. Cancel it."*
- Stale → *"Waiting 6 weeks. The base it was built on isn't there anymore."*
- Sizing drifted → *"Sized when your account was ₹5L and the market was Good. Both changed."*
- **Corporate action** → *"TITAN splits 22 Jul. Zerodha cancels GTTs on ex-date — recreate it."* Nearly free; we already have `corporate_actions`.

Untracked GTTs are landmines with a one-year fuse.

---

## What this changes in the roadmap

| Change | Why |
|---|---|
| **Per-trade charges + tax forecast: phase 6 → phase 5** | The tradable table is useless without them. FY reporting and ITR-2 export stay in phase 6. |
| **"Ask Claude" buttons: new, phase 3 (chart) and phase 5 (news)** | On-demand only. Minimal by construction — they fire when you click. |
| **Tradebook CSV import: phase 5, alongside manual entry** | Manual-only entry rots within a month, and everything downstream is built on it. |
| **Nightly job demoted to pre-warm** | Buttons are the mechanism; the job just makes them fast. |
| **`5d-range-bo` dropped** | Needs 15-min candles. No intraday data ([ADR-11](decisions.md)). |

## What this flow doesn't have, and should

Not in your description, worth keeping — say so if you disagree:

- **The journal.** Phase 5 auto-fills most of it from the trade. Without it, phase 7 can't tell you which trade types actually make you money, and the override log can't tell you whether ignoring a rule costs you.
- **Practice mode.** Everything above on fake money, flagged, excluded from tax. A month of it before real money.
- **The market gate having teeth.** You run the market check — but if Bad only *informs* rather than *blocks*, it's decoration. `common-mistakes.md` calls skipping it the most expensive mistake there is.
