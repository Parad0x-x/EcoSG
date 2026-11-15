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
governance)

ESG_CONTEXT and CONTROVERSY_EVENTS below are equally mock. Every event is an
illustrative placeholder ("Mock: ..."), never a real allegation about the
named company. Event ages are in months before the seed date, so the seed
script turns them into dates relative to the day it runs.

The universe is the full S&P 500: data/sp500.csv holds the real constituent
list (ticker, name, GICS sector, with "Information Technology" shortened to
"Technology") from github.com/datasets/s-and-p-500-companies (PDDL licence).
Only that list is real. The 30 CURATED_COMPANIES keep their hand-authored
numbers; every other company gets mock numbers drawn deterministically per
ticker, so reseeding always produces the same dataset.
"""
import csv
import hashlib
import random
from pathlib import Path

SP500_CSV = Path(__file__).parent / "data" / "sp500.csv"

CURATED_COMPANIES = [
    ("AAPL", "Apple Inc.", "Technology", 227.5, 3450.0, 18.2, 22.1, 24.0, 62, 68, 78),
    ("MSFT", "Microsoft Corp.", "Technology", 428.9, 3190.0, 14.6, 24.8, 21.0, 74, 76, 82),
    ("NVDA", "NVIDIA Corp.", "Technology", 118.3, 2900.0, 45.9, 78.3, 48.0, 55, 60, 70),
    ("XOM", "Exxon Mobil Corp.", "Energy", 118.0, 470.0, 9.1, 14.2, 27.0, 34, 48, 61),
    ("CVX", "Chevron Corp.", "Energy", 152.4, 280.0, 5.4, 9.8, 26.0, 38, 50, 64),
    ("NEE", "NextEra Energy", "Utilities", 72.1, 148.0, 11.3, 6.7, 20.0, 81, 63, 70),
    ("DUK", "Duke Energy", "Utilities", 113.6, 88.0, 16.8, 9.1, 15.0, 66, 61, 68),
    ("JPM", "JPMorgan Chase & Co.", "Financials", 218.7, 620.0, 24.5, 20.3, 22.0, 58, 66, 74),
    ("GS", "Goldman Sachs Group", "Financials", 540.2, 175.0, 31.2, 24.9, 27.0, 44, 58, 72),
    ("V", "Visa Inc.", "Financials", 289.4, 590.0, 12.9, 17.5, 18.0, 60, 71, 80),
    ("JNJ", "Johnson & Johnson", "Health Care", 156.8, 378.0, 4.7, 3.2, 14.0, 62, 70, 73),
    ("PFE", "Pfizer Inc.", "Health Care", 27.9, 158.0, -8.3, -12.1, 23.0, 55, 68, 66),
    ("UNH", "UnitedHealth Group", "Health Care", 512.0, 470.0, 6.1, 8.9, 20.0, 48, 55, 69),
    ("PG", "Procter & Gamble", "Consumer Staples", 168.3, 397.0, 8.4, 7.6, 13.0, 68, 72, 76),
    ("KO", "Coca-Cola Co.", "Consumer Staples", 63.5, 274.0, 10.1, 6.4, 12.0, 57, 66, 71),
    ("WMT", "Walmart Inc.", "Consumer Staples", 78.9, 636.0, 33.6, 28.4, 17.0, 63, 69, 74),
    ("AMZN", "Amazon.com Inc.", "Consumer Discretionary", 186.2, 1960.0, 27.3, 26.7, 29.0, 51, 57, 65),
    ("TSLA", "Tesla Inc.", "Consumer Discretionary", 251.4, 800.0, 62.1, 12.6, 55.0, 79, 42, 45),
    ("HD", "Home Depot Inc.", "Consumer Discretionary", 402.1, 400.0, 15.7, 11.2, 19.0, 60, 64, 72),
    ("META", "Meta Platforms Inc.", "Communication Services", 563.3, 1430.0, 38.9, 45.2, 33.0, 54, 46, 63),
    ("GOOGL", "Alphabet Inc.", "Communication Services", 175.6, 2150.0, 22.4, 24.9, 26.0, 63, 58, 68),
    ("LIN", "Linde plc", "Materials", 452.7, 218.0, 13.5, 15.8, 16.0, 66, 60, 71),
    ("FCX", "Freeport-McMoRan", "Materials", 44.8, 64.0, 3.2, 7.1, 38.0, 41, 47, 60),
    ("HON", "Honeywell International", "Industrials", 213.5, 137.0, 9.8, 10.4, 18.0, 58, 62, 70),
    ("CAT", "Caterpillar Inc.", "Industrials", 358.9, 178.0, 18.3, 16.9, 24.0, 46, 55, 66),
    ("RTX", "RTX Corp.", "Industrials", 132.4, 178.0, 41.2, 30.5, 22.0, 52, 57, 68),
    ("COP", "ConocoPhillips", "Energy", 102.3, 85.0, -2.1, 11.4, 29.0, 36, 49, 63),
    ("SO", "Southern Company", "Utilities", 92.0, 100.0, 14.2, 10.8, 16.0, 64, 62, 69),
    ("APD", "Air Products and Chemicals", "Materials", 278.4, 62.0, -6.8, -4.1, 24.0, 63, 58, 69),
    ("DIS", "Walt Disney Co.", "Communication Services", 113.2, 205.0, 19.6, -3.2, 28.0, 58, 54, 64),
]

# ticker -> (data_coverage_pct, rater_spread, env_prev, social_prev, gov_prev)
# Coverage: share of scoring inputs the company reports. Rater spread: simulated
# standard deviation of pillar scores across rating providers, 0-100 scale.
# *_prev: pillar scores one year earlier, for the trend signal.
ESG_CONTEXT = {
    "AAPL": (94, 6, 60, 67, 77),
    "MSFT": (96, 5, 69, 74, 81),
    "NVDA": (78, 11, 49, 57, 69),
    "XOM": (90, 12, 35, 49, 62),
    "CVX": (88, 10, 37, 50, 64),
    "NEE": (92, 7, 74, 61, 69),
    "DUK": (87, 7, 64, 60, 68),
    "JPM": (95, 7, 57, 66, 74),
    "GS": (85, 9, 45, 58, 72),
    "V": (89, 6, 59, 70, 79),
    "JNJ": (93, 8, 62, 71, 74),
    "PFE": (90, 9, 56, 70, 68),
    "UNH": (82, 12, 50, 60, 71),
    "PG": (95, 5, 67, 71, 76),
    "KO": (91, 8, 56, 66, 70),
    "WMT": (88, 9, 60, 66, 73),
    "AMZN": (76, 14, 47, 55, 64),
    "TSLA": (64, 21, 78, 47, 50),
    "HD": (86, 7, 59, 63, 72),
    "META": (72, 17, 55, 52, 66),
    "GOOGL": (84, 11, 62, 58, 68),
    "LIN": (91, 6, 64, 59, 71),
    "FCX": (70, 14, 40, 46, 60),
    "HON": (88, 8, 57, 61, 70),
    "CAT": (80, 10, 45, 54, 66),
    "RTX": (74, 13, 52, 57, 68),
    "COP": (83, 11, 36, 49, 63),
    "SO": (86, 9, 61, 61, 69),
    "APD": (82, 8, 58, 57, 68),
    "DIS": (79, 12, 59, 55, 65),
}

# ticker -> [(category 1-5, months before seed date, title)]. Illustrative only.
CONTROVERSY_EVENTS = {
    "AAPL": [(2, 10, "Mock: supply-chain labor complaint"), (1, 28, "Mock: repair-policy consumer complaint")],
    "MSFT": [(1, 26, "Mock: data privacy inquiry")],
    "NVDA": [(2, 6, "Mock: export-control compliance question"), (2, 24, "Mock: product disclosure complaint")],
    "XOM": [
        (5, 7, "Mock: major spill at an operating site"),
        (3, 16, "Mock: emissions reporting dispute"),
        (2, 3, "Mock: community health complaint"),
    ],
    "CVX": [
        (5, 20, "Mock: pipeline rupture and cleanup"),
        (4, 5, "Mock: flaring permit violations"),
        (3, 12, "Mock: indigenous land-rights dispute"),
    ],
    "NEE": [(2, 22, "Mock: wildlife impact complaint at a wind site")],
    "DUK": [(2, 10, "Mock: coal-ash storage complaint"), (1, 30, "Mock: rate-case billing complaint")],
    "JPM": [(3, 8, "Mock: regulatory fine over record-keeping"), (2, 20, "Mock: overdraft fee complaint")],
    "GS": [(4, 15, "Mock: fund mis-selling settlement"), (2, 5, "Mock: workplace culture complaint")],
    "V": [],
    "JNJ": [(4, 6, "Mock: product-safety litigation"), (3, 26, "Mock: marketing practices settlement")],
    "PFE": [(3, 8, "Mock: drug pricing inquiry"), (2, 20, "Mock: clinical-trial disclosure complaint")],
    "UNH": [(4, 3, "Mock: claims-denial investigation"), (3, 18, "Mock: patient data breach")],
    "PG": [(2, 18, "Mock: palm-oil sourcing complaint")],
    "KO": [(2, 6, "Mock: plastic packaging pollution complaint"), (2, 24, "Mock: water use dispute")],
    "WMT": [(2, 10, "Mock: store worker scheduling complaint"), (1, 28, "Mock: supplier payment-terms complaint")],
    "AMZN": [(3, 14, "Mock: warehouse safety citation"), (2, 4, "Mock: packaging waste complaint")],
    "TSLA": [
        (4, 2, "Mock: factory workplace discrimination suit"),
        (3, 10, "Mock: driver-assist safety probe"),
        (2, 30, "Mock: governance disclosure complaint"),
    ],
    "HD": [(2, 20, "Mock: lead-paint renovation complaint")],
    "META": [(4, 6, "Mock: user data privacy fine"), (3, 26, "Mock: content moderation labor complaint")],
    "GOOGL": [(3, 14, "Mock: competition law fine"), (2, 4, "Mock: data centre water use complaint")],
    "LIN": [(2, 18, "Mock: plant emissions permit complaint")],
    "FCX": [(4, 3, "Mock: tailings dam safety incident"), (3, 18, "Mock: community relocation dispute")],
    "HON": [(2, 6, "Mock: legacy contamination cleanup claim"), (2, 24, "Mock: export compliance complaint")],
    "CAT": [(3, 14, "Mock: tax structure dispute"), (2, 4, "Mock: dealer emissions complaint")],
    "RTX": [(4, 15, "Mock: defence contract pricing settlement"), (2, 5, "Mock: export licence complaint")],
    "COP": [
        (4, 2, "Mock: methane leak at a production site"),
        (3, 10, "Mock: Arctic drilling permit challenge"),
        (2, 30, "Mock: royalty payment dispute"),
    ],
    "SO": [(2, 10, "Mock: power plant cost overrun complaint"), (1, 30, "Mock: coal-ash disposal complaint")],
    "APD": [(2, 22, "Mock: hydrogen plant permit complaint")],
    "DIS": [(3, 14, "Mock: theme park labor dispute"), (2, 4, "Mock: content licensing complaint")],
}

# --- Mock numbers for the rest of the S&P 500 --------------------------------
# sector -> (E, S, G) mean pillar scores and typical annual volatility %,
# roughly matching the curated rows for each sector.
_SECTOR_PILLARS: dict[str, tuple[float, float, float, float]] = {
    "Energy": (37, 49, 62, 28),
    "Utilities": (68, 62, 69, 17),
    "Materials": (55, 55, 66, 25),
    "Industrials": (53, 58, 68, 22),
    "Technology": (62, 64, 74, 32),
    "Financials": (55, 64, 74, 23),
    "Health Care": (55, 64, 69, 22),
    "Consumer Discretionary": (60, 55, 64, 30),
    "Consumer Staples": (62, 68, 73, 15),
    "Communication Services": (58, 53, 65, 28),
    "Real Estate": (58, 58, 68, 22),
}
_DEFAULT_PILLARS = (56, 60, 68, 24)

_GENERIC_ISSUES = [
    "workplace safety complaint", "data privacy complaint", "supplier labor complaint",
    "accounting disclosure question", "consumer protection complaint", "board pay dispute",
]
_SECTOR_ISSUES: dict[str, list[str]] = {
    "Energy": ["emissions permit violation", "spill at an operating site", "methane leak report"],
    "Utilities": ["rate-case billing complaint", "coal-ash storage complaint", "outage response probe"],
    "Materials": ["plant emissions complaint", "tailings safety incident", "water discharge violation"],
    "Industrials": ["factory safety citation", "export compliance question", "product recall"],
    "Technology": ["user data breach", "export-control question", "product disclosure complaint"],
    "Financials": ["regulatory fine over record-keeping", "fee practices complaint", "mis-selling settlement"],
    "Health Care": ["product-safety litigation", "drug pricing inquiry", "patient data breach"],
    "Consumer Discretionary": ["warehouse safety citation", "product recall", "franchise labor dispute"],
    "Consumer Staples": ["packaging waste complaint", "sourcing deforestation complaint", "product labeling complaint"],
    "Communication Services": ["user privacy fine", "content moderation complaint", "competition law inquiry"],
    "Real Estate": ["tenant safety complaint", "building energy disclosure complaint", "zoning dispute"],
}
_HIGH_IMPACT_SECTORS = {"Energy", "Materials", "Utilities"}


def _rng(ticker: str) -> random.Random:
    return random.Random(int(hashlib.sha256(f"{ticker}:universe".encode()).hexdigest()[:12], 16))


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _mock_company(ticker: str, name: str, sector: str):
    """One seed row, its ESG context and its controversy events, all mock."""
    r = _rng(ticker)
    e_mu, s_mu, g_mu, vol_mu = _SECTOR_PILLARS.get(sector, _DEFAULT_PILLARS)
    vol = round(_clip(r.gauss(vol_mu, 6), 10, 70), 1)
    pillars = [round(_clip(r.gauss(mu, 9), 15, 95)) for mu in (e_mu, s_mu, g_mu)]
    row = (
        ticker, name, sector,
        round(_clip(r.lognormvariate(4.7, 0.8), 8, 1500), 2),     # price, median ~110
        round(_clip(r.lognormvariate(3.55, 0.85), 5, 900), 1),    # market cap $B, median ~35
        round(_clip(r.gauss(10, vol * 0.9), -60, 150), 1),        # 1y return %
        round(_clip(r.gauss(8, vol * 0.4), -30, 60), 1),          # 3y annualized %
        vol,
        *pillars,
    )
    context = (
        round(_clip(r.gauss(82, 9), 50, 99)),                     # data coverage %
        round(_clip(r.gauss(10, 4), 3, 25)),                      # rater spread
        *(round(_clip(p - r.gauss(1, 4), 15, 95)) for p in pillars),  # prior-year pillars
    )
    issues = _SECTOR_ISSUES.get(sector, []) + _GENERIC_ISSUES
    cat_weights = [25, 35, 25, 10, 5] if sector in _HIGH_IMPACT_SECTORS else [30, 40, 20, 8, 2]
    events = [
        (r.choices([1, 2, 3, 4, 5], weights=cat_weights)[0], r.randint(1, 34), f"Mock: {r.choice(issues)}")
        for _ in range(r.choices([0, 1, 2, 3], weights=[35, 40, 20, 5])[0])
    ]
    return row, context, events


def _build_universe():
    curated = {row[0] for row in CURATED_COMPANIES}
    rows, context, events = list(CURATED_COMPANIES), dict(ESG_CONTEXT), dict(CONTROVERSY_EVENTS)
    with SP500_CSV.open(encoding="utf-8", newline="") as f:
        for rec in csv.DictReader(f):
            if rec["ticker"] in curated:
                continue
            row, ctx, evs = _mock_company(rec["ticker"], rec["name"], rec["sector"])
            rows.append(row)
            context[rec["ticker"]] = ctx
            events[rec["ticker"]] = evs
    return rows, context, events


SEED_COMPANIES, ESG_CONTEXT, CONTROVERSY_EVENTS = _build_universe()
