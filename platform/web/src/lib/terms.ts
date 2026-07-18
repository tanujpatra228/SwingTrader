// Plain-language dictionary (ADR-6, terms.md). The DB and API speak real terms;
// the screen speaks plain English. Translation happens here, once.

export type TermDef = { plain: string; real: string }

export const TERMS: Record<string, TermDef> = {
  entry: { plain: "Buy at", real: "entry" },
  stop: { plain: "Exit if wrong", real: "stop loss" },
  target: { plain: "Take profit at", real: "target" },
  qty: { plain: "Shares to buy", real: "position size" },
  charges: { plain: "Fees & taxes", real: "charges" },
  breakeven: { plain: "Rise needed to break even", real: "breakeven move" },
  resting_zone: { plain: "Resting zone", real: "base" },
  delivery: { plain: "Shares actually kept", real: "delivery %" },
}

export function term(id: string): TermDef {
  return TERMS[id] ?? { plain: id, real: "" }
}
