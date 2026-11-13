import numpy as np
import pandas as pd
import pytest

from app.quant import backtest
from app.quant.config import RunConfig

N_DAYS = 520
WARMUP_ROWS = 280  # default_price_only_score needs this much history before it scores anything


def _synthetic_prices(n_tickers: int = 12) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2024-01-01", periods=N_DAYS)
    rets = rng.normal(0.0004, 0.015, size=(N_DAYS, n_tickers))
    return pd.DataFrame(100 * np.cumprod(1 + rets, axis=0), index=dates, columns=[f"T{i}" for i in range(n_tickers)])


def test_equity_curve_starts_when_the_strategy_first_holds_something():
    prices = _synthetic_prices()
    bench = prices.mean(axis=1)

    res = backtest.run_backtest(prices, bench, RunConfig())

    # Before the fix the curve began at the first month-end and carried ~13
    # months of 0% "returns" into CAGR, Sharpe, volatility and win rate.
    assert res.equity_curve.index[0] >= prices.index[WARMUP_ROWS - 1]
    assert (res.equity_curve.diff().iloc[1:22] != 0).all()


def test_performance_metrics_on_known_returns():
    returns = pd.Series([0.01, -0.005] * 126)

    m = backtest.compute_performance_metrics(returns, returns)

    assert m["Daily Win Rate"] == pytest.approx(0.5)
    assert m["Beta vs Benchmark"] == pytest.approx(1.0)
    assert m["Excess CAGR vs Benchmark"] == pytest.approx(0.0)
    assert m["Max Drawdown"] == pytest.approx(-0.005)


def test_benchmark_is_generated_on_the_stored_price_dates():
    from app.quant import data

    # A DB seeded weeks ago has prices ending in the past, not today.
    dates = pd.bdate_range(end="2026-08-28", periods=N_DAYS)

    bench = data.fetch_benchmark(dates)

    assert bench.index.equals(dates)
    assert bench.equals(data.fetch_benchmark(dates))  # deterministic, not tied to "today"
