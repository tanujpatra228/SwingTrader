export type SortDir = "asc" | "desc" | null

/** Click once: asc. Click same column again: desc. Click again: off. */
export function nextSortDir(current: SortDir): SortDir {
  return current === null ? "asc" : current === "asc" ? "desc" : null
}

export function sortRows<T>(rows: T[], key: keyof T | null, dir: SortDir): T[] {
  if (!key || !dir) return rows
  return [...rows].sort((a, b) => {
    const av = a[key]
    const bv = b[key]
    if (av == null && bv == null) return 0
    if (av == null) return 1     // missing values sink to the bottom either direction
    if (bv == null) return -1
    if (typeof av === "number" && typeof bv === "number") {
      return dir === "asc" ? av - bv : bv - av
    }
    const cmp = String(av).localeCompare(String(bv))
    return dir === "asc" ? cmp : -cmp
  })
}
