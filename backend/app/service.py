"""Query + scoring orchestration shared by the API routers.

Keeps scoring.py pure (no DB knowledge, no clock) and the routers thin (no
scoring math) by gluing the two together here.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import asdict

from sqlalchemy.orm import Session

from . import scoring
from .models import Company, EsgScoreOut


def score_company(c: Company, as_of: dt.date) -> scoring.ScoreBreakdown:
    return scoring.score_company(
        sector=c.sector,
        environmental_score=c.esg.environmental_score,
        social_score=c.esg.social_score,
        governance_score=c.esg.governance_score,
        events=c.controversies,
        as_of=as_of,
    )


def score_all(db: Session, as_of: dt.date | None = None) -> dict[int, scoring.ScoreBreakdown]:
    """Score breakdown for every company, keyed by company id."""
    as_of = as_of or dt.date.today()
    return {c.id: score_company(c, as_of) for c in db.query(Company).all()}


def sector_percentiles(db: Session, breakdowns: dict[int, scoring.ScoreBreakdown]) -> dict[int, float]:
    companies = db.query(Company).all()
    by_sector: dict[str, list[float]] = {}
    for c in companies:
        by_sector.setdefault(c.sector, []).append(breakdowns[c.id].composite_score)

    return {
        c.id: scoring.sector_percentile(breakdowns[c.id].composite_score, by_sector[c.sector])
        for c in companies
    }


def esg_score_out(c: Company, bd: scoring.ScoreBreakdown, percentile: float, as_of: dt.date) -> EsgScoreOut:
    """Full ESG detail: the score plus confidence and trend, kept as separate signals."""
    prior = scoring.score_company(
        sector=c.sector,
        environmental_score=c.esg.env_prev,
        social_score=c.esg.social_prev,
        governance_score=c.esg.gov_prev,
        events=c.controversies,
        as_of=scoring.one_year_before(as_of),
    )
    change = round(bd.composite_score - prior.composite_score, 1)
    return EsgScoreOut(
        **asdict(bd),
        sector_percentile=percentile,
        confidence=scoring.confidence(c.esg.data_coverage_pct, c.esg.rater_spread),
        prior_composite_score=prior.composite_score,
        trend=change,
        trend_label=scoring.trend_label(change),
    )


def get_company_by_ticker(db: Session, ticker: str) -> Company | None:
    return db.query(Company).filter(Company.ticker == ticker.upper()).first()
