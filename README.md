# ecosg

**Sustainable investing, made legible.** ecosg is a platform that closes the gap between
financial returns and ESG accountability for retail investors — bringing institutional-grade
sustainability analysis to individual investors, built from a from-scratch financial data
architecture and ESG scoring framework.

This repo is the MVP, and it now has two engines side by side, on purpose: an **ESG scoring
framework** (how accountable is this company) and a **hedge-fund-style multi-factor quant
model** (how would a return-focused fund rank this company on Value, Quality, Momentum, Growth,
and Low-Volatility). Showing both, for the same companies, without blending them into one number,
is the whole point — it's the "gap" the platform is named after, made visible instead of buried.

> **Status:** MVP / demo. All financial and ESG figures are mock/illustrative data, not sourced
> from a real market data or ESG data provider. Nothing in this app is investment advice.

## What's in the MVP

- **ESG scoring framework** (`backend/app/scoring.py`) — turns raw Environmental / Social /
  Governance sub-scores into a single composite score, using **sector-specific pillar
  weights** (materiality differs by industry — e.g. Environmental matters more for Energy than
  Financials), a **controversy penalty**, a **letter grade** (AAA…CCC, the convention used by
  major ESG ratings providers), and a **sector-relative percentile**.
- **Quant factor model** (`backend/app/quant/`) — a hedge-fund-style multi-factor stock model
  ported in from a standalone project: cross-sectional, sector-neutral z-scoring of Value,
  Quality, Momentum, Growth, and Low-Volatility metrics into one composite score and rank,
  inverse-volatility-sized top-N portfolio construction with buffer-band turnover control, and a
  walk-forward backtest engine (Sharpe, Sortino, CAGR, max drawdown, Calmar, beta vs. benchmark).
  See `docs/QUANT_RESEARCH.md` for the full methodology writeup — how hedge funds actually do
  this, and how each piece of the code implements it.
- **Financial data architecture** (`backend/app/models.py`, `database.py`) — a normalized
  SQLite schema (`companies` / `financial_metrics` / `esg_components` / `factor_fundamentals` /
  `price_points`) designed to map cleanly onto a real data warehouse later; both scoring engines
  read from it and compute derived scores on request, so either methodology can evolve without a
  data migration.
- **API** (`backend/app/routers/`) — company list/filter, single-ticker ESG lookup with full
  score breakdown, a portfolio screener endpoint that takes a weighted set of holdings and
  returns aggregated ESG *and* quant scores side by side, plus a `quant/` route group: ranked
  factor scores, a single-ticker factor breakdown, auto-generated top picks, and a backtest
  summary.
- **Frontend** (`frontend/`) — a dashboard (ESG score vs. return scatter + sortable table), a
  stock lookup page (ESG pillar breakdown *and* quant factor breakdown, side by side), a Quant
  Factors page (ESG-vs-quant scatter — the signature "gap" chart — ranked list, auto-generated
  top picks, and a backtest equity curve), and a portfolio screener that shows both scores per
  holding.

## Project structure

```
ecosg/
├── docs/
│   └── QUANT_RESEARCH.md    # Quant factor methodology writeup
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app, CORS, startup seeding
│   │   ├── database.py      # SQLAlchemy engine/session (SQLite)
│   │   ├── models.py        # ORM models + Pydantic schemas (ESG + quant)
│   │   ├── scoring.py       # The ESG scoring framework
│   │   ├── service.py       # ESG query + scoring orchestration
│   │   ├── data_seed.py     # Mock company/financial/ESG dataset
│   │   ├── quant_seed.py    # Synthetic fundamentals + price history for the quant model
│   │   ├── seed.py          # DB seed script (ESG + quant data)
│   │   ├── quant/           # Ported hedge-fund-style multi-factor model
│   │   │   ├── config.py        # Factor weights, sector-neutral scoring, portfolio caps
│   │   │   ├── data.py          # Reads ECOSG's DB (replaces the original's yfinance layer)
│   │   │   ├── factors.py       # Value/Quality/Momentum/Growth/Low-Vol metric computation
│   │   │   ├── scoring.py       # Winsorize -> z-score -> composite score + rank
│   │   │   ├── portfolio.py     # Position sizing, caps, buffer-band BUY/SELL/HOLD signals
│   │   │   ├── backtest.py      # Walk-forward backtest engine + performance metrics
│   │   │   └── service.py       # Query + scoring orchestration for the quant routes
│   │   └── routers/
│   │       ├── companies.py     # ESG endpoints
│   │       ├── portfolio.py     # Combined ESG + quant portfolio screener
│   │       └── quant.py         # Quant factor endpoints
│   ├── tests/               # pytest suite (scoring, quant, backtest, API)
│   ├── requirements.txt
│   └── requirements-dev.txt # + pytest, httpx
└── frontend/
    ├── src/
    │   ├── App.tsx
    │   ├── api.ts            # Typed API client
    │   ├── components.tsx    # Badges, bars, glossary <Term> tooltips, "What does this mean?" panels
    │   ├── glossary.ts       # Plain-English definitions used by tooltips and the Learn page
    │   ├── insights.ts       # One-sentence takeaways that open each page
    │   ├── importHoldings.ts # Parses broker CSV exports / pasted positions into weights (in-browser)
    │   ├── ImportPanel.tsx   # "Import from your broker" drop zone, paste box and review table
    │   └── pages/
    │       ├── Dashboard.tsx     # Explore: ESG vs. 1-year return across all companies
    │       ├── Lookup.tsx        # Company: ESG and quant side by side, each explained
    │       ├── QuantFactors.tsx  # Factors: the five factors, ESG-vs-quant scatter, picks, backtest
    │       ├── Portfolio.tsx     # Portfolio: import or type holdings, see both lenses for the mix
    │       └── Learn.tsx         # Short lessons and the full glossary
    ├── tests/                # node --test suites for insights.ts and importHoldings.ts
    └── package.json
```

## Running locally

Requires Python 3.13 and Node 24.

### Backend

macOS / Linux:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Windows (PowerShell):

```powershell
cd backend
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The database is auto-created and seeded with mock data (both ESG and quant factor data) on
first startup (`backend/ecosg.db`, gitignored). API docs at `http://localhost:8000/docs`.
To reseed from scratch, run `python -m app.seed` with the server stopped.

| Env var | Default | Purpose |
|---|---|---|
| `ECOSG_DB_PATH` | `backend/ecosg.db` | SQLite file to use (the tests point this at a temp file) |
| `ECOSG_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated origins allowed to call the API |

### Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

The suite runs against a throwaway database, never your local `ecosg.db`.

Frontend logic tests use Node's built-in test runner (no extra dependency):

```bash
cd frontend
npm test
```

CI (`.github/workflows/ci.yml`) runs both suites plus the frontend lint and build on every push and PR.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs at `http://localhost:5173` and talks to the backend at `http://localhost:8000` by default
(configurable via `VITE_API_BASE` in `frontend/.env`).

The UI follows the visual language of [Maybe](https://github.com/maybe-finance/maybe)'s
open-source design system (neutral grays, white cards, Geist type), reimplemented in plain CSS
in `src/index.css`; no Maybe code is included. Geist loads from Google Fonts, with a system-font
fallback when offline. It follows your OS light or dark setting.

## ESG scoring methodology (v0.1)

```
composite = sector_weight_E * environmental_score
          + sector_weight_S * social_score
          + sector_weight_G * governance_score
          - controversy_penalty
```

Sector weights and the full ruleset live in `backend/app/scoring.py`, along with the letter
grade bands. This is the single place that encodes "what does a good ESG score mean" — swapping
in real vendor data later (a licensed ESG data feed + a market data API) should only require
changing `data_seed.py` / the DB contents, not the scoring logic itself.

## Quant factor methodology (v0.1)

```
composite = factor_weight_value   * cross_sectional_zscore(value_metrics)
          + factor_weight_quality * cross_sectional_zscore(quality_metrics)
          + factor_weight_momentum * cross_sectional_zscore(momentum_metrics)
          + factor_weight_growth  * cross_sectional_zscore(growth_metrics)
          + factor_weight_low_vol * cross_sectional_zscore(low_vol_metrics)
```

Each z-score is computed **sector-neutrally** (within-sector, not across the whole universe) so
the score reflects stock-picking, not an accidental sector bet — see `docs/QUANT_RESEARCH.md`
for why that matters and the academic grounding for each factor. Unlike the ESG score (0-100),
the quant composite is a cross-sectional z-score (roughly -2.5 to +2.5, centered on 0) — it's
inherently relative to the current universe, so the app surfaces rank and percentile alongside
it rather than a fixed grade scale.

**Where the mock data lives:** `backend/app/quant_seed.py` generates yfinance-`.info`-shaped
fundamentals and ~2 years of synthetic daily prices per company, deterministically (seeded per
ticker) and calibrated to the same 1-year-return/volatility figures already used on the ESG side
— so the two engines describe *the same* mock companies consistently, not two disconnected
datasets. Swapping in real data means rewriting `backend/app/quant/data.py` (the original
project's own documented extension point) to pull from a real fundamentals/price API instead of
ECOSG's database — `factors.py` / `scoring.py` / `portfolio.py` / `backtest.py` don't change.

**What's read-only here vs. the original standalone bot:** the ported project was built to run
as a scheduled bot (`main.py scan` / `main.py backtest`, a Slack/Discord `notify()` hook, a
persisted `portfolio_state.json` for BUY/SELL/HOLD diffing run over run). None of that scheduling
/ notification / state-persistence layer is wired up here — the API exposes the same scoring,
ranking, portfolio-construction, and backtest logic as **read-only** endpoints for display. Anyone
wanting the actual scheduled-bot behavior back can start from `backend/app/quant/` plus the
original bot's `main.py` design (see `docs/QUANT_RESEARCH.md`) and re-add a scheduler and a
notification hook.

## Roadmap ideas beyond the MVP

- Real financial + fundamentals data (a market data API) and a licensed ESG data provider, behind
  the same two data-layer seams (`data_seed.py`+`quant_seed.py` on the ESG/mock side,
  `quant/data.py` on the quant side)
- User accounts + saved/tracked portfolios
- Historical ESG score trends, not just a point-in-time snapshot
- A real risk-adjusted "ESG alpha" model in place of the illustrative return–ESG gap metric, and
  a proper combined ESG+quant screening/optimization view (currently deliberately kept as two
  separate, comparable scores rather than one blended number)
- Point-in-time fundamentals (Sharadar/Compustat/FactSet-style) so the backtest can use the full
  Value/Quality/Growth model instead of the look-ahead-safe price-only default
- Scheduling + alerting (cron/Slack/Discord) if the quant side is ever run as an actual bot again,
  and a real broker-execution boundary (paper trading first) if signals become orders
- Authentication, deployment config, and a production Postgres database
