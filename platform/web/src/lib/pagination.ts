import { useEffect, useState } from "react"

const PAGE_SIZE = 10

/** Page a row list. Resets to page 1 whenever the row set changes (filter/sort/reload),
 * so stale pages never show fewer rows than expected after narrowing a filter. */
export function usePagination<T>(rows: T[]) {
  const [page, setPage] = useState(1)
  const pageCount = Math.max(1, Math.ceil(rows.length / PAGE_SIZE))

  useEffect(() => { setPage(1) }, [rows])

  const clamped = Math.min(page, pageCount)
  const start = (clamped - 1) * PAGE_SIZE
  const pageRows = rows.slice(start, start + PAGE_SIZE)

  return { page: clamped, pageCount, pageRows, setPage, pageSize: PAGE_SIZE }
}
