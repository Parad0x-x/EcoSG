"""ECOSG scoring framework (v0.2).

Turns raw E/S/G pillar scores plus dated controversy events into a 0-100
industry-adjusted score, a letter grade (with caps), a confidence level and
a year-on-year trend. This module is pure: no DB access, no clock. Callers
pass an `as_of` date so every result is reproducible and testable.

Methodology and sources
-----------------------

1. Materiality weights with a governance floor.
   Each sector weights E, S and G by how financially material each pillar is
   for that industry. The principle comes from SASB's industry materiality
   map and from Khan, Serafeim and Yoon (2016), "Corporate Sustainability:
   First Evidence on Materiality" (https://papers.ssrn.com/abstract=2575912),
   who found that only performance on material issues relates to returns.
   MSCI floors the governance pillar at 33% of the weight for every industry
   (MSCI ESG Ratings Methodology, Executive Summary, Nov 2020,
   https://fintech.mcu.edu.tw/wp-content/uploads/sites/42/2023/02/MSCI-ESG-Ratings-Methodology-Exec-Summary-Nov-2020.pdf).
   The exact per-sector numbers below are ecosg's own judgement built on
   those principles, not a vendor's published table.

2. Industry adjustment and grade bands.
   The weighted pillar score is rescaled against a fixed per-sector benchmark
   range (lo, hi): industry_adjusted = clip(100 * (weighted - lo) / (hi - lo)).
   MSCI does the same thing against live industry peer ranges. With only
   three peers per sector in the demo, live percentiles would be noise, so
   the ranges are fixed config describing a plausible wider universe for each
   sector (design choice). The 0-100 result is cut into MSCI's seven equal
   bands, AAA at 85.7 and up down to CCC below 14.3 (MSCI 2020, Figure 8).

3. Controversies as dated events.
   Each event has a Sustainalytics-style category from 1 (low) to 5 (severe)
   and a date. Its penalty is CATEGORY_POINTS[category] halved every 12
   months, and it drops out entirely after 36 months, matching MSCI's
   three-year controversy window. RepRisk also decays incidents, over two
   years. The 12-month half-life is ecosg's design choice. Total penalty is
   capped at 30 points.

4. Grade caps (design choice, documented here).
   A category 5 event younger than 12 months caps the grade at BB. A
   governance pillar below 30 caps the grade at BBB, because weak governance
   undermines trust in everything else a company reports.

5. Confidence and trend are separate signals, never blended into the score.
   Raters disagree a lot: Berg, Kolbel and Rigobon, "Aggregate Confusion"
   (https://papers.ssrn.com/abstract=3438533), find correlations around 0.54
   between major providers, and Avramov et al. (2022, JFE,
   https://doi.org/10.1016/j.jfineco.2021.09.009) show that this uncertainty
   changes how ESG relates to returns. Confidence comes from data coverage
   and rater spread; the thresholds are design choices.
   Trend compares today's score with the same algorithm run one year earlier.
   MSCI research (Nagy, Kassam and Lee, "Can ESG Add Alpha?",
   https://www.msci.com/research-and-insights/blog-post/can-esg-add-alpha)
   found ESG momentum carried information beyond the level of the score.

Swapping in real vendor data should only need data_seed.py / DB changes.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterable, Protocol

# --- 1. Pillar weights (E, S, G) -------------------------------------------

GOVERNANCE_WEIGHT_FLOOR = 0.33
DEFAULT_WEIGHTS = (0.34, 0.33, 0.33)

SECTOR_WEIGHTS: dict[str, tuple[float, float, float]] = {
    "Energy": (0.45, 0.22, 0.33),
    "Utilities": (0.45, 0.22, 0.33),
    "Materials": (0.42, 0.25, 0.33),
    "Industrials": (0.32, 0.35, 0.33),
    "Technology": (0.22, 0.45, 0.33),
    "Financials": (0.12, 0.38, 0.50),
    "Health Care": (0.12, 0.55, 0.33),
    "Consumer Discretionary": (0.25, 0.42, 0.33),
    "Consumer Staples": (0.30, 0.37, 0.33),
    "Communication Services": (0.12, 0.55, 0.33),
    # SASB Real Estate: energy, water and climate adaptation are the material topics.
    "Real Estate": (0.42, 0.25, 0.33),
}

for _sector, _w in {**SECTOR_WEIGHTS, "default": DEFAULT_WEIGHTS}.items():
    if abs(sum(_w) - 1.0) > 1e-9 or _w[2] < GOVERNANCE_WEIGHT_FLOOR:
        raise ValueError(f"Bad pillar weights for {_sector}: {_w}")

# --- 2. Industry benchmark ranges of the weighted pillar score -------------
# (lo, hi) for a plausible wider universe of each sector, set by hand, not fit to the mock data.
DEFAULT_BENCHMARK = (40.0, 80.0)

SECTOR_BENCHMARKS: dict[str, tuple[float, float]] = {
    "Energy": (20.0, 60.0),
    "Utilities": (45.0, 82.0),
    "Materials": (35.0, 75.0),
    "Industrials": (40.0, 78.0),
    "Technology": (45.0, 85.0),
    "Financials": (45.0, 82.0),
    "Health Care": (45.0, 82.0),
    "Consumer Discretionary": (40.0, 78.0),
    "Consumer Staples": (45.0, 82.0),
    "Communication Services": (38.0, 78.0),
    "Real Estate": (40.0, 78.0),
}

# MSCI 2020 Figure 8: seven equal bands on 0-100, best first.
GRADE_BANDS = [
    (85.7, "AAA"),
    (71.4, "AA"),
    (57.1, "A"),
    (42.9, "BBB"),
    (28.6, "BB"),
    (14.3, "B"),
    (0.0, "CCC"),
]
GRADES_BEST_FIRST = [g for _, g in GRADE_BANDS]

# --- 3. Controversies -------------------------------------------------------

CATEGORY_POINTS = {1: 1.0, 2: 3.0, 3: 6.0, 4: 10.0, 5: 15.0}
HALF_LIFE_MONTHS = 12.0
CONTROVERSY_WINDOW_MONTHS = 36.0
MAX_CONTROVERSY_PENALTY = 30.0
DAYS_PER_MONTH = 365.25 / 12

# --- 4. Grade caps ----------------------------------------------------------

SEVERE_CATEGORY = 5
SEVERE_CAP_MONTHS = 12.0
SEVERE_CAP_GRADE = "BB"
GOVERNANCE_GATE = 30.0
GOVERNANCE_CAP_GRADE = "BBB"

# --- 5. Confidence and trend ------------------------------------------------

HIGH_CONFIDENCE_COVERAGE = 85.0
HIGH_CONFIDENCE_SPREAD = 8.0
LOW_CONFIDENCE_COVERAGE = 70.0
LOW_CONFIDENCE_SPREAD = 15.0
TREND_THRESHOLD = 3.0


class ControversyLike(Protocol):
    category: int
    occurred_on: dt.date
    title: str


@dataclass(frozen=True)
class Controversy:
    category: int
    occurred_on: dt.date
    title: str


@dataclass(frozen=True)
class ScoredEvent:
    category: int
    occurred_on: dt.date
    title: str
    age_months: float
    decay_factor: float
    penalty_points: float


@dataclass(frozen=True)
class ScoreBreakdown:
    composite_score: float  # final 0-100 score: industry-adjusted minus penalty
    grade: str
    grade_before_cap: str
    grade_cap_reason: str | None
    weighted_pillar_score: float
    industry_adjusted_score: float
    benchmark_low: float
    benchmark_high: float
    environmental_score: float
    social_score: float
    governance_score: float
    controversy_penalty: float
    controversy_events: tuple[ScoredEvent, ...]


def pillar_weights(sector: str) -> tuple[float, float, float]:
    return SECTOR_WEIGHTS.get(sector, DEFAULT_WEIGHTS)


def sector_benchmark(sector: str) -> tuple[float, float]:
    return SECTOR_BENCHMARKS.get(sector, DEFAULT_BENCHMARK)


def grade_for_score(score: float) -> str:
    for threshold, grade in GRADE_BANDS:
        if score >= threshold:
            return grade
    return "CCC"


def age_in_months(occurred_on: dt.date, as_of: dt.date) -> float:
    return (as_of - occurred_on).days / DAYS_PER_MONTH


def decay(age_months: float) -> float:
    """Share of an event's points still counted at this age."""
    if age_months < 0 or age_months > CONTROVERSY_WINDOW_MONTHS:
        return 0.0
    return 0.5 ** (age_months / HALF_LIFE_MONTHS)


def score_events(events: Iterable[ControversyLike], as_of: dt.date) -> tuple[ScoredEvent, ...]:
    """Events that had happened by as_of and are still inside the window, newest first."""
    scored = []
    for e in events:
        age = age_in_months(e.occurred_on, as_of)
        factor = decay(age)
        if factor == 0.0:
            continue
        scored.append(ScoredEvent(
            category=e.category,
            occurred_on=e.occurred_on,
            title=e.title,
            age_months=round(age, 1),
            decay_factor=round(factor, 3),
            penalty_points=round(CATEGORY_POINTS[e.category] * factor, 2),
        ))
    return tuple(sorted(scored, key=lambda s: s.occurred_on, reverse=True))


def grade_cap(governance_score: float, events: Iterable[ScoredEvent]) -> tuple[str, str] | None:
    """Strictest grade ceiling that applies, with its reason, or None."""
    caps = []
    if any(e.category == SEVERE_CATEGORY and e.age_months < SEVERE_CAP_MONTHS for e in events):
        caps.append((SEVERE_CAP_GRADE, "A category 5 (severe) controversy in the last 12 months caps the grade at BB."))
    if governance_score < GOVERNANCE_GATE:
        caps.append((GOVERNANCE_CAP_GRADE, "A governance score below 30 caps the grade at BBB."))
    if not caps:
        return None
    return max(caps, key=lambda c: GRADES_BEST_FIRST.index(c[0]))


def score_company(
    sector: str,
    environmental_score: float,
    social_score: float,
    governance_score: float,
    events: Iterable[ControversyLike],
    as_of: dt.date,
) -> ScoreBreakdown:
    """Score one company as of a date. Pillars are 0-100, higher is better."""
    w_e, w_s, w_g = pillar_weights(sector)
    weighted = w_e * environmental_score + w_s * social_score + w_g * governance_score

    lo, hi = sector_benchmark(sector)
    adjusted = max(0.0, min(100.0, 100.0 * (weighted - lo) / (hi - lo)))

    scored = score_events(events, as_of)
    penalty = min(MAX_CONTROVERSY_PENALTY, sum(e.penalty_points for e in scored))
    composite = round(max(0.0, adjusted - penalty), 1)

    grade_before_cap = grade_for_score(composite)
    grade, reason = grade_before_cap, None
    cap = grade_cap(governance_score, scored)
    if cap and GRADES_BEST_FIRST.index(cap[0]) > GRADES_BEST_FIRST.index(grade_before_cap):
        grade, reason = cap

    return ScoreBreakdown(
        composite_score=composite,
        grade=grade,
        grade_before_cap=grade_before_cap,
        grade_cap_reason=reason,
        weighted_pillar_score=round(weighted, 1),
        industry_adjusted_score=round(adjusted, 1),
        benchmark_low=lo,
        benchmark_high=hi,
        environmental_score=environmental_score,
        social_score=social_score,
        governance_score=governance_score,
        controversy_penalty=round(penalty, 1),
        controversy_events=scored,
    )


def confidence(data_coverage_pct: float, rater_spread: float) -> str:
    if data_coverage_pct >= HIGH_CONFIDENCE_COVERAGE and rater_spread <= HIGH_CONFIDENCE_SPREAD:
        return "high"
    if data_coverage_pct < LOW_CONFIDENCE_COVERAGE or rater_spread > LOW_CONFIDENCE_SPREAD:
        return "low"
    return "medium"


def trend_label(change: float) -> str:
    if change >= TREND_THRESHOLD:
        return "improving"
    if change <= -TREND_THRESHOLD:
        return "worsening"
    return "stable"


def one_year_before(as_of: dt.date) -> dt.date:
    try:
        return as_of.replace(year=as_of.year - 1)
    except ValueError:  # 29 February
        return as_of.replace(year=as_of.year - 1, day=28)


def sector_percentile(composite_score: float, sector_scores: list[float]) -> float:
    """Percentile rank of composite_score among sector_scores (0-100)."""
    if not sector_scores:
        return 50.0
    n_below_or_equal = sum(1 for s in sector_scores if s <= composite_score)
    return round(100.0 * n_below_or_equal / len(sector_scores), 1)
