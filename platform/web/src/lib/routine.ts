import { useEffect, useState } from "react"
import { api, type Routine, type ScanResult } from "@/lib/api"

// Ankur's routine. `slug` opens the matching Chartink scan; `scanKey` runs one of our
// own scans on our data and shows the result. Items with neither are mark-only (the
// watchlist/positions/journal features aren't built yet, but tracking that you did
// them elsewhere is still useful).
export type RoutineItem = { id: string; label: string; slug?: string; scanKey?: string }

export const WEEKEND_ITEMS: RoutineItem[] = [
  { id: "wk_stage2", label: "Run Stage 2 scan (established uptrends)", scanKey: "stage2" },
  { id: "wk_52w_high", label: "Stocks closing the week at 52-week highs", slug: "copy-copy-52w-1" },
  { id: "wk_big_movers", label: "Note the week's big movers", slug: "momentum-stocks-797" },
  { id: "wk_narrow_range", label: "Weekly narrow-range / inside-bar stocks (contraction)" },
]

export const DAILY_ITEMS: RoutineItem[] = [
  { id: "d_rc", label: "Run contraction scan (RC)", slug: "ema-scan-2-7" },
  { id: "d_re", label: "Run volume expansion scan (RE)", slug: "ankur-s-volume-scan" },
  { id: "d_watchlist", label: "Update watchlist" },
  { id: "d_positions", label: "Check open positions against their stops" },
  { id: "d_journal", label: "Journal every trade — entry reason, stop, result" },
]

/** Shared state + actions for a routine checklist — used by both Weekly Prep and
 * Trading Day pages so "done" timestamps and scan results live in one place. */
export function useRoutine() {
  const [done, setDone] = useState<Routine>({})
  const [results, setResults] = useState<Record<string, ScanResult>>({})
  const [running, setRunning] = useState<string | null>(null)

  useEffect(() => { api.getRoutine().then((r) => r && setDone(r)).catch(() => {}) }, [])

  async function mark(id: string) {
    const res = await api.markDone(id)
    setDone((d) => ({ ...d, [id]: res.last_done }))
  }

  async function run(item: RoutineItem) {
    if (!item.scanKey) return
    setRunning(item.id)
    try {
      const res = await api.runScan(item.scanKey)
      setResults((r) => ({ ...r, [item.id]: res }))
      await mark(item.id)            // running it counts as doing it
    } finally {
      setRunning(null)
    }
  }

  const rowProps = (it: RoutineItem) => ({
    item: it, last: done[it.id], onDone: mark, onRun: run,
    running: running === it.id, result: results[it.id],
  })

  return { rowProps }
}
