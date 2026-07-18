"""Seed jobs: symbol master (+ sectors) and history backfill.

Run once to bootstrap, and the master refresh weekly. Backfill is resumable — it
skips symbols that already have enough candles, so a flaky-network retry costs only
the symbols that didn't finish (phase-0 task 0.3).
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from worker.db import get_db, setup_indexes
from worker.repo import record_job, upsert_candles, upsert_symbols
from worker.sources import nse, yahoo


def ingest_master() -> dict:
    started = datetime.now(timezone.utc)
    setup_indexes()
    s = nse._session()
    master = nse.fetch_symbol_master(s)
    sectors = nse.fetch_sector_map(s)
    n = upsert_symbols(master, sectors)
    counts = {"symbols": n, "with_sector": sum(1 for v in sectors.values() if v)}
    record_job("ingest_master", "ok", counts, started=started)
    print(f"master: {n} EQ symbols, {counts['with_sector']} sectors mapped")
    return counts


def backfill(only_with_sector: bool = True, period: str = "5y", batch: int = 100) -> dict:
    """History via yfinance. Defaults to sector-mapped symbols (the tradable universe;
    the junk filter drops the rest anyway), keeping the seed to ~500 not ~2000."""
    started = datetime.now(timezone.utc)
    db = get_db()
    q = {"active": True}
    if only_with_sector:
        q["sector"] = {"$ne": None}
    symbols = [d["_id"] for d in db.symbols.find(q, {"_id": 1})]

    # resume: skip symbols that already have plenty of candles
    have = {d["_id"] for d in db.candles.aggregate([
        {"$group": {"_id": "$symbol", "n": {"$sum": 1}}},
        {"$match": {"n": {"$gte": 200}}},
    ])}
    todo = [s for s in symbols if s not in have]
    print(f"backfill: {len(symbols)} target, {len(have)} already seeded, {len(todo)} to fetch")

    total, done = 0, 0
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        frames = yahoo.fetch_history(chunk, period=period)
        for sym, d in frames.items():
            d = d.reset_index().rename(columns={"Date": "date", "index": "date"})
            d["symbol"] = sym
            total += upsert_candles(d, source="yfinance")
            done += 1
        print(f"  {min(i + batch, len(todo))}/{len(todo)} symbols, {total} candles", flush=True)

    counts = {"symbols_fetched": done, "candles_upserted": total}
    record_job("backfill", "ok", counts, started=started)
    return counts


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("master", "all"):
        ingest_master()
    if cmd in ("backfill", "all"):
        backfill()
