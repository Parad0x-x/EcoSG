# ecosg

Sustainable investing, made legible: an MVP that shows two scores side by side for the same
companies, an ESG accountability score and a hedge-fund-style multi-factor quant score, without
blending them, so the gap between returns and accountability is visible. For retail investors.
All data is mock; nothing is investment advice.

## Live URLs

- Production: none (local only)
- Repo: https://github.com/Parad0x-x/ecosg
- Owner: Parad0x-x
- Deadline: none

## Source-of-truth docs

- `README.md`: product overview, run steps, env vars, both scoring methodologies
- `docs/QUANT_RESEARCH.md`: quant factor model methodology and its academic grounding

This file wins on repo-wide conventions.

# Layer 1: Conventions (I curate this)

Agents read this layer and never edit it unless I ask.

## Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI 0.115, SQLAlchemy 2, Pydantic 2, pandas/numpy, Python 3.13 |
| Frontend | React 19, React Router 7, Recharts 3, Vite 8, TypeScript 6 |
| Storage | SQLite (`backend/ecosg.db`, gitignored, auto-seeded with mock data) |
| Tests | pytest (backend), oxlint + `tsc` via `npm run build` (frontend) |
| CI | GitHub Actions, `.github/workflows/ci.yml` |
| Hosting | none yet |
| Package manager | pip (backend venv in `backend/.venv`), npm (frontend) |

## Locked conventions

- **Two engines stay separate:** ESG scoring lives in `backend/app/scoring.py`, the quant model in
  `backend/app/quant/`. Show them side by side; never blend them into one number.
- **Scores are computed on read**, never stored, so methodology changes need no migration.
- **Data seams:** swapping in real data means changing `data_seed.py` / `quant_seed.py` (ESG side)
  or `quant/data.py` (quant side) only. `quant/factors.py`, `scoring.py`, `portfolio.py`,
  `backtest.py` are ported modules; keep them data-source agnostic.
- **Backtests must stay look-ahead safe:** only price data known at each rebalance date.
- **Repo hygiene:** never commit `.env`, `*.db`, `.venv/`, `node_modules/`, `dist/`.
- **Do not build without asking:** auth/accounts, real data vendors or paid APIs, deployment.

## Tools

- Context7 or official docs for FastAPI, Pydantic, pandas, React, Vite, Recharts APIs.
- chrome-devtools MCP for checking UI changes in a real browser.

## Common tasks

| Task | Command |
|---|---|
| Install backend | `cd backend; python -m venv .venv; .venv\Scripts\pip install -r requirements-dev.txt` |
| Install frontend | `cd frontend; npm ci` |
| Dev backend | `cd backend; .venv\Scripts\python -m uvicorn app.main:app --reload --port 8000` |
| Dev frontend | `cd frontend; npm run dev` (http://localhost:5173) |
| Test | `cd backend; .venv\Scripts\python -m pytest` |
| Lint + build | `cd frontend; npm run lint; npm run build` |
| Reseed DB | `cd backend; .venv\Scripts\python -m app.seed` (server stopped) |
| Deploy | none |

# Layer 2: Build state (agents maintain this)

Update at the end of a session that shipped work: show me the diff, apply after I confirm.
Use ✅ shipped, 🔄 in flight, ⚠️ known issue or not done. Keep this file under 40,000 characters;
move old entries verbatim to AGENTS_ARCHIVE.md under `## Archived YYYY-MM-DD` instead of deleting.

## Architecture

```
backend/app/
  main.py            FastAPI app, CORS, lifespan seeding
  database.py        engine/session (ECOSG_DB_PATH override)
  models.py          ORM tables + Pydantic schemas
  scoring.py         ESG scoring framework
  service.py         ESG query + scoring glue
  data_seed.py       S&P 500 universe (503, from data/sp500.csv); 30 curated rows + deterministic mock numbers
  quant_seed.py      synthetic fundamentals, prices, benchmark
  seed.py            drop/create/seed, clears the quant cache
  quant/             factor model: data, factors, scoring, portfolio, backtest, service (cache)
  routers/           companies, portfolio (both engines), quant
backend/tests/       pytest suite
frontend/src/
  api.ts             typed API client
  pages/             Dashboard (Explore), Lookup (Company), QuantFactors (Factors), Portfolio, Learn (lazy-loaded)
  components.tsx     badges, bars, <GapTrack> (both scores on one line), glossary <Term> tooltips, <Explain> panels
  CompanySearch.tsx  header search by name or ticker (ranking in search.ts)
  glossary.ts        plain-English definitions (tooltips + Learn page)
  insights.ts        one-sentence takeaways that open each page
  importHoldings.ts  parses broker CSV / pasted positions into weights, in the browser
  ImportPanel.tsx    portfolio import UI: drop zone, paste box, review table
  sectors.ts         sector colors, chart axis/grid styles
frontend/tests/      node --test suites for insights.ts, importHoldings.ts and search.ts
```

## Current build state (2026-11-15)

- ✅ ESG scoring v0.2: SASB-materiality weights with a 33% governance floor, industry-adjusted
  score, MSCI seven-band grades, dated controversy events with 12-month decay and grade caps,
  confidence and one-year trend as separate signals (sources in README)
- ✅ Quant v0.2: rank z-scores with shrunk sector means, GP/A, cash-based quality, low beta,
  residual momentum, idiosyncratic vol; backtest uses portfolio.py sizing with drifting weights,
  reports IC and an equal-weight benchmark; mock prices share a market factor, no baked-in momentum
- ✅ 9 API endpoints, 5 frontend pages; startup reseeds a DB with an outdated schema
- ✅ pytest suite (106 tests) and CI for backend tests + frontend lint/tests/build
- ✅ UI is a guided explainer in plain CSS: green ESG and blue quant color fields, a gap track
  showing both scores on one line, header company search, light/dark toggle (`ecosg-theme`),
  tables paged 25 at a time, a takeaway sentence per page, glossary tooltips, Learn page
- ✅ Scatterplots use neutral dots with one highlight (picked sector, or the model's picks) and a trend line
- ✅ Full S&P 500 constituent list (real tickers/names/GICS sectors, mock numbers); Real Estate sector added
- ✅ Vercel deploy as one project with services (`vercel.json`); prod https://ecosg-one.vercel.app, deploy by CLI
- ✅ API reads are CDN-cached and scoring queries eager-load; first request after a deploy still takes ~10s
- ✅ Portfolio import from a broker CSV or pasted positions; parsed in the browser, only tickers and
  weights reach the API; uncovered tickers are flagged and excluded
- ✅ 18 frontend logic tests on Node's built-in runner (no new dependency)
- ✅ Backtest metrics start at the first invested rebalance; benchmark shares the price dates
- ✅ Quant results cached per process (seed() clears it); prices load in one query
- ✅ Routes code-split; Recharts only loads on Dashboard and Quant Factors
- ⚠️ All data is mock. The return-ESG "gap" metric is a naive placeholder, not an alpha model.
- ⚠️ No frontend component or e2e tests; only pure-logic modules are tested.
- ⚠️ Backtest is a mechanics demo: ~11 monthly rebalances, IC 0.06 (t 2.71) on mock prices, unproven.
- ⚠️ Mock numbers sit next to real company names (e.g. BRK.B market cap is not real).
- ⚠️ Mock controversy events use real company names (titles start with "Mock:").
- ⚠️ Import covers the 503 S&P 500 tickers only; real brokerage linking (e.g. SnapTrade) is paid, ask first.

## Environment

- `ECOSG_DB_PATH`: unset (defaults to `backend/ecosg.db`)
- `ECOSG_CORS_ORIGINS`: unset (defaults to the Vite dev origins)
- `VITE_API_BASE`: set in `frontend/.env` (gitignored)

## What's next, ranked

1. Component/e2e tests for Lookup and Portfolio flows (Vitest/Playwright would be new deps, ask first)
2. Neutral wording for mock controversy events, or fictional company names
3. Historical ESG score trends instead of a point-in-time snapshot
4. Replace the naive return-ESG gap with a risk-adjusted comparison
5. Real data behind the existing seams (ask first)
