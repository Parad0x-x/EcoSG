"""Query + orchestration glue for the quant factor model -- the quant-side
analogue of app/service.py. Keeps factors.py/scoring.py/portfolio.py/
backtest.py untouched (pure, data-source-agnostic) and the routers thin.
"""
from __future__ import annotations

import math

import pandas as pd
from sqlalchemy.orm import Session

from ..models import Company
from . import backtest, data, factors, scoring
from .config import RunConfig


def _clean(value: float | None) -> float | None:
    """NaN/inf -> None so Pydantic/JSON don't choke on them."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def compute_quant_scores(db: Session) -> tuple[pd.DataFrame, RunConfig]:
    """Full pipeline: universe -> fundamentals + prices -> factors -> composite
    score + rank, for every company ECOSG covers. Returns the scored
    DataFrame (one row per ticker, sorted by rank) and the RunConfig used.
    """
    universe = data.get_universe(db)
    tickers = universe["ticker"].tolist()
    fund = data.fetch_fundamentals(db, tickers)
    prices = data.fetch_price_history(db, tickers)
    prices = prices[[t for t in tickers if t in prices.columns]]

    raw = factors.build_all_factors(fund, prices)
    cfg = RunConfig()
    scored = scoring.compute_composite_score(raw, cfg)

    name_map = {c.ticker: c.name for c in db.query(Company).all()}
    scored = scored.copy()
    scored["name"] = scored["ticker"].map(name_map)

    n = len(scored)
    scored["percentile"] = scored["rank"].apply(
        lambda r: round(100.0 * (n - r + 1) / n, 1) if n else 50.0
    )
    return scored, cfg


def get_company_row(scored: pd.DataFrame, ticker: str) -> pd.Series | None:
    match = scored[scored["ticker"] == ticker.upper()]
    if match.empty:
        return None
    return match.iloc[0]


def run_universe_backtest(db: Session) -> dict:
    """Runs the walk-forward backtest (price-only momentum + low-vol score,
    the same look-ahead-safe default the original project ships) over the
    full stored synthetic price history vs. the synthetic benchmark.
    """
    universe = data.get_universe(db)
    tickers = universe["ticker"].tolist()
    prices = data.fetch_price_history(db, tickers)
    benchmark = data.fetch_benchmark(prices.index)

    cfg = RunConfig()
    from .config import TRANSACTION_COST_BPS
    result = backtest.run_backtest(prices, benchmark, cfg, transaction_cost_bps=TRANSACTION_COST_BPS)

    metric_key_map = {
        "CAGR": "cagr",
        "Annualized Volatility": "annualized_volatility",
        "Sharpe Ratio": "sharpe_ratio",
        "Sortino Ratio": "sortino_ratio",
        "Max Drawdown": "max_drawdown",
        "Calmar Ratio": "calmar_ratio",
        "Beta vs Benchmark": "beta_vs_benchmark",
        "Benchmark CAGR": "benchmark_cagr",
        "Excess CAGR vs Benchmark": "excess_cagr_vs_benchmark",
        "Daily Win Rate": "daily_win_rate",
        "Total Return": "total_return",
    }
    metrics = {v: _clean(result.metrics.get(k)) for k, v in metric_key_map.items()}

    equity_curve = [
        {
            "date": dt.strftime("%Y-%m-%d"),
            "portfolio": _clean(p) or 0.0,
            "benchmark": _clean(b) or 0.0,
        }
        for dt, p, b in zip(
            result.equity_curve.index,
            result.equity_curve.values,
            result.benchmark_curve.reindex(result.equity_curve.index).values,
        )
    ]

    return {"metrics": metrics, "equity_curve": equity_curve}
