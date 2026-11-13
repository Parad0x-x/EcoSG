import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiError, fetchCompany, fetchQuantCompany, type CompanyDetail, type QuantCompanyDetail } from "../api";
import { FactorBar, GradeBadge, PillarBar, ReturnValue } from "../components";

interface LookupResult {
  ticker: string;
  company: CompanyDetail | null;
  quant: QuantCompanyDetail | null;
  error: string | null;
}

export default function Lookup() {
  const ticker = useParams().ticker?.trim().toUpperCase();
  const navigate = useNavigate();
  const [input, setInput] = useState(ticker || "");
  const [result, setResult] = useState<LookupResult | null>(null);

  // The URL is the only trigger: submitting navigates, and this effect loads.
  useEffect(() => {
    if (!ticker) return;
    let stale = false;
    // Quant coverage is best-effort: a ticker can exist on the ESG side
    // without quant coverage, so its failure must not block the page.
    Promise.allSettled([fetchCompany(ticker), fetchQuantCompany(ticker)]).then(([c, q]) => {
      if (stale) return;
      setResult({
        ticker,
        company: c.status === "fulfilled" ? c.value : null,
        quant: q.status === "fulfilled" ? q.value : null,
        error:
          c.status === "rejected"
            ? c.reason instanceof ApiError
              ? c.reason.message
              : "Failed to look up ticker"
            : null,
      });
    });
    return () => {
      stale = true;
    };
  }, [ticker]);

  const current = result && result.ticker === ticker ? result : null;
  const loading = Boolean(ticker) && !current;
  const company = current?.company ?? null;
  const quant = current?.quant ?? null;
  const error = current?.error ?? null;

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const next = input.trim().toUpperCase();
    if (next) navigate(`/lookup/${encodeURIComponent(next)}`);
  }

  return (
    <>
      <h1>Stock Lookup</h1>
      <p className="subtitle">
        Look up a covered ticker to see its financials alongside a full ESG score breakdown.
      </p>

      <div className="panel">
        <form className="field-row" onSubmit={onSubmit}>
          <input
            type="text"
            placeholder="Ticker, e.g. AAPL"
            value={input}
            onChange={(e) => setInput(e.target.value.toUpperCase())}
            style={{ textTransform: "uppercase", width: 160 }}
          />
          <button type="submit" disabled={loading}>
            {loading ? "Looking up…" : "Look up"}
          </button>
        </form>
        {error && <div className="error-box">{error}</div>}
      </div>

      {company && (
        <>
          <div className="panel">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <div>
                <h1 style={{ marginBottom: 0 }}>
                  {company.ticker} <span style={{ color: "var(--text-dim)", fontWeight: 400 }}>{company.name}</span>
                </h1>
                <p className="subtitle" style={{ marginTop: 4 }}>{company.sector}</p>
              </div>
              <GradeBadge grade={company.esg_score.grade} />
            </div>

            <div className="stat-grid">
              <div className="stat">
                <div className="stat-label">ESG composite</div>
                <div className="stat-value">{company.esg_score.composite_score.toFixed(1)}</div>
              </div>
              <div className="stat">
                <div className="stat-label">Sector percentile</div>
                <div className="stat-value">{company.esg_score.sector_percentile.toFixed(0)}th</div>
              </div>
              <div className="stat">
                <div className="stat-label">Price</div>
                <div className="stat-value">${company.financials.price.toFixed(2)}</div>
              </div>
              <div className="stat">
                <div className="stat-label">1Y return</div>
                <div className="stat-value"><ReturnValue pct={company.financials.one_year_return_pct} /></div>
              </div>
            </div>

            <h3 style={{ marginBottom: 0 }}>ESG pillar breakdown</h3>
            <div className="pillar-bars">
              <PillarBar label="Environmental" value={company.esg_score.environmental_score} />
              <PillarBar label="Social" value={company.esg_score.social_score} />
              <PillarBar label="Governance" value={company.esg_score.governance_score} />
            </div>
            {company.esg_score.controversy_penalty > 0 && (
              <p style={{ color: "var(--grade-b)", fontSize: "0.85rem" }}>
                −{company.esg_score.controversy_penalty.toFixed(1)} pt controversy penalty applied
                (severity {company.esg_raw.controversy_severity.toFixed(1)}/10)
              </p>
            )}
          </div>

          {quant && (
            <div className="panel">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <h3 style={{ marginTop: 0, marginBottom: 0 }}>Quant factor breakdown</h3>
                <span style={{ color: "var(--text-dim)", fontSize: "0.85rem" }}>
                  Rank {quant.rank} · {quant.percentile.toFixed(0)}th percentile
                </span>
              </div>
              <p style={{ color: "var(--text-dim)", fontSize: "0.82rem" }}>
                Hedge-fund-style factor composite: {quant.composite_score >= 0 ? "+" : ""}
                {quant.composite_score.toFixed(2)} (sector-neutral z-score, positive = favored).
              </p>
              <div className="pillar-bars">
                <FactorBar label="Value" value={quant.families.value_score} />
                <FactorBar label="Quality" value={quant.families.quality_score} />
                <FactorBar label="Momentum" value={quant.families.momentum_score} />
                <FactorBar label="Growth" value={quant.families.growth_score} />
                <FactorBar label="Low Volatility" value={quant.families.low_vol_score} />
              </div>
            </div>
          )}

          <div className="panel">
            <h3 style={{ marginTop: 0 }}>Financials</h3>
            <div className="stat-grid">
              <div className="stat">
                <div className="stat-label">Market cap</div>
                <div className="stat-value">${company.financials.market_cap_b.toFixed(0)}B</div>
              </div>
              <div className="stat">
                <div className="stat-label">3Y annualized return</div>
                <div className="stat-value"><ReturnValue pct={company.financials.three_year_annualized_return_pct} /></div>
              </div>
              <div className="stat">
                <div className="stat-label">Volatility (annualized)</div>
                <div className="stat-value">{company.financials.volatility_pct.toFixed(1)}%</div>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}
