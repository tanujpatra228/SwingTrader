"""StokeBroker numeric worker.

Layout (see ../docs/structure.md):
    compute/  pure functions — DataFrame in, DataFrame out. No DB, no network, no clock.
    sources/  external data I/O (NSE, Yahoo).
    jobs/     orchestration.
    api.py    FastAPI job endpoints.

The purity of compute/ is what makes the numbers testable without infrastructure.
"""
