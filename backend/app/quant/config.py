"""
config.py
---------
Central configuration for the factor-based stock-selection model, ported
from the standalone hedge_stock_bot project into ECOSG. Every tunable knob
a hedge-fund-style quant process would expose lives here: factor weights,
sector neutralization, portfolio construction rules, and backtest settings.

Defaults are unchanged from the original bot EXCEPT the portfolio-
construction knobs (TOP_N, MAX_POSITION_WEIGHT, MAX_SECTOR_WEIGHT), which
are scaled down to fit ECOSG's ~25-name mock universe instead of the full
S&P 500 -- see the inline notes below.
"""
from dataclasses import dataclass, field
from typing import Dict, List

# ---------------------------------------------------------------------------
# Factor family weights (must sum to 1.0)
# ---------------------------------------------------------------------------
FACTOR_WEIGHTS: Dict[str, float] = {
    "value": 0.25,
    "quality": 0.30,
    "momentum": 0.20,
    "growth": 0.15,
    "low_vol": 0.10,
}

# Individual metric weights *within* each factor family (must each sum to 1.0)
VALUE_WEIGHTS = {
    "earnings_yield": 0.30,     # EBIT proxy / EV  (Greenblatt-style)
    "fcf_yield": 0.30,          # Free Cash Flow / Enterprise Value
    "book_to_price": 0.20,
    "earnings_to_price": 0.20,  # 1 / trailing P/E
}

QUALITY_WEIGHTS = {
    "roic": 0.20,               # ROA proxy
    "roe": 0.15,
    "gpoa": 0.20,               # gross profits / assets (Novy-Marx 2013)
    "cfoa": 0.15,               # free cash flow / assets (QMJ)
    "accruals": 0.10,           # -(net income - FCF) / assets (QMJ)
    "debt_to_equity_inv": 0.20, # inverted so lower leverage = better
}

MOMENTUM_WEIGHTS = {
    "mom_12_1": 0.60,   # 12-month return skipping the most recent month (academic standard)
    "mom_6_1": 0.40,    # 6-month return skipping the most recent month
}

GROWTH_WEIGHTS = {
    "revenue_growth_yoy": 0.50,
    "eps_growth_yoy": 0.50,
}

LOW_VOL_WEIGHTS = {
    "realized_vol_inv": 0.60,   # inverted 60-day realized volatility
    "low_beta": 0.40,           # -beta shrunk toward 1 (Betting Against Beta)
}

# ---------------------------------------------------------------------------
# Sector neutralization
# ---------------------------------------------------------------------------
# When True, factor z-scores are computed *within sector* so the model isn't
# just a disguised sector bet (e.g. always long Energy when it's cheap on
# book value, always short Tech). See RESEARCH.md for why this matters.
SECTOR_NEUTRAL_SCORING = True

# Winsorize each raw metric at these percentiles before z-scoring, to stop a
# single data error or extreme outlier from dominating the score.
WINSORIZE_LOWER_PCTL = 0.01
WINSORIZE_UPPER_PCTL = 0.99

# ---------------------------------------------------------------------------
# Portfolio construction
# ---------------------------------------------------------------------------
# NOTE: scaled down from the original bot's S&P-500-sized defaults (TOP_N=20,
# MAX_POSITION_WEIGHT=0.10, MAX_SECTOR_WEIGHT=0.30) to fit ECOSG's ~25-name
# mock universe -- otherwise TOP_N=20 would select nearly the whole universe.
TOP_N = 8                      # number of names to hold long
BUFFER_MULTIPLIER = 1.5        # hysteresis band -- see RESEARCH.md
MAX_POSITION_WEIGHT = 0.22     # single-name cap
MIN_POSITION_WEIGHT = 0.03     # don't bother with dust positions
MAX_SECTOR_WEIGHT = 0.45       # sector concentration cap
POSITION_SIZING_METHOD = "inverse_vol"   # "equal_weight" | "inverse_vol" | "score_weighted"
REBALANCE_FREQUENCY = "monthly"          # "weekly" | "monthly" | "quarterly"

# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------
BENCHMARK_TICKER = "SPY"
TRANSACTION_COST_BPS = 10   # 10 bps per trade, used in backtest realism


@dataclass
class RunConfig:
    """Bundle of the above, so other modules can accept one object
    (and so you can override settings per-run in tests without editing this file)."""
    factor_weights: Dict[str, float] = field(default_factory=lambda: dict(FACTOR_WEIGHTS))
    top_n: int = TOP_N
    buffer_multiplier: float = BUFFER_MULTIPLIER
    sector_neutral: bool = SECTOR_NEUTRAL_SCORING
    position_sizing_method: str = POSITION_SIZING_METHOD
    max_position_weight: float = MAX_POSITION_WEIGHT
    min_position_weight: float = MIN_POSITION_WEIGHT
    max_sector_weight: float = MAX_SECTOR_WEIGHT
