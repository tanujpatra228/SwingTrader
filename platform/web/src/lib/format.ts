// One place for money/percent/number formatting (frontend-standards §1.1).

const inr = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 })
const inr2 = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export const rupees = (n: number | null | undefined) => (n == null ? "—" : `₹${inr.format(n)}`)
export const rupees2 = (n: number | null | undefined) => (n == null ? "—" : `₹${inr2.format(n)}`)
export const pct = (n: number | null | undefined, d = 2) => (n == null ? "—" : `${n.toFixed(d)}%`)
export const num = (n: number | null | undefined) => (n == null ? "—" : inr.format(n))
