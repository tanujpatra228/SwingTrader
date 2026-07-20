import { useCallback, useEffect, useState } from "react"
import { api } from "@/lib/api"

/** Shared bookmark state — one fetch, one Set, usable by any table that shows a
 * symbol column. Optimistic toggle: flips locally immediately, reverts if the
 * request fails, so the icon never waits on a round-trip to respond. */
export function useWatchlist() {
  const [symbols, setSymbols] = useState<Set<string>>(new Set())

  useEffect(() => {
    api.getWatchlist().then((r) => r && setSymbols(new Set(r.map((e) => e.symbol)))).catch(() => {})
  }, [])

  const toggle = useCallback((symbol: string) => {
    setSymbols((prev) => {
      const had = prev.has(symbol)
      const next = new Set(prev)
      had ? next.delete(symbol) : next.add(symbol)
      ;(had ? api.removeFromWatchlist(symbol) : api.addToWatchlist(symbol)).catch(() => {
        // request failed -> put it back the way it was
        setSymbols((cur) => {
          const reverted = new Set(cur)
          had ? reverted.add(symbol) : reverted.delete(symbol)
          return reverted
        })
      })
      return next
    })
  }, [])

  return { watchlist: symbols, toggleWatchlist: toggle }
}
