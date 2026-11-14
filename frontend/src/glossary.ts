// Plain-English definitions shared by inline <Term> tooltips and the Learn page.
export interface GlossaryEntry {
  term: string;
  short: string;
  group: "ESG" | "Quant" | "Returns and risk" | "Portfolio";
}

export const GLOSSARY = {
  esg: {
    term: "ESG score",
    short: "A 0 to 100 score for how responsibly a company is run: its environmental impact, how it treats people, and how it is governed. Higher is better.",
    group: "ESG",
  },
  grade: {
    term: "ESG grade",
    short: "A letter version of the ESG score, from AAA (best) down to CCC (worst), so companies are easy to compare at a glance.",
    group: "ESG",
  },
  environmental: {
    term: "Environmental (E)",
    short: "Emissions, energy use, waste and other effects on the planet.",
    group: "ESG",
  },
  social: {
    term: "Social (S)",
    short: "How the company treats workers, customers, suppliers and communities.",
    group: "ESG",
  },
  governance: {
    term: "Governance (G)",
    short: "Who runs the company and how: board independence, executive pay, shareholder rights and accounting honesty.",
    group: "ESG",
  },
  sectorWeights: {
    term: "Sector weighting",
    short: "E, S and G count for different amounts in different industries. Emissions matter more for an oil company than for a bank, so Energy weights E more heavily.",
    group: "ESG",
  },
  controversy: {
    term: "Controversy penalty",
    short: "Points taken off the ESG score for recent scandals, lawsuits or accidents. The worse the controversy, the bigger the deduction, up to 30 points.",
    group: "ESG",
  },
  sectorPercentile: {
    term: "Sector percentile",
    short: "Where a company ranks against others in its own industry. 80th percentile means it scores better than 80% of its peers.",
    group: "ESG",
  },
  quant: {
    term: "Quant score",
    short: "How attractive a stock looks to the kind of rules-based model hedge funds use to chase returns. It ignores ESG entirely.",
    group: "Quant",
  },
  factor: {
    term: "Factor",
    short: "A measurable trait that has historically been linked to higher returns, such as being cheap (value) or rising in price (momentum).",
    group: "Quant",
  },
  zscore: {
    term: "Z-score",
    short: "How far above or below average something is. 0 is average, +1 is well above, -1 is well below. Most stocks land between -2 and +2.",
    group: "Quant",
  },
  value: {
    term: "Value",
    short: "Is the stock cheap compared with its earnings, cash flow and assets? Cheap stocks score higher.",
    group: "Quant",
  },
  quality: {
    term: "Quality",
    short: "Is the business profitable, efficient and not drowning in debt? Strong, steady businesses score higher.",
    group: "Quant",
  },
  momentum: {
    term: "Momentum",
    short: "Has the price been rising over the past year? Recent winners tend to keep winning for a while, so they score higher.",
    group: "Quant",
  },
  growth: {
    term: "Growth",
    short: "Are sales and earnings growing quickly? Faster growers score higher.",
    group: "Quant",
  },
  lowVol: {
    term: "Low volatility",
    short: "Does the price move calmly? Steadier stocks score higher, because they have historically delivered similar returns with smaller swings.",
    group: "Quant",
  },
  percentile: {
    term: "Percentile",
    short: "Rank out of 100. The 75th percentile means better than 75% of the companies we cover.",
    group: "Quant",
  },
  return1y: {
    term: "1-year return",
    short: "How much the share price changed over the last 12 months, as a percentage.",
    group: "Returns and risk",
  },
  volatility: {
    term: "Volatility",
    short: "How much a price swings up and down, per year. Higher volatility means a bumpier ride.",
    group: "Returns and risk",
  },
  marketCap: {
    term: "Market cap",
    short: "The total value of all the company's shares: share price times number of shares.",
    group: "Returns and risk",
  },
  cagr: {
    term: "CAGR",
    short: "Compound annual growth rate: the steady yearly return that would get you from the starting value to the ending value.",
    group: "Returns and risk",
  },
  sharpe: {
    term: "Sharpe ratio",
    short: "Return earned per unit of risk taken. Above 1 is good, above 2 is excellent, below 0 means you lost money.",
    group: "Returns and risk",
  },
  drawdown: {
    term: "Max drawdown",
    short: "The worst drop from a peak to a low. It answers: at the worst moment, how much would you have been down?",
    group: "Returns and risk",
  },
  benchmark: {
    term: "Benchmark",
    short: "What you compare a strategy against, usually the whole market. Beating the benchmark is the point of picking stocks.",
    group: "Returns and risk",
  },
  backtest: {
    term: "Backtest",
    short: "Testing a strategy on past prices to see how it would have done. Useful, but past results never guarantee future ones.",
    group: "Returns and risk",
  },
  weight: {
    term: "Weight",
    short: "How much of the portfolio a holding takes up. 25% weight means a quarter of your money is in it.",
    group: "Portfolio",
  },
  invVol: {
    term: "Inverse-volatility sizing",
    short: "Putting less money into jumpier stocks and more into calmer ones, so no single holding dominates the risk.",
    group: "Portfolio",
  },
  gap: {
    term: "Return-ESG gap",
    short: "A rough signal of whether a portfolio's returns are running ahead of its accountability or behind it. Illustrative only, not a risk-adjusted measure.",
    group: "Portfolio",
  },
} satisfies Record<string, GlossaryEntry>;

export type TermId = keyof typeof GLOSSARY;
