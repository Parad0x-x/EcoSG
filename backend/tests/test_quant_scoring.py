import numpy as np
import pandas as pd
import pytest

from app.quant import scoring
from app.quant.config import RunConfig


def test_zscore_of_constant_series_is_zero():
    out = scoring.zscore(pd.Series([5.0, 5.0, 5.0]))

    assert (out == 0).all()


def test_sector_neutral_zscore_skips_sectors_with_fewer_than_three_names():
    df = pd.DataFrame({
        "sector": ["A", "A", "A", "B", "B"],
        "metric": [1.0, 2.0, 3.0, 10.0, 20.0],
    })

    z = scoring.cross_sectional_zscore(df, "metric")

    assert z.iloc[:3].tolist() == pytest.approx([-1.0, 0.0, 1.0])
    assert z.iloc[3:].isna().all()


def test_family_score_renormalizes_over_present_metrics():
    df = pd.DataFrame({
        "sector": ["A"] * 4,
        "a": [1.0, 2.0, 3.0, 4.0],
        "b": [4.0, 3.0, 2.0, np.nan],
    })

    family = scoring.score_factor_family(df, {"a": 0.5, "b": 0.5}, sector_neutral=False, winsor_lower=0, winsor_upper=1)
    z_a = scoring.zscore(df["a"])

    # Row 3 has no "b", so its score is its "a" z-score alone, not half of it.
    assert family.iloc[3] == pytest.approx(z_a.iloc[3])


def test_composite_ranks_best_name_first():
    rng = np.random.default_rng(0)
    n = 9
    df = pd.DataFrame({"ticker": [f"T{i}" for i in range(n)], "sector": ["S"] * n})
    for col in ["earnings_yield", "fcf_yield", "book_to_price", "ev_to_ebitda_inv", "roic", "roe",
                "gross_margin", "debt_to_equity_inv", "earnings_stability", "mom_12_1", "mom_6_1",
                "revenue_growth_yoy", "revenue_growth_3y_cagr", "eps_growth_yoy",
                "realized_vol_inv", "beta_closeness"]:
        df[col] = rng.normal(size=n)
    df.loc[4, df.columns[2:]] = 10.0  # dominant on every metric

    scored = scoring.compute_composite_score(df, RunConfig())

    assert scored.iloc[0]["ticker"] == "T4"
    assert sorted(scored["rank"].tolist()) == list(range(1, n + 1))
