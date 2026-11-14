"""
factors.py
----------
Turns raw fundamentals + price history into the individual factor metrics
hedge funds actually screen on: value, quality, momentum, growth, low-vol.
Every function here is a pure transformation: DataFrame(s) in, DataFrame out.
No network calls live in this file -- that separation is what makes the
pipeline testable (feed it synthetic data) and swappable (feed it data from
any provider that matches the same schema).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

BETA_SHRINK_WEIGHT = 0.5

# ---------------------------------------------------------------------------
# Shared accounting proxies
# ---------------------------------------------------------------------------
def _net_income(df: pd.DataFrame) -> pd.Series:
    return df["profitMargins"] * df["totalRevenue"]

def _total_assets(df: pd.DataFrame) -> pd.Series:
    """Assets backed out of ROA = NI / assets. NaN unless both are usable and
    the implied assets are positive (a loss with negative ROA still works)."""
    roa = df["returnOnAssets"].replace(0, np.nan)
    assets = _net_income(df) / roa
    return assets.where(assets > 0)

# ---------------------------------------------------------------------------
# Value
# ---------------------------------------------------------------------------
def compute_value_factors(fund: pd.DataFrame) -> pd.DataFrame:
    df = fund.copy()
    ev = df["enterpriseValue"].where(df["enterpriseValue"] > 0)
    # EBIT proxy = operating margin x revenue. EBITDA/EV and the old inverted
    # EV/EBITDA were the same number twice; EBIT also charges depreciation.
    df["earnings_yield"] = df["operatingMargins"] * df["totalRevenue"] / ev
    df["fcf_yield"] = df["freeCashflow"] / ev
    df["book_to_price"] = 1.0 / df["priceToBook"].replace(0, np.nan)
    # Equity-level earnings yield (E/P), a distinct view from the EV-level one.
    df["earnings_to_price"] = 1.0 / df["trailingPE"].replace(0, np.nan)
    return df[["ticker", "earnings_yield", "fcf_yield", "book_to_price", "earnings_to_price"]]

# ---------------------------------------------------------------------------
# Quality (profitability, cash-based earnings quality, safety; see
# Asness, Frazzini, Pedersen "Quality Minus Junk" and Novy-Marx 2013)
# ---------------------------------------------------------------------------
def compute_quality_factors(fund: pd.DataFrame) -> pd.DataFrame:
    df = fund.copy()
    df["roic"] = df["returnOnAssets"]  # no balance-sheet line items for true ROIC; ROA is the proxy
    df["roe"] = df["returnOnEquity"]
    assets = _total_assets(df)
    net_income = _net_income(df)
    # Gross profits to assets (Novy-Marx 2013): the cleanest profitability measure.
    df["gpoa"] = df["grossMargins"] * df["totalRevenue"] / assets
    # Cash flow over assets and (negative) accruals, both from QMJ: profits
    # backed by cash beat profits that are mostly accounting accruals.
    df["cfoa"] = df["freeCashflow"] / assets
    df["accruals"] = -(net_income - df["freeCashflow"]) / assets
    # Zero debt is the best case, so it must stay 0 (score 1.0), not become missing.
    df["debt_to_equity_inv"] = 1.0 / (1.0 + df["debtToEquity"].abs())
    return df[["ticker", "roic", "roe", "gpoa", "cfoa", "accruals", "debt_to_equity_inv"]]

# ---------------------------------------------------------------------------
# Momentum (computed from price history -- no look-ahead issue, unlike fundamentals)
# ---------------------------------------------------------------------------
def compute_momentum_factors(prices: pd.DataFrame, as_of: pd.Timestamp = None) -> pd.DataFrame:
    """
    Classic academic momentum: total return over a lookback window, SKIPPING
    the most recent month (the '12-1' convention). Skipping the last month
    avoids short-term reversal, which is a well-documented *opposite* effect
    to momentum over 1-month horizons (Jegadeesh & Titman, 1993).
    """
    prices = prices.sort_index()
    if as_of is None:
        as_of = prices.index[-1]
    def total_return(window_trading_days: int, skip_trading_days: int) -> pd.Series:
        end_idx = prices.index.get_indexer([as_of], method="ffill")[0] - skip_trading_days
        start_idx = end_idx - window_trading_days
        if start_idx < 0 or end_idx < 0:
            return pd.Series(np.nan, index=prices.columns)
        p_end = prices.iloc[end_idx]
        p_start = prices.iloc[start_idx]
        return (p_end / p_start) - 1.0
    mom_12_1 = total_return(window_trading_days=252, skip_trading_days=21)
    mom_6_1 = total_return(window_trading_days=126, skip_trading_days=21)
    out = pd.DataFrame({
        "ticker": prices.columns,
        "mom_12_1": mom_12_1.values,
        "mom_6_1": mom_6_1.values,
    })
    return out

# ---------------------------------------------------------------------------
# Growth
# ---------------------------------------------------------------------------
def compute_growth_factors(fund: pd.DataFrame) -> pd.DataFrame:
    df = fund.copy()
    df["revenue_growth_yoy"] = df["revenueGrowth"]
    df["eps_growth_yoy"] = df["earningsGrowth"]
    # No multi-year revenue history in the snapshot, so there is no 3-year CAGR
    # metric; it used to be a copy of the YoY figure, which double-counted it.
    return df[["ticker", "revenue_growth_yoy", "eps_growth_yoy"]]

# ---------------------------------------------------------------------------
# Low volatility
# ---------------------------------------------------------------------------
def compute_low_vol_factors(prices: pd.DataFrame, fund: pd.DataFrame,
                             window: int = 60) -> pd.DataFrame:
    returns = prices.pct_change()
    realized_vol = returns.tail(window).std() * np.sqrt(252)
    realized_vol_inv = 1.0 / realized_vol.replace(0, np.nan)
    beta = fund.set_index("ticker")["beta"].reindex(prices.columns)
    # Betting Against Beta (Frazzini, Pedersen): low-beta stocks earn more per
    # unit of risk. Shrink toward 1 (Vasicek-style, weight 0.5) since a single
    # beta estimate is noisy; higher score = lower beta.
    low_beta = -(BETA_SHRINK_WEIGHT * beta + (1.0 - BETA_SHRINK_WEIGHT) * 1.0)
    out = pd.DataFrame({
        "ticker": prices.columns,
        "realized_vol_inv": realized_vol_inv.values,
        "low_beta": low_beta.values,
    })
    return out

# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def build_all_factors(fund: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """Merge all raw factor metrics into one wide DataFrame keyed by ticker."""
    value = compute_value_factors(fund)
    quality = compute_quality_factors(fund)
    momentum = compute_momentum_factors(prices)
    growth = compute_growth_factors(fund)
    low_vol = compute_low_vol_factors(prices, fund)
    out = value
    for other in (quality, momentum, growth, low_vol):
        out = out.merge(other, on="ticker", how="outer")
    # attach sector for sector-neutral scoring downstream
    if "sector" in fund.columns:
        out = out.merge(fund[["ticker", "sector"]], on="ticker", how="left")
    return out
