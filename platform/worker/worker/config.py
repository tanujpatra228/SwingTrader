"""Environment and constants. The only place that reads .env.

compute/ never imports this (purity law). Only sources/, jobs/, db, api may.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_DB = os.getenv("MONGO_DB", "stokebroker")
DATA_CACHE = Path(os.getenv("DATA_CACHE", "./data")).resolve()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

ACCOUNT_SIZE = float(os.getenv("ACCOUNT_SIZE", "500000"))
RISK_PCT = float(os.getenv("RISK_PCT", "1.0"))

DATA_CACHE.mkdir(parents=True, exist_ok=True)


def require_mongo_uri() -> str:
    if not MONGO_URI or "<db_password>" in MONGO_URI:
        raise RuntimeError(
            "MONGO_URI is unset or still has the <db_password> placeholder. "
            "Put the real Atlas password in platform/worker/.env (gitignored)."
        )
    return MONGO_URI
