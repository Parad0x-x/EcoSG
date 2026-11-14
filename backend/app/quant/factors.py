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
def _market_regression(returns: pd.DataFrame):
    """Per-stock OLS of daily returns on the equal-weighted universe return.
    Returns (alpha, beta, market) with alpha/beta indexed by ticker."""
    market = returns.mean(axis=1)
    m_dev = market - market.mean()
    beta = returns.sub(returns.mean()).mul(m_dev, axis=0).sum() / (m_dev ** 2).sum()
    alpha = returns.mean() - beta * market.mean()
    return alpha, beta, market

def compute_momentum_factors(prices: pd.DataFrame, as_of: pd.Timestamp = None) -> pd.DataFrame:
    """
    Two momentum measures, both skipping the most recent month to avoid
    short-term reversal (Jegadeesh & Titman, 1993):
    - mom_12_1: classic total return from t-12m to t-1m.
    - resid_mom: residual momentum (Blitz, Huij, Martens 2011). Regress each
      stock's daily returns over t-252..t-21 on the equal-weighted universe
      return; score = sum(residuals) / std(residuals). Stripping the market
      part makes it less exposed to momentum crashes when the market turns.
      shortcut: BHM estimate the regression on 36 months; with ~2 years of
      history the beta comes from the 12-1 window itself and the residual
      keeps the stock's own drift (r - beta * m), since an in-window
      intercept would force the residual sum to zero. Use a 36-month
      estimation window once longer history exists.
    The old 6-1 measure is dropped: it is a sub-window of 12-1 and mostly
    duplicates it, while residual momentum adds a different view.
    """
    prices = prices.sort_index()
    if as_of is None:
        as_of = prices.index[-1]
    end_pos = prices.index.get_indexer([as_of], method="ffill")[0]
    mom_12_1 = pd.Series(np.nan, index=prices.columns)
    resid_mom = pd.Series(np.nan, index=prices.columns)
    if end_pos - 21 - 252 >= 0:
        mom_12_1 = prices.iloc[end_pos - 21] / prices.iloc[end_pos - 21 - 252] - 1.0
        window = prices.pct_change().iloc[end_pos - 251:end_pos - 20]
        _alpha, beta, market = _market_regression(window)
        resid = window - np.outer(market, beta)
        resid_mom = resid.sum() / resid.std().replace(0, np.nan)
    return pd.DataFrame({
        "ticker": prices.columns,
        "mom_12_1": mom_12_1.values,
        "resid_mom": resid_mom.values,
    })

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
    returns = prices.pct_change().tail(window)
    realized_vol = returns.std() * np.sqrt(252)
    realized_vol_inv = 1.0 / realized_vol.replace(0, np.nan)
    # Idiosyncratic volatility (Ang, Hodrick, Xing, Zhang 2006): the part of
    # volatility the market does not explain. High idio vol predicts low returns.
    alpha, beta, market = _market_regression(returns)
    resid = returns - alpha - np.outer(market, beta)
    idio_vol_inv = 1.0 / (resid.std() * np.sqrt(252)).replace(0, np.nan)
    beta = fund.set_index("ticker")["beta"].reindex(prices.columns)
    # Betting Against Beta (Frazzini, Pedersen): low-beta stocks earn more per
    # unit of risk. Shrink toward 1 (Vasicek-style, weight 0.5) since a single
    # beta estimate is noisy; higher score = lower beta.
    low_beta = -(BETA_SHRINK_WEIGHT * beta + (1.0 - BETA_SHRINK_WEIGHT) * 1.0)
    out = pd.DataFrame({
        "ticker": prices.columns,
        "realized_vol_inv": realized_vol_inv.values,
        "idio_vol_inv": idio_vol_inv.values,
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
