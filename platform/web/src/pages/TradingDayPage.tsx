import { useEffect, useState } from "react"
import { api, type Screen } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { MarketCard } from "@/components/MarketCard"
import { CandidateTable } from "@/components/CandidateTable"
import { RoutineList } from "@/components/RoutineList"
import { useRoutine, DAILY_ITEMS } from "@/lib/routine"
import { Loader2, Search, ChevronRight, ExternalLink } from "lucide-react"

const CHARTINK_SCANS = [
  { label: "Quietly contracting (RC1)", slug: "ema-scan-2-7" },
  { label: "Quietly contracting (RC2)", slug: "new-daily-2045" },
  { label: "Big-buyer volume", slug: "ankur-s-volume-scan" },
]

function Arrow() {
  return <ChevronRight className="text-muted-foreground size-4 shrink-0" />
}

function FunnelStep({ n, label, value, unit, hint, highlight }: {
  n?: string; label: string; value: number; unit?: string; hint?: string; highlight?: boolean
}) {
  return (
    <div className={`rounded-lg border px-3 py-2 ${highlight ? "border-primary bg-primary/5" : "bg-card"}`}>
      <div className="flex items-center gap-2">
        {n && <span className="bg-primary text-primary-foreground inline-grid size-5 place-items-center rounded-full text-xs">{n}</span>}
        <span className="text-muted-foreground">{label}</span>
        <strong className={highlight ? "text-primary text-base" : ""}>{value}</strong>
        {unit && <span className="text-muted-foreground text-xs">{unit}</span>}
      </div>
      {hint && <div className="text-muted-foreground mt-0.5 text-xs">{hint}</div>}
    </div>
  )
}

// Steps 1-3 of the evening routine + trade numbers, all on one page.
export function TradingDayPage() {
  const [screen, setScreen] = useState<Screen | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [learn, setLearn] = useState(true)
  const { rowProps } = useRoutine()

  useEffect(() => {
    api.getScreen().then(setScreen).catch((e) => setError(String(e)))
  }, [])

  async function run() {
    setRunning(true)
    setError(null)
    try {
      setScreen(await api.runScreen())
    } catch (e) {
      setError(String(e))
    } finally {
      setRunning(false)
    }
  }

  const drops = Object.entries(screen?.dropped_summary ?? {})

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Trading Day</h1>
          <p className="text-muted-foreground text-sm">
            Check the market → search → remove the junk → see the numbers.
          </p>
        </div>
        <div className="flex items-center gap-4">
          <label className="text-muted-foreground flex items-center gap-2 text-sm">
            <input type="checkbox" checked={learn} onChange={(e) => setLearn(e.target.checked)} />
            Learn mode
          </label>
          <Button onClick={run} disabled={running}>
            {running ? <Loader2 className="size-4 animate-spin" /> : <Search className="size-4" />}
            {running ? "Working…" : "Run the evening routine"}
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-muted-foreground text-xs">Cross-check on Chartink:</span>
        {CHARTINK_SCANS.map((s) => (
          <a key={s.slug} href={`https://chartink.com/screener/${s.slug}`} target="_blank" rel="noopener noreferrer">
            <Button variant="outline" size="sm">
              <ExternalLink className="size-3.5" />
              {s.label}
            </Button>
          </a>
        ))}
      </div>

      {error && (
        <div className="rounded-md bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-400">
          Problem: {error}. Is the worker running on port 8001?
        </div>
      )}

      {!screen && !error && (
        <div className="text-muted-foreground py-16 text-center">
          No run yet. Press “Run the evening routine”.
        </div>
      )}

      {screen && (
        <div className="space-y-5">
          <MarketCard market={screen.market} learn={learn} />

          {(screen.excluded_largecap || screen.excluded_price) ? (
            <p className="text-muted-foreground text-xs">
              Set aside before searching: <strong>{screen.excluded_largecap ?? 0}</strong> big
              companies (they move too slowly) and <strong>{screen.excluded_price ?? 0}</strong> priced
              under ₹{screen.min_price ?? 99}.
            </p>
          ) : null}
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <FunnelStep n="2" label="Searched" value={screen.universe_size} unit="stocks" />
            <Arrow />
            <FunnelStep label="Matched a scan" value={screen.scan_hits ?? screen.candidates.length} />
            <Arrow />
            <FunnelStep n="3" label="After junk removed" value={screen.after_junk ?? screen.candidates.length} highlight
              hint={drops.length ? `dropped ${drops.map(([k, v]) => `${v} ${k}`).join(", ")}` : undefined} />
          </div>
          <p className="text-muted-foreground text-xs">
            Sort by tightness, distance from the high, or volume to find the calmest setups near their
            highs — those are the ones worth reading charts on.
          </p>

          <CandidateTable candidates={screen.candidates} />
        </div>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Every trading day</CardTitle>
        </CardHeader>
        <CardContent>
          <RoutineList items={DAILY_ITEMS} rowProps={rowProps} />
        </CardContent>
      </Card>

      <footer className="text-muted-foreground border-t pt-4 text-xs">
        Numbers use a quick estimate of the resting zone (last 10 days), not a confirmed base.
        Not financial advice.
      </footer>
    </div>
  )
}
