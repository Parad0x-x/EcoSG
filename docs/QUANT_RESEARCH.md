# Quant factor model — methodology

This is the methodology writeup for `backend/app/quant/` — ECOSG's hedge-fund-style
multi-factor stock model, ported in from a standalone project (see the package
docstring in `backend/app/quant/__init__.py` for what changed in the port: only the
data layer, which now reads ECOSG's own database instead of yfinance, and the
portfolio-construction defaults in `config.py`, rescaled for ECOSG's smaller mock
universe). Everything below — the five factors, the scoring math, the portfolio
construction rules — is unchanged from the original.

---

# How Hedge Funds Actually Pick Stocks — And How This Bot Implements It
## The short version
Hedge funds that aren't purely discretionary stock-pickers select stocks
through **factor investing**: they define a handful of measurable
characteristics that have historically predicted which stocks outperform —
cheapness, quality, momentum, growth, and low volatility are the five most
established — score every stock in a universe on each characteristic,
combine those scores into one number per stock, and build a portfolio out
of the highest scorers. Funds like AQR built their entire business on
formalizing this process; even more discretionary funds use factor
screens to narrow thousands of stocks down to the dozens an analyst
actually researches. The code in this repository is a working, from-scratch
implementation of that process, structured the way a quant equity team
would actually build it: a data layer, a factor layer, a scoring layer, a
portfolio-construction layer, and a backtest layer, each independently
testable and swappable.
This document explains the methodology and then maps every technique to
the file and function that implements it, so the code reads as an
answer to "how do hedge funds do this," not just as a black box.
## Where the evidence comes from
The value, momentum, and quality effects aren't folklore — they're some of
the most heavily studied phenomena in empirical finance. Eugene Fama and
Kenneth French's three-factor model formalized value (cheap stocks
outperform expensive ones on a risk-adjusted basis) and size, building on
CAPM; momentum was added as a fourth well-documented factor after Jegadeesh
and Titman's 1993 study showed stocks that outperformed over the past 3–12
months kept outperforming over the next few months, but reversed over the
following month — which is exactly why this bot's momentum factor uses a
"12-month return, skipping the most recent month" convention instead of a
naive trailing return ([Momentum: From Theory to Practical Application,
IFA](https://www.ifa.com/articles/momentum_fourth_factor); [The Academic
Roots of Factor Investing: Fama and
French](https://advisoranalyst.com/2026/03/19/the-academic-roots-of-factor-investing-fama-and-french.html/)).
Asness, Moskowitz, and Pedersen's "Value and Momentum Everywhere" showed
these effects hold across asset classes and geographies, not just US
large-cap stocks, which is a big part of why AQR and similar funds trust
factor investing enough to run hundreds of billions of dollars on it
([Value and Momentum Everywhere, NYU
Stern](https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf)).
"Quality" — profitability, low leverage, earnings stability — was added
later as funds and academics noticed cheap-and-risky stocks didn't
outperform as reliably as cheap-and-sound ones ([MSCI: Foundations of
Factor
Investing](https://www.msci.com/documents/1296102/1336482/Foundations_of_Factor_Investing.pdf);
[Factor Investing Explained,
Chase](https://www.chase.com/personal/investments/learning-and-insights/article/factor-investing-explained)).
## The five factors this bot screens on
Each factor family is a bet on a different, mostly-uncorrelated source of
excess return, which is the point of combining them rather than picking
just one — a stock can be a bad value but great quality, or vice versa, and
a multi-factor score captures that instead of forcing a single lens.
**Value** asks whether a stock is cheap relative to what the business
actually generates. This bot uses earnings yield (EBIT/EBITDA relative to
enterprise value — the Joel Greenblatt "Magic Formula" style metric, which
is capital-structure-neutral in a way a plain P/E isn't), free cash flow
yield, book-to-price, and EV/EBITDA. `factors.compute_value_factors()`
computes the raw numbers; `scoring.py` turns "cheap" into a comparable
score.
**Quality** asks whether the business itself is good, independent of
price: how efficiently it turns capital into profit (ROIC/ROE), how much
margin it keeps (gross margin), how levered it is (debt/equity, inverted
so lower leverage scores higher), and how stable its earnings are. Return
on invested capital is the metric quality-focused quant screens lean on
hardest — Terry Smith-style "quality compounder" screens typically look for
ROIC persistently above 15%, paired with a free-cash-flow-yield floor and a
sales-growth floor so a mature, capital-light cash cow doesn't score as a
"quality" stock purely because reinvestment happens to be low ([Why ROIC
Beats ROA For Stock Investing Success,
Quant Investing](https://www.quant-investing.com/blog/why-roic-beats-roa-for-stock-investing-success)).
The exact formula that source uses —
`ROIC = Trailing 12-Month EBIT / ((Current Assets − Current Liabilities) + Net Fixed Assets)`
— is worth pulling directly from balance-sheet line items
(`Ticker.balance_sheet`) if you want true ROIC rather than this bot's
free-data-source proxy (ROA), which `factors.py` documents inline.
**Momentum** asks whether the stock has been outperforming — not because
price trends are magic, but because information diffuses into prices
gradually and because institutional buying pressure itself takes months to
fully play out. `factors.compute_momentum_factors()` implements the
academic-standard "12-1" measure: total return over the trailing 12
months, excluding the most recent month, to avoid the well-documented
short-term reversal effect contaminating the signal.
**Growth** asks whether the business is expanding — revenue and earnings
growth. Growth without quality is a trap (a company can grow revenue while
burning cash), which is exactly why this factor gets a smaller weight
(15%) than quality (30%) in the default configuration — growth is meant to
be a tilt on top of a quality-and-value core, not the primary signal.
**Low volatility** asks whether the stock is less risky than its peers.
This sounds like it should conflict with wanting high returns, but the
"low-volatility anomaly" is one of the more robust empirical findings in
factor investing: low-vol stocks have historically delivered returns
comparable to the broad market with meaningfully less drawdown, likely
because leverage-constrained investors bid up high-beta "lottery ticket"
stocks beyond their risk-adjusted worth ([A Different Approach to Low
Volatility,
Nasdaq](https://indexes.nasdaqomx.com/docs/NQVMVUS%20Research.pdf)).
`factors.compute_low_vol_factors()` uses trailing realized volatility and
closeness of beta to 1.0.
### Raw metric formulas at a glance
| Factor | Metric | Formula used in this bot |
|---|---|---|
| Value | Earnings yield | EBITDA (EBIT proxy) / Enterprise Value |
| Value | FCF yield | Free Cash Flow / Enterprise Value |
| Value | Book-to-price | 1 / Price-to-Book |
| Quality | ROIC (proxy) | Return on Assets (see RESEARCH.md note on true ROIC formula) |
| Quality | Leverage | 1 / (1 + \|Debt/Equity\|) |
| Momentum | 12-1 momentum | (Price 1mo ago / Price 12mo ago) − 1 |
| Growth | Revenue growth | YoY revenue growth % |
| Low-vol | Realized vol | 1 / (60-day trailing annualized std dev of returns) |
## From raw metrics to one ranked list: normalization and scoring
You can't average a P/E ratio with an ROE percentage — they're on
completely different scales, and a raw average would be dominated by
whichever metric happens to have the biggest numbers. The standard fix,
and the one every quant factor desk uses, is the **cross-sectional
z-score**: for each metric, at each point in time, compute
`(value − universe_mean) / universe_std_dev` across every stock in the
universe. Now "2 standard deviations cheap" and "2 standard deviations
high-quality" are on the same scale and can be added together.
`scoring.cross_sectional_zscore()` does exactly this, after first
**winsorizing** each metric (clipping the most extreme 1% at each tail) so
one data error or one truly extreme outlier doesn't dominate an entire
factor score — this is standard practice, not a shortcut; every production
quant pipeline winsorizes before z-scoring.
The z-scores for each factor family's individual metrics are then combined
using the weights in `config.py` (e.g., within Value: 35% earnings yield,
35% FCF yield, 15% book-to-price, 15% EV/EBITDA), producing one score per
factor family per stock. Those five family scores are then combined using
the top-level `FACTOR_WEIGHTS` into one **composite score**, and the
universe is ranked by it (`scoring.compute_composite_score()`).
One refinement that matters more than people expect: **sector-neutral
scoring**. A bank's P/E and an oil producer's P/E aren't comparable to a
software company's — if you z-score across the whole market without
adjusting for sector, a multi-factor "value" model quietly turns into a
disguised bet on whichever sector happens to be statistically cheap or
expensive right now (Energy vs. Tech, say), rather than a genuine
stock-picking signal. `scoring.cross_sectional_zscore()` supports
computing the z-score *within each GICS sector* instead of across the
whole universe, which is the default (`SECTOR_NEUTRAL_SCORING = True` in
`config.py`) — this isolates "cheap/high-quality/strong-momentum stock
picking" from "sector timing," which are different bets that should be
made deliberately, not accidentally.
## Signal vetting: why this matters even for a screener
Production quant funds don't ship a signal just because it looks good on
one backtest. The standard vetting pipeline — hypothesis first, then
in-sample testing against metrics like the Information Coefficient
(correlation between predicted rank and actual future return), then
out-of-sample testing on 5–10 years the model never saw, then checks for
capacity, decay speed, and correlation with existing signals before
anything goes live — exists specifically to catch overfitting, since with
enough metrics and enough historical fishing you can always find *something*
that "worked" in the past by accident ([How Quant Hedge Funds Actually
Build and Vet Trading
Signals](https://youngandcalculated.substack.com/p/how-quant-hedge-funds-actually-build)).
This bot's factor choices (value, momentum, quality, growth, low-vol) are
deliberately the oldest, most independently-replicated factors in the
academic literature rather than something discovered by data-mining this
specific universe — that's the same discipline in spirit, applied by
picking factors with decades of out-of-sample evidence instead of
in-house-only backtests. If you extend this model with your own metrics,
apply the same standard: does it have a real economic rationale, and does
it hold up on data the model wasn't tuned on?
## From ranking to portfolio: construction and risk
A ranked list isn't a portfolio. Three more decisions turn it into one,
and all three are implemented in `portfolio.py`:
**How many names, and how much turnover.** Concentrating in the single
top-ranked stock is fragile — the whole point of a factor model is that
it's directionally right on average, not stock-by-stock. This bot holds
the top `TOP_N` (20 by default). But naively re-ranking every period and
holding exactly the top 20 causes needless turnover: a stock ranked #19
one month and #22 the next hasn't meaningfully changed, and trading it out
just pays the bid-ask spread and commissions for no signal. `portfolio.
select_candidates()` implements a **buffer band** (hysteresis): an existing
holding survives until it falls out of the top `TOP_N × BUFFER_MULTIPLIER`
(30 by default), while a new position still needs to crack the top 20
outright to get bought. This single rule is one of the more meaningful,
underrated levers in a real quant fund's cost model.
**How much to bet per name.** Equal-weighting every position ignores that
some of these stocks are twice as volatile as others, so equal dollar
amounts don't mean equal risk contribution. `portfolio.size_positions()`
defaults to **inverse-volatility weighting** — a lower-volatility stock
gets a proportionally larger weight — which is a simplified version of the
risk-parity logic quant funds use to keep any one name from dominating
portfolio-level risk. `score_weighted` (size by conviction) and
`equal_weight` are available as alternatives via `config.
POSITION_SIZING_METHOD`.
**Hard limits.** Even a good model can be wrong, or the data can be stale
or broken for one name — so `MAX_POSITION_WEIGHT` and `MAX_SECTOR_WEIGHT`
in `config.py` cap single-name and sector concentration regardless of what
the model wants to do, and `portfolio.size_positions()` enforces them by
iteratively redistributing any excess weight. This is the same reasoning
behind every real fund's hard risk limits: a scoring model is a source of
edge, not a substitute for guardrails.
## Backtesting honestly
It's easy to build a backtest that looks great and means nothing, usually
by accidentally letting the model see information it wouldn't have had at
the time (look-ahead bias) or by testing only on companies that survived
to the present day (survivorship bias). Both are called out explicitly in
`backtest.py` and `README.md` rather than papered over: this bot's included
backtest deliberately scores stocks using **only price history**
(12-1 momentum + realized volatility) instead of the full fundamental model,
because the free fundamentals data source used for live scanning
(`yfinance`) only exposes *today's* ROE and P/E, not what they were three
years ago — feeding today's fundamentals into a simulated 2022 decision
would be look-ahead bias, and would make the backtest's returns look better
than any strategy could have actually achieved in real time. The engine's
`score_func` interface is intentionally provider-agnostic so you can plug
in point-in-time fundamentals (e.g., Sharadar or Compustat) later and
backtest the full value/quality/growth model honestly, without touching
the rebalancing, position-sizing, or performance-metric code at all.
`backtest.run_backtest()` implements walk-forward monthly rebalancing
(configurable to weekly/quarterly), applies inverse-volatility position
sizing consistent with the live signal path, deducts a transaction cost
per unit of turnover, and reports the metrics a fund's risk team would
actually look at: CAGR, annualized volatility, Sharpe ratio, Sortino ratio
(downside-only volatility, arguably more relevant than Sharpe since
investors don't mind upside volatility), max drawdown, Calmar ratio
(return relative to worst drawdown — how much pain per unit of gain), beta
to the S&P 500, and excess CAGR over that benchmark.
## What this deliberately doesn't do
Real multi-strategy hedge funds run factor books alongside statistical
arbitrage (pairs and baskets trading on short-term mean reversion),
event-driven strategies (M&A arbitrage, earnings drift), and sometimes
machine-learning signals trained on alternative data (satellite imagery,
credit card panels, web-scraped pricing) — Renaissance Technologies and
similar firms built their edge partly on proprietary short-horizon
statistical signals that aren't public knowledge and aren't something a
from-scratch bot can replicate with public data ([How Renaissance
Technologies, AQR, and PDT Built $100
Billion](https://medium.com/@navnoorbawa/how-renaissance-technologies-aqr-and-pdt-built-100-billion-factor-models-statistical-arbitrage-ac0c9cd8a518)).
This bot is squarely in the long-only, public-data, classic-factor
category — the same category as most factor ETFs and a large share of
retail-accessible quant screening tools, which is both its honest
limitation and the reason it's actually buildable and testable with free
data.
## Sources
- [Value and Momentum Everywhere — Asness, Moskowitz, Pedersen (NYU Stern)](https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf)
- [MSCI: Foundations of Factor Investing](https://www.msci.com/documents/1296102/1336482/Foundations_of_Factor_Investing.pdf)
- [The Academic Roots of Factor Investing: Fama and French](https://advisoranalyst.com/2026/03/19/the-academic-roots-of-factor-investing-fama-and-french.html/)
- [Momentum: From Theory to Practical Application — Index Fund Advisors](https://www.ifa.com/articles/momentum_fourth_factor)
- [Factor Investing Explained — Chase](https://www.chase.com/personal/investments/learning-and-insights/article/factor-investing-explained)
- [Why ROIC Beats ROA For Stock Investing Success — Quant Investing](https://www.quant-investing.com/blog/why-roic-beats-roa-for-stock-investing-success)
- [A Different Approach to Low Volatility — Nasdaq](https://indexes.nasdaqomx.com/docs/NQVMVUS%20Research.pdf)
- [How Quant Hedge Funds Actually Build and Vet Trading Signals](https://youngandcalculated.substack.com/p/how-quant-hedge-funds-actually-build)
- [How Renaissance Technologies, AQR, and PDT Built $100 Billion](https://medium.com/@navnoorbawa/how-renaissance-technologies-aqr-and-pdt-built-100-billion-factor-models-statistical-arbitrage-ac0c9cd8a518)
- [Stock Screening Using Fundamental and Technical Analysis (Python approach) — pythoninvest.com](https://pythoninvest.com/long-read/stock-screening-using-paid-data)

