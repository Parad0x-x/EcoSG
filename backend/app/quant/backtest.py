"""
backtest.py
-----------
A walk-forward backtest engine for the factor strategy.
HONEST LIMITATION (read this before trusting backtest numbers): yfinance's
fundamentals endpoint (`Ticker.info`) only returns a *current* snapshot --
there's no historical point-in-time series of "what was this company's ROE
on 2021-03-15" available for free. Feeding today's fundamentals into a
backtest of 2021 would leak future information into the past (look-ahead
bias) and produce backtest returns that are systematically too good.
So this engine is built around a `score_func(date, price_history) -> scores`
callable, and by default plugs in a momentum + low-volatility score --
because both are computable purely from historical daily prices with no
look-ahead risk. This gives you an honest, runnable backtest out of the box.
To backtest the FULL value/quality/growth/momentum/low-vol model, supply a
score_func backed by a point-in-time fundamentals vendor (Sharadar, Compustat,
FactSet) via the same interface -- everything downstream (rebalancing,
position sizing, cost modeling, performance stats) is agnostic to where the
scores came from.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Callable, Optional
import numpy as np
import pandas as pd
from . import config as cfg_module
from . import portfolio
from . import factors
from .scoring import rank_zscore, score_factor_family

# ---------------------------------------------------------------------------
# Default, look-ahead-safe score function: momentum + low-vol, price-only
# ---------------------------------------------------------------------------
def default_price_only_score(as_of: pd.Timestamp, price_history: pd.DataFrame) -> pd.Series:
    """
    price_history: all daily prices up to (and including) `as_of` -- nothing
    later is passed in, so there is no way for this function to see the future.
    Scores the two price-only families the same way the live model does
    (momentum: 12-1 + residual momentum; low vol: realized + idiosyncratic
    vol; beta is left out because it comes from fundamentals), re-standardizes
    each family, and combines them in their FACTOR_WEIGHTS ratio.
    """
    prices = price_history.sort_index()
    if len(prices) < 280:
        return pd.Series(dtype=float)
    no_fund = pd.DataFrame({"ticker": prices.columns, "beta": np.nan})
    df = factors.compute_momentum_factors(prices).merge(
        factors.compute_low_vol_factors(prices, no_fund), on="ticker").set_index("ticker")
    family_metrics = {"momentum": cfg_module.MOMENTUM_WEIGHTS, "low_vol": cfg_module.LOW_VOL_WEIGHTS}
    composite = pd.Series(0.0, index=df.index)
    total_weight = 0.0
    for family, metric_weights in family_metrics.items():
        family_score = score_factor_family(df, metric_weights, sector_neutral=False,
                                           winsor_lower=cfg_module.WINSORIZE_LOWER_PCTL,
                                           winsor_upper=cfg_module.WINSORIZE_UPPER_PCTL)
        weight = cfg_module.FACTOR_WEIGHTS[family]
        composite += weight * rank_zscore(family_score).fillna(0)
        total_weight += weight
    return (composite / total_weight).sort_values(ascending=False)

@dataclass
class BacktestResult:
    equity_curve: pd.Series
    benchmark_curve: pd.Series
    turnover_by_period: pd.Series
    metrics: dict

def _rebalance_dates(index: pd.DatetimeIndex, freq: str) -> pd.DatetimeIndex:
    s = pd.Series(index=index, data=1)
    rule = {"weekly": "W-FRI", "monthly": "ME", "quarterly": "QE"}.get(freq, "ME")
    resampled = s.resample(rule).last()
    return index.intersection(pd.DatetimeIndex(
        [index[index <= d].max() for d in resampled.index if (index <= d).any()]
    )).unique().sort_values()

def _scores_to_ranked(scores: pd.Series, sectors: Optional[pd.Series]) -> pd.DataFrame:
    """Score Series -> the scored-DataFrame shape portfolio.py expects."""
    df = pd.DataFrame({"ticker": scores.index, "composite_score": scores.values})
    df["rank"] = df["composite_score"].rank(ascending=False, method="first")
    if sectors is not None:
        df["sector"] = df["ticker"].map(sectors).fillna("Unknown")
    return df.sort_values("rank").reset_index(drop=True)

def run_backtest(prices: pd.DataFrame, benchmark_prices: pd.Series, cfg,
                  score_func: Callable = default_price_only_score,
                  start: Optional[str] = None, end: Optional[str] = None,
                  top_n: Optional[int] = None,
                  transaction_cost_bps: float = 10.0,
                  sectors: Optional[pd.Series] = None) -> BacktestResult:
    """
    Walk-forward backtest. At each rebalance date the score_func sees only
    prices up to that date; selection (buffer band) and sizing (inverse vol,
    position and sector caps) are portfolio.py's live functions, so the
    backtest trades exactly what the live signal path would. Between
    rebalances weights drift with prices (buy and hold), and costs are
    charged on the turnover from the drifted weights to the new targets.
    `sectors`: optional ticker -> sector map so the sector cap applies.
    """
    prices = prices.sort_index()
    if start:
        prices = prices[prices.index >= start]
    if end:
        prices = prices[prices.index <= end]
    if top_n:
        cfg = replace(cfg, top_n=top_n)
    rebal_dates = _rebalance_dates(prices.index, cfg_module.REBALANCE_FREQUENCY)
    daily_returns = prices.pct_change().fillna(0)
    portfolio_daily_returns = pd.Series(0.0, index=prices.index)
    turnover_log = {}
    drifted_weights = pd.Series(dtype=float)  # holdings as they stand just before a rebalance
    first_invested = None
    for i, reb_date in enumerate(rebal_dates):
        history_up_to = prices.loc[:reb_date]
        scores = score_func(reb_date, history_up_to).dropna()
        if scores.empty:
            continue
        if first_invested is None:
            first_invested = reb_date
        ranked = _scores_to_ranked(scores, sectors)
        held = set(drifted_weights[drifted_weights > 0].index)
        selected = portfolio.select_candidates(ranked, cfg, current_holdings=held)
        sized = portfolio.size_positions(selected, history_up_to, cfg)
        target = pd.Series(sized["weight"].values, index=sized["ticker"].values)
        names = drifted_weights.index.union(target.index)
        turnover = (target.reindex(names, fill_value=0) - drifted_weights.reindex(names, fill_value=0)).abs().sum()
        turnover_log[reb_date] = turnover
        cost = turnover * (transaction_cost_bps / 10_000.0)
        period_end = rebal_dates[i + 1] if i + 1 < len(rebal_dates) else prices.index[-1]
        period_dates = prices.index[(prices.index > reb_date) & (prices.index <= period_end)]
        if len(period_dates) == 0:
            drifted_weights = target
            continue
        # Buy and hold within the period: each name's value compounds on its own,
        # any uninvested remainder (caps that cannot all bind) sits in cash at 0%.
        growth = (1 + daily_returns.loc[period_dates, target.index]).cumprod()
        values = growth.mul(target, axis=1)
        cash = 1.0 - target.sum()
        wealth = values.sum(axis=1) + cash
        period_returns = wealth.pct_change()
        period_returns.iloc[0] = wealth.iloc[0] - 1.0
        period_returns.iloc[0] -= cost  # rebalance cost, paid once at the start of the period
        portfolio_daily_returns.loc[period_dates] = period_returns
        drifted_weights = values.iloc[-1] / wealth.iloc[-1]
    equity_curve = (1 + portfolio_daily_returns).cumprod()
    # Measure from the first rebalance that actually held positions; the
    # score warm-up before it is cash at 0% and would dilute every metric.
    if first_invested is not None:
        equity_curve = equity_curve[equity_curve.index >= first_invested]
    bench_returns = benchmark_prices.pct_change().fillna(0).reindex(equity_curve.index).fillna(0)
    # The strategy earns nothing on its first day (it buys at that close), so the benchmark must not either.
    if len(bench_returns):
        bench_returns.iloc[0] = 0.0
    benchmark_curve = (1 + bench_returns).cumprod()
    metrics = compute_performance_metrics(portfolio_daily_returns.loc[equity_curve.index], bench_returns)
    return BacktestResult(
        equity_curve=equity_curve,
        benchmark_curve=benchmark_curve,
        turnover_by_period=pd.Series(turnover_log),
        metrics=metrics,
    )

def compute_performance_metrics(returns: pd.Series, benchmark_returns: pd.Series,
                                 rf_annual: float = 0.0) -> dict:
    n_days = len(returns)
    if n_days == 0:
        return {}
    cumulative = (1 + returns).prod()
    years = n_days / 252.0
    cagr = cumulative ** (1 / years) - 1 if years > 0 else np.nan
    ann_vol = returns.std() * np.sqrt(252)
    rf_daily = rf_annual / 252.0
    sharpe = ((returns.mean() - rf_daily) / returns.std()) * np.sqrt(252) if returns.std() > 0 else np.nan
    equity = (1 + returns).cumprod()
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    max_drawdown = drawdown.min()
    calmar = cagr / abs(max_drawdown) if max_drawdown != 0 else np.nan
    downside = returns[returns < 0]
    sortino = ((returns.mean() - rf_daily) / downside.std()) * np.sqrt(252) if len(downside) > 0 and downside.std() > 0 else np.nan
    bench_cumulative = (1 + benchmark_returns).prod()
    bench_cagr = bench_cumulative ** (1 / years) - 1 if years > 0 else np.nan
    cov = np.cov(returns, benchmark_returns)[0, 1] if len(returns) == len(benchmark_returns) and len(returns) > 1 else np.nan
    bench_var = benchmark_returns.var()
    beta = cov / bench_var if bench_var else np.nan
    win_rate = (returns > 0).mean()
    return {
        "CAGR": cagr,
        "Annualized Volatility": ann_vol,
        "Sharpe Ratio": sharpe,
        "Sortino Ratio": sortino,
        "Max Drawdown": max_drawdown,
        "Calmar Ratio": calmar,
        "Beta vs Benchmark": beta,
        "Benchmark CAGR": bench_cagr,
        "Excess CAGR vs Benchmark": cagr - bench_cagr if pd.notna(cagr) and pd.notna(bench_cagr) else np.nan,
        "Daily Win Rate": win_rate,
        "Total Return": cumulative - 1,
    }
