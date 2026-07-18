# Platform — Implementation

Build workspace for the swing trading platform. Strategy and product spec live in [`../platform-plan.md`](../platform-plan.md); this folder is *how it gets built*.

## Layout

```
platform/
├── README.md                    ← you are here
├── docs/
│   ├── decisions.md             locked technical choices + rationale (ADRs)
│   ├── structure.md             repo layout, tooling, conventions
│   ├── engineering-standards.md how backend code gets written (normative)
│   ├── frontend-standards.md    how frontend code gets written (normative)
│   ├── schema.md                MongoDB collections, indexes, contracts
│   ├── terms.md                 the plain↔real dictionary (seed data)
│   ├── phase-0-data-spine.md    ← the only phase planned to task level
│   └── roadmap.md               phases 1–7, one paragraph each
├── api/                         Node/Express        (phase 1+)
├── web/                         React + Vite        (phase 1+)
└── worker/                      Python + FastAPI    (phase 0)
```

## How this planning is scoped, and why

**Phase 0 is planned to the task, with acceptance criteria. Phases 1–7 get one paragraph each.**

That's deliberate. Writing a task-level spec for the trade planner today would be writing fiction — phases 0–3 will teach us that the base engine's thresholds are wrong, that NSE's data has a quirk we didn't expect, that a screen we thought we needed we don't. Detailed plans written ahead of that knowledge get followed instead of questioned, which is worse than having no plan. Each phase gets its own doc when the phase before it lands.

What *is* worth deciding now: the things that are expensive to change later and that every phase depends on — the data model, the language layer, the choice of what's immutable. Those are in `decisions.md` and `schema.md`.

## Reading order

1. `docs/decisions.md` — what's locked and why
2. `docs/structure.md` — where code goes
3. `docs/schema.md` — the data model
4. `docs/phase-0-data-spine.md` — start here to build

Before writing code, read the standards for the side you're on — `docs/engineering-standards.md` (backend) or `docs/frontend-standards.md` (frontend). They are normative and written for AI coding agents; `decisions.md` outranks both.

## Status

| Phase | State |
|---|---|
| 0 — Data spine | planned, not started |
| 1–7 | see `docs/roadmap.md` |

## Before starting

**This directory is not a git repository.** Nothing here is under version control yet — no history, no undo, no branches. That should be fixed before the first line of code, not after:

```bash
cd f:/xampp/htdocs/mern/StokeBroker
git init
```

A `.gitignore` covering `.env`, `node_modules/`, `.venv/`, `__pycache__/`, and `data/` is part of task 0.1.
