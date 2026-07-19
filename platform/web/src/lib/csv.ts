// Chartink's CSV export column names vary by scan (some show "Symbol", others
// "Nsecode", custom scans can add arbitrary columns) — so instead of hardcoding
// one header name, match common aliases first, then fall back to picking whichever
// column's values look most like stock tickers.

const SYMBOL_HEADER_ALIASES = ["symbol", "nsecode", "nse code", "stock code", "scrip", "ticker", "scrip code"]

function parseCsvLine(line: string): string[] {
  const cells: string[] = []
  let cur = ""
  let inQuotes = false
  for (let i = 0; i < line.length; i++) {
    const c = line[i]
    if (inQuotes) {
      if (c === '"') {
        if (line[i + 1] === '"') { cur += '"'; i++ } else { inQuotes = false }
      } else cur += c
    } else if (c === '"') {
      inQuotes = true
    } else if (c === ",") {
      cells.push(cur); cur = ""
    } else {
      cur += c
    }
  }
  cells.push(cur)
  return cells.map((c) => c.trim())
}

function looksLikeSymbol(v: string): boolean {
  return /^[A-Z0-9&-]{1,20}$/.test(v.trim())
}

/** Parse CSV text and return just the symbol column, auto-detecting which one it is. */
export function extractSymbolsFromCsv(text: string): string[] {
  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)
  if (lines.length === 0) return []
  const rows = lines.map(parseCsvLine)
  const header = rows[0].map((h) => h.toLowerCase())

  let col = header.findIndex((h) => SYMBOL_HEADER_ALIASES.includes(h))
  const body = col >= 0 ? rows.slice(1) : rows   // no header match -> treat every row as data

  if (col < 0) {
    const width = Math.max(...rows.map((r) => r.length))
    let best = 0
    let bestScore = -1
    for (let c = 0; c < width; c++) {
      const score = body.filter((r) => r[c] && looksLikeSymbol(r[c])).length
      if (score > bestScore) { bestScore = score; best = c }
    }
    col = best
  }

  return body.map((r) => r[col]).filter(Boolean).map((s) => s.toUpperCase())
}

/** Accepts either a flat comma/newline symbol list OR pasted CSV content (header +
 * multiple columns) and returns symbols either way — one input, both paths. */
export function parseSymbolInput(raw: string): string[] {
  const firstLine = raw.split("\n")[0] ?? ""
  const looksLikeCsv = raw.includes("\n") && firstLine.split(",").length > 2
  if (looksLikeCsv) return extractSymbolsFromCsv(raw)
  return raw.split(/[,\n]/).map((s) => s.trim().toUpperCase()).filter(Boolean)
}

export type CsvRow = {
  symbol: string; name?: string; close?: number; changePct?: number
  volume?: number; sector?: string; marketcap?: string
}

const COLUMN_ALIASES: Record<keyof Omit<CsvRow, "symbol">, string[]> = {
  name: ["stock name", "name", "company", "company name"],
  close: ["close", "price", "ltp"],
  changePct: ["%_change", "% chg", "%chg", "change", "% change", "day_change%"],
  volume: ["volume", "vol"],
  sector: ["sector", "industry"],
  marketcap: ["marketcapname", "market cap name", "marketcap", "market cap"],
}

function num(v: string | undefined): number | undefined {
  if (!v) return undefined
  const n = parseFloat(v)
  return Number.isFinite(n) ? n : undefined
}

/** Parse a full Chartink CSV export into rows carrying every column it gave us —
 * no lookup against our own data. Chartink's own price/sector/volume at the
 * moment you exported, used as-is. Only `symbol` is guaranteed present. */
export function parseChartinkCsv(text: string): CsvRow[] {
  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)
  if (lines.length === 0) return []
  const rows = lines.map(parseCsvLine)
  const header = rows[0].map((h) => h.toLowerCase())

  const symbolCol = header.findIndex((h) => SYMBOL_HEADER_ALIASES.includes(h))
  if (symbolCol < 0) {
    // no recognizable header at all -> fall back to symbol-only extraction
    return extractSymbolsFromCsv(text).map((symbol) => ({ symbol }))
  }

  const cols = Object.fromEntries(
    (Object.entries(COLUMN_ALIASES) as [keyof typeof COLUMN_ALIASES, string[]][])
      .map(([key, aliases]) => [key, header.findIndex((h) => aliases.includes(h))])
  )

  return rows.slice(1).filter((r) => r[symbolCol]).map((r) => ({
    symbol: r[symbolCol].toUpperCase(),
    name: cols.name >= 0 ? r[cols.name] : undefined,
    close: num(cols.close >= 0 ? r[cols.close] : undefined),
    changePct: num(cols.changePct >= 0 ? r[cols.changePct] : undefined),
    volume: num(cols.volume >= 0 ? r[cols.volume] : undefined),
    sector: cols.sector >= 0 ? r[cols.sector] : undefined,
    marketcap: cols.marketcap >= 0 ? r[cols.marketcap] : undefined,
  }))
}
