"""Persistence bridge between MongoDB and the pure compute layer.

Reads raw candles out of Mongo into DataFrames, hands them to compute/, writes
results back. This is the only module that both touches the DB and knows the shape
compute/ expects — keeping that adapter in one place (engineering-standards §DRY).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from pymongo import UpdateOne

from worker.db import get_db


def upsert_symbols(master: pd.DataFrame, sector_map: dict[str, str]) -> int:
    """Upsert the symbol master. Symbols absent from this master are marked inactive,
    never deleted (schema.md) — their candles and any trades must survive."""
    db = get_db()
    now = datetime.now(timezone.utc)
    incoming = set(master["symbol"])
    ops = []
    for _, r in master.iterrows():
        ops.append(UpdateOne(
            {"_id": r["symbol"]},
            {"$set": {
                "name": r["name"], "isin": r.get("isin"), "series": r["series"],
                "listing_date": str(r.get("listing_date", "")),
                "sector": sector_map.get(r["symbol"]),
                "active": True, "updated_at": now,
            }},
            upsert=True,
        ))
    if ops:
        db.symbols.bulk_write(ops, ordered=False)
    # deactivate symbols no longer in the master
    db.symbols.update_many({"_id": {"$nin": list(incoming)}}, {"$set": {"active": False}})
    return len(ops)


def upsert_candles(df: pd.DataFrame, source: str) -> int:
    """Idempotent upsert on {symbol, date}. Re-running a day changes nothing."""
    if df.empty:
        return 0
    db = get_db()
    now = datetime.now(timezone.utc)
    ops = []
    for _, r in df.iterrows():
        d = r["date"]
        d = d.to_pydatetime() if hasattr(d, "to_pydatetime") else d
        doc = {k: (None if pd.isna(r[k]) else float(r[k]))
               for k in ("o", "h", "l", "c", "v") if k in df.columns}
        for opt in ("turnover", "trades", "delivery_qty", "delivery_pct"):
            if opt in df.columns and not pd.isna(r[opt]):
                doc[opt] = float(r[opt])
        doc["source"] = source
        doc["ingested_at"] = now
        ops.append(UpdateOne({"symbol": r["symbol"], "date": d},
                             {"$set": doc}, upsert=True))
    if ops:
        db.candles.bulk_write(ops, ordered=False)
    return len(ops)


def load_candles(symbol: str, limit: int = 400) -> pd.DataFrame:
    """Most recent `limit` sessions for one symbol, ascending, compute-ready."""
    db = get_db()
    cur = db.candles.find({"symbol": symbol}).sort("date", -1).limit(limit)
    rows = list(cur)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).sort_values("date")
    df = df.set_index("date")
    keep = [c for c in ["o", "h", "l", "c", "v", "delivery_pct"] if c in df.columns]
    return df[keep]


def load_all_recent(limit: int = 400, symbols: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Every symbol's recent candles in ONE query, grouped in memory. Replaces 500
    per-symbol round-trips to Atlas (which took ~3 min) with a single scan (~seconds).
    Pass `symbols` to restrict to a list (e.g. a pasted Chartink import) instead of
    the whole DB. Returns {symbol: ascending compute-ready frame}."""
    db = get_db()
    query = {"symbol": {"$in": symbols}} if symbols else {}
    cur = db.candles.find(
        query, {"symbol": 1, "date": 1, "o": 1, "h": 1, "l": 1, "c": 1, "v": 1, "delivery_pct": 1}
    ).sort([("symbol", 1), ("date", 1)])
    frames: dict[str, list] = {}
    for d in cur:
        frames.setdefault(d["symbol"], []).append(d)
    out: dict[str, pd.DataFrame] = {}
    for sym, rows in frames.items():
        df = pd.DataFrame(rows[-limit:]).set_index("date")
        keep = [c for c in ["o", "h", "l", "c", "v", "delivery_pct"] if c in df.columns]
        out[sym] = df[keep]
    return out


def active_symbols() -> list[str]:
    db = get_db()
    return [d["_id"] for d in db.symbols.find({"active": True}, {"_id": 1})]


def symbol_meta() -> dict[str, dict]:
    db = get_db()
    return {d["_id"]: {"sector": d.get("sector"), "name": d.get("name"),
                       "mcap_cr": d.get("mcap_cr"), "tier": d.get("tier")}
            for d in db.symbols.find({}, {"sector": 1, "name": 1, "mcap_cr": 1, "tier": 1})}


def tag_tiers(largecaps: set[str]) -> dict:
    """Mark NIFTY-100 symbols as 'large', everything else 'mid_small'. One-off tag,
    re-runnable — the universe pre-filter (screen.py) reads it to exclude large caps."""
    db = get_db()
    db.symbols.update_many({}, {"$set": {"tier": "mid_small"}})
    r = db.symbols.update_many({"_id": {"$in": list(largecaps)}}, {"$set": {"tier": "large"}})
    return {"large": r.modified_count, "total": db.symbols.count_documents({})}


def get_routine() -> dict[str, str]:
    """{item_id: last_done_iso} for the routine checklist."""
    db = get_db()
    return {d["_id"]: d["last_done"].isoformat()
            for d in db.routine.find({}, {"last_done": 1})}


def mark_routine_done(item_id: str) -> str:
    """Stamp an item done now; returns the ISO timestamp."""
    db = get_db()
    now = datetime.now(timezone.utc)
    db.routine.update_one({"_id": item_id}, {"$set": {"last_done": now}}, upsert=True)
    return now.isoformat()


def record_job(job: str, status: str, counts: dict, errors: list | None = None,
               started: datetime | None = None) -> None:
    db = get_db()
    now = datetime.now(timezone.utc)
    db.job_runs.insert_one({
        "job": job, "status": status, "counts": counts, "errors": errors or [],
        "started_at": started or now, "finished_at": now,
        "duration_ms": int((now - (started or now)).total_seconds() * 1000),
        "triggered_by": "cli",
    })


def save_screen(payload: dict) -> None:
    """Store the latest screen result (market + candidates) for the API to serve."""
    db = get_db()
    payload["created_at"] = datetime.now(timezone.utc)
    db.screens.insert_one(payload)


def latest_screen() -> dict | None:
    db = get_db()
    return db.screens.find_one(sort=[("created_at", -1)])
