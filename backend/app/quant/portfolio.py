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
    sectors = df["sector"] if "sector" in df.columns else None
    # Capping and dropping dust each renormalize, and either can push another
    # name back over a cap, so repeat until the set of names stops changing.
    for _ in range(len(df) + 1):
        weight = _apply_caps(weight, sectors, cfg.max_position_weight, cfg.max_sector_weight)
        keep = weight >= cfg.min_position_weight
        if keep.all() or not keep.any():
            break
        weight = weight[keep] / weight[keep].sum()
        sectors = sectors[keep] if sectors is not None else None
    df = df.loc[weight.index].copy()
    df["weight"] = weight
    return df

_CAP_TOL = 1e-9

def _apply_caps(weight: pd.Series, sectors: Optional[pd.Series],
                max_position: float, max_sector: float) -> pd.Series:
    """
    Enforce single-name and sector caps exactly, handing freed weight to names
    that still have room under both caps (water-filling). If the caps cannot
    all hold with weights summing to 1 (too few names or sectors), the
    leftover stays uninvested as cash rather than breaching a cap.
    """
    w = weight.astype(float).copy()
    for _ in range(100):
        w = w.clip(upper=max_position)
        if sectors is not None:
            sector_total = w.groupby(sectors).transform("sum")
            w = w * (max_sector / sector_total).clip(upper=1.0)
        shortfall = 1.0 - w.sum()
        if shortfall <= _CAP_TOL:
            break
        room = w < max_position - _CAP_TOL
        if sectors is not None:
            room &= w.groupby(sectors).transform("sum") < max_sector - _CAP_TOL
        if not room.any() or w[room].sum() <= 0:
            break
        w[room] += shortfall * w[room] / w[room].sum()
    return w

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
