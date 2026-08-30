"""Synthetic quant-factor data generation for the ECOSG mock universe.

This is the bridge between ECOSG's existing mock dataset (data_seed.py --
ticker, sector, price, returns, ESG scores) and the hedge-fund-style factor
model ported into quant/. That model expects the same shape of data a real
fundamentals provider (yfinance-style) and a real price-history provider
would return; this module manufactures a plausible, internally-consistent
version of both, deterministically (seeded per ticker) so re-seeding the
database always produces the same numbers.

Nothing here is real financial data -- see data_seed.py's module docstring
for the same disclaimer, which applies equally here.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Sector-level baseline distributions for fundamentals not already present in
# data_seed.py. These exist so the factor model has real cross-sectional
# signal to find (e.g. Tech skews high-margin/high-growth/expensive, Energy
# skews cheap/high-leverage/low-growth) rather than pure noise.
# Each tuple is (mean, stdev) unless noted otherwise.
# ---------------------------------------------------------------------------
SECTOR_PROFILES: dict[str, dict[str, tuple[float, float]]] = {
    "Technology":             dict(pe=(32, 8), pb=(9, 3),  roe=(0.28, 0.08), roa=(0.14, 0.05), gross_margin=(0.62, 0.10), debt_equity=(45, 25), rev_growth=(0.14, 0.08), eps_growth=(0.16, 0.10), beta=(1.15, 0.20)),
    "Energy":                 dict(pe=(11, 3),  pb=(1.8, 0.6), roe=(0.13, 0.06), roa=(0.07, 0.03), gross_margin=(0.35, 0.08), debt_equity=(55, 20), rev_growth=(0.02, 0.06), eps_growth=(0.00, 0.12), beta=(1.05, 0.20)),
    "Utilities":               dict(pe=(18, 3),  pb=(2.0, 0.5), roe=(0.10, 0.03), roa=(0.03, 0.01), gross_margin=(0.45, 0.08), debt_equity=(120, 30), rev_growth=(0.04, 0.03), eps_growth=(0.04, 0.05), beta=(0.55, 0.12)),
    "Financials":              dict(pe=(13, 3),  pb=(1.6, 0.5), roe=(0.14, 0.04), roa=(0.011, 0.004), gross_margin=(0.55, 0.10), debt_equity=(180, 50), rev_growth=(0.06, 0.05), eps_growth=(0.08, 0.08), beta=(1.10, 0.20)),
    "Health Care":             dict(pe=(20, 6),  pb=(4.5, 1.5), roe=(0.18, 0.07), roa=(0.08, 0.03), gross_margin=(0.58, 0.12), debt_equity=(60, 25), rev_growth=(0.06, 0.06), eps_growth=(0.05, 0.10), beta=(0.80, 0.18)),
    "Consumer Staples":        dict(pe=(21, 4),  pb=(5.5, 1.5), roe=(0.30, 0.08), roa=(0.09, 0.03), gross_margin=(0.44, 0.08), debt_equity=(80, 25), rev_growth=(0.04, 0.04), eps_growth=(0.05, 0.06), beta=(0.60, 0.12)),
    "Consumer Discretionary":  dict(pe=(24, 8),  pb=(6.0, 2.5), roe=(0.24, 0.10), roa=(0.09, 0.04), gross_margin=(0.38, 0.10), debt_equity=(70, 30), rev_growth=(0.09, 0.08), eps_growth=(0.10, 0.14), beta=(1.20, 0.22)),
    "Communication Services":  dict(pe=(19, 6),  pb=(4.5, 1.8), roe=(0.16, 0.08), roa=(0.07, 0.03), gross_margin=(0.55, 0.12), debt_equity=(65, 25), rev_growth=(0.08, 0.08), eps_growth=(0.09, 0.12), beta=(1.05, 0.20)),
    "Materials":               dict(pe=(16, 4),  pb=(2.8, 0.8), roe=(0.15, 0.05), roa=(0.06, 0.02), gross_margin=(0.32, 0.08), debt_equity=(55, 20), rev_growth=(0.03, 0.06), eps_growth=(0.02, 0.12), beta=(1.00, 0.18)),
    "Industrials":             dict(pe=(19, 5),  pb=(4.0, 1.2), roe=(0.19, 0.06), roa=(0.07, 0.03), gross_margin=(0.34, 0.08), debt_equity=(65, 25), rev_growth=(0.05, 0.05), eps_growth=(0.06, 0.10), beta=(1.05, 0.18)),
}

DEFAULT_PROFILE = dict(pe=(18, 5), pb=(3.5, 1.5), roe=(0.16, 0.06), roa=(0.06, 0.03),
                        gross_margin=(0.40, 0.10), debt_equity=(70, 25), rev_growth=(0.06, 0.06),
                        eps_growth=(0.06, 0.10), beta=(1.0, 0.2))


def _rng_for(ticker: str, salt: str) -> np.random.Generator:
    """Deterministic per-ticker RNG so re-seeding the DB is reproducible."""
    h = hashlib.sha256(f"{ticker}:{salt}".encode()).hexdigest()
    seed = int(h[:8], 16)
    return np.random.default_rng(seed)


def generate_fundamentals(ticker: str, sector: str, price: float, market_cap_b: float) -> dict:
    """Yfinance-`.info`-shaped fundamentals for one company, sector-aware and
    deterministic. Field names match hedge_stock_bot's FUNDAMENTAL_FIELDS."""
    rng = _rng_for(ticker, "fundamentals")
    p = SECTOR_PROFILES.get(sector, DEFAULT_PROFILE)

    def draw(key: str) -> float:
        mu, sigma = p[key]
        return float(rng.normal(mu, sigma))

    market_cap = market_cap_b * 1e9
    debt_to_equity = max(5.0, draw("debt_equity"))
    total_revenue = market_cap / max(1.0, draw("pe")) * rng.uniform(3.0, 6.0)  # rough revenue-scale anchor
    total_debt = market_cap * (debt_to_equity / 100.0) * rng.uniform(0.35, 0.55)
    enterprise_value = market_cap + total_debt * rng.uniform(0.7, 0.95)
    ebitda = total_revenue * max(0.05, draw("gross_margin") * rng.uniform(0.35, 0.55))
    free_cashflow = ebitda * rng.uniform(0.35, 0.75)
    total_cash = market_cap * rng.uniform(0.02, 0.12)

    return {
        "marketCap": market_cap,
        "enterpriseValue": enterprise_value,
        "trailingPE": max(3.0, draw("pe")),
        "priceToBook": max(0.3, draw("pb")),
        "returnOnEquity": draw("roe"),
        "returnOnAssets": draw("roa"),
        "grossMargins": min(0.9, max(0.05, draw("gross_margin"))),
        "operatingMargins": min(0.6, max(0.01, draw("gross_margin") * rng.uniform(0.3, 0.6))),
        "profitMargins": min(0.5, max(-0.1, draw("gross_margin") * rng.uniform(0.1, 0.35))),
        "debtToEquity": debt_to_equity,
        "freeCashflow": free_cashflow,
        "ebitda": ebitda,
        "revenueGrowth": draw("rev_growth"),
        "earningsGrowth": draw("eps_growth"),
        "beta": max(0.2, draw("beta")),
        "currentPrice": price,
        "totalRevenue": total_revenue,
        "totalDebt": total_debt,
        "totalCash": total_cash,
    }


def generate_price_history(ticker: str, current_price: float, one_year_return_pct: float,
                            volatility_pct: float, n_days: int = 520) -> pd.Series:
    """~2 years of synthetic daily closes ending exactly at `current_price`.

    Daily drift/vol are calibrated from the company's stated 1Y return and
    annualized volatility so the resulting price path -- and the momentum /
    low-vol factors computed from it -- are roughly consistent with the
    return and volatility already shown elsewhere in the app, without being
    a literal re-derivation of the same number (a real 12-1 momentum reading
    and a trailing-12-month total return are related but not identical
    measures, same as in live markets).
    """
    rng = _rng_for(ticker, "prices")
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n_days)

    annual_return = one_year_return_pct / 100.0
    mu_daily = np.log1p(annual_return) / 252.0
    sigma_daily = max(0.001, (volatility_pct / 100.0) / np.sqrt(252.0))

    daily_returns = rng.normal(mu_daily, sigma_daily, n_days)
    raw_path = np.cumprod(1 + daily_returns)
    # pin the path so it ends exactly at the stated current price
    scale = current_price / raw_path[-1]
    path = raw_path * scale
    return pd.Series(path, index=dates, name=ticker)


def generate_benchmark_series(n_days: int = 520) -> pd.Series:
    """Synthetic benchmark ('SPY'-like) series for the backtest engine."""
    rng = np.random.default_rng(20260830)
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n_days)
    daily_returns = rng.normal(0.00035, 0.011, n_days)
    path = 100.0 * np.cumprod(1 + daily_returns)
    return pd.Series(path, index=dates, name="SPY")
