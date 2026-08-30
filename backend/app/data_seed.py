"""Mock dataset for the ECOSG MVP.

Financial figures and E/S/G sub-scores below are illustrative /
hand-authored approximations for demo purposes -- NOT sourced from
any real financial or ESG data provider, and not investment advice.
Swap `SEED_COMPANIES` for a real data ingestion pipeline (e.g. a
market data API + a licensed ESG data feed) to go from MVP to
production; nothing downstream (scoring.py, the API routes, the
frontend) needs to change shape.

Each row: (ticker, name, sector, price, market_cap_b, 1y_return_pct,
3y_annualized_return_pct, volatility_pct, environmental, social,
governance, controversy_severity)
"""

SEED_COMPANIES = [
    ("AAPL", "Apple Inc.", "Technology", 227.5, 3450.0, 18.2, 22.1, 24.0, 62, 68, 78, 1.5),
    ("MSFT", "Microsoft Corp.", "Technology", 428.9, 3190.0, 14.6, 24.8, 21.0, 74, 76, 82, 0.5),
    ("NVDA", "NVIDIA Corp.", "Technology", 118.3, 2900.0, 45.9, 78.3, 48.0, 55, 60, 70, 2.0),
    ("XOM", "Exxon Mobil Corp.", "Energy", 118.0, 470.0, 9.1, 14.2, 27.0, 34, 48, 61, 6.5),
    ("CVX", "Chevron Corp.", "Energy", 152.4, 280.0, 5.4, 9.8, 26.0, 38, 50, 64, 5.5),
    ("NEE", "NextEra Energy", "Utilities", 72.1, 148.0, 11.3, 6.7, 20.0, 81, 63, 70, 1.0),
    ("DUK", "Duke Energy", "Utilities", 113.6, 88.0, 16.8, 9.1, 15.0, 66, 61, 68, 1.5),
    ("JPM", "JPMorgan Chase & Co.", "Financials", 218.7, 620.0, 24.5, 20.3, 22.0, 58, 66, 74, 3.0,),
    ("GS", "Goldman Sachs Group", "Financials", 540.2, 175.0, 31.2, 24.9, 27.0, 44, 58, 72, 3.5),
    ("V", "Visa Inc.", "Financials", 289.4, 590.0, 12.9, 17.5, 18.0, 60, 71, 80, 0.5),
    ("JNJ", "Johnson & Johnson", "Health Care", 156.8, 378.0, 4.7, 3.2, 14.0, 62, 70, 73, 4.0),
    ("PFE", "Pfizer Inc.", "Health Care", 27.9, 158.0, -8.3, -12.1, 23.0, 55, 68, 66, 3.0),
    ("UNH", "UnitedHealth Group", "Health Care", 512.0, 470.0, 6.1, 8.9, 20.0, 48, 55, 69, 4.5),
    ("PG", "Procter & Gamble", "Consumer Staples", 168.3, 397.0, 8.4, 7.6, 13.0, 68, 72, 76, 1.0),
    ("KO", "Coca-Cola Co.", "Consumer Staples", 63.5, 274.0, 10.1, 6.4, 12.0, 57, 66, 71, 2.0),
    ("WMT", "Walmart Inc.", "Consumer Staples", 78.9, 636.0, 33.6, 28.4, 17.0, 63, 69, 74, 1.5),
    ("AMZN", "Amazon.com Inc.", "Consumer Discretionary", 186.2, 1960.0, 27.3, 26.7, 29.0, 51, 57, 65, 2.5),
    ("TSLA", "Tesla Inc.", "Consumer Discretionary", 251.4, 800.0, 62.1, 12.6, 55.0, 79, 42, 45, 5.0),
    ("HD", "Home Depot Inc.", "Consumer Discretionary", 402.1, 400.0, 15.7, 11.2, 19.0, 60, 64, 72, 1.0),
    ("META", "Meta Platforms Inc.", "Communication Services", 563.3, 1430.0, 38.9, 45.2, 33.0, 54, 46, 63, 4.0),
    ("GOOGL", "Alphabet Inc.", "Communication Services", 175.6, 2150.0, 22.4, 24.9, 26.0, 63, 58, 68, 2.5),
    ("LIN", "Linde plc", "Materials", 452.7, 218.0, 13.5, 15.8, 16.0, 66, 60, 71, 1.0),
    ("FCX", "Freeport-McMoRan", "Materials", 44.8, 64.0, 3.2, 7.1, 38.0, 41, 47, 60, 4.5),
    ("HON", "Honeywell International", "Industrials", 213.5, 137.0, 9.8, 10.4, 18.0, 58, 62, 70, 2.0),
    ("CAT", "Caterpillar Inc.", "Industrials", 358.9, 178.0, 18.3, 16.9, 24.0, 46, 55, 66, 2.5),
    ("RTX", "RTX Corp.", "Industrials", 132.4, 178.0, 41.2, 30.5, 22.0, 52, 57, 68, 3.5),
    ("COP", "ConocoPhillips", "Energy", 102.3, 85.0, -2.1, 11.4, 29.0, 36, 49, 63, 5.0),
    ("SO", "Southern Company", "Utilities", 92.0, 100.0, 14.2, 10.8, 16.0, 64, 62, 69, 1.5),
    ("APD", "Air Products and Chemicals", "Materials", 278.4, 62.0, -6.8, -4.1, 24.0, 63, 58, 69, 1.0),
    ("DIS", "Walt Disney Co.", "Communication Services", 113.2, 205.0, 19.6, -3.2, 28.0, 58, 54, 64, 2.5),
]
