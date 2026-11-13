import { useState } from "react";
import { ApiError, screenPortfolio, type PortfolioResult } from "../api";
import { GradeBadge, ReturnValue } from "../components";

interface Row {
  ticker: string;
  weight: string;
}

const DEFAULT_ROWS: Row[] = [
  { ticker: "AAPL", weight: "40" },
  { ticker: "XOM", weight: "30" },
  { ticker: "NEE", weight: "30" },
];

export default function Portfolio() {
  const [rows, setRows] = useState<Row[]>(DEFAULT_ROWS);
  const [result, setResult] = useState<PortfolioResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function updateRow(i: number, field: keyof Row, value: string) {
    setRows((prev) => prev.map((r, idx) => (idx === i ? { ...r, [field]: value } : r)));
  }

  function addRow() {
    setRows((prev) => [...prev, { ticker: "", weight: "" }]);
  }

  function removeRow(i: number) {
    setRows((prev) => prev.filter((_, idx) => idx !== i));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);

    const holdings = rows
      .filter((r) => r.ticker.trim() && r.weight.trim())
      .map((r) => ({ ticker: r.ticker.trim().toUpperCase(), weight_pct: Number(r.weight) }));

    if (holdings.length === 0) {
      setError("Add at least one holding with a ticker and weight.");
      return;
    }
    if (holdings.some((h) => !Number.isFinite(h.weight_pct) || h.weight_pct <= 0)) {
      setError("Weights must be positive numbers.");
      return;
    }
    if (new Set(holdings.map((h) => h.ticker)).size !== holdings.length) {
      setError("Each ticker can only appear once. Combine the weights into one row.");
      return;
    }

    setLoading(true);
    try {
      const r = await screenPortfolio(holdings);
      setResult(r);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to screen portfolio");
    } finally {
      setLoading(false);
    }
  }

  const totalWeight = rows.reduce((sum, r) => sum + (Number(r.weight) || 0), 0);

  return (
    <>
      <h1>Portfolio Screener</h1>
      <p className="subtitle">
        Enter holdings by ticker and weight (weights don't need to sum to 100 — they're
        normalized automatically) to see a weighted ESG score and return-vs-ESG gap for the
        portfolio as a whole.
      </p>

      <div className="panel">
        <form onSubmit={onSubmit}>
          {rows.map((row, i) => (
            <div className="holding-row" key={i}>
              <input
                type="text"
                placeholder="Ticker"
                value={row.ticker}
                onChange={(e) => updateRow(i, "ticker", e.target.value.toUpperCase())}
              />
              <input
                type="number"
                placeholder="Weight %"
                value={row.weight}
                onChange={(e) => updateRow(i, "weight", e.target.value)}
                min={0}
              />
              <span style={{ color: "var(--text-dim)", fontSize: "0.85rem" }}>%</span>
              <button type="button" className="remove-btn" onClick={() => removeRow(i)} aria-label="Remove holding">
                ✕
              </button>
            </div>
          ))}
          <div className="field-row">
            <button type="button" className="secondary" onClick={addRow}>
              + Add holding
            </button>
            <span style={{ color: "var(--text-dim)", fontSize: "0.85rem" }}>
              Total weight entered: {totalWeight.toFixed(0)}%
            </span>
          </div>
          <button type="submit" disabled={loading}>
            {loading ? "Screening…" : "Screen portfolio"}
          </button>
        </form>
        {error && <div className="error-box" style={{ marginTop: "1rem" }}>{error}</div>}
      </div>

      {result && (
        <>
          <div className="panel">
            <div className="stat-grid">
              <div className="stat">
                <div className="stat-label">Weighted ESG score</div>
                <div className="stat-value">{result.weighted_esg_score.toFixed(1)}</div>
              </div>
              <div className="stat">
                <div className="stat-label">Grade</div>
                <div className="stat-value"><GradeBadge grade={result.grade} /></div>
              </div>
              <div className="stat">
                <div className="stat-label">Weighted 1Y return</div>
                <div className="stat-value"><ReturnValue pct={result.weighted_one_year_return_pct} /></div>
              </div>
              <div className="stat">
                <div className="stat-label">Return–ESG gap</div>
                <div className="stat-value">{result.return_esg_gap > 0 ? "+" : ""}{result.return_esg_gap.toFixed(1)}</div>
              </div>
              {result.weighted_quant_score !== null && (
                <div className="stat">
                  <div className="stat-label">Weighted quant factor score</div>
                  <div className="stat-value">
                    {result.weighted_quant_score >= 0 ? "+" : ""}
                    {result.weighted_quant_score.toFixed(2)}
                  </div>
                </div>
              )}
            </div>
            <p style={{ color: "var(--text-dim)", fontSize: "0.82rem" }}>
              Return–ESG gap is an illustrative placeholder metric (weighted return minus
              weighted ESG score) meant to visualize the "returns vs. accountability" tradeoff —
              not a risk-adjusted alpha model. Weighted quant factor score is the same portfolio's
              weighted hedge-fund-style Value/Quality/Momentum/Growth/Low-Vol composite (z-score),
              shown alongside rather than blended in, so the two lenses stay distinguishable.
            </p>
          </div>

          <div className="panel">
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Company</th>
                  <th>Weight</th>
                  <th>ESG Score</th>
                  <th>Grade</th>
                  <th>1Y Return</th>
                  <th>Quant Score</th>
                </tr>
              </thead>
              <tbody>
                {result.holdings.map((h) => (
                  <tr key={h.ticker}>
                    <td><strong>{h.ticker}</strong></td>
                    <td>{h.name}</td>
                    <td>{h.weight_pct.toFixed(1)}%</td>
                    <td>{h.composite_score.toFixed(1)}</td>
                    <td><GradeBadge grade={h.grade} /></td>
                    <td><ReturnValue pct={h.one_year_return_pct} /></td>
                    <td>
                      {h.quant_composite_score !== null
                        ? `${h.quant_composite_score >= 0 ? "+" : ""}${h.quant_composite_score.toFixed(2)}`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
