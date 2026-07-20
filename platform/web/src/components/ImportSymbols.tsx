import { useEffect, useMemo, useRef, useState } from "react"
import { api, type ImportedSymbol, type LookupResult, type SavedImportSummary } from "@/lib/api"
import { parseChartinkCsv, parseSymbolInput, type CsvRow } from "@/lib/csv"
import { nextSortDir, sortRows, type SortDir } from "@/lib/tableSort"
import { usePagination } from "@/lib/pagination"
import { useWatchlist } from "@/lib/watchlist"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Upload, FileUp, Loader2, ExternalLink, TrendingUp, TrendingDown, Minus,
  ArrowUp, ArrowDown, ChevronsUpDown, X, Save, FolderOpen, Trash2, Check,
  Bookmark, BookmarkCheck, ChevronLeft, ChevronRight,
} from "lucide-react"

/** "Jul 14–18 import" — this week's Mon-Fri, editable before saving. */
function defaultImportName(): string {
  const now = new Date()
  const day = now.getDay()
  const monday = new Date(now)
  monday.setDate(now.getDate() - ((day + 6) % 7))
  const friday = new Date(monday)
  friday.setDate(monday.getDate() + 4)
  const fmt = (d: Date) => d.toLocaleDateString("en-IN", { month: "short", day: "numeric" })
  return `${fmt(monday)}–${fmt(friday)} import`
}

function relativeDate(iso: string): string {
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins} min ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return days === 1 ? "yesterday" : `${days} days ago`
}

function tradingViewUrl(symbol: string): string {
  return `https://www.tradingview.com/chart/?symbol=NSE:${encodeURIComponent(symbol)}`
}

function uniqueSorted(values: (string | undefined | null)[]): string[] {
  return [...new Set(values.filter((v): v is string => !!v))].sort()
}

const fieldClass = "border-input bg-background h-8 rounded-md border px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"

function IndustryTrend({ row }: { row: ImportedSymbol }) {
  if (row.industry_trending === null || row.industry_trending === undefined) {
    return <span className="text-muted-foreground inline-flex items-center gap-1"><Minus className="size-3.5" />—</span>
  }
  const pct = row.industry_pct_above_50
  if (row.industry_trending) {
    return (
      <span className="inline-flex items-center gap-1 text-green-600 dark:text-green-500">
        <TrendingUp className="size-3.5" />{pct}%
      </span>
    )
  }
  return (
    <span className="text-muted-foreground inline-flex items-center gap-1">
      <TrendingDown className="size-3.5" />{pct}%
    </span>
  )
}

function BookmarkCell({ symbol, watchlist, onToggle }: {
  symbol: string; watchlist: Set<string>; onToggle: (symbol: string) => void
}) {
  const on = watchlist.has(symbol)
  return (
    <td className="w-8 px-2 py-1.5 text-center">
      <button
        onClick={() => onToggle(symbol)}
        title={on ? "Remove from watchlist" : "Add to watchlist"}
        className={cn("transition-colors", on ? "text-amber-500" : "text-muted-foreground/50 hover:text-muted-foreground")}
      >
        {on ? <BookmarkCheck className="size-4 fill-amber-500/20" /> : <Bookmark className="size-4" />}
      </button>
    </td>
  )
}

function StockCell({ symbol, name }: { symbol: string; name?: string }) {
  return (
    <td className="px-3 py-1.5">
      <a href={tradingViewUrl(symbol)} target="_blank" rel="noopener noreferrer"
         className="inline-flex items-center gap-1 font-medium hover:underline">
        {symbol}
        <ExternalLink className="size-3 opacity-50" />
      </a>
      {name && <span className="text-muted-foreground ml-1.5 text-xs">{name}</span>}
    </td>
  )
}

/** Clickable column header — click to sort ascending, again for descending, again
 * to clear. One shared header for both tables below, keyed on each row type's own
 * field names via the generic `K`. */
function SortTh<K extends string>({ label, sortKey, activeKey, dir, onSort, align = "left" }: {
  label: string; sortKey: K; activeKey: K | null; dir: SortDir
  onSort: (key: K) => void; align?: "left" | "right"
}) {
  const active = activeKey === sortKey
  return (
    <th
      onClick={() => onSort(sortKey)}
      className={cn("cursor-pointer px-3 py-2 text-left font-medium select-none", align === "right" && "text-right")}
    >
      <span className={cn("inline-flex items-center gap-1", align === "right" && "flex-row-reverse")}>
        {label}
        {active
          ? dir === "asc" ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" />
          : <ChevronsUpDown className="size-3 opacity-30" />}
      </span>
    </th>
  )
}

function Toolbar({ search, onSearch, filters, count, total, onClear, watchlistOnly, onToggleWatchlistOnly }: {
  search: string; onSearch: (v: string) => void
  filters: { label: string; value: string; onChange: (v: string) => void; options: string[] }[]
  count: number; total: number; onClear: () => void
  watchlistOnly: boolean; onToggleWatchlistOnly: () => void
}) {
  const active = search !== "" || filters.some((f) => f.value !== "all") || watchlistOnly
  return (
    <div className="flex flex-wrap items-center gap-2 border-b p-3">
      <input
        value={search}
        onChange={(e) => onSearch(e.target.value)}
        placeholder="Search symbol or name…"
        className={cn(fieldClass, "min-w-[180px] flex-1")}
      />
      {filters.map((f) => (
        <select key={f.label} value={f.value} onChange={(e) => f.onChange(e.target.value)}
                className={cn(fieldClass, "capitalize")}>
          <option value="all">All {f.label}</option>
          {f.options.map((o) => <option key={o} value={o} className="capitalize">{o}</option>)}
        </select>
      ))}
      <Button variant={watchlistOnly ? "default" : "outline"} size="sm" onClick={onToggleWatchlistOnly}>
        {watchlistOnly ? <BookmarkCheck className="size-3.5" /> : <Bookmark className="size-3.5" />}
        Watchlist
      </Button>
      <span className="text-muted-foreground text-xs whitespace-nowrap">{count} of {total}</span>
      {active && (
        <Button variant="ghost" size="sm" onClick={onClear}><X className="size-3.5" />Clear</Button>
      )}
    </div>
  )
}

function Pager({ page, pageCount, onPage }: { page: number; pageCount: number; onPage: (p: number) => void }) {
  if (pageCount <= 1) return null
  return (
    <div className="flex items-center justify-end gap-2 border-t px-3 py-2">
      <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        <ChevronLeft className="size-3.5" />
      </Button>
      <span className="text-muted-foreground text-xs">Page {page} of {pageCount}</span>
      <Button variant="outline" size="sm" disabled={page >= pageCount} onClick={() => onPage(page + 1)}>
        <ChevronRight className="size-3.5" />
      </Button>
    </div>
  )
}

/** Straight from the Chartink export — no lookup against our own data, so this
 * renders instantly and shows exactly what Chartink gave us (as of export time). */
function CsvTable({ rows, watchlist, onToggleWatchlist }: {
  rows: CsvRow[]; watchlist: Set<string>; onToggleWatchlist: (symbol: string) => void
}) {
  const [search, setSearch] = useState("")
  const [sector, setSector] = useState("all")
  const [cap, setCap] = useState("all")
  const [watchlistOnly, setWatchlistOnly] = useState(false)
  const [sortKey, setSortKey] = useState<keyof CsvRow | null>(null)
  const [sortDir, setSortDir] = useState<SortDir>(null)

  const sectors = useMemo(() => uniqueSorted(rows.map((r) => r.sector)), [rows])
  const caps = useMemo(() => uniqueSorted(rows.map((r) => r.marketcap)), [rows])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return rows.filter((r) => {
      if (sector !== "all" && r.sector !== sector) return false
      if (cap !== "all" && r.marketcap !== cap) return false
      if (watchlistOnly && !watchlist.has(r.symbol)) return false
      if (q && !r.symbol.toLowerCase().includes(q) && !(r.name ?? "").toLowerCase().includes(q)) return false
      return true
    })
  }, [rows, sector, cap, watchlistOnly, watchlist, search])

  const sorted = useMemo(() => sortRows(filtered, sortKey, sortDir), [filtered, sortKey, sortDir])
  const { page, pageCount, pageRows, setPage } = usePagination(sorted)

  function onSort(key: keyof CsvRow) {
    if (sortKey !== key) { setSortKey(key); setSortDir("asc"); return }
    const next = nextSortDir(sortDir)
    setSortDir(next)
    if (!next) setSortKey(null)
  }

  function clear() { setSearch(""); setSector("all"); setCap("all"); setWatchlistOnly(false) }

  return (
    <Card>
      <Toolbar
        search={search} onSearch={setSearch}
        filters={[
          { label: "industries", value: sector, onChange: setSector, options: sectors },
          { label: "caps", value: cap, onChange: setCap, options: caps },
        ]}
        watchlistOnly={watchlistOnly} onToggleWatchlistOnly={() => setWatchlistOnly((v) => !v)}
        count={sorted.length} total={rows.length} onClear={clear}
      />
      <CardContent className="p-0">
        <div className="max-h-[70vh] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/60 text-muted-foreground sticky top-0 text-xs">
              <tr>
                <th className="w-8"></th>
                <th className="w-10 px-3 py-2 text-left font-medium">#</th>
                <SortTh label="Stock" sortKey="symbol" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortTh label="Industry" sortKey="sector" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortTh label="Cap" sortKey="marketcap" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortTh label="Price" sortKey="close" activeKey={sortKey} dir={sortDir} onSort={onSort} align="right" />
                <SortTh label="% chg" sortKey="changePct" activeKey={sortKey} dir={sortDir} onSort={onSort} align="right" />
                <SortTh label="Volume" sortKey="volume" activeKey={sortKey} dir={sortDir} onSort={onSort} align="right" />
              </tr>
            </thead>
            <tbody>
              {pageRows.map((r, i) => (
                <tr key={r.symbol + i} className="border-t">
                  <BookmarkCell symbol={r.symbol} watchlist={watchlist} onToggle={onToggleWatchlist} />
                  <td className="text-muted-foreground px-3 py-1.5">{(page - 1) * 10 + i + 1}</td>
                  <StockCell symbol={r.symbol} name={r.name} />
                  <td className="text-muted-foreground px-3 py-1.5">{r.sector ?? "—"}</td>
                  <td className="text-muted-foreground px-3 py-1.5">{r.marketcap ?? "—"}</td>
                  <td className="px-3 py-1.5 text-right tabular-nums">
                    {r.close != null ? `₹${r.close.toLocaleString("en-IN")}` : "—"}
                  </td>
                  <td className={cn("px-3 py-1.5 text-right tabular-nums",
                    r.changePct != null && (r.changePct >= 0
                      ? "text-green-600 dark:text-green-500" : "text-red-600 dark:text-red-400"))}>
                    {r.changePct != null ? `${r.changePct > 0 ? "+" : ""}${r.changePct}%` : "—"}
                  </td>
                  <td className="px-3 py-1.5 text-right tabular-nums">
                    {r.volume != null ? r.volume.toLocaleString("en-IN") : "—"}
                  </td>
                </tr>
              ))}
              {sorted.length === 0 && (
                <tr><td colSpan={8} className="text-muted-foreground px-3 py-6 text-center">No matches.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <Pager page={page} pageCount={pageCount} onPage={setPage} />
      </CardContent>
    </Card>
  )
}

/** From a plain symbol paste (no attached data) — we look up price/sector/trend
 * against our own DB, since the paste carries nothing but names. */
function LookupTable({ result, watchlist, onToggleWatchlist }: {
  result: LookupResult; watchlist: Set<string>; onToggleWatchlist: (symbol: string) => void
}) {
  const [search, setSearch] = useState("")
  const [sector, setSector] = useState("all")
  const [trend, setTrend] = useState("all")
  const [watchlistOnly, setWatchlistOnly] = useState(false)
  const [sortKey, setSortKey] = useState<keyof ImportedSymbol | null>(null)
  const [sortDir, setSortDir] = useState<SortDir>(null)

  const sectors = useMemo(() => uniqueSorted(result.rows.map((r) => r.sector)), [result.rows])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return result.rows.filter((r) => {
      if (sector !== "all" && r.sector !== sector) return false
      if (trend === "trending" && r.industry_trending !== true) return false
      if (trend === "weak" && r.industry_trending !== false) return false
      if (watchlistOnly && !watchlist.has(r.symbol)) return false
      if (q && !r.symbol.toLowerCase().includes(q) && !(r.name ?? "").toLowerCase().includes(q)) return false
      return true
    })
  }, [result.rows, sector, trend, watchlistOnly, watchlist, search])

  const sorted = useMemo(() => sortRows(filtered, sortKey, sortDir), [filtered, sortKey, sortDir])
  const { page, pageCount, pageRows, setPage } = usePagination(sorted)

  function onSort(key: keyof ImportedSymbol) {
    if (sortKey !== key) { setSortKey(key); setSortDir("asc"); return }
    const next = nextSortDir(sortDir)
    setSortDir(next)
    if (!next) setSortKey(null)
  }

  function clear() { setSearch(""); setSector("all"); setTrend("all"); setWatchlistOnly(false) }

  return (
    <Card>
      <Toolbar
        search={search} onSearch={setSearch}
        filters={[
          { label: "industries", value: sector, onChange: setSector, options: sectors },
          { label: "trend", value: trend, onChange: setTrend, options: ["trending", "weak"] },
        ]}
        watchlistOnly={watchlistOnly} onToggleWatchlistOnly={() => setWatchlistOnly((v) => !v)}
        count={sorted.length} total={result.rows.length} onClear={clear}
      />
      <CardContent className="p-0">
        <div className="max-h-[70vh] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/60 text-muted-foreground sticky top-0 text-xs">
              <tr>
                <th className="w-8"></th>
                <th className="w-10 px-3 py-2 text-left font-medium">#</th>
                <SortTh label="Stock" sortKey="symbol" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortTh label="Industry" sortKey="sector" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortTh label="Trend" sortKey="industry_pct_above_50" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortTh label="Price" sortKey="close" activeKey={sortKey} dir={sortDir} onSort={onSort} align="right" />
                <th className="px-3 py-2 text-center font-medium">Above trend line</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map((r, i) => (
                <tr key={r.symbol} className="border-t">
                  <BookmarkCell symbol={r.symbol} watchlist={watchlist} onToggle={onToggleWatchlist} />
                  <td className="text-muted-foreground px-3 py-1.5">{(page - 1) * 10 + i + 1}</td>
                  <StockCell symbol={r.symbol} name={r.name} />
                  <td className="text-muted-foreground px-3 py-1.5">{r.sector ?? "—"}</td>
                  <td className="px-3 py-1.5"><IndustryTrend row={r} /></td>
                  <td className="px-3 py-1.5 text-right tabular-nums">₹{r.close.toLocaleString("en-IN")}</td>
                  <td className="px-3 py-1.5 text-center">
                    {r.above_ema50 === null ? (
                      <span className="text-muted-foreground">—</span>
                    ) : r.above_ema50 ? (
                      <span className="text-green-600 dark:text-green-500">Yes</span>
                    ) : (
                      <span className="text-muted-foreground">No</span>
                    )}
                  </td>
                </tr>
              ))}
              {sorted.length === 0 && (
                <tr><td colSpan={7} className="text-muted-foreground px-3 py-6 text-center">No matches.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <Pager page={page} pageCount={pageCount} onPage={setPage} />
      </CardContent>
    </Card>
  )
}

function SaveBar({ suggestedName, onSave, saving, saved }: {
  suggestedName: string; onSave: (name: string) => void; saving: boolean; saved: boolean
}) {
  const [name, setName] = useState(suggestedName)
  return (
    <div className="flex items-center gap-2">
      <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name this import…"
             className={cn(fieldClass, "min-w-[220px] flex-1 max-w-sm")} />
      <Button size="sm" onClick={() => onSave(name)} disabled={saving || !name.trim()}>
        {saving ? <Loader2 className="size-3.5 animate-spin" /> : saved ? <Check className="size-3.5" /> : <Save className="size-3.5" />}
        {saving ? "Saving…" : saved ? "Saved" : "Save for later"}
      </Button>
    </div>
  )
}

function SavedImportsList({ imports, onLoad, onDelete, loadingId }: {
  imports: SavedImportSummary[]; onLoad: (id: string) => void; onDelete: (id: string) => void
  loadingId: string | null
}) {
  if (imports.length === 0) return null
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Saved imports</CardTitle>
      </CardHeader>
      <CardContent className="divide-y p-0">
        {imports.map((imp) => (
          <div key={imp.id} className="flex items-center gap-2 px-4 py-2">
            <FolderOpen className="text-muted-foreground size-4 shrink-0" />
            <span className="flex-1 truncate text-sm font-medium">{imp.name}</span>
            <span className="text-muted-foreground text-xs">
              {imp.row_count} stocks · {imp.source === "csv" ? "CSV" : "pasted"} · {relativeDate(imp.created_at)}
            </span>
            <Button variant="outline" size="sm" disabled={loadingId === imp.id} onClick={() => onLoad(imp.id)}>
              {loadingId === imp.id ? <Loader2 className="size-3.5 animate-spin" /> : "Load"}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => onDelete(imp.id)}>
              <Trash2 className="text-muted-foreground size-3.5" />
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

export function ImportSymbols() {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Only one of these is populated at a time — whichever import ran last.
  const [result, setResult] = useState<LookupResult | null>(null)
  const [csvRows, setCsvRows] = useState<CsvRow[] | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [savedImports, setSavedImports] = useState<SavedImportSummary[]>([])
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const [importVersion, setImportVersion] = useState(0)   // bump on each new import -> fresh SaveBar
  const { watchlist, toggleWatchlist } = useWatchlist()
  const [saveBarName, setSaveBarName] = useState(defaultImportName())

  const symbols = parseSymbolInput(text)

  function refreshSaved() {
    api.listImports().then((r) => r && setSavedImports(r)).catch(() => {})
  }
  useEffect(refreshSaved, [])

  async function doImport() {
    if (symbols.length === 0) return
    setLoading(true)
    setError(null)
    try {
      setResult(await api.lookupSymbols(symbols))
      setCsvRows(null)
      setSaved(false)
      setSaveBarName(defaultImportName())
      setImportVersion((v) => v + 1)
      setOpen(false)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ""   // allow picking the same file again
    if (!file) return
    setError(null)
    try {
      const rows = parseChartinkCsv(await file.text())
      if (rows.length === 0) {
        setError("Couldn't find a symbol column in that file — check it's a Chartink export.")
        return
      }
      setCsvRows(rows)     // renders straight from the file, no lookup
      setResult(null)
      setSaved(false)
      setSaveBarName(defaultImportName())
      setImportVersion((v) => v + 1)
      setOpen(false)
    } catch {
      setError("Couldn't read that file.")
    }
  }

  async function doSave(name: string) {
    const rows = csvRows ?? result?.rows
    const source = csvRows ? "csv" : "paste"
    if (!rows || rows.length === 0) return
    setSaving(true)
    try {
      await api.saveImport(name, source, rows)
      setSaved(true)
      refreshSaved()
    } catch (e) {
      setError(String(e))
    } finally {
      setSaving(false)
    }
  }

  async function doLoad(id: string) {
    setLoadingId(id)
    setError(null)
    try {
      const doc = await api.getImport(id)
      if (!doc) return
      if (doc.source === "csv") {
        setCsvRows(doc.rows as unknown as CsvRow[])
        setResult(null)
      } else {
        setResult({ requested: doc.rows.length, found: doc.rows.length, not_found: [],
                   rows: doc.rows as unknown as ImportedSymbol[] })
        setCsvRows(null)
      }
      setSaved(true)   // already saved, this is the saved copy
      setSaveBarName(doc.name)
      setImportVersion((v) => v + 1)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoadingId(null)
    }
  }

  async function doDelete(id: string) {
    try {
      await api.deleteImport(id)
      refreshSaved()
    } catch (e) {
      setError(String(e))
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Button variant="outline" onClick={() => fileInput.current?.click()}>
          <FileUp className="size-4" />
          Upload Chartink CSV
        </Button>
        <input ref={fileInput} type="file" accept=".csv,text/csv" onChange={onFile} className="hidden" />
        <Button variant={open ? "secondary" : "ghost"} onClick={() => setOpen((o) => !o)}>
          <Upload className="size-4" />
          Or paste a symbol list
        </Button>
        {csvRows && <span className="text-muted-foreground text-sm">{csvRows.length} loaded from CSV</span>}
        {result && (
          <span className="text-muted-foreground text-sm">
            {result.found} of {result.requested} loaded
            {result.not_found.length > 0 && <> · {result.not_found.length} not found</>}
          </span>
        )}
      </div>

      {open && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Paste a symbol list</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-muted-foreground text-xs">
              No file to upload? Paste comma-separated symbols and we'll look up price, sector, and
              trend from our own data. Uploading the CSV directly above is faster and needs no lookup.
            </p>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="RELAXO, RESPONIND, ECLERX, PAR, FINOPB..."
              rows={5}
              className="border-input bg-background w-full resize-y rounded-lg border px-3 py-2 font-mono text-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
            />
            <div className="flex items-center gap-2">
              <Button onClick={doImport} disabled={loading || symbols.length === 0}>
                {loading ? <Loader2 className="size-4 animate-spin" /> : <Upload className="size-4" />}
                {loading ? "Loading…" : `Look up ${symbols.length || ""} symbols`}
              </Button>
              <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            </div>
            {error && <p className="text-sm text-red-600 dark:text-red-400">Problem: {error}</p>}
          </CardContent>
        </Card>
      )}

      {error && !open && <p className="text-sm text-red-600 dark:text-red-400">Problem: {error}</p>}

      {(csvRows?.length || result?.rows.length) ? (
        <SaveBar key={importVersion} suggestedName={saveBarName} onSave={doSave} saving={saving} saved={saved} />
      ) : null}

      {csvRows && csvRows.length > 0 && (
        <CsvTable rows={csvRows} watchlist={watchlist} onToggleWatchlist={toggleWatchlist} />
      )}
      {result && result.rows.length > 0 && (
        <LookupTable result={result} watchlist={watchlist} onToggleWatchlist={toggleWatchlist} />
      )}

      {result && result.not_found.length > 0 && (
        <p className="text-muted-foreground text-xs">
          Not found in our data: {result.not_found.join(", ")}
        </p>
      )}

      <SavedImportsList imports={savedImports} onLoad={doLoad} onDelete={doDelete} loadingId={loadingId} />
    </div>
  )
}
