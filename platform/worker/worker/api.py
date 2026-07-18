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

from worker.compute.scans import ALL_SCANS
from worker.db import ping
from worker.jobs.screen import run_named_scan, run_screen
from worker.repo import get_routine, latest_screen, mark_routine_done

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


@app.post("/scan/{scan_key}")
def run_scan_endpoint(scan_key: str) -> dict:
    """Run one scan across the universe on demand (e.g. Stage 2 from the routine)."""
    if scan_key not in ALL_SCANS:
        raise HTTPException(404, f"unknown scan {scan_key!r}")
    return run_named_scan(scan_key)


@app.get("/routine")
def routine() -> dict:
    """{item_id: last_done_iso} — when each routine item was last marked done."""
    return get_routine()


@app.post("/routine/{item_id}/done")
def routine_done(item_id: str) -> dict:
    """Stamp a routine item done now."""
    return {"item_id": item_id, "last_done": mark_routine_done(item_id)}
