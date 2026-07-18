# Terms Dictionary — Seed Data

Source content for `web/src/terms.js` (ADR-6). Plain wording is what ships on screen; the real term renders beneath it in small grey text, and is what the code and database use.

Shape:

```js
{
  ema20: {
    plain: "Short-term average line",
    real:  "20 EMA",
    help:  "beginners-guide/step-1-check-the-market.md#thing-1",
    unit:  null
  },
  rvol: {
    plain: "Traded {v}× more than usual today",
    real:  "RVOL {v}",
    help:  "beginners-guide/step-5-wait-for-trigger.md",
    unit:  "multiplier"
  }
}
```

`plain` may be a template — per `platform-plan.md` §5.3, a metric never renders as a bare label, because the unit *is* the explanation. `help` points at the guide file that teaches the idea, so every term on screen is one click from its own lesson.

## Chart & price

| key | plain | real |
|---|---|---|
| `ema10` | Fast average line (10 days) | 10 EMA |
| `ema20` | Short-term average line (20 days) | 20 EMA |
| `ema50` | Trend line (50 days) | 50 EMA |
| `ema200` | Long-term line (200 days) | 200 EMA |
| `base` | Resting zone | base, consolidation |
| `pivot` | Top of the resting zone — the breakout price | pivot |
| `base_low` | Bottom of the resting zone | base low |
| `days_in_base` | Resting for {n} days | days in base |
| `linear_base` | Steady rest | linear base |
| `choppy_base` | Jumpy rest | choppy base |
| `efficiency_ratio` | How straight the rise was | efficiency ratio |
| `breakout` | It broke out — price moved above the resting zone | breakout, trigger |
| `extended` | Already moved too far | extended |
| `chasing` | Buying late | chasing |
| `dist_52wh` | {v}% below its highest price of the past year | distance from 52-week high |
| `range_5w` | Last 5 weeks moved within {v}% | 5-week range |

Never name a line by its colour — `step-1-check-the-market.md` says blue/green, `how-to-screen-stocks.md` says red/orange, for the same two lines. Colours are a legend detail; names describe what the line measures.

## Volume

| key | plain | real |
|---|---|---|
| `rvol` | Traded {v}× more than usual today | RVOL |
| `vol_dryup` | Quiet — nobody's selling | volume dry-up |
| `pocket_pivot` | Big-buyer day | pocket pivot |
| `bull_snort` | Huge-buying day | bull snort |
| `overhead_supply` | Sellers waiting above this price | overhead supply |
| `delivery_pct` | {v}% of shares were actually kept, not day-traded | delivery % |
| `turnover` | ₹{v} of this stock changed hands | turnover |

## Market

| key | plain | real |
|---|---|---|
| `regime_green` | Market is Good | regime: green |
| `regime_caution` | Market is Shaky | regime: caution |
| `regime_red` | Market is Bad | regime: red |
| `breadth` | {v}% of stocks are healthy | market breadth |
| `drawdown` | Fell {v}% from its recent high | drawdown |
| `distribution_days` | {n} heavy-selling days recently | distribution days |
| `rs_rank` | Stronger than {v}% of all stocks | relative strength rank |
| `sector_rank` | Its industry ranks #{n} right now | sector strength |

## Trades

| key | plain | real |
|---|---|---|
| `stop_loss` | Exit price if wrong | stop loss |
| `position_size` | How many shares to buy | position size |
| `entry` | Buy at | entry |
| `buy_stop` | Only buys if price crosses this | buy-stop order |
| `target` | Take profit at | target |
| `risk_per_share` | If wrong, you lose ₹{v} per share | risk per share, 1R |
| `r_multiple` | {v}× what you risked | R-multiple |
| `exposure` | Money you're putting in | exposure |
| `concentration` | Too many from the same industry | sector concentration |
| `trail_stop` | Move your exit price up | trailing stop |
| `climax` | It shot up too fast — consider taking profit | climax, parabolic move |
| `time_stop` | It's stuck — consider freeing the money | time stop |
| `adr` | Typically swings about {v}% a day | ADR |
| `setup` | Trade type | setup |

## Process

| key | plain | real |
|---|---|---|
| `scanner` | Search for stocks | scanner, screener |
| `universe` | All stocks | universe |
| `candidates` | Promising stocks | candidates |
| `watchlist` | Watchlist | watchlist |
| `backtest` | Test on past data | backtest |
| `paper_trade` | Practice mode — not real money | paper trading |
| `series_eq` | Normal stocks | series EQ |
| `series_be` | Restricted stocks | series BE / BZ / SM |
| `expectancy` | Average result per trade | expectancy |
| `profit_factor` | Money made ÷ money lost | profit factor |
| `realized_pnl` | Profit already booked | realized P&L |
| `unrealized_pnl` | Profit on paper | unrealized P&L |

## Tax — explained, never renamed

These appear verbatim on your contract note, your broker's tax statement, and the ITR form. Renaming them would hurt you at filing time. They keep their real names and get a plain sentence beside them.

| key | real name (shown as-is) | explanation shown beside it |
|---|---|---|
| `stcg` | Short-term capital gains (STCG) | Held under a year, so profit is taxed at 20%, plus 4% cess |
| `ltcg` | Long-term capital gains (LTCG) | Held over a year — 12.5% above ₹1.25 lakh of gains |
| `sec_111a` | Section 111A | The rule that makes short-term stock profit 20% |
| `sec_87a` | Section 87A | The ₹12 lakh rebate everyone talks about — **does not apply** to short-term stock profit. Common surprise. |
| `stt` | STT | A 0.1% government charge on both buying and selling |
| `dp_charges` | DP charges | ~₹13–16 your broker charges each time you sell a stock |
| `cess` | Cess | 4% added on top of the tax itself |
| `advance_tax` | Advance tax | If you'll owe over ₹10,000 this year, you must pay in four instalments — miss one and it's 1% per month interest |
| `itr2` | ITR-2 | The tax form for someone with stock profits and no business income |
| `fifo` | FIFO | Oldest shares you bought are counted as sold first — the government's rule, not a choice |
| `carry_forward` | Loss carry-forward | Losses can offset gains for 8 years, but only if you file ITR-2 on time |

## Guardrail messages

Blocks state what you tried, why it stopped, and the fix (`platform-plan.md` §5.4). Never a bare rule name.

```js
"exposure-cap": {
  title: "Hold on — this puts too much money in at once.",
  body:  "This buy would put ₹{attempted} into the market. Right now your limit " +
         "is ₹{cap}, because the market is {condition}.",
  fix:   ["Buy {safe_qty} shares instead of {attempted_qty}",
          "Wait for the market to steady",
          "Override, and tell me why"],
  source: "beginners-guide/common-mistakes.md#mistake-12"
}
```

Every message carries `source`, linking to the guide file it enforces. The rule and its lesson stay attached — so when a block fires, the answer to "why?" is one click away, not tribal knowledge.
