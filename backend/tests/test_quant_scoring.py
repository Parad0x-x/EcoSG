import numpy as np
import pandas as pd
import pytest

from app.quant import scoring
from app.quant.config import RunConfig


def test_zscore_of_constant_series_is_zero():
    out = scoring.zscore(pd.Series([5.0, 5.0, 5.0]))

    assert (out == 0).all()


def test_rank_zscore_has_mean_zero_std_one_and_ignores_outliers():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 1e9, np.nan])

    z = scoring.rank_zscore(s)

    assert z.iloc[:5].mean() == pytest.approx(0.0)
    assert z.iloc[:5].std() == pytest.approx(1.0)
    assert np.isnan(z.iloc[5])
    # The 1e9 outlier is just "the largest", one rank step above 4.0.
    assert z.iloc[4] - z.iloc[3] == pytest.approx(z.iloc[1] - z.iloc[0])


def test_sector_mean_is_shrunk_toward_the_universe_mean():
    x = pd.Series([1.0, 2.0, 3.0, 10.0, 20.0, 30.0])
    sectors = pd.Series(["A", "A", "A", "B", "B", "B"])

    mu = scoring.shrunk_sector_mean(x, sectors, k=3)

    # (3 * 2 + 3 * 11) / 6 = 6.5 for A; (3 * 20 + 3 * 11) / 6 = 15.5 for B
    assert mu.tolist() == pytest.approx([6.5] * 3 + [15.5] * 3)


def test_one_missing_value_does_not_drop_its_whole_sector():
    df = pd.DataFrame({
        "sector": ["A", "A", "A", "B", "B", "B"],
        "metric": [1.0, np.nan, 3.0, 10.0, 20.0, 30.0],
    })

    z = scoring.cross_sectional_zscore(df, "metric")

    assert np.isnan(z.iloc[1])
    assert z.drop(index=1).notna().all()
    assert z.iloc[2] > z.iloc[0]


def test_sector_adjustment_is_partial_not_full():
    # Sector B is uniformly higher. Full neutralization would tie A's best with B's best;
    # with shrinkage B's names keep part of their level advantage.
    df = pd.DataFrame({"sector": ["A"] * 3 + ["B"] * 3, "metric": [1.0, 5.0, 9.0, 5.0, 9.0, 13.0]})

    z = scoring.cross_sectional_zscore(df, "metric", winsor_lower=0, winsor_upper=1)

    assert z.iloc[5] > z.iloc[2]
    assert z.iloc[3] < z.iloc[2]  # but B's worst no longer beats A's best


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
    from app.quant import config
    metrics = [m for w in (config.VALUE_WEIGHTS, config.QUALITY_WEIGHTS, config.MOMENTUM_WEIGHTS,
                           config.GROWTH_WEIGHTS, config.LOW_VOL_WEIGHTS) for m in w]
    for col in metrics:
        df[col] = rng.normal(size=n)
    df.loc[4, df.columns[2:]] = 10.0  # dominant on every metric

    scored = scoring.compute_composite_score(df, RunConfig())

    assert scored.iloc[0]["ticker"] == "T4"
    assert sorted(scored["rank"].tolist()) == list(range(1, n + 1))


def test_family_scores_are_restandardized_before_the_composite():
    rng = np.random.default_rng(3)
    n = 12
    from app.quant import config
    df = pd.DataFrame({"ticker": [f"T{i}" for i in range(n)], "sector": ["S"] * n})
    for w in (config.VALUE_WEIGHTS, config.QUALITY_WEIGHTS, config.MOMENTUM_WEIGHTS,
              config.GROWTH_WEIGHTS, config.LOW_VOL_WEIGHTS):
        for m in w:
            df[m] = rng.normal(size=n)

    scored = scoring.compute_composite_score(df, RunConfig())

    for fam in ["value", "quality", "momentum", "growth", "low_vol"]:
        assert scored[f"{fam}_score"].mean() == pytest.approx(0.0, abs=1e-12)
        assert scored[f"{fam}_score"].std() == pytest.approx(1.0)
