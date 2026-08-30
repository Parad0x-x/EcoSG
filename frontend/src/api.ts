const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export interface CompanySummary {
  ticker: string;
  name: string;
  sector: string;
  one_year_return_pct: number;
  composite_score: number;
  grade: string;
}

export interface FinancialMetric {
  price: number;
  market_cap_b: number;
  one_year_return_pct: number;
  three_year_annualized_return_pct: number;
  volatility_pct: number;
}

export interface EsgComponentRaw {
  environmental_score: number;
  social_score: number;
  governance_score: number;
  controversy_severity: number;
}

export interface EsgScore {
  composite_score: number;
  grade: string;
  sector_percentile: number;
  environmental_score: number;
  social_score: number;
  governance_score: number;
  controversy_penalty: number;
}

export interface CompanyDetail {
  ticker: string;
  name: string;
  sector: string;
  financials: FinancialMetric;
  esg_raw: EsgComponentRaw;
  esg_score: EsgScore;
}

export interface PortfolioHoldingResult {
  ticker: string;
  name: string;
  weight_pct: number;
  composite_score: number;
  grade: string;
  one_year_return_pct: number;
  quant_composite_score: number | null;
  quant_percentile: number | null;
}

export interface PortfolioResult {
  weighted_esg_score: number;
  weighted_one_year_return_pct: number;
  grade: string;
  return_esg_gap: number;
  weighted_quant_score: number | null;
  holdings: PortfolioHoldingResult[];
}

// ---------------------------------------------------------------------------
// Quant factor model
// ---------------------------------------------------------------------------

export interface QuantFactorSummary {
  ticker: string;
  name: string;
  sector: string;
  composite_score: number;
  percentile: number;
  rank: number;
}

export interface QuantFactorFamilyScores {
  value_score: number | null;
  quality_score: number | null;
  momentum_score: number | null;
  growth_score: number | null;
  low_vol_score: number | null;
}

export interface QuantCompanyDetail {
  ticker: string;
  name: string;
  sector: string;
  families: QuantFactorFamilyScores;
  composite_score: number;
  percentile: number;
  rank: number;
  raw_metrics: Record<string, number | null>;
}

export interface QuantTopPick {
  ticker: string;
  name: string;
  sector: string;
  target_weight_pct: number;
  composite_score: number;
  rank: number;
}

export interface BacktestMetrics {
  cagr: number | null;
  annualized_volatility: number | null;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  max_drawdown: number | null;
  calmar_ratio: number | null;
  beta_vs_benchmark: number | null;
  benchmark_cagr: number | null;
  excess_cagr_vs_benchmark: number | null;
  daily_win_rate: number | null;
  total_return: number | null;
}

export interface EquityCurvePoint {
  date: string;
  portfolio: number;
  benchmark: number;
}

export interface BacktestSummary {
  metrics: BacktestMetrics;
  equity_curve: EquityCurvePoint[];
  methodology_note: string;
}

class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore parse errors */
    }
    throw new ApiError(detail);
  }
  return res.json();
}

export async function fetchCompanies(sector?: string): Promise<CompanySummary[]> {
  const url = new URL(`${API_BASE}/api/companies`);
  if (sector) url.searchParams.set("sector", sector);
  return handle(await fetch(url));
}

export async function fetchSectors(): Promise<string[]> {
  return handle(await fetch(`${API_BASE}/api/sectors`));
}

export async function fetchCompany(ticker: string): Promise<CompanyDetail> {
  return handle(await fetch(`${API_BASE}/api/companies/${encodeURIComponent(ticker)}`));
}

export async function screenPortfolio(
  holdings: { ticker: string; weight_pct: number }[]
): Promise<PortfolioResult> {
  return handle(
    await fetch(`${API_BASE}/api/portfolio/screen`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ holdings }),
    })
  );
}

export async function fetchQuantFactors(sector?: string): Promise<QuantFactorSummary[]> {
  const url = new URL(`${API_BASE}/api/quant/factors`);
  if (sector) url.searchParams.set("sector", sector);
  return handle(await fetch(url));
}

export async function fetchQuantCompany(ticker: string): Promise<QuantCompanyDetail> {
  return handle(await fetch(`${API_BASE}/api/quant/companies/${encodeURIComponent(ticker)}`));
}

export async function fetchQuantTopPicks(): Promise<QuantTopPick[]> {
  return handle(await fetch(`${API_BASE}/api/quant/portfolio/picks`));
}

export async function fetchQuantBacktest(): Promise<BacktestSummary> {
  return handle(await fetch(`${API_BASE}/api/quant/backtest`));
}

export { ApiError };
