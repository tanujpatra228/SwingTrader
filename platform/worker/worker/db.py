"""MongoDB (Atlas) client + collection handles + idempotent index creation.

Indexes exactly as schema.md specifies. createIndex is a no-op when the index
exists, so setup_indexes() is safe to call on every startup — it removes "did anyone
create the index on the new machine" as a class of problem.
"""

from __future__ import annotations

from functools import lru_cache

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database

from worker.config import MONGO_DB, require_mongo_uri


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    return MongoClient(require_mongo_uri(), serverSelectionTimeoutMS=8000, tz_aware=True)


def get_db() -> Database:
    return get_client()[MONGO_DB]


def ping() -> dict:
    """Cheap connectivity check — used by the connection test and job preflight."""
    return get_client().admin.command("ping")


def setup_indexes() -> None:
    db = get_db()
    db.symbols.create_index([("sector", ASCENDING)])
    db.symbols.create_index([("active", ASCENDING)])
    db.candles.create_index([("symbol", ASCENDING), ("date", ASCENDING)], unique=True)
    db.candles.create_index([("date", ASCENDING)])
    db.corporate_actions.create_index(
        [("symbol", ASCENDING), ("ex_date", ASCENDING), ("type", ASCENDING)], unique=True
    )
    db.indicators.create_index([("symbol", ASCENDING), ("date", ASCENDING)], unique=True)
    db.indicators.create_index([("date", ASCENDING), ("rs_rank", DESCENDING)])
    db.job_runs.create_index([("job", ASCENDING), ("started_at", DESCENDING)])
    db.reconcile_flags.create_index([("symbol", ASCENDING), ("date", ASCENDING)])
    db.reconcile_flags.create_index([("resolved", ASCENDING)])
