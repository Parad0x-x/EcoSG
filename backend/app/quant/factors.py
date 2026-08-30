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

# ---------------------------------------------------------------------------
# Value
# ---------------------------------------------------------------------------
def compute_value_factors(fund: pd.DataFrame) -> pd.DataFrame:
    df = fund.copy()
    ev = df["enterpriseValue"].replace(0, np.nan)
    ebit_proxy = df["ebitda"]  # yfinance doesn't expose EBIT directly; EBITDA is the closest free proxy
    df["earnings_yield"] = ebit_proxy / ev
    df["fcf_yield"] = df["freeCashflow"] / ev
    df["book_to_price"] = 1.0 / df["priceToBook"].replace(0, np.nan)
    ev_to_ebitda = ev / ebit_proxy.replace(0, np.nan)
    df["ev_to_ebitda_inv"] = 1.0 / ev_to_ebitda  # invert: higher = cheaper = better
    return df[["ticker", "earnings_yield", "fcf_yield", "book_to_price", "ev_to_ebitda_inv"]]

# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------
def compute_quality_factors(fund: pd.DataFrame) -> pd.DataFrame:
    df = fund.copy()
    df["roic"] = df["returnOnAssets"]  # yfinance has no direct ROIC; ROA is the closest free proxy
                                        # (swap in true ROIC = EBIT*(1-tax) / invested capital if you
                                        #  have balance-sheet line items -- see README for the formula)
    df["roe"] = df["returnOnEquity"]
    df["gross_margin"] = df["grossMargins"]
    dte = df["debtToEquity"].replace(0, np.nan)
    df["debt_to_equity_inv"] = 1.0 / (1.0 + dte.abs())  # bounded, higher = less levered = better
    # Earnings stability isn't in a single snapshot field; approximate with
    # margin stability if multi-period data isn't available.
    df["earnings_stability"] = df["profitMargins"].clip(lower=-1, upper=1)
    return df[["ticker", "roic", "roe", "gross_margin", "debt_to_equity_inv", "earnings_stability"]]

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
    # yfinance's snapshot .info has no 3yr CAGR field; without multi-year
    # financial statements pulled separately it collapses to the YoY figure.
    # See README for how to extend this with df["revenue"] time series from
    # ticker.financials for a true 3-year CAGR.
    df["revenue_growth_3y_cagr"] = df["revenueGrowth"]
    return df[["ticker", "revenue_growth_yoy", "revenue_growth_3y_cagr", "eps_growth_yoy"]]

# ---------------------------------------------------------------------------
# Low volatility
# ---------------------------------------------------------------------------
def compute_low_vol_factors(prices: pd.DataFrame, fund: pd.DataFrame,
                             window: int = 60) -> pd.DataFrame:
    returns = prices.pct_change()
    realized_vol = returns.tail(window).std() * np.sqrt(252)
    realized_vol_inv = 1.0 / realized_vol.replace(0, np.nan)
    beta = fund.set_index("ticker")["beta"].reindex(prices.columns)
    beta_closeness = -1.0 * (beta - 1.0).abs()  # closer to market beta=1 scores higher (less idiosyncratic risk)
    out = pd.DataFrame({
        "ticker": prices.columns,
        "realized_vol_inv": realized_vol_inv.values,
        "beta_closeness": beta_closeness.values,
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
