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
from dataclasses import dataclass
from typing import Callable, Optional
import numpy as np
import pandas as pd
from . import config as cfg_module
from .scoring import cross_sectional_zscore

# ---------------------------------------------------------------------------
# Default, look-ahead-safe score function: momentum + low-vol, price-only
# ---------------------------------------------------------------------------
def default_price_only_score(as_of: pd.Timestamp, price_history: pd.DataFrame) -> pd.Series:
    """
    price_history: all daily prices up to (and including) `as_of` -- nothing
    later is passed in, so there is no way for this function to see the future.
    Returns a composite score per ticker (12-1 momentum + 60d inverse vol).
    """
    prices = price_history.sort_index()
    if len(prices) < 280:
        return pd.Series(dtype=float)
    p_end = prices.iloc[-22]     # skip most recent month (12-1 momentum convention)
    p_12m = prices.iloc[-274] if len(prices) >= 274 else prices.iloc[0]
    mom_12_1 = (p_end / p_12m) - 1.0
    returns = prices.pct_change()
    vol_60d = returns.tail(60).std() * np.sqrt(252)
    low_vol_score = -1.0 * vol_60d  # lower vol = higher score
    df = pd.DataFrame({"mom_12_1": mom_12_1, "low_vol": low_vol_score})
    df["ticker"] = df.index
    z_mom = cross_sectional_zscore(df, "mom_12_1", sector_neutral=False)
    z_vol = cross_sectional_zscore(df, "low_vol", sector_neutral=False)
    composite = 0.7 * z_mom.fillna(0) + 0.3 * z_vol.fillna(0)
    return composite.sort_values(ascending=False)

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

def run_backtest(prices: pd.DataFrame, benchmark_prices: pd.Series, cfg,
                  score_func: Callable = default_price_only_score,
                  start: Optional[str] = None, end: Optional[str] = None,
                  top_n: Optional[int] = None,
                  transaction_cost_bps: float = 10.0) -> BacktestResult:
    prices = prices.sort_index()
    if start:
        prices = prices[prices.index >= start]
    if end:
        prices = prices[prices.index <= end]
    top_n = top_n or cfg.top_n
    rebal_dates = _rebalance_dates(prices.index, cfg_module.REBALANCE_FREQUENCY)
    daily_returns = prices.pct_change().fillna(0)
    portfolio_daily_returns = pd.Series(0.0, index=prices.index)
    turnover_log = {}
    current_weights = pd.Series(dtype=float)
    for i, reb_date in enumerate(rebal_dates):
        history_up_to = prices.loc[:reb_date]
        scores = score_func(reb_date, history_up_to)
        scores = scores.dropna()
        if scores.empty:
            continue
        top = scores.head(top_n)
        # inverse-vol position sizing, consistent with portfolio.py's live logic
        vol = daily_returns.loc[:reb_date, top.index].tail(60).std() * np.sqrt(252)
        vol = vol.replace(0, np.nan).fillna(vol.median())
        inv_vol = 1.0 / vol
        new_weights = inv_vol / inv_vol.sum()
        new_weights = new_weights.clip(upper=cfg.max_position_weight)
        new_weights = new_weights / new_weights.sum()
        turnover = (new_weights.reindex(current_weights.index.union(new_weights.index), fill_value=0)
                    - current_weights.reindex(current_weights.index.union(new_weights.index), fill_value=0)
                    ).abs().sum()
        turnover_log[reb_date] = turnover
        cost = turnover * (transaction_cost_bps / 10_000.0)
        current_weights = new_weights
        period_end = rebal_dates[i + 1] if i + 1 < len(rebal_dates) else prices.index[-1]
        period_mask = (prices.index > reb_date) & (prices.index <= period_end)
        period_dates = prices.index[period_mask]
        if len(period_dates) == 0:
            continue
        held_returns = daily_returns.loc[period_dates, current_weights.index].fillna(0)
        weighted_returns = held_returns.mul(current_weights, axis=1).sum(axis=1)
        # apply the rebalance transaction cost as a one-time drag on the first day of the period
        weighted_returns.iloc[0] -= cost
        portfolio_daily_returns.loc[period_dates] = weighted_returns
    equity_curve = (1 + portfolio_daily_returns).cumprod()
    equity_curve = equity_curve[equity_curve.index >= rebal_dates[0]] if len(rebal_dates) else equity_curve
    bench_returns = benchmark_prices.pct_change().fillna(0).reindex(equity_curve.index).fillna(0)
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
