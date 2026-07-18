import { useState } from "react"
import type { Candidate } from "@/lib/api"
import { num, pct, rupees, rupees2 } from "@/lib/format"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"

// Steps 2-3 survivors with the trade numbers. entry/stop/target are tagged as
// estimates because the resting zone is a proxy (mvp.md).
export function CandidateTable({ candidates }: { candidates: Candidate[] }) {
  const [showAll, setShowAll] = useState(false)
  if (!candidates?.length) {
    return <div className="text-muted-foreground py-10 text-center">No stocks passed the search and filter this run.</div>
  }
  const shown = showAll ? candidates : candidates.slice(0, 25)

  return (
    <div>
      <div className="overflow-x-auto rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Stock</TableHead>
              <TableHead>Industry</TableHead>
              <TableHead className="text-right" title="How tight the last 3 weekly closes are — smaller is tighter">Tightness</TableHead>
              <TableHead className="text-right" title="Distance below its 1-year high">Near high</TableHead>
              <TableHead className="text-right" title="Recent volume vs its average — under 1 means quiet">Volume</TableHead>
              <TableHead className="text-right">
                Buy at<span className="block text-[10px] font-normal text-amber-500">estimate</span>
              </TableHead>
              <TableHead className="text-right">Exit if wrong</TableHead>
              <TableHead className="text-right">Take profit</TableHead>
              <TableHead className="text-right">Shares</TableHead>
              <TableHead className="text-right">Money in</TableHead>
              <TableHead className="text-right">If wrong</TableHead>
              <TableHead className="text-right">If right</TableHead>
              <TableHead className="text-right">Fees</TableHead>
              <TableHead className="text-right" title="How much it must rise just to cover fees">Breakeven</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {shown.map((c) => {
              const lv = c.levels
              const p = c.position
              const ch = c.charges
              return (
                <TableRow key={c.symbol} className={c.tradeable ? "" : "opacity-50"}>
                  <TableCell>
                    <div className="font-semibold">{c.symbol}</div>
                    <div className="text-muted-foreground max-w-[160px] truncate text-xs">{c.name}</div>
                  </TableCell>
                  <TableCell className="text-muted-foreground text-xs">{c.sector ?? "—"}</TableCell>
                  <TableCell className="text-right tabular-nums">{pct(c.wk_tight_pct, 1)}</TableCell>
                  <TableCell className="text-right tabular-nums">{pct(c.dist_52wh_pct, 0)}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {c.vol_dry != null ? `${c.vol_dry.toFixed(2)}×` : "—"}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{rupees2(lv.entry)}</TableCell>
                  <TableCell className="text-right tabular-nums text-red-500">{rupees2(lv.stop)}</TableCell>
                  <TableCell className="text-right tabular-nums text-emerald-500">{rupees2(lv.target)}</TableCell>
                  <TableCell className="text-right tabular-nums">{c.tradeable ? num(p.qty) : "—"}</TableCell>
                  <TableCell className="text-right tabular-nums">{c.tradeable ? rupees(p.capital) : "—"}</TableCell>
                  <TableCell className="text-right tabular-nums text-red-500">
                    {c.tradeable ? `−${rupees(c.forecast_loss_if_stopped)}` : "—"}
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-emerald-500">
                    {c.tradeable ? `+${rupees(c.forecast_profit_pre_tax)}` : "—"}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{c.tradeable && ch ? rupees2(ch.total) : "—"}</TableCell>
                  <TableCell className={`text-right tabular-nums ${c.min_amount_ok === false ? "text-amber-500" : ""}`}>
                    {c.tradeable && ch ? pct(ch.breakeven_move_pct) : "—"}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>

      {candidates.length > 25 && (
        <button className="text-muted-foreground hover:text-foreground mt-2 text-sm underline"
          onClick={() => setShowAll((v) => !v)}>
          {showAll ? "Show top 25" : `Show all ${candidates.length}`}
        </button>
      )}

      <p className="text-muted-foreground mt-3 text-xs">
        “Buy at”, “Exit if wrong” and “Take profit” are quick estimates from the last 10 days — a
        stand-in until the platform reads the chart properly. Shares are sized so a wrong trade loses
        at most your per-trade limit.
      </p>
    </div>
  )
}
