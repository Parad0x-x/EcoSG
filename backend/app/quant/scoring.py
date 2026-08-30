"""
scoring.py
----------
Cross-sectional normalization and composite scoring -- the heart of a
quant factor model. Raw metrics (a P/E of 14, an ROE of 22%) aren't
comparable to each other or combinable into one number. The standard fix,
used across the industry, is:
  1. Winsorize each raw metric (clip extreme outliers) so a single bad data
     point or genuine extreme value doesn't dominate.
  2. Convert each metric to a cross-sectional z-score: (x - mean) / std,
     computed across the universe (optionally within-sector) at each point
     in time. Now "cheap on earnings yield" and "high ROIC" are on the same
     scale and can be averaged.
  3. Combine z-scores within a factor family (e.g. average the value
     sub-metrics) using configured weights.
  4. Combine factor families into one composite score using configured
     weights.
  5. Rank the universe by composite score.
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

def cross_sectional_zscore(df: pd.DataFrame, col: str, sector_col: str = "sector",
                            sector_neutral: bool = True,
                            winsor_lower: float = 0.01, winsor_upper: float = 0.99) -> pd.Series:
    """
    Winsorize then z-score a single metric column, optionally within each
    sector group so the score reflects "cheap/strong FOR ITS SECTOR" rather
    than an accidental sector tilt.
    """
    s = df[col]
    valid = s.notna()
    result = pd.Series(np.nan, index=df.index)
    if sector_neutral and sector_col in df.columns:
        for sector, group_idx in df.groupby(sector_col, dropna=False).groups.items():
            group_idx = group_idx.intersection(df.index[valid])
            if len(group_idx) < 3:
                continue  # too few names in-sector to z-score meaningfully; leave NaN -> neutral
            w = winsorize(df.loc[group_idx, col], winsor_lower, winsor_upper)
            result.loc[group_idx] = zscore(w)
    else:
        w = winsorize(s[valid], winsor_lower, winsor_upper)
        result.loc[valid.index[valid]] = zscore(w)
    return result

def score_factor_family(df: pd.DataFrame, metric_weights: Dict[str, float],
                         sector_neutral: bool, winsor_lower: float, winsor_upper: float) -> pd.Series:
    """Weighted average of z-scored metrics within one factor family (e.g. all value metrics)."""
    zscored_cols = {}
    for metric, weight in metric_weights.items():
        if metric not in df.columns:
            continue
        zscored_cols[metric] = cross_sectional_zscore(
            df, metric, sector_neutral=sector_neutral,
            winsor_lower=winsor_lower, winsor_upper=winsor_upper,
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
        )
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
