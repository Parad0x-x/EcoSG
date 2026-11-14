"""One-shot DB seeding script.

Run with:  python -m app.seed
Safe to re-run -- it drops and recreates all tables each time, since
this is mock demo data, not a production migration story.
"""
from __future__ import annotations

import datetime

from .data_seed import CONTROVERSY_EVENTS, ESG_CONTEXT, SEED_COMPANIES
from .database import Base, SessionLocal, engine
from .models import Company, ControversyEvent, EsgComponent, FactorFundamentals, FinancialMetric, PricePoint
from .quant import service as quant_service
from .scoring import DAYS_PER_MONTH
from .quant_seed import generate_fundamentals, generate_price_history


def seed() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Mock event ages are relative to the seed date, so they stay sensible.
    reference_date = datetime.date.today()

    db = SessionLocal()
    try:
        for row in SEED_COMPANIES:
            (
                ticker, name, sector, price, market_cap_b,
                one_year_return_pct, three_year_annualized_return_pct, volatility_pct,
                environmental_score, social_score, governance_score,
            ) = row
            coverage, rater_spread, env_prev, social_prev, gov_prev = ESG_CONTEXT[ticker]

            company = Company(ticker=ticker, name=name, sector=sector)
            db.add(company)
            db.flush()  # assign company.id

            db.add(FinancialMetric(
                company_id=company.id,
                price=price,
                market_cap_b=market_cap_b,
                one_year_return_pct=one_year_return_pct,
                three_year_annualized_return_pct=three_year_annualized_return_pct,
                volatility_pct=volatility_pct,
            ))
            db.add(EsgComponent(
                company_id=company.id,
                environmental_score=environmental_score,
                social_score=social_score,
                governance_score=governance_score,
                data_coverage_pct=coverage,
                rater_spread=rater_spread,
                env_prev=env_prev,
                social_prev=social_prev,
                gov_prev=gov_prev,
            ))
            db.add_all([
                ControversyEvent(
                    company_id=company.id,
                    category=category,
                    occurred_on=reference_date - datetime.timedelta(days=round(months_ago * DAYS_PER_MONTH)),
                    title=title,
                )
                for category, months_ago, title in CONTROVERSY_EVENTS[ticker]
            ])

            fund = generate_fundamentals(ticker, sector, price, market_cap_b)
            db.add(FactorFundamentals(
                company_id=company.id,
                market_cap=fund["marketCap"],
                enterprise_value=fund["enterpriseValue"],
                trailing_pe=fund["trailingPE"],
                price_to_book=fund["priceToBook"],
                return_on_equity=fund["returnOnEquity"],
                return_on_assets=fund["returnOnAssets"],
                gross_margins=fund["grossMargins"],
                operating_margins=fund["operatingMargins"],
                profit_margins=fund["profitMargins"],
                debt_to_equity=fund["debtToEquity"],
                free_cashflow=fund["freeCashflow"],
                ebitda=fund["ebitda"],
                revenue_growth=fund["revenueGrowth"],
                earnings_growth=fund["earningsGrowth"],
                beta=fund["beta"],
                current_price=fund["currentPrice"],
                total_revenue=fund["totalRevenue"],
                total_debt=fund["totalDebt"],
                total_cash=fund["totalCash"],
            ))

            price_series = generate_price_history(
                ticker, price, one_year_return_pct, volatility_pct, beta=fund["beta"]
            )
            db.bulk_save_objects([
                PricePoint(company_id=company.id, date=dt.date(), close=float(close))
                for dt, close in price_series.items()
            ])

        db.commit()
        quant_service.clear_cache()
        print(f"Seeded {len(SEED_COMPANIES)} companies (ESG + quant factor data).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
