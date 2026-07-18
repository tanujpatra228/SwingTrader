# Roadmap

Phase 0 is specified in `phase-0-data-spine.md`. Everything below is deliberately one paragraph — see the scoping note in `../README.md`. Each gets a real doc when the phase before it lands.

**Read [`user-flow.md`](user-flow.md) first** — it is the canonical spec for what the user does, and it outranks the screens in `platform-plan.md` §6. The phases below deliver it.

Every phase ends in something usable that evening. No phase is scaffolding you can't see.

---

## Phase 0 — Data spine · ~1 wk · [detailed](phase-0-data-spine.md)
Symbol master, 5 years of history, nightly bhavcopy ingest, corporate-action adjustment, indicators, verification harness. **Gate: `verify` green before phase 1.**

## Phase 1 — Chart + market check + the language layer · ~1 wk
Lightweight Charts with the four average lines, volume bars coloured by `vol_class`, and the measurements panel. The market-condition page: NIFTY, its averages, breadth, and a Good/Shaky/Bad verdict with the exposure caps from `platform-plan.md` §4.2. Plus `terms.js`, the `<Term>` component, Learn-mode toggle, and glossary — **built here, not retrofitted**, so every later screen inherits plain wording for free. Also the first Node API and React app, so the plumbing is proven while the surface area is still small. **Step 1 of the evening routine is now automated.**

Data-freshness handling lands here too, because it's the first screen that can lie: show the age of the data, block planning on stale data, and say plainly that today's bhavcopy isn't out before ~18:30 rather than passing yesterday's off as today's (ADR-11).

## Phase 2 — Search + filter · ~1 wk
The ten scan clauses from `ankur-patel-swing-trading-learnings.md` §67–116, each with its `role` label (ADR-10). Junk filter. Run history. Chartink import + diff view, so the known gap in ADR-5 stays visible. **Steps 2–3 automated.** At this point most of the manual evening is gone, and the platform is already worth using daily.

## Phase 3 — Base engine + the chart table · ~2 wk
The hard part and the platform's real value: detect resting zones, score them on tightness, linearity, volume dry-up, accumulation, overhead supply, trend context, and sector strength (`platform-plan.md` §4.5). The step-4 table with per-row score reasons. **Mark tradable** captures the zone as drawn, with drag-to-correct stored for phase 7 tuning. Ships with manual override from day one — the engine is a proxy for judgement, not a replacement.

**Ask Claude to check** lands here (`user-flow.md` §Step 4): shell `claude -p` with our own prices, EMAs, detected zone and volume classes — **not** a browser pointed at TradingView. We already have the data; driving a browser to read pixels off a chart we could hand over as numbers is the flaky version of a problem we don't have. On-demand per row, so it stays minimal by construction.

**Step 4 assisted.** Expect this phase to be wrong on the first pass; that's why it's two weeks and why override comes first.

## Phase 4 — Breakouts + catch-up + alerts · ~1 wk
Trigger detection **across the gap since the last run**, not "today" (ADR-11) — anything found in the gap arrives already flagged as chased. Watchlist invalidation and staleness. The **"While you were away"** landing screen, which is the real deliverable here: the dashboard is the truth and alerts are only a convenience, because a Telegram alert only fires if the PC was on. **Step 5 automated.**

## Phase 5 — Planner + GTT + trades + journal · ~2–3 wk
The rules engine, the trade planner with its checklist, position monitoring, journal. Append-only stop history and the add-below-entry rejection (ADR-7) land here.

Plus the things `user-flow.md` and ADR-12 force, which is why this phase grew:

- **The tradable table** — entry, exit, stop, position size, forecast profit/loss, **charges, tax, breakeven move, and the minimum-sensible-amount verdict**. Which means the **per-trade charge and tax forecast moves here from phase 6** — the table is useless without it. FY reporting and ITR-2 export stay in phase 6.
- **GTT slips** — copy-ready buy GTT + the OCO to create after it fills, and the Kite price alert that closes the unprotected window. A held position with no exit GTT is a loud dashboard state.
- **GTT tracker** — a module, not a nicety. Tells you to go cancel when the market flips to Bad, the base breaks down, the GTT goes stale, sizing drifts, or a corporate action voids it. Untracked GTTs are landmines with a one-year fuse, and the platform is asleep while they arm.
- **Ask Claude for news** — on-demand per trade, the one place a web search genuinely earns its call.
- **Tradebook CSV import** alongside manual entry. Manual-only fill entry rots within a month, and phases 6 and 7 are built on that data.

Zerodha has no free API (Kite Connect is ₹2,000/month), so the CSV is the free path. Paper mode from day one of this phase; the whole flow runs a month on fake money first. **Step 6 automated. This is where the platform starts protecting you from yourself, which is the part that pays.**

## Phase 6 — Tax · ~1 wk
FIFO lots, the full charges model, financial-year realized P&L, advance-tax planner with its four deadlines, ITR-2 export, reconciliation against the broker's own statement. Money in paise, per `structure.md`.

## Phase 7 — Practice & history · ongoing
Reuse `backtest/ankur_backtest2.py` against 5 years of local data instead of Chartink's 160-day cap — the limitation `REPORT.md` names as its biggest. Replay tool for studying past winners. Journal analytics: results by trade type, by score band, by market condition, by whether you overrode a rule. This is where the base engine's weights get retuned from your own data instead of guesses.

---

## The honest sequencing note

Phases 0–2 are engineering: known inputs, checkable outputs. Phase 3 is a research problem wearing engineering clothes — the efficiency ratio is a *reasonable proxy* for what Ankur means by linear vs choppy, not a proof of it. And `REPORT.md` already found that the scans alone lost money over its 9-month window, which means the edge this whole platform is built to support is **not yet demonstrated**.

That's not a reason to stop. It's a reason to build phases 0–2 (which are useful regardless — they replace an hour of manual work every evening), get phase 7 running early against real history, and treat phase 3's scores as a hypothesis under test rather than an answer. Paper mode in phase 5 exists for the same reason.

Build the measuring instrument before trusting what it measures.
