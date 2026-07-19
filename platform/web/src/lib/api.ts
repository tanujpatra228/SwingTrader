// Typed client for the worker API. Components never call fetch directly
// (frontend-standards §1.1). Dev calls go through Vite's /api proxy -> :8001.

export type Levels = {
  pivot: number; base_low: number; entry: number; stop: number; target: number
  risk_per_share: number; reward_per_share: number; lookback: number; is_estimate: boolean
}
export type Position = {
  qty: number; capital: number; risk_amount: number; account_pct: number; risk_pct_actual: number
}
export type Charges = { total: number; pct_of_buy: number; breakeven_move_pct: number; breakdown: Record<string, number> }

export type Candidate = {
  symbol: string; name?: string; sector?: string | null
  scans: string[]; scan_count: number; close: number; delivery_pct?: number | null
  wk_tight_pct?: number; dist_52wh_pct?: number; vol_dry?: number; tightness?: number
  levels: Levels; position: Position; charges: Charges | null
  tradeable: boolean; min_amount_ok?: boolean; min_amount_hint?: string
  forecast_profit_pre_tax?: number; forecast_loss_if_stopped?: number
}

export type Market = {
  verdict: "good" | "shaky" | "bad"
  max_exposure_pct: number; max_positions: number; max_risk_pct: number
  reasons: string[]; as_of: string; metrics: Record<string, number | null>
}

export type Screen = {
  market: Market; candidates: Candidate[]; dropped_summary: Record<string, number>
  universe_size: number; scan_hits?: number; after_junk?: number
  excluded_largecap?: number; excluded_price?: number; min_price?: number
  account: number; risk_pct: number
}

async function get<T>(path: string): Promise<T | null> {
  const r = await fetch(`/api${path}`)
  if (r.status === 404) return null
  if (!r.ok) throw new Error(`${path}: ${r.status}`)
  return r.json()
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`/api${path}`, {
    method: "POST",
    ...(body !== undefined && {
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  })
  if (!r.ok) throw new Error(`${path}: ${r.status}`)
  return r.json()
}

export type Routine = Record<string, string>  // item_id -> last_done ISO

export type ScanResult = {
  scan: string; label?: string; count: number; universe_size: number
  results: { symbol: string; name?: string; sector?: string | null; close: number; dist_52wh_pct?: number }[]
}

export type ImportedSymbol = {
  symbol: string; name?: string; sector?: string | null
  close: number; above_ema50: boolean | null
  industry_trending: boolean | null; industry_pct_above_50: number | null
  tier?: string | null
}
export type LookupResult = {
  requested: number; found: number; not_found: string[]; rows: ImportedSymbol[]
}

export const api = {
  health: () => get<{ status: string }>("/health"),
  getScreen: () => get<Screen>("/screen"),
  runScreen: () => post<Screen>("/screen/run"),
  getRoutine: () => get<Routine>("/routine"),
  markDone: (id: string) => post<{ item_id: string; last_done: string }>(`/routine/${id}/done`),
  runScan: (key: string) => post<ScanResult>(`/scan/${key}`),
  lookupSymbols: (symbols: string[]) => post<LookupResult>("/symbols/lookup", { symbols }),
}
