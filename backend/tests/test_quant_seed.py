import numpy as np
import pandas as pd
import pytest

from app.quant_seed import generate_benchmark_series, generate_price_history


def test_price_path_ends_at_price_and_matches_stated_one_year_return():
    s = generate_price_history("AAA", 100.0, 25.0, 20.0, beta=1.1)

    assert s.iloc[-1] == pytest.approx(100.0)
    assert s.iloc[-1] / s.iloc[-253] - 1 == pytest.approx(0.25)


def test_older_drift_does_not_come_from_the_stated_return():
    low = generate_price_history("AAA", 100.0, -20.0, 20.0)
    high = generate_price_history("AAA", 100.0, 60.0, 20.0)
    first_year = slice(0, 268)

    # Same ticker, same shocks: only the final year may differ.
    np.testing.assert_allclose(
        np.diff(np.log(low.iloc[first_year])), np.diff(np.log(high.iloc[first_year])))


def test_stocks_load_on_the_benchmark_market_factor():
    stock = generate_price_history("BBB", 50.0, 10.0, 25.0, beta=1.3)
    bench = generate_benchmark_series(stock.index)
    rs, rb = stock.pct_change().dropna(), bench.pct_change().dropna()

    beta = np.cov(rs, rb)[0, 1] / rb.var()

    assert 0.9 < beta < 1.7
    assert isinstance(bench.index, pd.DatetimeIndex)
