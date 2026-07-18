# Technical Decisions

Locked choices, each with the reasoning that produced it. If a decision turns out wrong, amend it here with the date and what changed — don't silently drift.

---

## ADR-1 — React + Node + MongoDB, with a Python worker for math

**Decision.** Web UI in React (Vite). API in Node/Express. Storage in MongoDB. All numeric work — ingestion, indicators, scans, base detection, backtests — in a separate Python service.

**Why.** The folder is `mern/StokeBroker`, so the web stack is settled. But the existing backtest code (`backtest/ankur_backtest2.py`) is pandas + yfinance, and every data source in this domain has a mature Python client and a neglected or non-existent JS one. Rewriting EMA/base math in JavaScript buys nothing and costs the ability to reuse work that already exists and already runs.

**The split.** Node owns *state* — things you edit through the UI (trades, plans, settings, rules). Python owns *derived numbers* — things recomputed from price data. They meet in MongoDB and at one job endpoint. Neither imports the other.

**Cost accepted.** Two runtimes to install and keep alive. Worth it.

---

## ADR-2 — Candles in a regular collection, NOT a MongoDB time-series collection

**Decision.** `candles` is an ordinary collection with a unique compound index on `{symbol, date}`.

**Why this is not the obvious choice.** Time-series collections are exactly what daily OHLC data looks like, and they compress well. But they exist on the assumption that history is **append-only and never edited** — updates and deletes on them are restricted, awkward, and version-dependent.

That assumption breaks here. A 1:5 split means every historical price for that symbol must be rewritten. That's not an edge case; it's a routine Tuesday. Choosing a storage type that fights the single most common historical mutation would be optimising a write path we don't need at the cost of a correctness path we do.

Scale doesn't justify it either: ~2,000 symbols × ~1,250 sessions ≈ 2.5M documents. That's small. Mongo will not notice.

---

## ADR-3 — Raw prices are immutable; adjusted prices and indicators are derived

**Decision.** Three layers:

```
candles           what the exchange published. Written once. Never updated.
corporate_actions splits, bonuses, as separate facts with effective dates.
indicators        materialised nightly: adjusted OHLC + every derived number.
                  Freely deletable and rebuildable from the two above.
```

**Why.** The instinct is to adjust prices in place on ingest. Don't. In-place adjustment destroys the original data, so a bug in adjustment logic is **unrecoverable** — you cannot re-derive what the exchange actually said, and you won't notice for months because the numbers still look plausible. It also makes a late-arriving or corrected corporate action a data-archaeology problem instead of a re-run.

Keeping raw immutable means:

- Adjustment bugs are fixed by deleting `indicators` for a symbol and re-running. No restore, no re-download.
- A corporate action discovered late touches one collection, not history.
- The nightly reconciliation (ADR-4) has ground truth to compare against.
- `candles` can be re-derived only by re-downloading years of files; `indicators` can be rebuilt in seconds. Protecting the expensive one and treating the cheap one as disposable is the whole point.

**Cost accepted.** Adjustment math runs on every read that needs it, and `indicators` roughly doubles storage. Both are irrelevant at this scale.

---

## ADR-4 — NSE bhavcopy is the source of truth; yfinance backfills and audits

**Decision.** Daily prices come from NSE's official bhavcopy. yfinance seeds the initial 5 years of history and then runs nightly as an **independent check**, not as a source.

**Why.** Bhavcopy is the exchange's own file — authoritative, and it carries delivery quantity, which yfinance does not have and which is a genuinely useful quality filter. yfinance is an unofficial scraper of a free endpoint Yahoo has never promised to keep; building a daily dependency on it is building on sand.

But yfinance is *split-adjusted by someone else*, which makes it perfect for auditing our own adjustment logic. Two independent sources that should agree: when they don't, one of them is broken and we want to know that night, not at tax time.

**The check:** nightly, compare our adjusted close against yfinance's for every symbol. Drift >0.5% → flag, don't silently pick a winner.

---

## ADR-5 — Our own scan engine is the source of truth; Chartink is a cross-check

**Decision.** Reimplement the scan clauses from `ankur-patel-swing-trading-learnings.md` in Python against our own data. Support importing Chartink's results alongside, and show the difference.

**Why.** Chartink has no public API. The unofficial endpoint the backtest used works, but building a daily dependency on someone's unpublished internals — against their terms — is a dependency that breaks without warning and that we have no standing to complain about. Our own engine works offline, has no history cap (Chartink gives 160 days; `REPORT.md` names that as its biggest limitation), and can be backtested over 5 years.

**The known gap, stated plainly.** His clauses include `buyer initiated trades >= 200`, which comes from tick data with no free equivalent. We substitute delivery % + turnover + volume. **Our hit lists will therefore not exactly match Chartink's.** The diff view exists so that gap stays visible instead of becoming a silent mystery six months from now.

---

## ADR-6 — Plain language is a rendering concern; the database speaks the real terms

**Decision.** Collections, fields, and Python variables use `ema20`, `pivot`, `base_low`, `rvol`. Plain English exists only in `terms.js`, applied by a `<Term>` component at render time.

**Why.** The user isn't an expert and the UI must not assume otherwise (`platform-plan.md` §5). But a schema field named `resting_zone_bottom` would put the code at odds with every formula, every reference doc, every source we're implementing from, and every search result anyone will ever look up while debugging it. Translate at the edge, exactly once, in one file.

**Corollary:** built in phase 1, not retrofitted. Bolting a language layer onto eight phases of finished screens means rewriting all of them.

---

## ADR-7 — Guardrails live in the API and the schema, not the UI

**Decision.** The rules from `common-mistakes.md` are enforced server-side. Two are enforced structurally rather than by validation:

- `trades.stop_history` is **append-only, monotonically non-decreasing**. Lowering a stop is a 400. (Mistake 4)
- Adding to a position below its entry price is rejected. (Mistake 8)

**Why.** A guardrail implemented as a disabled button is a guardrail you route around at 9pm on a bad day — which is precisely when it matters. The user of this platform is also its developer, so "just don't do that" is not a control. Making the mistake *unrepresentable* is the only version that holds.

Overrides exist for the rules that are judgement calls, but they require a typed reason and are logged. After ~2 months the journal can answer whether overriding made money. That's the real feedback loop.

---

## ADR-8 — Local-first, single user, no auth

**Decision.** Everything runs on localhost, on one PC that is **not on 24/7**. No login, no multi-tenancy, no cloud. A VPS is a possible later move, explicitly not now.

**Why.** One user, one machine, matching the existing XAMPP setup. No hosting cost, no data leaving the box, no auth surface.

**Consequence to respect:** because there is no auth, the API binds to `127.0.0.1` only, never `0.0.0.0`. A trading database with no login listening on a LAN interface is quiet until it isn't.

**Keeping the VPS door open** without building for it — four cheap constraints now, expensive to retrofit:

1. No hardcoded paths (`F:\...`). Everything through `.env`.
2. Jobs are plain CLI commands. Task Scheduler *calls* them; cron later calls the same thing. Nothing Windows-specific inside a job.
3. Mongo reached by URI from env, so Atlas or VPS-local Mongo is a config change.
4. When the VPS happens, put it behind **Tailscale or an SSH tunnel** rather than writing auth. Free, and stronger than any login we'd build.

---

## ADR-11 — The platform is a batch system, not a monitor

**Decision.** Nothing in the platform may assume it is running when something happens. **"You have been away for N days" is the normal case, not an error path.**

**Why.** The PC is off overnight, on weekends, on holidays. This isn't a limitation to work around — it's a property that decides the architecture, and pretending otherwise produces a system that is subtly wrong exactly when you weren't watching.

**What follows, non-negotiably:**

- **Alerts are a convenience. The dashboard is the truth.** A Telegram alert only fires if the job ran, which only happens if the PC was on. Nothing may *depend* on the user having been told. Opening the app must answer "what did I miss" — catch-up is a feature, not error handling.
- **The trigger engine scans a gap, not a day.** "Did anything break out today?" is the wrong question. "Did anything break out since my last run?" is the right one — and anything found in the gap is flagged chased on arrival, because it is.
- **Stale data blocks planning.** A market verdict from three days ago is fiction, and planning against it is worse than not planning. Refuse, and offer to run the update. Before ~18:30 IST, say plainly that today's bhavcopy isn't published yet rather than showing yesterday's as if it were today's.
- **"While you were away" is the landing screen** whenever the gap is >1 session. Not a table to scroll to — the first thing on screen.
- **`StartWhenAvailable` + `WakeToRun`** on the scheduled task (task 0.7). If the PC was off at 18:45 and boots at 21:00, the job runs at 21:00. This covers the ordinary case with no code and should not be skipped.
- **No intraday anything.** No live prices, no intraday fill detection, no 15-minute scans. This formally rules out the `5d-range-bo` scan (its clause needs 15-min candles) — drop it from the phase 2 set rather than half-supporting it.

---

## ADR-12 — GTT is the always-on limb; the platform is the brain that sleeps

**Decision.** Entry, stop, and target execution are delegated to Zerodha GTT orders. The platform generates them for manual entry in Kite, and **tracks them**. It never places them.

**Why.** Per ADR-11 the platform is asleep most of the time, so anything that must act while it sleeps has to live somewhere awake. Zerodha's servers are the only such place available. This makes GTT load-bearing rather than convenient:

| Always on — Zerodha | Evening batch — this platform |
|---|---|
| entry trigger, stop, target | scoring, planning, records, tracking |

GTT is also exactly what `step-6-plan-your-exit.md` already asks for ("set a buy-stop order at the breakout price"), and it resolves step 5's "what if you miss the breakout day" — a GTT can't miss it.

**Three structural constraints this imposes:**

1. **OCO needs holdings.** Zerodha's two-leg (stop + target) GTT only works on shares you already own, so it cannot be pre-set. Sequence is forced: buy GTT fires → you hold, *unprotected* → you create the OCO that evening. That gap is Mistake 4 baked into the broker's design. Mitigation: a free **Kite price alert** at the same trigger, created alongside the GTT, so your phone tells you within minutes. A held position with no exit GTT is a loud dashboard state until confirmed.
2. **GTT fires on price alone — it cannot check volume.** The trigger rule is price *and* volume; a GTT knows only price, so it will buy fake breakouts. Accepted deliberately: only high-scoring bases earn a GTT, and the next run checks whether the fill happened on real volume — if not, exit small rather than waiting for the stop. The alternative (wait for evening volume confirmation, buy next day) is the −0.88% path `REPORT.md` measured.
3. **GTT is fire-and-forget; the strategy is market-dependent.** A GTT set in a Good market still fires in a Bad one. GTT's whole value (acting without you) directly contradicts the strategy's first rule (don't act in a bad market). **This is why the GTT tracker is a module, not a nicety** — the platform must tell you to go cancel when the market flips, the base breaks down, the GTT goes stale, sizing drifts, or a corporate action voids it (Zerodha cancels GTTs on ex-date — `corporate_actions` gives us this nearly free). Untracked GTTs are landmines with a one-year fuse.

**Known, unfixable:** a stop-loss GTT does not protect against a gap down — the trigger fires, the limit order never fills, and you hold well below your planned exit. True of stop orders everywhere. State it plainly once during setup rather than letting it be discovered on the day.

**Zerodha has no free API** (correcting an earlier assumption — free read-only APIs exist at Upstox/Dhan/Fyers/Angel, but not Zerodha). Kite Connect is ₹2,000/month. Fills therefore come from **Zerodha Console tradebook CSV export** (free, ~10 seconds), not an API. Revisit only if trade volume makes ₹24,000/year cheap.

---

## ADR-9 — Tooling

| Choice | Rationale |
|---|---|
| **Node 22 LTS**, pnpm | LTS through 2027. pnpm for a lean workspace. |
| **Python 3.12+**, uv | uv resolves and installs fast, single tool for venv + deps. |
| **MongoDB Community, native Windows install** | Docker Desktop needs WSL2 and is a heavy dependency for one database on one machine. Native install is fewer moving parts. A `docker-compose.yml` stays in the repo as an alternative for anyone who prefers it. |
| **Lightweight Charts** (Apache-2.0) | TradingView's own open-source chart library. Free, and exactly the primitives needed: candles, volume histogram with per-bar colours, line overlays. |
| **FastAPI** for the worker | Job endpoints + automatic schemas, minimal ceremony. |

---

## ADR-10 — Scans are labelled by role, and the label is load-bearing

**Decision.** Every scan carries `role: "universe" | "watchlist" | "signal"`. The API refuses to create a trade plan from a hit on a non-`signal` scan. No scan in the initial set is tagged `signal`.

**Why.** This is `REPORT.md`'s finding turned into a constraint. Buying the day after a volume spike measured −0.88% average over ~3,000 samples. The volume scan and momentum scan are *watchlist inputs*, and the guide says so three separate times — which tells you how easy the mistake is to make anyway. A tooltip won't stop it. A 400 will.

---

## Open questions

| Question | Blocked on | Default if unresolved |
|---|---|---|
| Exact current bhavcopy URL and format | NSE changed formats in July 2024 (UDiFF). **Verify on day 1 of phase 0** — do not trust any URL in this doc, including mine, without fetching it. | Fall back to yfinance-only; lose delivery %, keep everything else. |
| Sector mapping source | NSE index constituent CSVs vs. the industry column in the master | Index CSVs — sector strength is computed from index membership anyway |
| Which free broker API, if intraday ever happens | Not needed until 15-min scans matter | Defer entirely |
| Telegram vs. desktop notification for alerts | Phase 4 | Telegram — works when you're away from the desk |
