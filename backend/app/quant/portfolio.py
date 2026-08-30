"""
portfolio.py
------------
Turns a ranked list of stocks into an actual portfolio: which names to hold,
at what weight, respecting position and sector caps -- then diffs against
the bot's current holdings to produce BUY / SELL / HOLD signals.
Two hedge-fund techniques are implemented deliberately:
1. Hysteresis / buffer bands (avoid churning a position that ranked #19
   last month and #22 this month -- that's noise, not signal, and every
   unnecessary trade costs money).
2. Risk-based position sizing (inverse-volatility weighting) rather than
   naive equal-weight, so one shaky small-cap doesn't dominate portfolio risk.
"""
from __future__ import annotations
from typing import Dict, Optional
import numpy as np
import pandas as pd

def select_candidates(scored_df: pd.DataFrame, cfg,
                       current_holdings: Optional[set] = None) -> pd.DataFrame:
    """
    Apply the buffer-band rule: current holdings survive until they fall out
    of the top (TOP_N * BUFFER_MULTIPLIER); new entries must crack the top
    TOP_N outright. Returns the selected subset of scored_df.
    """
    current_holdings = current_holdings or set()
    buffer_n = int(round(cfg.top_n * cfg.buffer_multiplier))
    core = scored_df[scored_df["rank"] <= cfg.top_n]
    retained_holdings = scored_df[
        (scored_df["ticker"].isin(current_holdings)) &
        (scored_df["rank"] <= buffer_n)
    ]
    selected = pd.concat([core, retained_holdings]).drop_duplicates(subset="ticker")
    selected = selected.sort_values("rank")
    return selected

def size_positions(selected: pd.DataFrame, prices: pd.DataFrame, cfg,
                    vol_window: int = 60) -> pd.DataFrame:
    """
    Assign portfolio weights to the selected names, then apply single-name
    and sector caps and renormalize. Returns selected with a `weight` column.
    """
    df = selected.copy()
    if cfg.position_sizing_method == "equal_weight":
        raw_weight = pd.Series(1.0, index=df.index)
    elif cfg.position_sizing_method == "score_weighted":
        shifted = df["composite_score"] - df["composite_score"].min() + 0.01
        raw_weight = shifted
    else:  # "inverse_vol" (default) -- risk-parity-style sizing
        returns = prices[df["ticker"].tolist()].pct_change()
        vol = returns.tail(vol_window).std() * np.sqrt(252)
        vol = vol.reindex(df["ticker"]).values
        vol = np.where((vol == 0) | np.isnan(vol), np.nanmedian(vol), vol)
        raw_weight = pd.Series(1.0 / vol, index=df.index)
    weight = raw_weight / raw_weight.sum()
    # single-name cap, with the excess redistributed proportionally to
    # everything still under cap (a couple of iterations converges fine
    # for portfolios this size)
    for _ in range(10):
        over = weight > cfg.max_position_weight
        if not over.any():
            break
        excess = (weight[over] - cfg.max_position_weight).sum()
        weight[over] = cfg.max_position_weight
        under = ~over
        if under.sum() == 0:
            break
        weight[under] += excess * (weight[under] / weight[under].sum())
    df["weight"] = weight
    # sector cap
    if "sector" in df.columns:
        for _ in range(10):
            sector_weight = df.groupby("sector")["weight"].transform("sum")
            over = sector_weight > cfg.max_sector_weight
            if not over.any():
                break
            for sector in df.loc[over, "sector"].unique():
                sec_mask = df["sector"] == sector
                sec_total = df.loc[sec_mask, "weight"].sum()
                scale = cfg.max_sector_weight / sec_total
                df.loc[sec_mask, "weight"] *= scale
            df["weight"] = df["weight"] / df["weight"].sum()
    df = df[df["weight"] >= cfg.min_position_weight]
    df["weight"] = df["weight"] / df["weight"].sum()  # final renormalization
    return df

def generate_signals(scored_df: pd.DataFrame, prices: pd.DataFrame, cfg,
                      current_holdings: Optional[Dict[str, float]] = None) -> pd.DataFrame:
    """
    Full pipeline: rank -> buffer-band selection -> position sizing -> diff
    against current holdings -> BUY/SELL/HOLD signal table.
    `current_holdings`: dict of {ticker: current_weight}, e.g. loaded from
    a JSON state file the bot persists between runs. Pass None / {} for a
    fresh/live scan with no prior state (everything selected shows as BUY).
    """
    current_holdings = current_holdings or {}
    current_tickers = set(current_holdings.keys())
    selected = select_candidates(scored_df, cfg, current_holdings=current_tickers)
    sized = size_positions(selected, prices, cfg)
    sized = sized.set_index("ticker")
    new_tickers = set(sized.index)
    signals = []
    for ticker in sorted(new_tickers | current_tickers):
        target_w = sized["weight"].get(ticker, 0.0)
        current_w = current_holdings.get(ticker, 0.0)
        if ticker in new_tickers and ticker not in current_tickers:
            action = "BUY"
        elif ticker not in new_tickers and ticker in current_tickers:
            action = "SELL"
        elif abs(target_w - current_w) > 0.01:
            action = "REBALANCE"
        else:
            action = "HOLD"
        row = {
            "ticker": ticker,
            "action": action,
            "current_weight": round(current_w, 4),
            "target_weight": round(target_w, 4),
        }
        if ticker in sized.index:
            row["composite_score"] = sized.loc[ticker, "composite_score"]
            row["rank"] = sized.loc[ticker, "rank"]
            row["sector"] = sized.loc[ticker].get("sector", "Unknown")
        signals.append(row)
    return pd.DataFrame(signals).sort_values(
        by=["action", "target_weight"], ascending=[True, False]
    ).reset_index(drop=True)
