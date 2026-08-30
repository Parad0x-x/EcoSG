"""Query + scoring orchestration shared by the API routers.

Keeps scoring.py pure (no DB knowledge) and the routers thin (no
scoring math) by gluing the two together here.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from . import scoring
from .models import Company


def score_all(db: Session) -> dict[int, scoring.ScoreBreakdown]:
    """Composite score breakdown for every company, keyed by company id."""
    companies = db.query(Company).all()
    return {
        c.id: scoring.score_company(
            sector=c.sector,
            environmental_score=c.esg.environmental_score,
            social_score=c.esg.social_score,
            governance_score=c.esg.governance_score,
            controversy_severity=c.esg.controversy_severity,
        )
        for c in companies
    }


def sector_percentiles(db: Session, breakdowns: dict[int, scoring.ScoreBreakdown]) -> dict[int, float]:
    companies = db.query(Company).all()
    by_sector: dict[str, list[float]] = {}
    for c in companies:
        by_sector.setdefault(c.sector, []).append(breakdowns[c.id].composite_score)

    return {
        c.id: scoring.sector_percentile(breakdowns[c.id].composite_score, by_sector[c.sector])
        for c in companies
    }


def get_company_by_ticker(db: Session, ticker: str) -> Company | None:
    return db.query(Company).filter(Company.ticker == ticker.upper()).first()
