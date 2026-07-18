"""Daily refresh: pull the full bhavcopy for every missing session and upsert candles.

Processes the GAP since the last stored session, not just "today" (ADR-11) — the PC
is not on 24/7, so coming back after days off must catch up all of them. NSE 404s
non-trading days; those are skipped, which is also how weekends/holidays self-handle
without a holiday calendar for the MVP.
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone

import requests

from worker.db import get_db
from worker.repo import record_job, upsert_candles
from worker.sources import nse


def _last_session() -> date | None:
    db = get_db()
    doc = db.candles.find_one({"source": "bhavcopy"}, sort=[("date", -1)])
    if doc:
        return doc["date"].date()
    # no bhavcopy yet — start from the newest backfilled candle, or 10 days back
    doc = db.candles.find_one(sort=[("date", -1)])
    return (doc["date"].date() if doc else date.today() - timedelta(days=10))


def run_daily(max_days: int = 15) -> dict:
    started = datetime.now(timezone.utc)
    session = nse._session()
    start = (_last_session() or date.today() - timedelta(days=max_days))
    today = date.today()

    day = start + timedelta(days=1)
    fetched, skipped, candles = [], 0, 0
    while day <= today:
        if day.weekday() < 5:                    # skip weekends outright
            try:
                df = nse.fetch_bhavcopy(day, session)
                candles += upsert_candles(df, source="bhavcopy")
                fetched.append(str(day))
            except requests.HTTPError:
                skipped += 1                     # holiday / not published yet
            except requests.RequestException:
                skipped += 1
        day += timedelta(days=1)

    status = "ok" if fetched or skipped else "partial"
    counts = {"sessions_fetched": len(fetched), "sessions_skipped": skipped,
              "candles_upserted": candles, "dates": fetched}
    record_job("daily", status, counts, started=started)
    print(f"daily: fetched {len(fetched)} sessions ({', '.join(fetched) or 'none'}), "
          f"skipped {skipped}, {candles} candles")
    return counts


if __name__ == "__main__":
    run_daily()
