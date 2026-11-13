from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import service
from ..database import get_db
from ..models import PortfolioHoldingResult, PortfolioRequest, PortfolioResult
from ..quant import service as quant_service
from ..scoring import grade_for_score

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["portfolio"])


@router.post("/portfolio/screen", response_model=PortfolioResult)
def screen_portfolio(payload: PortfolioRequest, db: Session = Depends(get_db)):
    if not payload.holdings:
        raise HTTPException(status_code=400, detail="Provide at least one holding")

    total_weight = sum(h.weight_pct for h in payload.holdings)
    if total_weight <= 0:
        raise HTTPException(status_code=400, detail="Weights must sum to a positive number")

    breakdowns = service.score_all(db)

    # Quant factor coverage is best-effort: if it fails for any reason, the
    # ESG side of the screener should still work standalone.
    quant_scored = None
    try:
        quant_scored, _cfg = quant_service.compute_quant_scores(db)
    except Exception:
        logger.exception("Quant scoring failed; returning ESG-only portfolio screen")
        quant_scored = None

    results: list[PortfolioHoldingResult] = []
    weighted_score = 0.0
    weighted_return = 0.0
    weighted_quant = 0.0
    quant_weight_covered = 0.0

    for holding in payload.holdings:
        company = service.get_company_by_ticker(db, holding.ticker)
        if not company:
            raise HTTPException(status_code=404, detail=f"Unknown ticker '{holding.ticker.upper()}'")

        bd = breakdowns[company.id]
        norm_weight = holding.weight_pct / total_weight

        weighted_score += bd.composite_score * norm_weight
        weighted_return += company.financials.one_year_return_pct * norm_weight

        quant_row = None
        if quant_scored is not None:
            quant_row = quant_service.get_company_row(quant_scored, company.ticker)
            if quant_row is not None:
                weighted_quant += float(quant_row.composite_score) * norm_weight
                quant_weight_covered += norm_weight

        results.append(PortfolioHoldingResult(
            ticker=company.ticker,
            name=company.name,
            weight_pct=round(holding.weight_pct, 2),
            composite_score=bd.composite_score,
            grade=bd.grade,
            one_year_return_pct=company.financials.one_year_return_pct,
            quant_composite_score=round(float(quant_row.composite_score), 3) if quant_row is not None else None,
            quant_percentile=float(quant_row.percentile) if quant_row is not None else None,
        ))

    # Illustrative "gap" metric: how far weighted return sits from what you'd
    # "expect" if 1 pt of ESG composite score mapped 1:1 to 1 pt of return.
    # This is a deliberately naive placeholder for a real risk-adjusted
    # ESG-alpha model -- flagged as such in the API response shape/docs.
    return_esg_gap = round(weighted_return - weighted_score, 1)

    return PortfolioResult(
        weighted_esg_score=round(weighted_score, 1),
        weighted_one_year_return_pct=round(weighted_return, 1),
        grade=grade_for_score(weighted_score),
        return_esg_gap=return_esg_gap,
        weighted_quant_score=round(weighted_quant / quant_weight_covered, 3) if quant_weight_covered > 0 else None,
        holdings=sorted(results, key=lambda h: h.weight_pct, reverse=True),
    )
