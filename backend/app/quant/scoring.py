"""
scoring.py
----------
Cross-sectional normalization and composite scoring -- the heart of a
quant factor model. Raw metrics (a P/E of 14, an ROE of 22%) aren't
comparable to each other or combinable into one number. The pipeline:
  1. Winsorize each raw metric so one bad data point can't drag a sector mean.
  2. Partially sector-adjust: subtract a sector mean shrunk toward the
     universe mean, mu_s* = (n_s * mu_s + k * mu_all) / (n_s + k)
     (industry-relative characteristics, Asness, Porter, Stevens 2000; the
     shrinkage keeps a 3-name sector from being pure noise).
  3. Rank-based z-score across the whole universe: rank, then standardize
     (as in Asness, Frazzini, Pedersen, Quality Minus Junk). Ranks are
     robust to outliers and skew; the output has mean 0 and std 1.
  4. Combine metric z-scores within a family with configured weights, then
     re-standardize each family score so FACTOR_WEIGHTS are the effective
     weights (an average of z-scores has std below 1, more so when the
     metrics disagree, which would silently shrink that family's weight).
  5. Combine families into one composite score and rank the universe.
"""
from __future__ import annotations
from typing import Dict
import numpy as np
import pandas as pd

def winsorize(s: pd.Series, lower: float, upper: float) -> pd.Series:
    lo, hi = s.quantile(lower), s.quantile(upper)
    return s.clip(lower=lo, upper=hi)

def zscore(s: pd.Series) -> pd.Series:
    mu, sigma = s.mean(), s.std()
    if not sigma or np.isnan(sigma) or sigma == 0:
        return pd.Series(0.0, index=s.index)
    return (s - mu) / sigma

def rank_zscore(s: pd.Series) -> pd.Series:
    """Rank the non-missing values (ties averaged), then z-score the ranks. NaN stays NaN."""
    out = pd.Series(np.nan, index=s.index)
    valid = s.notna()
    out[valid] = zscore(s[valid].rank(method="average"))
    return out

def shrunk_sector_mean(x: pd.Series, sectors: pd.Series, k: float) -> pd.Series:
    """Per-row sector mean shrunk toward the universe mean with k pseudo-names."""
    valid = x.notna()
    mu_all = x[valid].mean()
    grp = x[valid].groupby(sectors[valid])
    n_s = grp.transform("count")
    mu_s = grp.transform("mean")
    out = pd.Series(np.nan, index=x.index)
    out[valid] = (n_s * mu_s + k * mu_all) / (n_s + k)
    return out

def cross_sectional_zscore(df: pd.DataFrame, col: str, sector_col: str = "sector",
                            sector_neutral: bool = True,
                            winsor_lower: float = 0.01, winsor_upper: float = 0.99,
                            shrinkage_k: float = 3.0) -> pd.Series:
    """
    Winsorize, optionally subtract the shrunk sector mean, then rank-z across
    the whole universe. A NaN only leaves its own row missing; every other
    name in that sector is still scored (the sector mean uses the names present).
    """
    s = df[col].astype(float)
    valid = s.notna()
    x = pd.Series(np.nan, index=df.index)
    if valid.any():
        x[valid] = winsorize(s[valid], winsor_lower, winsor_upper)
    if sector_neutral and sector_col in df.columns:
        sectors = df[sector_col].fillna("Unknown")
        x = x - shrunk_sector_mean(x, sectors, shrinkage_k)
    return rank_zscore(x)

def score_factor_family(df: pd.DataFrame, metric_weights: Dict[str, float],
                         sector_neutral: bool, winsor_lower: float, winsor_upper: float,
                         shrinkage_k: float = 3.0) -> pd.Series:
    """Weighted average of z-scored metrics within one factor family (e.g. all value metrics)."""
    zscored_cols = {}
    for metric, weight in metric_weights.items():
        if metric not in df.columns:
            continue
        zscored_cols[metric] = cross_sectional_zscore(
            df, metric, sector_neutral=sector_neutral,
            winsor_lower=winsor_lower, winsor_upper=winsor_upper,
            shrinkage_k=shrinkage_k,
        )
    if not zscored_cols:
        return pd.Series(np.nan, index=df.index)
    z_df = pd.DataFrame(zscored_cols)
    weights = pd.Series({m: metric_weights[m] for m in z_df.columns})
    # Missing-data handling: renormalize weights over the metrics that ARE
    # present for each row, rather than silently treating a NaN as 0 (which
    # would unfairly punish a stock just because one data field was missing).
    mask = z_df.notna()
    eff_weights = mask.mul(weights, axis=1)
    weight_sums = eff_weights.sum(axis=1)
    weighted = z_df.fillna(0).mul(weights, axis=1).sum(axis=1)
    family_score = weighted / weight_sums.replace(0, np.nan)
    return family_score

def compute_composite_score(factors_df: pd.DataFrame, cfg) -> pd.DataFrame:
    """
    Takes the wide raw-factor DataFrame from factors.build_all_factors() and
    a RunConfig, and returns a DataFrame with per-family z-scores, the
    weighted composite score, and a rank column.
    """
    from .config import (VALUE_WEIGHTS, QUALITY_WEIGHTS, MOMENTUM_WEIGHTS,
                         GROWTH_WEIGHTS, LOW_VOL_WEIGHTS,
                         WINSORIZE_LOWER_PCTL, WINSORIZE_UPPER_PCTL)
    df = factors_df.copy()
    family_metric_weights = {
        "value": VALUE_WEIGHTS,
        "quality": QUALITY_WEIGHTS,
        "momentum": MOMENTUM_WEIGHTS,
        "growth": GROWTH_WEIGHTS,
        "low_vol": LOW_VOL_WEIGHTS,
    }
    for family, metric_weights in family_metric_weights.items():
        df[f"{family}_score"] = score_factor_family(
            df, metric_weights,
            sector_neutral=cfg.sector_neutral,
            winsor_lower=WINSORIZE_LOWER_PCTL,
            winsor_upper=WINSORIZE_UPPER_PCTL,
            shrinkage_k=cfg.sector_shrinkage_k,
        )
        df[f"{family}_score"] = rank_zscore(df[f"{family}_score"])  # re-standardize the family
    family_scores = df[[f"{f}_score" for f in cfg.factor_weights]]
    mask = family_scores.notna()
    fam_weight_series = pd.Series(cfg.factor_weights)
    fam_weight_series.index = [f"{f}_score" for f in fam_weight_series.index]
    eff_weights = mask.mul(fam_weight_series, axis=1)
    weight_sums = eff_weights.sum(axis=1)
    weighted = family_scores.fillna(0).mul(fam_weight_series, axis=1).sum(axis=1)
    df["composite_score"] = weighted / weight_sums.replace(0, np.nan)
    df["rank"] = df["composite_score"].rank(ascending=False, method="first")
    df = df.sort_values("rank")
    return df
