from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import service
from ..database import get_db
from ..models import Company, CompanyOut, CompanySummaryOut, EsgScoreOut

router = APIRouter(prefix="/api", tags=["companies"])


@router.get("/companies", response_model=list[CompanySummaryOut])
def list_companies(sector: str | None = None, db: Session = Depends(get_db)):
    breakdowns = service.score_all(db)
    query = db.query(Company)
    if sector:
        query = query.filter(Company.sector == sector)
    companies = query.order_by(Company.ticker).all()

    return [
        CompanySummaryOut(
            ticker=c.ticker,
            name=c.name,
            sector=c.sector,
            one_year_return_pct=c.financials.one_year_return_pct,
            composite_score=breakdowns[c.id].composite_score,
            grade=breakdowns[c.id].grade,
        )
        for c in companies
    ]


@router.get("/sectors", response_model=list[str])
def list_sectors(db: Session = Depends(get_db)):
    rows = db.query(Company.sector).distinct().order_by(Company.sector).all()
    return [r[0] for r in rows]


@router.get("/companies/{ticker}", response_model=CompanyOut)
def get_company(ticker: str, db: Session = Depends(get_db)):
    company = service.get_company_by_ticker(db, ticker)
    if not company:
        raise HTTPException(status_code=404, detail=f"No company found for ticker '{ticker.upper()}'")

    breakdowns = service.score_all(db)
    percentiles = service.sector_percentiles(db, breakdowns)
    bd = breakdowns[company.id]

    return CompanyOut(
        ticker=company.ticker,
        name=company.name,
        sector=company.sector,
        financials=company.financials,
        esg_raw=company.esg,
        esg_score=EsgScoreOut(
            composite_score=bd.composite_score,
            grade=bd.grade,
            sector_percentile=percentiles[company.id],
            environmental_score=bd.environmental_score,
            social_score=bd.social_score,
            governance_score=bd.governance_score,
            controversy_penalty=bd.controversy_penalty,
        ),
    )
