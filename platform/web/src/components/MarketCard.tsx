import type { Market } from "@/lib/api"
import { pct, rupees } from "@/lib/format"
import { Card } from "@/components/ui/card"
import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react"

// Step 1 verdict. Plain wording; the real regime term rides alongside in muted text.
const LOOK = {
  good: { label: "Market looks good", real: "green", bar: "bg-emerald-500", Icon: CheckCircle2, icon: "text-emerald-500" },
  shaky: { label: "Market looks shaky", real: "caution", bar: "bg-amber-500", Icon: AlertTriangle, icon: "text-amber-500" },
  bad: { label: "Market looks bad", real: "red", bar: "bg-red-500", Icon: XCircle, icon: "text-red-500" },
} as const

export function MarketCard({ market, learn }: { market: Market; learn: boolean }) {
  const look = LOOK[market.verdict] ?? LOOK.shaky
  const m = market.metrics ?? {}
  const Icon = look.Icon

  return (
    <Card className="relative overflow-hidden p-5">
      <div className={`absolute top-0 bottom-0 left-0 w-1.5 ${look.bar}`} />
      <div className="flex flex-wrap items-start justify-between gap-3 pl-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Icon className={`size-5 ${look.icon}`} />
          {look.label}
          {learn && <span className="text-muted-foreground text-xs font-normal">regime: {look.real}</span>}
        </h2>
        <div className="text-muted-foreground text-sm">
          Invest up to <strong className="text-foreground">{market.max_exposure_pct}%</strong> · risk up to{" "}
          <strong className="text-foreground">{pct(market.max_risk_pct, 1)}</strong> per trade · max{" "}
          <strong className="text-foreground">{market.max_positions}</strong> trades
        </div>
      </div>

      <ul className="mt-3 list-disc space-y-1 pl-8 text-sm">
        {market.reasons?.map((r, i) => <li key={i}>{r}</li>)}
      </ul>

      <div className="text-muted-foreground mt-3 border-t pt-3 pl-3 text-xs">
        NIFTY {rupees(m.close)} · short-term line {rupees(m.ema20)} · trend line {rupees(m.ema50)}
        {m.breadth_pct_above_20 != null && <> · {m.breadth_pct_above_20}% of stocks healthy</>}
        {market.as_of && <> · as of {market.as_of}</>}
      </div>

      {market.verdict === "bad" && (
        <div className="mt-3 ml-3 rounded-md bg-amber-500/10 px-3 py-2 text-sm text-amber-600 dark:text-amber-400">
          The guide says sit in cash when the market looks bad. You can still build a watchlist below, but this is not the time to buy.
        </div>
      )}
    </Card>
  )
}
