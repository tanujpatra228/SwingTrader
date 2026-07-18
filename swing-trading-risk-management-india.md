# Risk Management for Swing Trading — India (2026)

---

## The Golden Rules

1. **Never risk >2% of capital on one trade** (Ankur Patel style: 0.25–1%; beginners 0.25–0.5%)
2. **Never have >6% total portfolio at risk simultaneously**
3. **Minimum 1:2 risk-reward — no exceptions**
4. **Stop loss set BEFORE entry, not after**
5. **Stop sits where the setup is invalidated — never at a round % number** (Ankur Patel)

---

## Position Sizing (Most Critical Skill)

### Formula
```
Position Size = (Capital × Risk %) ÷ (Entry Price − Stop Loss Price)

Example:
Capital = ₹5,00,000
Risk per trade = 2% = ₹10,000
Entry = ₹500
Stop loss = ₹480 (₹20 risk per share)

Position Size = ₹10,000 ÷ ₹20 = 500 shares
Total position value = 500 × ₹500 = ₹2,50,000 (50% of capital)
```

### Capital Allocation Per Trade

| Capital | 2% Risk Cap | Max Loss Per Trade |
|---------|-------------|-------------------|
| ₹1,00,000 | ₹2,000 | ₹2,000 |
| ₹5,00,000 | ₹10,000 | ₹10,000 |
| ₹10,00,000 | ₹20,000 | ₹20,000 |
| ₹25,00,000 | ₹50,000 | ₹50,000 |

---

## Stop Loss Placement

### Method 1: Pivot Low (Ankur Patel's Primary Method)
```
Breakout entry from a base → stop below the base's pivot low + 0.5–1% buffer

Why: pivot low = last point where buyers showed conviction.
Price back below it = breakout failed, thesis dead. Exit — no hoping,
no averaging down. Buffer avoids getting wicked out by noise.

Entry ₹500 on breakout, base pivot low ₹482
Stop loss = ₹482 − 1% ≈ ₹477
```

By entry type:
| Entry | Stop |
|-------|------|
| Base/range breakout | Below pivot low + 0.5–1% |
| Episodic pivot (gap on news) | Low of gap day |
| 20 EMA pullback | Below pullback swing low |
| Tight range / inside bar | Below range low |

Sanity check: stop distance should be ≥ ~1× ADR away, else it's inside normal noise.

### Method 2: ATR-Based
```
ATR(14) of stock = ₹15
Stop loss = Entry − (1.5 × ATR) = Entry − ₹22.5

Why ATR: Adapts to each stock's actual volatility.
Fixed % stops get triggered by normal noise.
ATR stops reduce premature stop-outs by ~35%.
```

### Method 3: % Fixed (Simplest, Least Accurate)
```
Swing trade stop = 5–8% below entry
Use only if structure/ATR not clear
```

### What Kills Returns (Ankur Patel)
- Too tight (arbitrary 1–2%) → wicked out of winners repeatedly
- Too loose (10%+ "hope" stops) → few losses erase many gains
- Both fixed by putting the stop at the invalidation level and sizing the position to it

### Types of Stop Loss Orders (NSE/BSE)

| Type | When to Use |
|------|------------|
| **SL-M (Stop Loss Market)** | Guaranteed exit, slippage risk |
| **SL (Stop Limit)** | Price control, may not execute in fast fall |
| **Trailing SL** | Lock profits as stock moves up |

---

## Risk-Reward Ratio

### Minimum Acceptable Setups

| R:R Ratio | Win Rate Needed to Break Even |
|-----------|-------------------------------|
| 1:1 | 50% |
| 1:2 | 34% |
| 1:3 | 25% |
| 1:2 (target) | Most swing traders hit 40–50% win rate → profitable |

### Never Take Trades Below 1:1.5

Even with 40% win rate at 1:2 R:R:
```
10 trades:
4 winners × ₹10,000 = +₹40,000
6 losers × ₹5,000 = −₹30,000
Net = +₹10,000 profit
```

---

## Portfolio Heat Management

**Max 5–8 open positions at once.** More = can't monitor properly.

```
Example portfolio (₹5,00,000 capital):
Position 1 — ICICI Bank  → 2% risk = ₹10,000
Position 2 — Tata Motors → 2% risk = ₹10,000
Position 3 — Persistent  → 2% risk = ₹10,000
Total heat = 6% = ₹30,000 max loss if all stop out
```

### Sector Diversification Rule
- Never put >2 positions in same sector
- If Nifty IT falls, all IT stocks fall together
- Spread across Banking, IT, Auto, Metals, Pharma

---

## Trailing Stop Loss (Lock Profits)

```
Entry: ₹500
Target: ₹560
Stock reaches ₹530 → move stop to ₹510 (breakeven+)
Stock reaches ₹545 → move stop to ₹530
Stock hits ₹560 → exit or trail further
```

**Rule:** Move stop only UP, never down. Never widen stop to avoid a loss.

### Selling Winners (Ankur Patel)
- Don't cut winners early "to protect capital" — expensive habit. If the position feels too big to hold, the fix is position sizing, not premature exits.
- Parabolic move (steep acceleration, 3rd+ leg up, climax volume) → sell into strength or trail very tight. Stocks crash hardest right after their biggest moves.
- Gaps against you at open: exit if the gap breaks your invalidation level; don't freeze and hope.

---

## Market-Based Exposure (Ankur Patel)

Scale total exposure with market health, not a fixed allocation:

```
Market confirming (Nifty uptrend, breakouts working,
your last trades winning)        → scale up toward fully invested
Market choppy (breakouts failing,
stopped out repeatedly)          → cut size, fewer positions
Market downtrend                 → mostly/all cash; no long breakouts
```

Your own recent trade results = feedback signal on market condition. Progression: 0% → 100% invested and back to cash as conditions change.

---

## Drawdown Management

| Drawdown Level | Action |
|---------------|--------|
| −5% of capital | Review open positions |
| −10% of capital | Reduce position size by 50% |
| −15% of capital | Stop trading, paper trade for 2 weeks |
| −20% of capital | Full stop. Reassess strategy |

**Consecutive losses rule:** 3 losses in a row → take 1–2 day break. Revenge trading destroys accounts.

---

## Gap Risk (India-Specific)

Stocks gap down overnight due to global news, earnings, FII selling.

### How to Protect
- **Never hold >15% of capital in one stock overnight**
- **Avoid holding through earnings** — gaps are 10–15%+ common
- **Check global cues** (US markets, SGX Nifty) before holding overnight
- **Reduce size** before RBI policy, Budget, F&O expiry

---

## F&O Expiry Risk

Last Thursday of every month = high volatility, stop hunts, fake moves.

```
Rule: Close or tighten stops on Wednesday if expiry next day.
Don't initiate new swing trades on expiry Thursday.
```

---

## Psychology Rules (Risk to Capital)

| Bad Habit | Consequence | Fix |
|-----------|-------------|-----|
| Moving stop loss lower | Small loss → big loss | Hard SL, no touch |
| Averaging down | Doubles losing position | Never average losers |
| Overtrading after loss | Revenge trading | Max 3 trades/day |
| No trade journal | Repeat same mistakes | Log every trade |
| Holding losers, selling winners | Portfolio full of losers | Let winners run |

---

## Minimum Capital to Start

| Capital | Viability |
|---------|-----------|
| < ₹50,000 | Too small. Brokerage eats profit |
| ₹1–2 lakh | Minimum viable. 5–8 positions possible |
| ₹5–10 lakh | Comfortable. Full strategy executable |
| > ₹25 lakh | Reduce % risk to 0.5–1% per trade |

---

## Simple Risk Checklist (Before Every Trade)

```
[ ] Stop loss identified before entry — at setup invalidation (pivot low + buffer)?
[ ] Stop distance ≥ ~1× ADR (outside normal noise)?
[ ] Position size calculated (0.25–2% risk)?
[ ] R:R ratio at least 1:2?
[ ] Not more than 6% total portfolio at risk?
[ ] Not more than 2 positions in same sector?
[ ] No earnings/RBI/expiry in next 3 days?
[ ] Nifty trend aligned with trade direction (70%+ stocks follow market)?
[ ] Exposure level matches market health?
```

---

## Sources

- [Swing Trading Risk Management — TradeAlgo](https://www.tradealgo.com/trading-guides/stocks/swing-trading-risk-management-position-sizing-stop-losses-and-portfolio-rules)
- [The 1% Risk Rule — Trade That Swing](https://tradethatswing.com/the-1-risk-rule-for-day-trading-and-swing-trading/)
- [Stop Loss Orders India — Jainam](https://www.jainam.in/blog/stop-loss-order/)
- [Risk-Reward Ratios for Indian Traders — ICFM India](https://www.icfmindia.com/blog/how-to-apply-risk-reward-ratios-to-trading-for-better-decision-making-for-indian-traders/)
- [Swing Trading ETFs Risk Management India — 5paisa](https://www.5paisa.com/stock-market-guide/etf/swing-trading-etfs-in-india)
- [Position Sizing Calculator — Marketfeed](https://www.marketfeed.com/calculators/swing-position-sizing-calculator)
- Ankur Patel — [X threads](https://threadreaderapp.com/user/AnkurPatel59), [YouTube](https://www.youtube.com/@AnkurPatel57), book *Swing Trading Simplified*; see `ankur-patel-swing-trading-learnings.md`
