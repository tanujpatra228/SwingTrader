# Phase 0 — Data Spine

**Goal.** A local MongoDB holding 5 years of correct, split-adjusted daily prices for every NSE stock, refreshed automatically each evening, with a verification harness that proves it's right.

**Why this is phase 0.** Every later phase is a function of this data. A wrong EMA doesn't announce itself — it produces a plausible number, which produces a plausible scan hit, which produces a plausible trade. Errors here don't surface as crashes; they surface as losses months later, indistinguishable from bad luck. This phase is the only one whose deliverable is *trust*.

**Estimate.** ~1 week. Task 0.5 (corporate actions) is most of the risk.

---

## Day 1 comes before the task list

Three unknowns must be settled by fetching real files, before any code is written around them. **Do not trust the URLs below — including mine.** NSE changed its bhavcopy format in July 2024 (the UDiFF migration) and retired the old `cm{DD}{MON}{YYYY}bhav.csv.zip`. What's true in 2026 needs checking in 2026.

```bash
# 1. Does the full bhavcopy (with delivery data) still exist at this path?
curl -sI -A "Mozilla/5.0" \
  "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_15072026.csv"

# 2. What does the UDiFF bhavcopy look like, and does it carry delivery?
curl -sI -A "Mozilla/5.0" \
  "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_20260715_F_0000.csv.zip"

# 3. Do the JSON APIs still respond to a cookie-warmed session?
#    (holiday-master, corporates-corporateActions)
```

Write down what actually works in `sources/nse.py` as a comment with the date you checked. When one of these breaks in eight months — and one will — that comment is what turns a two-hour mystery into a five-minute fix.

### VERIFIED 2026-07-17 (this environment)

- **`EQUITY_L.csv`** → 200. Cols: `SYMBOL, NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN`. 2,386 EQ symbols.
- **`sec_bhavdata_full_DDMMYYYY.csv`** → **still 200** (the full bhavcopy survived the UDiFF migration). Cols: `SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, DELIV_PER`. **Delivery data present** — the ADR-5 substitution gets real delivery %, not a proxy guess.
- `www.nseindia.com` home → 403 to a bare client, but the `nsearchives.nseindia.com` archive host serves the CSVs directly with just a browser UA. Cookie-warming not needed for archives in practice.
- Host is `nsearchives.nseindia.com` (not the old `www.nseindia.com/...` paths).

**If the full bhavcopy is gone:** fall back to UDiFF plus a separate delivery file, or accept losing `delivery_pct` and drop it from the scan substitutions in ADR-5. Not a blocker. Decide explicitly rather than discovering it in phase 2.

---

## Tasks

### 0.1 — Skeleton
- [ ] `git init` at repo root; `.gitignore` for `.env`, `node_modules/`, `.venv/`, `__pycache__/`, `data/`, `*.log`
- [ ] `platform/worker/` with `pyproject.toml` — deps: `pymongo`, `pandas`, `requests`, `yfinance`, `fastapi`, `uvicorn`, `python-dotenv`, `pytest`
- [ ] MongoDB Community installed, running, reachable at `127.0.0.1:27017`
- [ ] `worker/config.py` — env loading; `worker/db.py` — client, collection handles, idempotent index creation (see `schema.md`)
- [ ] `.env.example` committed, `.env` not

**Done when:** `uv run python -c "from worker.db import db; print(db.list_collection_names())"` connects and creates indexes.

**Pin `yfinance` to an exact version.** It's an unofficial scraper of an endpoint Yahoo never promised to keep; an unpinned minor bump can change column names or silently return empty frames. Pin it, and let the reconciliation catch it if it drifts.

### 0.2 — Symbol master
- [ ] `sources/nse.py`: session with browser `User-Agent`, warm cookies by hitting `nseindia.com` first
- [ ] Fetch `EQUITY_L.csv` → filter `SERIES == "EQ"` → upsert `symbols`
- [ ] Fetch index constituent CSVs (`ind_nifty500list.csv`, sector indices) → map symbol → sector + index membership
- [ ] Mark symbols missing from the master as `active: false` (never delete — see `schema.md`)

**NSE blocks bare HTTP clients.** A plain `requests.get` returns 403. You need a real `User-Agent` and a prior request to the homepage to pick up cookies, reused across the session. Budget an hour for this; it's the single most common wall in NSE scripting and it looks like a network failure rather than a policy one.

**Done when:** ~1,800–2,000 EQ symbols in `symbols`, >90% with a non-null sector.

### 0.3 — Historical backfill (one-time)
- [ ] `sources/yahoo.py`: batch `yf.download` in chunks of ~100 tickers (`SYMBOL.NS`), `period="5y"`, `auto_adjust=True`
- [ ] Write to `candles` with `source: "yfinance"`
- [ ] Log symbols with no Yahoo match; don't fail the run for them
- [ ] `jobs/backfill.py`, resumable — skip symbols already backfilled

**Done when:** ≥95% of active EQ symbols have ≥1,200 sessions. Runtime measured in minutes.

**Resumable, not restartable.** 2,000 symbols over a flaky network will fail partway. A backfill you must restart from zero is one you'll be tempted to "fix" by hand.

### 0.4 — Daily bhavcopy ingest
- [ ] Download for a given date (default: today), cache the raw file to `data/`
- [ ] Parse → normalise columns → upsert into `candles` with `source: "bhavcopy"`
- [ ] Trading calendar: fetch NSE holiday list, cache it; skip weekends/holidays
- [ ] Detect and backfill gaps — on run, check the last N sessions for missing dates and fetch them

**Done when:** running it twice for the same date leaves the DB byte-identical (upsert on `{symbol, date}`), and a deliberately skipped day is picked up automatically on the next run.

**The gap-detector is the point.** Your PC will be off some evening. Without it, that day is missing forever, silently, and every EMA computed across that hole is quietly wrong.

### 0.5 — Corporate actions & adjustment ← highest risk
- [ ] Fetch NSE corporate actions → parse split/bonus ratios → `corporate_actions`
- [ ] Keep the original text in `raw` — ratio parsing from free text ("Face value split from Rs.10 to Rs.2") is where this breaks
- [ ] `compute/adjust.py` — **pure**: given raw candles + CAs, return adjusted OHLCV. Prices before `ex_date` divided by ratio; volume multiplied.
- [ ] Tests against handmade cases before any real data: a 1:5 split, a 1:1 bonus, two splits on one symbol, a split on the first day of history, a split on today.

**Handle the backfill seam.** yfinance rows are *already* adjusted by Yahoo; bhavcopy rows are raw. Applying our adjustment to both double-adjusts the backfilled half. The `source` field exists for exactly this: adjust `bhavcopy` rows only, and treat `yfinance` rows as already-adjusted. The seam sits at the backfill cutover date and is invisible in the data — a 5:1 split there just looks like a stock that fell 80% on an ordinary Tuesday. Every EMA crossing it would be wrong, and every scan would still return plausible-looking results.

The clean alternative, worth considering if the seam gets fiddly: re-derive adjusted prices for the *entire* history from raw bhavcopy once enough history is ingested, and demote yfinance to audit-only. More download, one less class of bug.

**Done when:** the pure-function tests pass, and a known real split in the last 5 years produces a continuous adjusted price series with no artificial gap.

### 0.6 — Indicators
- [ ] `compute/indicators.py`, **pure** — every field in `schema.md`'s `indicators`, from an adjusted DataFrame
- [ ] Per-symbol pass, then a cross-sectional pass for `rs_rank` (it's a percentile against the universe; it cannot exist inside the per-symbol loop)
- [ ] `vol_class` per `platform-plan.md` §4.1: blue = up-day volume > highest down-day volume of last 10; red = down-day above 50-day average; green = up-day above average; orange = below 20% of average
- [ ] Rebuild for a symbol on any change to its candles or CAs
- [ ] Tests: EMA against a hand-computed 30-row series; each `vol_class` branch with a constructed case

**Done when:** our EMA20 for 10 spot-checked stocks matches TradingView to within 0.1%.

**Check EMA seeding.** EMA needs a seed — usually an SMA of the first N bars — and different seeds give different answers for the first ~50 bars. If ours disagrees with TradingView on recent bars, the seeding is fine; if it disagrees only on old bars, that's the seed and it's harmless. Knowing which is which before phase 3 saves a day of chasing a non-bug.

### 0.7 — Job runner & schedule
- [ ] `jobs/daily.py` chains: bhavcopy → CAs → adjust → indicators → reconcile → backup → write `job_runs`
- [ ] Every job writes `job_runs` — status `ok`/`partial`/`failed`, counts, errors
- [ ] `worker/api.py` — `POST /jobs/{name}`, `GET /jobs/{name}/status`
- [ ] Windows Task Scheduler, 18:45 IST, Mon–Fri, **with `StartWhenAvailable` and `WakeToRun`**
- [ ] `daily` accepts a date range and defaults to "every session since the last successful run", not "today"
- [ ] Failure → log loudly now; Telegram lands in phase 4

**The PC is not on 24/7 (ADR-11), so this task is catch-up machinery, not a cron line.** `StartWhenAvailable` makes a job missed at 18:45 run at 21:00 when you boot — that covers the ordinary evening-out case for free, and skipping it means hand-running the job every time life happens. `WakeToRun` covers sleep rather than shutdown.

A `daily` that processes "today" is wrong for the same reason: come back from a week away and six sessions are silently missing. It must process the whole gap, which is also why 0.4's gap-detector and this share a definition of "sessions since last success."

**Done when:** the scheduled task runs unattended for 3 consecutive evenings at `status: "ok"` in under 5 minutes — *and* a deliberate 3-day PC-off gap is fully caught up by a single run on the 4th day.

### 0.9 — Backup ← do not defer this
- [ ] `mongodump` of the **owned tier** (`trades`, `journal`, `plans`, `settings`, `tax_lots`, `realized`) at the end of every `daily` run
- [ ] Dump to a folder already synced by Google Drive / OneDrive — free, no new infrastructure
- [ ] Keep the last ~30 dumps; they're tiny
- [ ] `verify` asserts a dump was written in the last 7 days

**Why this is in phase 0 and not phase 5.** Local-only means the owned tier exists on exactly one disk with no copy anywhere. Per `schema.md`'s tiering: lose `indicators`, a job rebuilds it in seconds; lose `candles`, it's a bad afternoon of re-downloading; **lose `trades` and your tax filing has no basis and your journal is gone permanently.** Nothing re-derives it, at any price.

It costs an hour now. It gets built after it's needed otherwise, which is the wrong time. The collections don't exist until phase 5 — dump what's there and let the list grow.

### 0.8 — Verification harness ← the acceptance gate
`jobs/verify.py`, prints a report and exits non-zero on failure:

- [ ] **Coverage** — ≥95% of active EQ symbols have ≥1,200 sessions
- [ ] **No gaps** — zero missing trading days across the last 250 sessions, calendar-aware
- [ ] **Spot check** — 10 named large caps: our adjusted close vs yfinance, within 0.5%
- [ ] **EMA cross-check** — our EMA20 vs pandas `ewm` on yfinance data, within 0.1%
- [ ] **Split integrity** — a known real split yields no >20% single-day artificial move
- [ ] **Idempotency** — run `daily` twice; assert the second changes nothing
- [ ] **Sanity** — no negative or zero prices; no `h < l`; no volume < 0; no future dates

**This is the phase gate. Phase 1 does not start until `verify` is green.**

The temptation will be to move on at "mostly working" — the charts will look right, the numbers will look plausible, and that's the trap. Plausible-looking wrong data is the specific failure mode this whole phase exists to prevent, and it is invisible without a harness that fails out loud.

---

## Definition of done

```
✅ verify passes clean
✅ daily runs unattended, <5 min, 3 evenings straight
✅ a 3-day PC-off gap is caught up by one run, automatically
✅ ~2,000 symbols, 5y candles, ≥95% coverage
✅ known split adjusts correctly, no seam artefact
✅ EMA20 matches TradingView within 0.1% on 10 spot checks
✅ running daily twice is a no-op
✅ compute/ is pure and unit-tested — no DB, no network
✅ every raw file cached to data/
✅ owned-tier backup written on every run, to synced storage
```

---

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Bhavcopy URL/format changed since 2024 | **High** | Day-1 verification above. Fallback: yfinance-only, lose `delivery_pct`. |
| NSE blocks the scraper (403) | High | UA + cookie warm-up + backoff. It's policy, not network — don't debug it as network. |
| Split-ratio parsing from free text is wrong | Medium | Keep `raw`; test handmade cases; reconciliation catches the misses. |
| Double-adjusting the backfill seam | Medium | The `source` field; consider full re-derivation from bhavcopy. |
| yfinance breaks | Medium | Pinned version. It's audit-only after backfill, so a break degrades the check, not the data. |
| Symbol renames orphan history | Low | ISIN is the stable identity; symbol is not. If it bites, key on ISIN. |

The recurring shape here: **every one of these fails quietly.** None throw. That's why 0.8 is a gate and not a nice-to-have.

---

## Next

Phase 1 (chart + market check + the language layer) gets its own doc once `verify` is green — written knowing what phase 0 actually taught us about the data, rather than what we guessed today.
