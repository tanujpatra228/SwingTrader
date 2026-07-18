# Repo Structure & Conventions

## Layout

```
StokeBroker/
├── beginners-guide/            existing — the product's rulebook, cited by code
├── backtest/                   existing — reused by the worker in phase 7
├── platform-plan.md            existing — product spec
├── platform/
│   ├── docs/                   this planning
│   ├── worker/                 Python — all numeric work
│   │   ├── pyproject.toml
│   │   ├── worker/
│   │   │   ├── config.py       env, paths, constants
│   │   │   ├── db.py           Mongo client, collection handles, index setup
│   │   │   ├── sources/        one module per external source, each isolated
│   │   │   │   ├── nse.py      session/cookie handling, bhavcopy, master, CA, holidays
│   │   │   │   └── yahoo.py    yfinance backfill + reconciliation
│   │   │   ├── jobs/           orchestration, one file per scheduled job
│   │   │   │   ├── backfill.py
│   │   │   │   ├── daily.py
│   │   │   │   └── verify.py
│   │   │   ├── compute/        pure functions — no I/O, no DB
│   │   │   │   ├── adjust.py   corporate action application
│   │   │   │   ├── indicators.py
│   │   │   │   ├── regime.py   (phase 1)
│   │   │   │   ├── scans.py    (phase 2)
│   │   │   │   └── bases.py    (phase 3)
│   │   │   └── api.py          FastAPI — job trigger + status
│   │   └── tests/
│   ├── api/                    Node/Express (phase 1+)
│   └── web/                    React + Vite (phase 1+)
├── docker-compose.yml          optional Mongo, per ADR-9
└── .gitignore
```

## The one structural rule: `compute/` is pure

Everything in `worker/compute/` takes a DataFrame and returns a DataFrame. No database, no network, no clock, no config reads.

This is not tidiness for its own sake. It's what makes the numbers testable: a base-detection function that fetches its own data can only be tested by standing up a database and a network. One that takes a DataFrame can be tested with twelve rows of handmade prices and a known answer. Given that the base engine is the platform's largest assumption (`platform-plan.md` §13.3), the ability to test it against handmade cases is the difference between tuning it and guessing at it.

I/O lives in `sources/`. Orchestration lives in `jobs/`. Those two are allowed to be untidy; `compute/` is not.

## Conventions

**Naming.** Real terms everywhere in code and DB, per ADR-6 — `ema20`, not `short_term_line`. Symbols are bare NSE tickers (`TITAN`), uppercase. The `.NS` suffix is a yfinance detail and exists only inside `sources/yahoo.py`.

**Dates.** Everything is IST. Store dates as UTC midnight of the IST trading date — a session is a date, not a moment, and giving it a time zone invites an off-by-one at 00:00 that surfaces as a missing day six weeks later. Never `datetime.now()` inside `compute/`.

**Money.** Prices as floats are fine for analysis. Prices in `trades`, `tax_lots`, and `realized` are **stored in paise as integers**. Tax figures that don't reconcile with a broker statement to the rupee are worthless, and float drift across a few hundred FIFO lot matches is exactly how that happens.

**Idempotency.** Every job re-runnable with the same result. Upserts keyed on natural keys, never blind inserts. A job that half-ran and needs a hand-cleanup before retry is a job that will be half-run at 19:00 on a day you're not watching.

**Config.** `.env`, never committed. `.env.example` committed with every key present and no values.

**Errors.** Jobs write to `job_runs` — status, duration, counts, error. A job that fails silently is worse than one that doesn't run, because the UI will show yesterday's numbers as if they were today's.

## Commands

```bash
# worker
cd platform/worker
uv sync
uv run python -m worker.jobs.backfill        # once
uv run python -m worker.jobs.daily           # nightly
uv run python -m worker.jobs.verify          # acceptance harness
uv run pytest
uv run uvicorn worker.api:app --port 8001    # job endpoints

# scheduling — Windows Task Scheduler, 18:45 IST weekdays
schtasks /create /tn "StokeBroker Daily" /tr "..." /sc weekly /d MON,TUE,WED,THU,FRI /st 18:45
```

## Environment

```
MONGO_URI=mongodb://127.0.0.1:27017
MONGO_DB=stokebroker
NSE_BASE=https://www.nseindia.com
DATA_CACHE=./data                 # raw downloaded files, gitignored
LOG_LEVEL=INFO
TELEGRAM_BOT_TOKEN=               # phase 4
TELEGRAM_CHAT_ID=                 # phase 4
```

Raw downloads are cached to `data/` and kept. Re-parsing a file you already have beats re-downloading it, and when a parser bug appears the original file is still sitting there to test the fix against.
