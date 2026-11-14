from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    BacktestSummary,
    QuantCompanyOut,
    QuantFactorFamilyScores,
    QuantFactorSummary,
)
from ..quant import portfolio as quant_portfolio
from ..quant import service as quant_service

router = APIRouter(prefix="/api/quant", tags=["quant"])

# Raw metrics worth surfacing per family, for the transparency panel on the
# single-ticker view (kept small and readable rather than dumping every
# intermediate column).
_RAW_METRIC_LABELS = {
    "earnings_yield": "earnings_yield",
    "fcf_yield": "fcf_yield",
    "book_to_price": "book_to_price",
    "roic": "roic_proxy",
    "roe": "roe",
    "gpoa": "gross_profit_to_assets",
    "cfoa": "fcf_to_assets",
    "mom_12_1": "momentum_12_1",
    "revenue_growth_yoy": "revenue_growth_yoy",
    "realized_vol_inv": "realized_vol_inv",
    "low_beta": "low_beta",
}


@router.get("/factors", response_model=list[QuantFactorSummary])
def list_factor_scores(sector: str | None = None, db: Session = Depends(get_db)):
    scored, _cfg = quant_service.compute_quant_scores(db)
    if sector:
        scored = scored[scored["sector"] == sector]
    return [
        QuantFactorSummary(
            ticker=row.ticker,
            name=row.name,
            sector=row.sector,
            composite_score=round(float(row.composite_score), 3),
            percentile=float(row.percentile),
            rank=int(row.rank),
        )
        for row in scored.itertuples()
    ]


@router.get("/companies/{ticker}", response_model=QuantCompanyOut)
def get_company_factors(ticker: str, db: Session = Depends(get_db)):
    scored, _cfg = quant_service.compute_quant_scores(db)
    row = quant_service.get_company_row(scored, ticker)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No quant coverage for ticker '{ticker.upper()}'")

    raw = {
        label: (round(float(row[col]), 4) if col in row.index and row[col] == row[col] else None)
        for col, label in _RAW_METRIC_LABELS.items()
    }

    def _val(col: str) -> float | None:
        v = row[col]
        return round(float(v), 3) if v == v else None  # v == v is False for NaN

    return QuantCompanyOut(
        ticker=row["ticker"],
        name=row["name"],
        sector=row["sector"],
        families=QuantFactorFamilyScores(
            value_score=_val("value_score"),
            quality_score=_val("quality_score"),
            momentum_score=_val("momentum_score"),
            growth_score=_val("growth_score"),
            low_vol_score=_val("low_vol_score"),
        ),
        composite_score=round(float(row["composite_score"]), 3),
        percentile=float(row["percentile"]),
        rank=int(row["rank"]),
        raw_metrics=raw,
    )


@router.get("/portfolio/picks")
def get_top_picks(db: Session = Depends(get_db)):
    """Auto-generated top-N picks from the factor model (inverse-vol sized),
    the same output `main.py scan` would hand a scheduler in the original
    standalone bot -- here just read-only, for display."""
    scored, cfg = quant_service.compute_quant_scores(db)
    prices = quant_service.load_prices(db)
    signals = quant_portfolio.generate_signals(scored, prices, cfg, current_holdings={})
    picks = signals[signals["action"] == "BUY"].sort_values("target_weight", ascending=False)
    return [
        {
            "ticker": r["ticker"],
            "name": scored.set_index("ticker").loc[r["ticker"], "name"],
            "sector": r.get("sector", "Unknown"),
            "target_weight_pct": round(float(r["target_weight"]) * 100, 2),
            "composite_score": round(float(r["composite_score"]), 3),
            "rank": int(r["rank"]),
        }
        for _, r in picks.iterrows()
    ]


@router.get("/backtest", response_model=BacktestSummary)
def get_backtest(db: Session = Depends(get_db)):
    result = quant_service.run_universe_backtest(db)
    return BacktestSummary(
        metrics=result["metrics"],
        equity_curve=result["equity_curve"],
        methodology_note=(
            "Walk-forward monthly-rebalanced backtest using a look-ahead-safe, price-only "
            "momentum + low-volatility score (not the full fundamentals model) -- the same "
            "honest limitation the original factor model documents: fundamentals snapshots "
            "have no point-in-time history, so using them here would leak future information "
            "into the past. Synthetic price data; not a real historical simulation."
        ),
    )
