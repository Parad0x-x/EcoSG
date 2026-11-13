"""
data.py
-------
Data-access layer for the quant factor model -- the ECOSG-native
replacement for the original hedge_stock_bot project's yfinance-based
data.py. Same job (turn a data source into the clean DataFrames factors.py
/ scoring.py / portfolio.py / backtest.py expect), different source: our
own database instead of the network, so the quant model runs on exactly the
same mock company set as the ESG side of the app, with no external calls.

Every function here takes a SQLAlchemy Session and returns the same shape
of pandas object the original project's function of the same name did, so
factors.py / scoring.py / portfolio.py / backtest.py needed zero changes.
"""
from __future__ import annotations

from typing import List

import pandas as pd
from sqlalchemy.orm import Session

from ..models import Company, FactorFundamentals, PricePoint

FUNDAMENTAL_FIELDS = [
    "marketCap", "enterpriseValue", "trailingPE", "priceToBook",
    "returnOnEquity", "returnOnAssets", "grossMargins", "operatingMargins",
    "profitMargins", "debtToEquity", "freeCashflow", "ebitda",
    "revenueGrowth", "earningsGrowth", "beta", "currentPrice",
    "totalRevenue", "totalDebt", "totalCash",
]

_FIELD_TO_COLUMN = {
    "marketCap": "market_cap",
    "enterpriseValue": "enterprise_value",
    "trailingPE": "trailing_pe",
    "priceToBook": "price_to_book",
    "returnOnEquity": "return_on_equity",
    "returnOnAssets": "return_on_assets",
    "grossMargins": "gross_margins",
    "operatingMargins": "operating_margins",
    "profitMargins": "profit_margins",
    "debtToEquity": "debt_to_equity",
    "freeCashflow": "free_cashflow",
    "ebitda": "ebitda",
    "revenueGrowth": "revenue_growth",
    "earningsGrowth": "earnings_growth",
    "beta": "beta",
    "currentPrice": "current_price",
    "totalRevenue": "total_revenue",
    "totalDebt": "total_debt",
    "totalCash": "total_cash",
}


def get_universe(db: Session) -> pd.DataFrame:
    """DataFrame [ticker, sector, sub_industry] -- every company ECOSG covers."""
    companies = db.query(Company).order_by(Company.ticker).all()
    return pd.DataFrame({
        "ticker": [c.ticker for c in companies],
        "sector": [c.sector for c in companies],
        "sub_industry": [c.sector for c in companies],  # no finer taxonomy in the mock dataset
    })


def fetch_fundamentals(db: Session, tickers: List[str]) -> pd.DataFrame:
    """DataFrame [ticker, sector, <FUNDAMENTAL_FIELDS>] for the given tickers."""
    companies = (
        db.query(Company)
        .filter(Company.ticker.in_(tickers))
        .order_by(Company.ticker)
        .all()
    )
    rows = []
    for c in companies:
        ff = c.factor_fundamentals
        row = {"ticker": c.ticker, "sector": c.sector}
        for api_field, column in _FIELD_TO_COLUMN.items():
            row[api_field] = getattr(ff, column)
        rows.append(row)
    return pd.DataFrame(rows)


def fetch_price_history(db: Session, tickers: List[str]) -> pd.DataFrame:
    """Wide DataFrame: index=date, columns=ticker, values=close."""
    companies = (
        db.query(Company)
        .filter(Company.ticker.in_(tickers))
        .all()
    )
    series = {}
    for c in companies:
        points = (
            db.query(PricePoint)
            .filter(PricePoint.company_id == c.id)
            .order_by(PricePoint.date)
            .all()
        )
        if not points:
            continue
        idx = pd.to_datetime([p.date for p in points])
        series[c.ticker] = pd.Series([p.close for p in points], index=idx)
    prices = pd.DataFrame(series)
    return prices.sort_index()


def fetch_benchmark(dates: pd.DatetimeIndex) -> pd.Series:
    """Synthetic benchmark ('SPY'-like) series on `dates` -- see quant_seed.generate_benchmark_series."""
    from ..quant_seed import generate_benchmark_series
    return generate_benchmark_series(dates)
