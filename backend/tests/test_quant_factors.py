import numpy as np
import pandas as pd
import pytest

from app.quant import factors


def _fund(**overrides):
    base = dict(
        ticker=["A", "B", "C"], enterpriseValue=[100.0, 100.0, 100.0], ebitda=[10.0, 10.0, 10.0],
        operatingMargins=[0.2, 0.1, 0.1], totalRevenue=[50.0, 50.0, 50.0], freeCashflow=[5.0, 5.0, 5.0],
        priceToBook=[2.0, 2.0, 2.0], trailingPE=[10.0, 20.0, 20.0], returnOnAssets=[0.05, 0.05, 0.05],
        returnOnEquity=[0.1, 0.1, 0.1], grossMargins=[0.5, 0.5, 0.5], profitMargins=[0.1, 0.1, 0.1],
        debtToEquity=[0.0, 50.0, np.nan], beta=[0.6, 1.0, 1.6],
    )
    base.update(overrides)
    return pd.DataFrame(base)


def test_earnings_yield_uses_ebit_and_ep_replaces_the_ebitda_duplicate():
    v = factors.compute_value_factors(_fund())

    assert v["earnings_yield"].tolist() == pytest.approx([0.10, 0.05, 0.05])
    assert v["earnings_to_price"].tolist() == pytest.approx([0.1, 0.05, 0.05])
    assert "ev_to_ebitda_inv" not in v


def test_zero_debt_scores_best_and_missing_debt_stays_missing():
    q = factors.compute_quality_factors(_fund())

    assert q["debt_to_equity_inv"].iloc[0] == pytest.approx(1.0)
    assert q["debt_to_equity_inv"].iloc[0] > q["debt_to_equity_inv"].iloc[1]
    assert np.isnan(q["debt_to_equity_inv"].iloc[2])


def test_cash_based_quality_metrics_from_derived_assets():
    # NI = 0.1 * 50 = 5, assets = 5 / 0.05 = 100
    q = factors.compute_quality_factors(_fund(freeCashflow=[8.0, 5.0, 2.0]))

    assert q["gpoa"].tolist() == pytest.approx([0.25, 0.25, 0.25])
    assert q["cfoa"].tolist() == pytest.approx([0.08, 0.05, 0.02])
    assert q["accruals"].tolist() == pytest.approx([0.03, 0.0, -0.03])


def test_quality_metrics_are_missing_when_assets_cannot_be_derived():
    q = factors.compute_quality_factors(_fund(returnOnAssets=[0.0, np.nan, 0.05]))

    assert q[["gpoa", "cfoa", "accruals"]].iloc[:2].isna().all().all()
    assert q["gpoa"].iloc[2] == pytest.approx(0.25)


def test_growth_has_no_duplicated_cagr_column():
    g = factors.compute_growth_factors(_fund(revenueGrowth=[0.1] * 3, earningsGrowth=[0.2] * 3))

    assert list(g.columns) == ["ticker", "revenue_growth_yoy", "eps_growth_yoy"]


def test_low_beta_scores_higher_than_high_beta():
    rng = np.random.default_rng(1)
    prices = pd.DataFrame(100 * np.cumprod(1 + rng.normal(0, 0.01, (120, 3)), axis=0), columns=["A", "B", "C"])

    lv = factors.compute_low_vol_factors(prices, _fund()).set_index("ticker")

    assert lv.loc["A", "low_beta"] > lv.loc["B", "low_beta"] > lv.loc["C", "low_beta"]
    assert lv.loc["A", "low_beta"] == pytest.approx(-0.8)  # shrunk halfway to 1


def _market_universe(n_days=300):
    rng = np.random.default_rng(7)
    m = rng.normal(0.002, 0.01, n_days)  # rising market
    rets = {
        "HIBETA": 2.0 * m,                                  # pure market exposure, no alpha
        "ALPHA": 0.5 * m + 0.001,                           # steady stock-specific drift
        "NOISY": m + rng.normal(0, 0.03, n_days),           # large idiosyncratic risk
    }
    for i in range(5):
        rets[f"F{i}"] = m + rng.normal(0, 0.005, n_days)
    rets = pd.DataFrame(rets)
    rets.iloc[0] = 0.0
    return 100 * (1 + rets).cumprod()


def test_residual_momentum_rewards_stock_specific_trend_not_market_beta():
    mom = factors.compute_momentum_factors(_market_universe()).set_index("ticker")

    assert mom.loc["HIBETA", "mom_12_1"] > mom.loc["ALPHA", "mom_12_1"]
    assert mom.loc["ALPHA", "resid_mom"] > mom.loc["HIBETA", "resid_mom"]


def test_idiosyncratic_vol_separates_market_risk_from_stock_risk():
    prices = _market_universe()
    fund = pd.DataFrame({"ticker": prices.columns, "beta": 1.0})

    lv = factors.compute_low_vol_factors(prices, fund).set_index("ticker")

    assert lv.loc["HIBETA", "idio_vol_inv"] > lv.loc["NOISY", "idio_vol_inv"]
