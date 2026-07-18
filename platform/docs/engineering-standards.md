# Backend Engineering Standards

**Audience: AI coding agents writing backend code in this repo.** Node/Express (`platform/api`) and Python/FastAPI worker (`platform/worker`).

This file is normative. Where it conflicts with a habit, tutorial, or training-data pattern, this file wins. Where it conflicts with [`decisions.md`](decisions.md), **`decisions.md` wins** — it holds the locked architectural choices and this file only tells you how to write code inside them.

Rules are stated as **MUST / SHOULD / NEVER**. Each carries its reason, because a rule whose reason you can't see is a rule you'll route around the first time it's inconvenient.

---

## 0. The three laws of this codebase

Read these before anything else. Everything below is a consequence of one of them.

1. **`worker/compute/` is pure.** DataFrame in, DataFrame out. No DB, no network, no clock, no config. ([structure.md](structure.md))
2. **Raw data is immutable; derived data is disposable.** `candles` is written once. `indicators` is rebuildable. ([ADR-3](decisions.md))
3. **The platform is asleep most of the time.** "You have been away for N days" is the normal case, not an error path. ([ADR-11](decisions.md))

An agent that violates law 1 makes the numbers untestable. Law 2, unrecoverable. Law 3, silently wrong on exactly the days nobody was watching.

---

## 1. Clean code

### 1.1 Naming

- **MUST** use the real domain term: `ema20`, `pivot`, `base_low`, `rvol`, `delivery_pct`. Never `short_term_line`, `resting_zone_bottom`, `data2`, `temp`. ([ADR-6](decisions.md))
- **MUST** name booleans as predicates: `is_stale`, `has_open_position`, `can_plan`. Not `flag`, `status2`, `check`.
- **MUST** put the unit in the name when a unit exists and is not obvious: `stop_price_paise`, `gap_days`, `timeout_ms`, `drift_pct`. Unit-less numerics in money or time code are how paise get added to rupees.
- **SHOULD** let name length track scope: `df` inside a 3-line comprehension is fine; `df` as a module-level cache is not.
- **NEVER** abbreviate to save keystrokes (`calc_pos_sz_frm_stp`). Abbreviate only where the abbreviation *is* the domain term (`ema`, `rvol`, `oco`, `gtt`, `ist`).

### 1.2 Functions

- **MUST** do one thing at one level of abstraction. If you cannot name a function without "and", split it.
- **SHOULD** stay under ~30 lines. This is a smell threshold, not a lint rule — a 40-line pure state machine that reads top-to-bottom beats four 10-line functions that hop.
- **MUST** take ≤3 positional parameters. Beyond that, pass a typed object / dataclass / Pydantic model. `plan_trade(sym, e, s, t, q, r, m, f)` is a bug waiting for two arguments to swap.
- **NEVER** use boolean parameters that select behaviour. `compute_stop(df, trailing=True)` is two functions wearing one coat. Write `compute_initial_stop` and `compute_trailing_stop`.
- **MUST** return early. Guard clauses at the top; the happy path unindented at the bottom. No `else` after a `return`.
- **MUST** keep functions either *deciding* or *doing* — never both. A function that computes a stop AND writes it to Mongo cannot be tested without Mongo, which means it will not be tested.

### 1.3 Comments

- **MUST** comment **why**, never **what**. `# NSE publishes UDiFF ~18:15 IST; earlier reads return yesterday's file` earns its line. `# loop over symbols` does not.
- **MUST** cite the source when code encodes a domain rule: `# per common-mistakes.md Mistake 4: stops never loosen`. These citations are the only thing linking the code to the rulebook it implements.
- **NEVER** leave commented-out code. Delete it (once git exists, it's recoverable; until then, it's still noise).
- **NEVER** write changelog comments (`# changed by ...`, `# new version`). That's the commit's job.

### 1.4 Structure

- **MUST** respect the layer boundaries from [structure.md](structure.md):

  | Layer | May do I/O? | May import |
  |---|---|---|
  | `compute/` | **no** | stdlib, pandas, numpy only |
  | `sources/` | yes — network | `compute/`, `config` |
  | `jobs/` | yes — network + DB | everything |
  | `api.py` | thin | `jobs/`, `db` |

  Imports point **downward only**. `compute/` importing `db` is a rejected change, not a style nit.
- **MUST** keep Node and Python decoupled: they meet in MongoDB and at one job endpoint. Neither imports, shells out to, or parses the other's internals. ([ADR-1](decisions.md))
- **MUST** put Node's rule enforcement in the API/schema layer, never only in a response shape the UI happens to render. ([ADR-7](decisions.md))

### 1.5 Errors

- **MUST** fail loudly and early. A job that fails silently is worse than a job that doesn't run, because the UI shows yesterday's numbers as if they were today's.
- **MUST** write every job outcome to `job_runs`: status, duration, counts, error. No exceptions — a job with no `job_runs` row is invisible.
- **NEVER** swallow an exception (`except Exception: pass`, empty `catch {}`). If a failure is genuinely tolerable, log it at WARN with the reason it's tolerable, and count it.
- **NEVER** substitute a default for missing data in a numeric path. A missing close is not `0` and not `last_close`. It is an error or a documented gap — a fabricated price propagates into every indicator downstream and looks plausible forever.
- **MUST** return actionable API errors: HTTP status + a stable machine-readable `code` + a human message. `400 {code: "STOP_LOWERED"}`, not `500 "error"`.

### 1.6 Money, dates, config

Restating from [structure.md](structure.md) because these are the three places where "clean" and "correct" are the same rule:

- **MUST** store `trades`, `tax_lots`, `realized` prices as **integer paise**. Floats there produce tax figures that don't reconcile to the rupee, which makes them worthless. Analysis-only prices may be floats.
- **MUST** treat a session as a **date, not a moment** — UTC midnight of the IST trading date.
- **NEVER** call `datetime.now()` / `Date.now()` inside `compute/` or inside any rule function. Pass the clock in. Non-injected time is untestable time.
- **MUST** read config from env. **NEVER** hardcode `F:\...` paths or `localhost:27017`. ([ADR-8](decisions.md))
- **MUST** bind the API to `127.0.0.1`, never `0.0.0.0`. There is no auth; the bind address *is* the auth. ([ADR-8](decisions.md))

---

## 2. TDD

### 2.1 The loop

**Red → Green → Refactor.** Write a failing test that states the intent. Write the least code that passes it. Then clean up with the test as your net.

- **MUST** write the test first for: every function in `compute/`, every guardrail in the API, every money or tax calculation, every date/gap calculation.
- **SHOULD** write test-first elsewhere; **MAY** write test-after for `sources/` glue and throwaway scripts.
- **MUST NOT** write the test after the fact and call it TDD. A test written against code you just wrote tests what the code *does*, not what it *should do* — it locks the bug in.

### 2.2 What a test looks like

- **MUST** be named for the behaviour, not the function: `test_stop_cannot_be_lowered`, not `test_update_stop_2`.
- **MUST** follow Arrange–Act–Assert with blank lines between the three. One logical assertion per test.
- **MUST** use handmade data with a known answer. Twelve rows of hand-written OHLC where you know the EMA by hand beats 500 rows of downloaded prices where you know nothing.
- **NEVER** assert against output the code itself produced ("golden file made by running it once"). That tests that the code hasn't changed, not that it's right. If you need a golden file, its values must be derived independently — by hand, by a reference implementation, or from the source doc.
- **NEVER** hit the network or a live DB in a unit test. `compute/` needs neither by construction — that's the point of law 1.

### 2.3 What to test

The base engine is the platform's largest assumption ([platform-plan.md §13.3](../../platform-plan.md)). Test it like it is.

- **MUST** cover, for every numeric function: the normal case, the **boundary** (exactly at threshold), the **empty** input, and the **insufficient-history** input (fewer rows than the indicator's period).
- **MUST** write a regression test *first* for every bug: reproduce it red, then fix it. A fixed bug with no test is a bug scheduled to return.
- **MUST** test guardrails by their rejection, not their acceptance. The interesting assertion is `400 STOP_LOWERED`, not that a valid stop saves.
- **MUST** test the **gap path** for anything the scheduler touches: "last run 4 sessions ago" is the normal case, so it gets a test, not a comment. ([ADR-11](decisions.md))
- **SHOULD** use property-based tests (`hypothesis`) where an invariant is cheap to state: adjusted prices never go negative; FIFO lot matching conserves total quantity; a trailing stop's history is monotonically non-decreasing.
- **NEVER** chase a coverage number. Coverage measures lines executed, not truths asserted. An untested boundary in `bases.py` matters; an untested `__repr__` does not.

### 2.4 Test doubles

- **SHOULD** prefer real objects and pure functions to mocks. A mock is an assertion about *how* the code works and breaks on every refactor.
- **MUST** confine mocking to the boundary you don't own — HTTP calls in `sources/`, the Mongo client in `jobs/`.
- **MUST** mock the network with recorded real payloads (a saved bhavcopy file), not with invented ones. Invented payloads test your imagination of NSE, and NSE is more creative than you.
- **NEVER** mock `compute/`. If you need to, law 1 has already been broken.

---

## 3. Event-driven architecture

### 3.1 Read this before you reach for a broker

**This platform is a batch system, not a monitor** ([ADR-11](decisions.md)). There is no Kafka, no RabbitMQ, no Redis Streams, and adding one is an architectural change requiring a new ADR — **not a decision an agent makes mid-task**.

The reason EDA is in this document anyway: the platform is *already* event-driven in the way that matters. It has producers (jobs), events (a breakout happened; a stop was hit; a GTT went stale), consumers (alerts, dashboard, tracker), and — crucially — **a delivery channel that is offline most of the time**. That's the hard part of EDA arriving without the fun part. The patterns below exist to stop the classic distributed-systems failures from showing up in a single-box app that thought it was too small to have them.

MongoDB is the event log. Jobs are the dispatcher. That is enough at this scale, and it's what these rules assume.

### 3.2 Events

- **MUST** model a domain event as a **fact in the past tense**: `BreakoutTriggered`, `StopHit`, `GttVoidedByCorporateAction`, `MarketRegimeChanged`. Never imperative (`SendAlert`) — imperatives are commands, and a command hidden in an event log is coupling with extra steps.
- **MUST** give every event: a stable `event_id`, an `occurred_at` (the IST **session date** it is about), a `recorded_at` (when we noticed), a `type`, and a `version`.
- **MUST** keep `occurred_at` and `recorded_at` separate. They differ by days whenever the PC was off, and every "why is this alert dated wrong" bug is these two collapsed into one field.
- **MUST** treat events as immutable. Wrong event → emit a corrective event. Never `updateOne` an event.
- **SHOULD** make events self-contained enough to interpret without a lookup (carry `symbol`, `price_paise`, `session_date`), but **NEVER** let an event carry a *derived* number that `indicators` owns — that's a stale copy waiting to disagree.

### 3.3 Idempotency — non-negotiable

Every job is re-runnable with the same result ([structure.md](structure.md)). At-least-once is the only delivery guarantee available, so **every consumer must be safe to run twice**.

- **MUST** upsert on a natural key. Never blind-insert. `{symbol, date}` for candles; `{symbol, session_date, type}` for events.
- **MUST** make alert dispatch idempotent via a dispatch record: check `alerts_sent` for the `event_id` before sending; insert the send record in the same operation flow as the send. Duplicate Telegram messages at 21:00 train the user to ignore alerts, which disables the alert system permanently.
- **MUST** design every job to be killable at any line and re-runnable with no hand-cleanup. A job that half-ran and needs manual repair before retry *will* be half-run at 19:00 on a day you're not watching.
- **NEVER** use "did we already do this?" logic based on wall-clock time (`if last_run.date() == today`). The PC being off makes that false in both directions. Key on the data, not the clock.

### 3.4 Outbox

- **MUST** use an outbox when a state change and an external side effect must agree: write the event to Mongo **in the same operation as the state change**, then let a separate dispatch step read unsent events and deliver them, marking sent on success.
- **Why:** the alternative — write to Mongo, then call Telegram — has two failure modes with no good answer. Telegram fails after the write: the user is never told. Telegram succeeds and the write fails: the user is told about something that didn't happen. The outbox makes the second impossible and the first self-healing, because the next run picks up the unsent row.
- **MUST** treat the outbox as the reason alerts can be *late* but never *invented*. This matches [ADR-11](decisions.md): alerts are a convenience, the dashboard is the truth.

### 3.5 Failure handling

- **MUST** give every external delivery a bounded retry with backoff, then a dead-letter state (`status: "failed"` + error on the event), never an infinite loop.
- **MUST** surface dead-lettered events on the dashboard. A DLQ nobody looks at is a silent data-loss channel with paperwork.
- **MUST** make the consumer handle **gaps**, not days: "what happened since my last run?" is the only correct question. Anything found in the gap is flagged `chased` on arrival, because it is. ([ADR-11](decisions.md))
- **MUST** refuse to serve planning decisions on stale data rather than serving them quietly. Staleness is a first-class state with its own UI, not a caveat.

### 3.6 What NOT to do

- **NEVER** introduce a message broker, event-sourcing framework, CQRS split, or saga orchestrator. One user, one box, ~2.5M documents. Mongo will not notice the load ([ADR-2](decisions.md)); you will notice the two new daemons that must be alive for the app to work — on a PC that is off half the time.
- **NEVER** make Node and Python communicate by events they invented for each other. Node owns state, Python owns derived numbers, they meet in Mongo and at one job endpoint. ([ADR-1](decisions.md))
- **NEVER** rebuild current state by replaying an event log. State lives in collections. Events are a record of what happened, not the source of truth for what *is*.

---

## 4. Checklist before you call backend work done

- [ ] Nothing in `compute/` touches DB, network, clock, or config.
- [ ] Tests written **before** the code for every `compute/` function, guardrail, and money path.
- [ ] Boundary, empty, and insufficient-history cases covered on every numeric function.
- [ ] Every bug fixed has a regression test that was red first.
- [ ] Job is re-runnable end-to-end with identical results; all writes upsert on natural keys.
- [ ] Job writes status/duration/counts/error to `job_runs` on **both** success and failure.
- [ ] The "away for N days" gap path is handled and tested.
- [ ] Money in `trades` / `tax_lots` / `realized` is integer paise.
- [ ] No hardcoded paths, URIs, or secrets; `.env.example` updated with every new key (no values).
- [ ] API binds `127.0.0.1`.
- [ ] Guardrails enforced server-side and proven by a rejection test.
- [ ] Domain rules encoded in code cite their source doc in a comment.
- [ ] No new runtime, broker, or dependency without an ADR.

---

## Sources

Internal — these override anything below: [`decisions.md`](decisions.md), [`structure.md`](structure.md), [`schema.md`](schema.md), [`platform-plan.md`](../../platform-plan.md), [`beginners-guide/common-mistakes.md`](../../beginners-guide/common-mistakes.md), [`backtest/REPORT.md`](../../backtest/REPORT.md).

External research informing §2–§3:

- [Outbox, Inbox patterns and delivery guarantees explained — Event-Driven.io](https://event-driven.io/en/outbox_inbox_patterns_and_delivery_guarantees_explained/)
- [Transactional outbox pattern — AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
- [Building Reliable Event-Driven Architectures: Outbox, Exactly-Once, Idempotent Consumers — Java Code Geeks](https://www.javacodegeeks.com/2025/09/understanding-event-driven-architectures-kafka-outbox-pattern-and-exactly-once-guarantees.html)
- [Event-Driven Architecture & Message Queues: 2026 Reference — Digital Applied](https://www.digitalapplied.com/blog/event-driven-architecture-message-queues-2026-engineering-reference)
- [Event-Driven Architecture and the Outbox Pattern — Varo Engineering](https://medium.com/engineering-varo/event-driven-architecture-and-the-outbox-pattern-569e6fba7216)
