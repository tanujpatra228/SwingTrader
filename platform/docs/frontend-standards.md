# Frontend Engineering Standards

**Audience: AI coding agents writing frontend code in this repo.** `platform/web`.

This file is normative. Where it conflicts with a habit, tutorial, or training-data pattern, this file wins. Where it conflicts with [`decisions.md`](decisions.md), **`decisions.md` wins**.

Rules are **MUST / SHOULD / NEVER**, each with its reason.

---

## 0. The three laws of this UI

1. **The database speaks real terms; the screen speaks plain English. Translation happens at the rendering layer, exactly once.** ([ADR-6](decisions.md))
2. **The UI is not where rules live.** A disabled button is not a guardrail. ([ADR-7](decisions.md))
3. **"You have been away for N days" is the landing screen, not an error state.** ([ADR-11](decisions.md))

---

## 1. The stack — locked

| Concern | Choice | Notes |
|---|---|---|
| Build | **Vite** | React 19 + the React Compiler. See §4.4 before typing `useMemo`. |
| Styling | **Tailwind CSS v4** | CSS-first config. **No `tailwind.config.js`** — tokens live in `@theme`. §6. |
| Components | **shadcn/ui** | Vendored into `components/ui/`. You own the code. §6. |
| Server state | **TanStack Query v5** | Owns *everything* from the API. §5. |
| Client state | **Redux Toolkit** | Owns *only* client-only state. §4.1. |
| HTTP | **Axios** | One instance, in the API client module. Never called from a component. §5.1. |
| Tables | **TanStack Table v8** | Headless; renders through shadcn table primitives. §7. |
| Charts | **Lightweight Charts** | Apache-2.0, per [ADR-9](decisions.md). §9. |

- **MUST NOT** add a library that overlaps a lane above. The overlaps that will tempt you, and the answer:
  - **RTK Query** → no. TanStack Query owns server state. Two caches for one concern is the exact duplication §2 exists to prevent.
  - **fetch / ky / SWR** → no. Axios + Query.
  - **Zustand / Jotai / MobX** → no. Redux owns client state.
  - **MUI / Chakra / AntD / Bootstrap** → no. shadcn + Tailwind.
  - **Chart.js / Recharts / D3** → no. Lightweight Charts ([ADR-9](decisions.md)).
- **MUST** get a new dependency past this bar: it does something none of the above does, and the alternative is materially worse than writing it. Otherwise write the ~40 lines.
- **SHOULD** treat "add a library" as an [ADR](decisions.md)-shaped decision, not a task-shaped one.

---

## 2. DRY — and its overcorrection

DRY is **"every piece of knowledge has one authoritative representation"** — not "no two lines may look alike". The distinction is the whole rule. Two blocks of similar-looking code encoding *different* knowledge are not duplication, and merging them creates a coupling paid for later, with interest.

### 2.1 DRY as it applies here

- **MUST** define each of these exactly once, and import it everywhere:
  - **Plain-language labels** → `terms.js` + `<Term>`. Never inline a plain-English label for a real term anywhere else. ([ADR-6](decisions.md), §8)
  - **Formatting** — paise→rupee, percentages, session dates, symbol display → one `format/` module. Money formatted ad-hoc in three components will disagree in three ways.
  - **HTTP** → one Axios instance, one client module per resource. §5.1.
  - **Query keys** → a `queryKeys` factory. Hand-written key arrays scattered across files make invalidation a guessing game. §5.2.
  - **Domain constants** — thresholds, regime labels, scan roles, status enums → one place, ideally derived from what the API returns.
  - **Design tokens** — colour, spacing, radius → `@theme` in `index.css`. §6.2.
- **MUST** treat a **third** occurrence as the trigger to extract. Two similar things may be coincidence; three is a pattern with a name.
- **MUST** dedupe **knowledge**, not **shape**. If two components would need different props for different reasons, they are not duplicates.

### 2.2 The wrong abstraction is worse than duplication

- **NEVER** add a boolean/mode/variant prop to make one component serve two callers that are drifting apart. That's the classic path: `<Panel isCompact isScanner hideHeader variant="watchlist">` — a component with a truth table instead of an interface.
- **MUST** prefer **composition** over configuration. Pass children and slots, not flags.
- **SHOULD** inline the duplication back out when an abstraction starts sprouting conditionals for its callers. Deleting a bad abstraction is cheap now and expensive after four more screens depend on it.
- **MUST** keep **copy** DRY but **layout** WET. Two screens showing the same number share the formatter and the term — they do not share a layout because they happened to look alike in week one.

### 2.3 Where DRY does not apply

- **NEVER** import backend code, re-derive an indicator, or reimplement a rule in JS to avoid a round trip. Derived numbers are Python's ([ADR-1](decisions.md)); rules are the API's ([ADR-7](decisions.md)). A "DRY" client-side copy of a stop calculation is a **second source of truth** — the most expensive kind of duplication there is, and the one DRY was written to prevent.
- **NEVER** copy server data into Redux because two components need it. That is duplication *of the authoritative representation itself*. §4.1.

---

## 3. Components

- **MUST** keep components **presentational by default**: props in, JSX out. Data fetching lives in a route/container or a query hook, never in a leaf.
- **MUST** name for domain role, not shape: `CandidateRow`, `MarketGateBanner`, `StaleDataNotice` — never `Table2`, `MyComponent`, `Wrapper`.
- **SHOULD** stay under ~150 lines. Past that, the component usually holds a hook that wants extracting or a child that wants a name.
- **MUST** extract a **custom hook** when logic (not markup) repeats: `useJobProgress`, `useGapSinceLastRun`, `useCandles`. That is the correct DRY unit in React — it dedupes behaviour without forcing shared markup.
- **MUST** derive during render. Do **not** mirror props/server data into state:
  ```jsx
  // NEVER — two sources of truth, guaranteed to desync
  const [rows, setRows] = useState(props.rows)
  // MUST — derive
  const rows = sortRows(props.rows)
  ```
- **MUST** use a **stable domain `key`** in lists (`symbol`, `trade_id`). **NEVER** the array index — reordered scan results with index keys blend rows into each other silently.
- **MUST** keep components pure: no mutating props/state, no side effects during render, no `Math.random()` / `new Date()` in the render body. ([Rules of React](https://react.dev/reference/rules))
- **NEVER** use `dangerouslySetInnerHTML` for API or file content.

---

## 4. State

### 4.1 The ownership boundary — the rule that keeps this stack sane

Redux and TanStack Query coexist **only** because the line between them is absolute. TanStack Query is a *server-state* library; Redux is a *client-state* library. Blur this and you get both of their costs and neither of their benefits.

| | **TanStack Query owns** | **Redux Toolkit owns** |
|---|---|---|
| What | Anything that came from the API | Client-only state that never existed on the server |
| Here | candles, indicators, scan hits, candidates, watchlist, trades, positions, GTTs, tax lots, job runs, market regime | active filters, sort/column visibility, selected symbols, planner wizard step, modal/drawer state, theme, layout prefs |
| Why | It already solves caching, dedupe, background refetch, invalidation, retry — **and staleness**, which is a domain concept here | Deterministic, inspectable transitions for interdependent client flows |

- **NEVER** put server data in a Redux slice — not "to share it", not "to keep it after unmount", not "so the planner can read it". You would then own cache invalidation, refetch, and staleness by hand, per screen. Staleness is load-bearing in this platform ([ADR-11](decisions.md)); hand-rolling it per screen guarantees one screen gets it wrong and shows three-day-old numbers as if they were today's.
- **NEVER** `dispatch` an action from `onSuccess` to copy query data into a slice. That is the same bug with a ceremony.
- **MUST** store an **identifier** in Redux and read the entity from Query. `selectedSymbol: "TITAN"` in Redux; the candles come from `useCandles(symbol)`.
- **MUST** justify each new slice: if the state is derivable from server data + a URL param, it is not client state.

Realistic expectation: with Query owning the server and the URL owning navigation, **Redux's share of this app is small** — filters, selections, wizard progress, prefs. That's correct, not a sign it's misconfigured. Don't inflate it to feel used.

### 4.2 Choosing where client state lives

Ask in order — stop at the first yes:

1. Can it be **derived** from props/query data/URL? → derive it. Don't store it.
2. Does it belong in the **URL** (symbol, tab, filter set)? → URL. It survives reload and is shareable/linkable; a Redux slice isn't.
3. Used by **one** component? → `useState` there. Not everything is global.
4. **Several sub-values change together**, or next state depends on previous, but stays local? → `useReducer`.
5. Interdependent client state spanning screens? → **a Redux slice**.

- **MUST** use **Redux Toolkit** (`createSlice`, `configureStore`). **NEVER** hand-written action-type constants, switch reducers, or `redux-thunk` boilerplate.
- **MUST** keep reducers pure and state serialisable. No class instances, no `Date` objects, no chart handles in the store.
- **MUST** select narrowly (`useSelector(s => s.filters.minRvol)`), never whole subtrees. **SHOULD** memoise derived selections with `createSelector` when the selector builds a new array/object — this is selector identity, not render memoisation, and §4.4 does not apply to it.
- **NEVER** add a slice to dodge two levels of prop drilling. Composition (`children`) solves most drilling with no store.

### 4.3 Rules of Hooks

- **MUST** call hooks only at the **top level** of a component or custom hook — never in loops, conditions, nested functions, or after an early return.
- **MUST** prefix custom hooks with `use`.
- **MAY** use React 19's `use()` to read promises/context conditionally — the documented exception, not a licence to loosen the rule elsewhere.

### 4.4 Effects

Most `useEffect` in a React codebase should not exist. Before writing one:

- **NEVER** use an effect to **fetch data** → that's Query's job. §5.2.
- **NEVER** use an effect to **transform data for rendering** → derive during render.
- **NEVER** use an effect to **handle a user event** → put it in the handler.
- **NEVER** use an effect to **sync state to state** → lift, derive, or key the component.
- **MUST** reserve effects for **synchronising with an external system**: SSE subscription, the Lightweight Charts instance, a timer, `document.title`.
- **MUST** clean up: every subscription, chart, interval, and listener returns a teardown. An SSE stream left open per job page is a socket leak that shows up as "the app got slow after an hour".
- **MUST** list every reactive value in the dependency array. **NEVER** silence the lint rule — fix the code it points at.

### 4.5 Memoisation (React 19 + Compiler)

- **MUST NOT** hand-write `useMemo` / `useCallback` / `React.memo` in new code. The compiler inserts equivalent memoisation; manual memo is noise that hides intent and rots as deps drift.
- **MAY** memoise when **profiling proves a need** — then **MUST** leave a comment saying what was measured.
- **MUST** still memoise **non-render** work the compiler doesn't cover: TanStack Table `columns` identity (§7), heavy transforms feeding the imperative chart API, `createSelector`.
- **MUST** leave existing memoisation alone; the compiler coexists with it. No memo-removal side quests.

---

## 5. Data layer — Axios + TanStack Query + SSE

### 5.1 Axios

- **MUST** create **one** instance in `api/client.js`: `baseURL` from `import.meta.env`, timeout, JSON defaults. **NEVER** hardcode `http://127.0.0.1:3000`. ([ADR-8](decisions.md))
- **MUST** call Axios only from resource modules (`api/candles.js`, `api/trades.js`). **NEVER** from a component, and **NEVER** `axios.get(...)` off the bare import — that bypasses the instance and every interceptor on it.
- **MUST** normalise errors in **one** response interceptor into a typed error carrying HTTP status + the API's machine-readable `code` + message. The `code` is what the UI branches on ([§10](#10-accessibility-forms-quality)); parsing error strings per screen is how `STOP_LOWERED` becomes "Something went wrong".
- **MUST** forward Query's `AbortSignal` into Axios (`({ signal }) => api.get(url, { signal })`). Without it, cancellation silently does nothing and a fast symbol-switch races stale responses onto the screen.
- **NEVER** put auth headers or token logic in interceptors. There is no auth ([ADR-8](decisions.md)); a login flow appearing here is an ADR, not a task.

### 5.2 TanStack Query

- **MUST** fetch through Query hooks. **NEVER** `useEffect` + `setState`.
- **MUST** build keys from a `queryKeys` factory: `queryKeys.candles(symbol)` → `['candles', symbol]`. Hierarchical and stable, so invalidation targets a subtree instead of guessing.
- **MUST** include **every** input the request depends on in the key — symbol, session date, filter set. A key that omits an input serves another input's data. This is the single most common Query bug.
- **MUST** invalidate on mutation (`onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.trades() })`). **NEVER** hand-write the new server state into the cache from a guessed shape — invalidate, or use the mutation's real response.
- **MUST** set `staleTime` deliberately per resource, and **MUST** know that Query's `staleTime` is a **cache** concept and has nothing to do with this platform's **domain** staleness (§5.4). A fresh cache of three-day-old data is still stale data. Never render one to answer the other.
- **SHOULD** set `staleTime` high for data that changes once a night. Candles and indicators change at ~18:45 IST; refetching them on every window focus is pure noise. `retry` should be low — a job that isn't running won't start because you asked five times.
- **MUST** handle mutations for anything that writes: trades, plans, stop updates, overrides. **NEVER** optimistic-update a **guardrail** path — showing a stop as saved before the server rejects it teaches the user the rule doesn't exist. ([ADR-7](decisions.md))
- **SHOULD** keep one `useX` hook per resource (`useCandles`, `useCandidates`) that wraps `useQuery` with the key, fn, and options. Components import the hook, never `useQuery` directly.

### 5.3 SSE

- **MUST** consume job progress through one `useJobProgress` hook owning connect, reconnect, and close. Components render progress; they don't manage sockets.
- **MUST** invalidate the affected query keys when a job completes — that's the handoff from the SSE stream back to Query.
- **NEVER** poll on an interval where SSE exists. **NEVER** put the `EventSource` in Redux or in Query.

### 5.4 The five states — staleness is one of them

- **MUST** handle **loading / error / empty / stale / loaded** on every screen that reads the API. An "empty" scan result is a normal Tuesday and gets a designed screen, not a blank div.
- **MUST** treat **stale** as first-class, with its own component. Stale data blocks planning: refuse, explain, offer to run the update. Before ~18:30 IST, say today's bhavcopy isn't published yet — **NEVER** render yesterday's numbers as if they were today's. ([ADR-11](decisions.md))
- **MUST** make **"While you were away"** the landing content whenever the gap is >1 session — first thing on screen, not a table to scroll to.
- **MUST** derive staleness from what the **server** says about the data's session date. **NEVER** from `Date.now()` in a component — the PC is off half the time, so the browser clock has no idea what the last session was.

---

## 6. shadcn/ui + Tailwind v4

### 6.1 shadcn — vendored, therefore yours

- **MUST** add primitives with the CLI (`npx shadcn@latest add button`) rather than hand-copying from a blog. They land in `components/ui/` and **you own them** — that's the point of shadcn, not an accident.
- **MUST** keep `components/ui/` for **unmodified-in-spirit primitives**. Domain components (`CandidateRow`, `MarketGateBanner`) live in `components/`, built *from* those primitives. A trading rule inside `components/ui/button.jsx` is unfindable forever.
- **MUST** edit the primitive when a genuine app-wide change is needed — that's allowed, it's your file. **NEVER** fork it into `button-2.jsx` / `CustomButton` for one screen.
- **MUST** extend variants through the primitive's **CVA config**, not a pile of `className` overrides at call sites. One `variant="destructive"` beats twelve hand-tuned class strings.
- **MUST** use `cn()` (clsx + tailwind-merge) for conditional classes. **NEVER** template-string classnames — precedence conflicts resolve by source order and produce "the class is there but doesn't apply".
- **NEVER** construct class names dynamically from data (`` `text-${color}-500` ``). Tailwind scans source statically; the class won't exist in the build. Map to whole class strings.

### 6.2 Tailwind v4 — tokens live in CSS

Tailwind v4 is **CSS-first**: there is no `tailwind.config.js`. Configuration is `@theme` in `index.css`, and shadcn's theming is CSS variables.

- **MUST** define every colour, radius, and spacing token in **`@theme`**, once. Light and dark both.
- **NEVER** write a raw hex, `rgb()`, or arbitrary value (`bg-[#26a69a]`, `text-[13.5px]`) in a component. A literal in JSX is a token that escaped, and the next screen won't match it.
- **MUST** express semantic intent, not appearance: `bg-destructive`, `text-muted-foreground`. **NEVER** `bg-red-500` for "a stop was hit" — the meaning is what's reused, and it's what changes when the palette does.
- **MUST** define domain-signal colours as their own tokens (`--color-up`, `--color-down`, `--color-regime-bad`). They're read by both Tailwind classes and the chart (§9.3), so they can only live in one place.
- **MUST** use `@import "tw-animate-css"`. `tailwindcss-animate` is deprecated for v4.
- **SHOULD** keep dark mode automatic via the `@theme` variable pattern rather than per-component `dark:` chains. A `dark:` variant on every element is the CSS-variable layer being bypassed.

---

## 7. TanStack Table

- **MUST** use TanStack Table for anything with sorting, filtering, pagination, or column controls — candidates, watchlist, positions, journal, tax lots. **NEVER** hand-roll sort state onto a `<table>`; you will get the third feature wrong.
- **MUST** render through shadcn's table primitives. The library is **headless** — it owns state and logic, not markup. Bringing another table's CSS defeats both.
- **MUST** define `columns` **outside** the component, or memoised. A `columns` array rebuilt every render resets internal table state — this is real, the compiler does not cover it, and it presents as "sorting randomly resets".
- **MUST** put `accessorKey` on the **real term** and translate in `header` via `<Term>`. The column knows `rvol`; the header says the plain phrase. ([ADR-6](decisions.md), §8)
- **MUST** format in `cell`, using the shared formatters (§2.1). **NEVER** paise→rupee arithmetic inline in a cell.
- **MUST** give `getRowId` a domain id (`row.symbol`). Row selection keyed by index breaks the moment a sort or filter runs.
- **SHOULD** keep client-side sorting/filtering — ~2,000 symbols filtered to 10–40 candidates ([platform-plan.md](../../platform-plan.md) §1) is nothing for the browser, and a round trip per sort click on a local box is latency for no gain.
- **MUST** switch to manual/server-side pagination only for genuinely large sets (full symbol master, multi-year journal), and then **MUST** set `manualPagination`/`manualSorting` and put the params **in the query key** (§5.2). Half-manual tables silently sort one page.
- **MUST** keep **user-facing** table state (visible columns, active filters) in Redux if it must survive navigation — but the **rows** stay in Query. §4.1.

---

## 8. Language layer — the one rule that can't be retrofitted

- **MUST** render every domain term through `<Term>` / `terms.js`. **NEVER** hardcode plain English for a real term in a component, a column header, a chart legend, or a toast.
- **MUST** keep real terms in props, state, query keys, API payloads, and variable names. `ema20` travels through the code; "the 20-day average line" appears only at the last inch. ([ADR-6](decisions.md))
- **MUST** add the `terms.js` entry in the **same change** that puts a new domain term on screen. A term shipped without its dictionary entry is a permanent inconsistency — this layer is built in phase 1 precisely because bolting it onto eight phases of finished screens means rewriting all of them.

---

## 9. Charts

- **MUST** wrap Lightweight Charts in one component owning the imperative lifecycle: create on mount, `applyOptions`/`setData` on prop change, `remove()` on unmount. **NEVER** create a chart in a component that also fetches or filters.
- **MUST** hold the chart instance in a `ref`, never in state — writing an imperative handle to state re-renders on every tick.
- **MUST** feed it data already shaped by the API/formatters. No indicator maths in the chart component. ([ADR-1](decisions.md))
- **MUST** read chart colours from the **`@theme` CSS variables** (§6.2) via `getComputedStyle`, not from hardcoded hex. Lightweight Charts is canvas — Tailwind classes cannot reach it, which makes it the one place a literal will *seem* justified. It isn't: hardcode here and the chart is the one thing that doesn't change with the theme.
- **MUST** `remove()` on unmount **and** on symbol change. Leaked chart instances are the fastest way to make this app feel broken.

---

## 10. Accessibility, forms, quality

- **MUST** use semantic elements and shadcn primitives (Radix underneath) rather than reinventing. A `<div onClick>` is not a button: no keyboard, no focus, no role.
- **MUST** label every input and tie errors to their field.
- **MUST** keep any override flow ([ADR-7](decisions.md)) explicit: a typed reason, no default text, visible logging. Overrides exist for judgement calls, and the journal must be able to answer whether overriding made money — an override that's one easy click gets clicked without thought and poisons that data.
- **MUST** surface the API's error `code`, not a generic "Something went wrong". The user of this platform is also its developer; a rejection should say which rule fired and why.
- **MUST** never block the UI on a job; SSE progress exists for this.
- **SHOULD** test by **behaviour** (React Testing Library): render, act as a user, assert what a user sees. **NEVER** assert internal state or a snapshot blob — snapshots test that nothing changed, which isn't the same as being right.
- **MUST** test the states nobody demos: stale, gap >1 session, empty scan, rejected guardrail. Those carry the domain.
- **SHOULD** wrap components under test in a fresh `QueryClient` per test with `retry: false`. A shared client leaks cache between tests and makes failures order-dependent.

---

## 11. Checklist before you call frontend work done

- [ ] No library added that overlaps a locked lane (§1).
- [ ] No server data in Redux; no `dispatch` copying query data into a slice.
- [ ] Query keys come from the factory and contain **every** input the request depends on.
- [ ] Mutations invalidate; no hand-written cache shapes; no optimistic guardrail paths.
- [ ] Axios only from `api/` modules; Query's `signal` forwarded; errors normalised in one interceptor.
- [ ] Loading / error / empty / **stale** / loaded all handled; staleness derived from the server's session date, not the browser clock.
- [ ] Gap >1 session shows "While you were away" first.
- [ ] No plain-English domain term outside `terms.js` / `<Term>` — components, headers, legends, toasts included.
- [ ] No rule, threshold, or derived number recomputed client-side.
- [ ] Every effect synchronises an external system, and every one cleans up.
- [ ] No `useMemo`/`useCallback`/`memo` added without a profiling note (Table `columns` and `createSelector` excepted).
- [ ] No props/server data mirrored into state; no index keys; `getRowId` is a domain id.
- [ ] Table `columns` defined outside the component; manual pagination params in the query key.
- [ ] No hex, arbitrary value, or dynamic class-name construction; semantic tokens only; `cn()` for conditionals.
- [ ] shadcn primitives edited in place, not forked; domain logic out of `components/ui/`.
- [ ] Chart instance in a ref; colours read from CSS variables; `remove()` on unmount and symbol change.
- [ ] Behaviour tests cover stale, gap, empty, and rejected-guardrail paths.

---

## Sources

Internal — these override anything below: [`decisions.md`](decisions.md), [`structure.md`](structure.md), [`terms.md`](terms.md), [`platform-plan.md`](../../platform-plan.md) (§5 plain-language spec). Backend counterpart: [`engineering-standards.md`](engineering-standards.md).

External research informing §2–§7:

- [Rules of React — react.dev](https://react.dev/reference/rules)
- [React v19 — react.dev](https://react.dev/blog/2024/12/05/react-19)
- [React 19 Hooks: The Modern Mental Model in the Compiler Era — AI Wisdom](https://www.aiwisdom.dev/articles/frontend-react/hooks)
- [Does TanStack Query replace Redux, MobX or other global state managers? — TanStack Query v5 docs](https://tanstack.com/query/v5/docs/framework/react/guides/does-this-replace-client-state)
- [State Management in 2026: Redux vs Context vs TanStack Query — DEV](https://dev.to/iamsaadmehmood/state-management-in-2026-redux-vs-context-vs-tanstack-query-1b0b)
- [State Management with TanStack Query and Redux — Nx Blog](https://nx.dev/blog/state-management-nx-react-native-expo-apps-with-tanstack-query-and-redux)
- [Tailwind v4 — shadcn/ui docs](https://ui.shadcn.com/docs/tailwind-v4)
- [Vite installation — shadcn/ui docs](https://ui.shadcn.com/docs/installation/vite)
- [Hooks Pattern — patterns.dev](https://www.patterns.dev/react/hooks-pattern/)
