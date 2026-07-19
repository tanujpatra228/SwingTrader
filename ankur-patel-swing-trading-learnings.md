# Ankur Patel — Swing Trading Learnings

Compiled from public sources (X threads, course listings, interviews) — not from the copyrighted book *Swing Trading Simplified*.

## Core Philosophy

- **Simplicity wins.** Price action + volume + risk management. No indicator soup.
- **Follow institutions.** The easiest edge: join a stock when big money starts buying, then ride the momentum.
- **Trade fresh Stage 2 stocks** — stocks that just broke out of an accumulation base. Early trend = biggest profits. Late trend = risk.
- **Pick one lane.** Master one setup style instead of trying to trade everything.

## Market First (Top-Down Approach)

- 70%+ of stocks follow the broad market. Check the market trend BEFORE picking stocks.
- Breakouts work in uptrends and fail in downtrends. "Work with the tide, not against it."
- Professionals reverse the retail process: market conditions → sector → stock. Not setup-first.

## Entries

- Buy breakouts from a range/base **early in the trend**, not after the big move is already done.
- Momentum stock signals: strong price action + solid volume. Scan daily and build a watchlist.
- Tightness/contraction before a breakout = quality setup (range contraction → expansion cycle).
- Tools: TradingView scans, Base Finder indicator for consolidation detection.

## Momentum Stage Framework (from "Build a Momentum Watchlist" video)

Every stock in an uptrend falls into one of three stages. Identifying the stage determines your action:

| Stage | Description | Action |
|---|---|---|
| **Emerging** | Just broke out of base — day 1 or 2 | Add to radar. Do NOT buy yet. Wait for tight range to form. Cannot pre-empt. |
| **Established** | Moved from base, had first pullback/flag, now consolidating again | Primary target. Can pre-empt (buy at 20 EMA pullback before next breakout). EOD entries work. Most money made here. |
| **Late stage** | 70–100%+ run, 3rd or 4th flag done | Avoid new positions. If forced: target 8–10% only, sell 70–80% immediately. |

**Late stage behavior after peak:** 8–12 weeks of consolidation, 20–40% price correction, 20 EMA cut multiple times. Not tradeable until fresh base forms.

**Watchlist rule:** include Emerging (track) + Established (trade). Remove Late stage.

### Momentum scan key condition
- **90 days, 30% move = mandatory filter. Never remove this.**
- For monthly/weekly watchlist building: turn off the daily 4.5% candle filter (want all stocks, not just today's movers)
- Monthly scanning is valid — build once, stocks stay relevant for weeks

## Stop Loss

- Place the stop below the **pivot low** of the base, plus a 0.5–1% buffer to avoid wick-outs.
- Logic: the base low is the last point where buyers showed conviction. A break below it means the breakout failed and the thesis is dead. Exit — no hoping.
- Bad stops kill returns two ways: too tight (early exit from winners), too loose (big losses).

## Exits / Trade Management

- Use defined sell rules, with special handling for parabolic moves (climax runs).
- Don't cut winners early "to protect capital" — an expensive habit. Fix it via position sizing, not premature exits.
- Size positions so a stop-loss hit is a tolerable loss. Sizing matters more than prediction.

## Trader Development

- Four phases of trader progression — skill builds in stages; expect losses early.
- Psychology and discipline are core to his teaching, not add-ons.

## Episodic Pivots (from interviews)

- Gap of 10%+ on an earnings/news catalyst, buy day 1, stop at low of day.
- A setup he discusses in interviews; the concept originates with Pradeep Bonde / Qullamaggie.

## Stock Scanning Method

### Chartink scanners (his shared scans)

| Scanner | Criteria | Link |
|---|---|---|
| Momentum Stocks | Up 20% in 5 days OR up 30% in 30 days | [chartink](https://chartink.com/screener/momentum-stocks-797) |
| Volume Spike | Price move + strong volume | [chartink](https://chartink.com/screener/ankur-s-volume-scan) |
| 3 Week Tight Close (3WTC) | Closing within tight range 3 weeks straight; run weekly | [chartink](https://chartink.com/screener/3-week-tight-close-19) |
| 52-Week High Zone | Trading within 25% of 52-week high | [chartink](https://chartink.com/screener/copy-copy-52w-1) |
| Range Contraction / 20 EMA | Close > 20 EMA (length customizable) | [chartink](https://chartink.com/screener/ema-scan-1414) |
| 5-Day Range Breakout | Breaking 5-day high on 15-min candle | [chartink](https://chartink.com/screener/5d-range-bo) |
| Reversal Scan | Down 20%+ in 5 days | [chartink](https://chartink.com/screener/ankur-s-reversal-scan) |
| Reversal Scan 2 | Down 5 consecutive days (3–5 day reversal concept) | [chartink](https://chartink.com/screener/reversal-scan-5-down-days) |
| RC Scan 1 (Range Contraction) | Daily contraction setups (from "My Daily Scans" video) | [chartink](https://chartink.com/screener/ema-scan-2-7) |
| RC Scan 2 (Range Contraction) | Second daily contraction scan | [chartink](https://chartink.com/screener/new-daily-2045) |
| RE Scan (Range Expansion) | Volume-backed expansion moves (= Volume Spike scan) | [chartink](https://chartink.com/screener/ankur-s-volume-scan) |
| Flag Pattern Scan | Flag/tight consolidation after momentum leg | [chartink](https://chartink.com/screener/ats-modified) |
| 20 EMA Pullback Scan | Uptrending stocks pulling back to 20 EMA | [chartink](https://chartink.com/screener/ankur-patel-s-20-ema-scan) |

### Exact Chartink scan clauses (extracted from scan pages)

```
RE / Volume Spike (ankur-s-volume-scan):
( volume > sma(volume,50) * 3 AND close > 30 AND day-change% >= 6.5
  AND sma(volume,50) >= 25000 AND volume > 50000 )

RC Scan 1 (ema-scan-2-7):
( close > ema(close,20) AND day-change% between -4.5 and +4.5
  AND volume > 50000 AND close > 30
  AND buyer initiated trades >= 200 AND seller initiated trades >= 200
  AND sma(volume,50) >= 25000 )

RC Scan 2 (new-daily-2045):
( day-change% between -4.5 and +4.5 AND close >= 30 AND liquidity filters
  AND ( close >= 5d low * 1.1 OR close >= 10d low * 1.2 OR close >= 30d low * 1.2
        OR close >= 90d low * 1.3 OR close >= 6m low * 1.8 OR close >= 11m low * 1.9 ) )

20 EMA Pullback (ankur-patel-s-20-ema-scan):
( close between ema(close,20) * 0.95 and * 1.05 AND close > 30
  AND volume > 100000 AND same momentum-leg ladder as RC Scan 2 )

3 Week Tight Close (3-week-tight-close-19):
( abs( (max(3, weekly close) / min(3, weekly close) - 1) * 100 ) <= 3.01
  AND close >= 3-month low * 1.3 AND close > 30 AND sma(volume,50) >= 10000 )

Momentum Stocks (momentum-stocks-797):
( close >= 5d low * 1.2 OR close >= 30d low * 1.3 OR close >= 90d low * 1.3 )
  AND close > 30 AND sma(volume,50) >= 50000

Flag Scan (ats-modified):
( day-change% between -2.5 and +2.5 AND close > ema(close,50)
  AND close <= sma(close,50) * 1.25  ← not over-extended
  AND recent leg: close >= 5d close * 1.1 OR 10d/30d * 1.2 OR 90d * 1.3
  AND sma(volume,50) >= 50000 )

52-Week High Zone (copy-copy-52w-1):
( close >= weekly max(52, weekly high) * 0.75 AND close > 50
  AND buyer/seller initiated trades >= 200 AND sma(volume,50) >= 50000 )

Reversal Scan (ankur-s-reversal-scan):
( close < 5-days-ago close * 0.85 AND sma(volume,50) >= 50000 AND close > 30 )

Reversal Scan 2 (reversal-scan-5-down-days):
( 5 consecutive lower closes AND close > 30 AND sma(volume,20)*close > 50000 )

5-Day Range Breakout (5d-range-bo):
( highs of last 4 days all < 5-days-ago high AND close > 5-days-ago high
  AND 15-min close > 5-days-ago high AND turnover > 5 cr AND close > 30 )
```

**Common filters across all scans:** close > 30 (no penny stocks), avg volume 25K–100K+, buyer & seller initiated trades ≥ 200 (two-sided liquidity), market cap > 0. His momentum definition = % above recent-low ladder (1.1× 5-day low up to 1.9× 11-month low), reused in 4 scans. Contraction = daily change within ±2.5–4.5% after a momentum leg.

### Weekend routine (6 scans, prep for coming week)

1. Stage 2 stocks (Minervini framework) — established uptrend above rising long MAs.
2. 52-week high weekly closes — closing at highs, not just touching = genuine strength.
3. Weekly big movers — big moves attract buyers back.
4. Stage 2 entry points — stocks just entering Stage 2, positional entries.
5. Weekly narrow-range inside bars — contraction in uptrend → expansion coming.
6. Weekly double inside bars — tighter contraction, stronger signal.

### Process after scan

Scan → strong price action + good volume → watchlist → wait for setup (tight base/pivot) → buy breakout → stop below pivot low (0.5–1% buffer).

## His TradingView Indicators

- **[AP AI1 Tool](https://in.tradingview.com/script/eBKI4Sjk-AP-AI1/)** — contraction-scanning dashboard. Plots EMAs 10/20/50/200, marks Bull Snorts and Inside Bars. Table: % distance from EMA10/20/50, RVOL, ADR, distance from 52-week high, 5-week range %, 50-day avg vs current volume, turnover INR.
- **[Simple Volume with Pocket Pivots](https://in.tradingview.com/script/JkB0iCFp-Simple-Volume-with-Pocket-Pivots/)** — volume color coding:
  - Blue = Pocket Pivot Volume (up-day volume > highest down-day volume of last 10 days) — "best indicator of institutional accumulation", especially multiple PPVs in base or on breakout candle.
  - Red = down-day volume above 50-MA = unconsumed supply; overcome it (take out that day's high) before buying.
  - Green = up-day volume above 50-MA.
  - Orange = dry volume (<20% of average) — supply exhaustion in base.
  - Bull Snort = 3× average volume, close in upper 35% of range, above prior close.
- [NSE Equity Price Band v1.0](https://in.tradingview.com/script/fImrapqb-NSE-EQUITY-PRICE-BAND-v1-0-ILuvMarkets/) — circuit-limit bands (third-party, recommended by him).

## His Structured Material (paid)

- **Book:** *Swing Trading Simplified* (303 pages, mybookmojo, April 2025, ISBN 978-81-964761-4-4) — [Amazon.in](https://www.amazon.in/Swing-Trading-Simplified-Guide-Profitable/dp/8196476140)
- **Course:** [Upsurge.club](https://www.upsurge.club/course/swing-trading-strategy-by-ankur-patel) — price action (expansion/contraction, momentum cycle) → entry rules → stops → exits → parabolic management → scanners → risk/psychology.

## Free Originals

- [Thread Reader — all his threads](https://threadreaderapp.com/user/AnkurPatel59)
- [Institutional-following thread](https://threadreaderapp.com/thread/1803711041458909214.html)
- [YouTube channel](https://www.youtube.com/@AnkurPatel59/videos)
- [Episodic pivot interview (Hindi)](https://www.youtube.com/watch?v=CcVEU0M7uPQ)

## YouTube Channel Topic Map

Channel: [@AnkurPatel57](https://www.youtube.com/@AnkurPatel57) (~9.4K subs, 62 videos). His setups universe: **VCP, flags, long bases, tight ranges, episodic pivots (incl. delayed EP), 20 EMA pullbacks, shakeouts**. Key videos by theme:

### Setups
- [How to Trade the VCP Pattern — Step by Step](https://www.youtube.com/watch?v=JiAaLcY6Y1Y) · [VCP Trade Management](https://www.youtube.com/watch?v=Eenfov1IwM4)
- [Flag Pattern Setup — Nuances](https://www.youtube.com/watch?v=D-UPlB1XQOk) · [How to Scan for Flag Patterns](https://www.youtube.com/watch?v=zSfBvmBwq2A)
- [The Power of Tight Range Setups](https://www.youtube.com/watch?v=Ca0BK7ElDLI) · [Why Tight Stocks Make the Biggest Moves](https://www.youtube.com/watch?v=QOY0tFTAskY)
- [How to Trade Delayed Episodic Pivot](https://www.youtube.com/watch?v=GPhf8HpPW_c) · [Scanning for Delayed EP Setups](https://www.youtube.com/watch?v=0nz-LUsL6Kc)
- [The Pullback Entry Most Traders Miss](https://www.youtube.com/watch?v=ZcK5RBAoIY8) · [20 EMA Pullback Scanner](https://www.youtube.com/watch?v=L3fiDFZIpzc)
- [The Shakeout Setup](https://www.youtube.com/watch?v=QPj8hpHO0rc) · [Best Setup for Choppy Markets](https://www.youtube.com/watch?v=mwFLohDp8Lc)
- [Strong vs Weak Base](https://www.youtube.com/watch?v=Vycp0gRhxnU) · [Linear vs Choppy Base](https://www.youtube.com/watch?v=JTbqYRS9o1Y) · [Every Winning Stock Follows This Pattern](https://www.youtube.com/watch?v=oCuI_gBkD0g)

### Scanning & tools
- [My Daily Scans — How I Find Tradable Setups](https://www.youtube.com/watch?v=aeyTthOS7Z0) (RC/RE scan links in description)
- [My Exact Method to Scan Strong Sectors in Minutes](https://www.youtube.com/watch?v=TTgFumxrJXM) · [Sector Rotation for Strongest Stocks](https://www.youtube.com/watch?v=k6rHNrSqPkM)
- [RVol (Relative Volume) Explained](https://www.youtube.com/watch?v=gmCnvstswjw)
- [Tools, Charts & Layout I Use Every Day](https://www.youtube.com/watch?v=wnhGCYBk4Gg) · [How I Organize My Watchlist](https://www.youtube.com/watch?v=KPuDFFG0Mjc)

### Trade management & risk
- [Where Should You Put Stop Loss?](https://www.youtube.com/watch?v=MhXZ8IlIuQY) · [Types of Buying Entries](https://www.youtube.com/watch?v=YBl0Orf-5I4)
- [Parabolic Moves Simplified](https://www.youtube.com/watch?v=jMhKXuR0kyk) · [Why Stocks Crash After Their Biggest Moves](https://www.youtube.com/watch?v=n2XnFVrmdRs)
- [Handling Gaps](https://www.youtube.com/watch?v=sO2bPsS9KwE) · [Drawdowns — Handling Losses](https://www.youtube.com/watch?v=uyh-wDhtxLM)
- [When Market Is Ready for Bigger Positions](https://www.youtube.com/watch?v=v2nFQiYX2P0)

### Process & study
- [If I Started Swing Trading in 2026, This Is What I'd Do](https://www.youtube.com/watch?v=Jqx_mxjzk5E)
- [How to Build Your Own Library of Winning Setups](https://www.youtube.com/watch?v=40SexnPytFI) · [How to Study a Past Winner](https://www.youtube.com/watch?v=QhEf9zPmNTE)
- [My Trading Journal — Track Mistakes, Improve Faster](https://www.youtube.com/watch?v=njSExtr3gvQ)
- [The Secret Sign of a True Market Leader](https://www.youtube.com/watch?v=J6fSgtkB0gg)
- Guest interviews: Manas Arora (execution > analysis), DayEndTrader (0%→100% invested cycle), Nitin R masterclass, Kiran Bhosale (techno-funda), Jainish Lamoria (momentum entry-to-exit), Vivek Gautam (swing + intraday), Chhirag Kedia
- Weekly "Market Outlook / Conditions" series — applies his top-down market-first rule

## Other Resources

- [Previous winners list (X post)](https://x.com/AnkurPatel59/status/1958144507204997539)
- [TradingView profile — published scripts](https://in.tradingview.com/u/ank5956/#published-scripts)
- Second YouTube handle: [@AnkurPatel57](https://www.youtube.com/@AnkurPatel57)
- [Resource links compilation (JustPaste.it)](https://justpaste.it/ikaqe)

## Sources

- [Thread Reader profile](https://threadreaderapp.com/user/AnkurPatel59)
- [Thread 1803711041458909214](https://threadreaderapp.com/thread/1803711041458909214.html)
- [Upsurge course](https://www.upsurge.club/course/swing-trading-strategy-by-ankur-patel)
- [Scribd tightness doc (paywalled)](https://www.scribd.com/document/771732478/if-you-are-trading-thread-by-ankurpatel59-mar-26-22)
- [Finer Market Points — EP guide](https://www.finermarketpoints.com/post/episodic-pivot-trading-complete-guide)
- [TradeZella — EP strategy](https://www.tradezella.com/strategies/episode-pivot-strategy)
- [A Bored Trader — EP setup](https://aboredtrader.com/episodic-pivot-setup/)
