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


def test_benchmark_starts_at_one_on_the_strategy_start_date():
    prices = _synthetic_prices()
    bench = prices.mean(axis=1)

    res = backtest.run_backtest(prices, bench, RunConfig())

    assert res.benchmark_curve.index[0] == res.equity_curve.index[0]
    assert res.benchmark_curve.iloc[0] == pytest.approx(1.0)
    assert res.equity_curve.iloc[0] == pytest.approx(1.0)


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


def _fixed_score(as_of, history):
    return pd.Series({"UP": 2.0, "FLAT": 1.0, "OUT": 0.0})


def test_weights_drift_between_rebalances_instead_of_resetting_daily():
    dates = pd.bdate_range("2024-01-01", periods=80)
    prices = pd.DataFrame({
        "UP": 100 * 1.01 ** np.arange(80),
        "FLAT": np.full(80, 100.0),
        "OUT": np.full(80, 100.0),
    }, index=dates)
    cfg = RunConfig(top_n=2, buffer_multiplier=1.0, position_sizing_method="equal_weight",
                    max_position_weight=1.0, max_sector_weight=1.0, min_position_weight=0.0)

    res = backtest.run_backtest(prices, prices["FLAT"], cfg, score_func=_fixed_score, transaction_cost_bps=0)

    start, second = res.turnover_by_period.index[:2]
    k = len(prices.loc[start:second]) - 1
    # Buy and hold of 50/50: half compounds at 1%/day, half stays flat.
    assert res.equity_curve.loc[second] == pytest.approx(0.5 * 1.01 ** k + 0.5)
    # Rebalancing back to 50/50 must trade away the drift, so turnover is positive.
    assert res.turnover_by_period.loc[second] > 0


def test_backtest_sizes_with_the_live_portfolio_functions(monkeypatch):
    from app.quant import portfolio

    calls = []
    real = portfolio.size_positions
    monkeypatch.setattr(portfolio, "size_positions", lambda *a, **k: calls.append(1) or real(*a, **k))
    prices = _synthetic_prices()
    sectors = pd.Series({t: "S" + str(i % 3) for i, t in enumerate(prices.columns)})

    backtest.run_backtest(prices, prices.mean(axis=1), RunConfig(), sectors=sectors)

    assert calls


def test_price_only_score_ignores_prices_after_the_rebalance_date():
    prices = _synthetic_prices()
    as_of = prices.index[300]
    tampered = prices.copy()
    tampered.iloc[301:] *= np.linspace(0.2, 5.0, prices.shape[1])  # rewrite the future

    clean = backtest.default_price_only_score(as_of, prices.loc[:as_of])
    after = backtest.default_price_only_score(as_of, tampered.loc[:as_of])

    pd.testing.assert_series_equal(clean, after)
    assert clean.notna().all() and len(clean) == prices.shape[1]


def test_backtest_path_before_a_date_does_not_depend_on_later_prices():
    prices = _synthetic_prices()
    cut = prices.index[400]
    tampered = prices.copy()
    tampered.loc[tampered.index > cut] *= np.linspace(0.2, 5.0, prices.shape[1])

    a = backtest.run_backtest(prices, prices.mean(axis=1), RunConfig())
    b = backtest.run_backtest(tampered, tampered.mean(axis=1), RunConfig())

    pd.testing.assert_series_equal(a.equity_curve.loc[:cut], b.equity_curve.loc[:cut])


def test_backtest_reports_ic_and_an_equal_weight_benchmark():
    prices = _synthetic_prices()

    res = backtest.run_backtest(prices, prices.mean(axis=1), RunConfig())

    assert {"Mean IC", "IC t-stat", "IC Periods", "Equal-Weight CAGR"} <= set(res.metrics)
    assert res.metrics["IC Periods"] == len(res.ic_by_period) > 3
    assert res.ic_by_period.between(-1, 1).all()
    assert res.equal_weight_curve.index.equals(res.equity_curve.index)
    assert res.equal_weight_curve.iloc[0] == pytest.approx(1.0)


def test_ic_summary_t_stat():
    s = backtest.ic_summary(pd.Series([0.1, 0.2, 0.3]))

    assert s["Mean IC"] == pytest.approx(0.2)
    assert s["IC t-stat"] == pytest.approx(0.2 / (0.1 / np.sqrt(3)))
    assert s["IC Periods"] == 3


def test_spearman_ic_is_one_for_a_perfect_ranking():
    scores = pd.Series({"A": 3.0, "B": 2.0, "C": 1.0})

    assert backtest.spearman_ic(scores, pd.Series({"A": 0.5, "B": 0.1, "C": -0.2})) == pytest.approx(1.0)
