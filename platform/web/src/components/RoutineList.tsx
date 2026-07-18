import { Button } from "@/components/ui/button"
import type { RoutineItem } from "@/lib/routine"
import type { ScanResult } from "@/lib/api"
import { ExternalLink, Check, Play, Loader2 } from "lucide-react"

function ago(iso?: string): string {
  if (!iso) return "not yet"
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins} min ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return days === 1 ? "yesterday" : `${days} days ago`
}

type RowProps = {
  item: RoutineItem; last?: string; onDone: (id: string) => void
  onRun: (item: RoutineItem) => void; running: boolean; result?: ScanResult
}

function Row({ item, last, onDone, onRun, running, result }: RowProps) {
  const stale = !last || Date.now() - new Date(last).getTime() > 36 * 3600 * 1000
  return (
    <div className="py-2">
      <div className="flex items-center gap-2">
        <span className="flex-1 text-sm">{item.label}</span>
        <span className={`w-24 text-right text-xs ${stale ? "text-muted-foreground" : "text-green-600 dark:text-green-500"}`}>
          {ago(last)}
        </span>
        {item.scanKey && (
          <Button variant="default" size="sm" disabled={running} onClick={() => onRun(item)}>
            {running ? <Loader2 className="size-3.5 animate-spin" /> : <Play className="size-3.5" />}
            {running ? "Running…" : "Run scan"}
          </Button>
        )}
        {item.slug && (
          <a href={`https://chartink.com/screener/${item.slug}`} target="_blank" rel="noopener noreferrer">
            <Button variant="outline" size="sm"><ExternalLink className="size-3.5" />Open</Button>
          </a>
        )}
        <Button variant={stale ? "secondary" : "ghost"} size="sm" onClick={() => onDone(item.id)}>
          <Check className="size-3.5" />Done
        </Button>
      </div>
      {result && (
        <div className="bg-muted/40 mt-1.5 rounded-md p-2">
          <div className="text-muted-foreground mb-2 text-xs">
            <strong className="text-foreground">{result.count}</strong> stocks in a confirmed uptrend
            {" "}(from {result.universe_size} searched) — sorted by nearest to their 1-year high
          </div>
          <div className="max-h-80 overflow-y-auto rounded border">
            <table className="w-full text-xs">
              <thead className="bg-muted/60 text-muted-foreground sticky top-0">
                <tr className="[&>th]:px-2 [&>th]:py-1 [&>th]:text-left">
                  <th className="w-10">#</th>
                  <th>Stock</th>
                  <th>Industry</th>
                  <th className="text-right">Price</th>
                  <th className="text-right">From 1-yr high</th>
                </tr>
              </thead>
              <tbody>
                {result.results.map((s, i) => (
                  <tr key={s.symbol} className="border-t [&>td]:px-2 [&>td]:py-1">
                    <td className="text-muted-foreground">{i + 1}</td>
                    <td className="font-medium">
                      {s.symbol}
                      {s.name && <span className="text-muted-foreground ml-1 font-normal">· {s.name}</span>}
                    </td>
                    <td className="text-muted-foreground">{s.sector ?? "—"}</td>
                    <td className="text-right tabular-nums">₹{s.close.toLocaleString("en-IN")}</td>
                    <td className="text-right tabular-nums">
                      {s.dist_52wh_pct != null ? `${s.dist_52wh_pct.toFixed(1)}%` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

export function RoutineList({ items, rowProps }: {
  items: RoutineItem[]; rowProps: (it: RoutineItem) => RowProps
}) {
  return (
    <div className="divide-y">
      {items.map((it) => <Row key={it.id} {...rowProps(it)} />)}
    </div>
  )
}
