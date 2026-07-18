"""FastAPI — serves the screen to the UI and triggers jobs.

MVP scoping (deviates from ADR-1, deliberately): Node was to own the API, but Node's
role is owning *state* — trades, plans, settings — none of which exist in the
steps-1-3 MVP. Everything here is read-only derived data from the worker, so a Node
pass-through would be empty. Node arrives with the first owned collection (trades).
Until then the worker serves the UI directly. Bind to 127.0.0.1 only (ADR-8).
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from worker.db import ping
from worker.jobs.screen import run_screen
from worker.repo import latest_screen

app = FastAPI(title="StokeBroker worker", version="0.1.0")

# local dev UI only
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    try:
        ok = ping().get("ok") == 1
    except Exception as e:  # noqa: BLE001 — surface any connectivity failure to the UI
        raise HTTPException(503, f"db unreachable: {e}")
    return {"status": "ok" if ok else "degraded"}


@app.get("/screen")
def get_screen() -> dict:
    """Latest stored screen (market + candidates). 404 until one has been run."""
    doc = latest_screen()
    if not doc:
        raise HTTPException(404, "no screen yet — POST /screen/run first")
    doc["_id"] = str(doc["_id"])
    return doc


@app.post("/screen/run")
def post_screen_run(account: float | None = None, risk_pct: float | None = None) -> dict:
    """Run steps 1-3 + trade numbers now and store the result."""
    kwargs = {}
    if account is not None:
        kwargs["account"] = account
    if risk_pct is not None:
        kwargs["risk_pct"] = risk_pct
    result = run_screen(**kwargs)
    result.pop("_id", None)
    return result
