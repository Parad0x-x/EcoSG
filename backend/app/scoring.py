"""ECOSG scoring framework.

This is the core IP surface of the product: it turns raw E/S/G
sub-scores into a single, comparable composite score, a letter
grade, and a sector-relative percentile -- the same shape of output
an institutional ESG data provider (MSCI, Sustainalytics, etc.)
exposes, distilled to something a retail investor can act on.

Methodology (v0.1, MVP):

1. Pillar weighting
   Composite = 0.40 * Environmental + 0.30 * Social + 0.30 * Governance
   Weights are configurable per-sector below because materiality
   differs by industry (e.g. Environmental matters more for Energy
   than for Financials) -- this is standard practice among ESG
   ratings providers (materiality-weighted scoring).

2. Controversy penalty
   A flat, severity-scaled deduction is applied on top of the
   weighted pillar score, capped so a single controversy can't push
   a score below 0. This mirrors how providers cap ratings after a
   major controversy regardless of otherwise-strong pillar scores.

3. Sector percentile
   Each company's composite is ranked against same-sector peers only,
   since raw E/S/G scores are not directly comparable across sectors
   (a 70 for an Energy company and a 70 for a Software company do not
   reflect the same difficulty).

4. Letter grade
   Composite score is bucketed into a 7-tier grade scale (AAA..CCC),
   again mirroring the convention used by major providers so it reads
   as familiar to anyone who has seen an ESG rating before.

This module is intentionally the single place that encodes "what does
a good ESG score mean" -- swapping in real vendor data later should
only require changing data_seed.py / the DB contents, not this file.
"""
from __future__ import annotations

from dataclasses import dataclass

# Sector-specific pillar weights (environmental, social, governance).
# Falls back to DEFAULT_WEIGHTS for any sector not listed.
DEFAULT_WEIGHTS = (0.40, 0.30, 0.30)

SECTOR_WEIGHTS: dict[str, tuple[float, float, float]] = {
    "Energy": (0.55, 0.20, 0.25),
    "Utilities": (0.50, 0.20, 0.30),
    "Materials": (0.50, 0.25, 0.25),
    "Industrials": (0.40, 0.30, 0.30),
    "Technology": (0.25, 0.35, 0.40),
    "Financials": (0.15, 0.35, 0.50),
    "Health Care": (0.20, 0.45, 0.35),
    "Consumer Discretionary": (0.30, 0.40, 0.30),
    "Consumer Staples": (0.35, 0.40, 0.25),
    "Communication Services": (0.20, 0.45, 0.35),
}

# Controversy severity (0-10 scale) -> points deducted from composite.
CONTROVERSY_PENALTY_PER_SEVERITY_POINT = 3.0
MAX_CONTROVERSY_PENALTY = 30.0

GRADE_BANDS = [
    (85.0, "AAA"),
    (75.0, "AA"),
    (65.0, "A"),
    (55.0, "BBB"),
    (45.0, "BB"),
    (35.0, "B"),
    (0.0, "CCC"),
]


@dataclass(frozen=True)
class ScoreBreakdown:
    composite_score: float
    grade: str
    environmental_score: float
    social_score: float
    governance_score: float
    controversy_penalty: float


def pillar_weights(sector: str) -> tuple[float, float, float]:
    return SECTOR_WEIGHTS.get(sector, DEFAULT_WEIGHTS)


def grade_for_score(score: float) -> str:
    for threshold, grade in GRADE_BANDS:
        if score >= threshold:
            return grade
    return "CCC"


def score_company(
    sector: str,
    environmental_score: float,
    social_score: float,
    governance_score: float,
    controversy_severity: float,
) -> ScoreBreakdown:
    """Compute the composite ESG score for one company.

    All inputs are assumed already normalized to 0-100 per pillar
    (see data_seed.py for how the mock data is generated).
    """
    w_e, w_s, w_g = pillar_weights(sector)
    weighted = (
        w_e * environmental_score
        + w_s * social_score
        + w_g * governance_score
    )

    penalty = min(
        controversy_severity * CONTROVERSY_PENALTY_PER_SEVERITY_POINT,
        MAX_CONTROVERSY_PENALTY,
    )

    composite = max(0.0, min(100.0, weighted - penalty))

    return ScoreBreakdown(
        composite_score=round(composite, 1),
        grade=grade_for_score(composite),
        environmental_score=environmental_score,
        social_score=social_score,
        governance_score=governance_score,
        controversy_penalty=round(penalty, 1),
    )


def sector_percentile(composite_score: float, sector_scores: list[float]) -> float:
    """Percentile rank of composite_score among sector_scores (0-100)."""
    if not sector_scores:
        return 50.0
    n_below_or_equal = sum(1 for s in sector_scores if s <= composite_score)
    return round(100.0 * n_below_or_equal / len(sector_scores), 1)
