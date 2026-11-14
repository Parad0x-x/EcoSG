import { useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, screenPortfolio, type PortfolioResult } from "../api";
import { Explain, FactorBar, GradeBadge, ReturnValue, Term } from "../components";
import { esgPhrase } from "../insights";

interface Row {
  ticker: string;
  weight: string;
}

const DEFAULT_ROWS: Row[] = [
  { ticker: "AAPL", weight: "40" },
  { ticker: "XOM", weight: "30" },
  { ticker: "NEE", weight: "30" },
];

// Weighted z-score past which we say the model has an opinion.
const NOTABLE_Z = 0.3;

function quantVerdict(z: number): string {
  if (z >= NOTABLE_Z) return "the quant model likes this mix";
  if (z <= -NOTABLE_Z) return "the quant model is not keen on this mix";
  return "the quant model sees it as about average";
}

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
      <div className="page-head">
        <p className="eyebrow">Portfolio</p>
        <h1>Check a portfolio</h1>
        <p className="subtitle">
          List what you own and roughly how much of each. We'll show how the whole mix scores on
          both lenses. <Term id="weight">Weights</Term> don't need to add up to 100; we scale them for you.
        </p>
      </div>

      <section className="card">
        <form onSubmit={onSubmit}>
          {rows.map((row, i) => (
            <div className="holding-row" key={i}>
              <input
                type="text"
                placeholder="Ticker"
                aria-label={`Holding ${i + 1} ticker`}
                value={row.ticker}
                onChange={(e) => updateRow(i, "ticker", e.target.value.toUpperCase())}
              />
              <input
                type="number"
                placeholder="Weight"
                aria-label={`Holding ${i + 1} weight percent`}
                value={row.weight}
                onChange={(e) => updateRow(i, "weight", e.target.value)}
                min={0}
              />
              <span className="muted">%</span>
              <button type="button" className="remove-btn" onClick={() => removeRow(i)} aria-label={`Remove holding ${i + 1}`}>
                ✕
              </button>
            </div>
          ))}
          <div className="field-row" style={{ marginTop: "0.75rem" }}>
            <button type="button" className="btn-ghost" onClick={addRow}>
              + Add holding
            </button>
            <button type="submit" className="btn" disabled={loading}>
              {loading ? "Checking…" : "Check portfolio"}
            </button>
            <span className="muted small">Total entered: {totalWeight.toFixed(0)}%</span>
          </div>
        </form>
        {error && <div className="callout error" style={{ margin: "1rem 0 0" }}>{error}</div>}
      </section>

      {result && (
        <>
          <p className="takeaway" style={{ margin: "1.5rem 0 1rem" }}>
            This portfolio is {esgPhrase(result.grade)} on accountability
            {result.weighted_quant_score !== null
              ? `, and ${quantVerdict(result.weighted_quant_score)}.`
              : ". Quant scores are unavailable right now, so only the ESG side is shown."}
          </p>

          <div className="grid-2">
            <section className="card lens lens-esg" aria-label="Portfolio ESG">
              <span className="lens-label"><span><Term id="esg">ESG accountability</Term>, weighted</span></span>
              <div className="lens-value">
                <span className="lens-number">{result.weighted_esg_score.toFixed(0)}</span>
                <span className="lens-of">out of 100</span>
                <GradeBadge grade={result.grade} />
              </div>
              <div className="meter"><span style={{ width: `${result.weighted_esg_score}%` }} /></div>
              <div className="meter-scale"><span>0 weak</span><span>100 strong</span></div>
            </section>
            <section className="card lens lens-quant" aria-label="Portfolio quant signal">
              <span className="lens-label"><span><Term id="quant">Quant return signal</Term>, weighted</span></span>
              {result.weighted_quant_score !== null ? (
                <>
                  <div className="lens-value">
                    <span className="lens-number">
                      {result.weighted_quant_score >= 0 ? "+" : ""}
                      {result.weighted_quant_score.toFixed(2)}
                    </span>
                    <span className="lens-of"><Term id="zscore">z-score</Term>, 0 is average</span>
                  </div>
                  <FactorBar label="vs. average" value={result.weighted_quant_score} />
                </>
              ) : (
                <p className="muted">Unavailable right now.</p>
              )}
            </section>
          </div>

          <section className="card">
            <div className="stat-grid">
              <div className="stat">
                <div className="stat-label">Weighted <Term id="return1y">1-year return</Term></div>
                <div className="stat-value"><ReturnValue pct={result.weighted_one_year_return_pct} /></div>
              </div>
              <div className="stat">
                <div className="stat-label"><Term id="gap">Return-ESG gap</Term></div>
                <div className="stat-value">{result.return_esg_gap > 0 ? "+" : ""}{result.return_esg_gap.toFixed(1)}</div>
                <div className="stat-note">illustrative only</div>
              </div>
            </div>

            <div className="table-wrap" style={{ marginTop: "1rem" }}>
              <table>
                <thead>
                  <tr>
                    <th>Holding</th>
                    <th className="num">Weight</th>
                    <th className="num">ESG</th>
                    <th>Grade</th>
                    <th className="num">1Y return</th>
                    <th className="num">Quant</th>
                  </tr>
                </thead>
                <tbody>
                  {result.holdings.map((h) => (
                    <tr key={h.ticker}>
                      <td>
                        <Link className="row-link" to={`/lookup/${h.ticker}`}>{h.ticker}</Link>
                        <span className="cell-sub">{h.name}</span>
                      </td>
                      <td className="num">{h.weight_pct.toFixed(1)}%</td>
                      <td className="num">{h.composite_score.toFixed(0)}</td>
                      <td><GradeBadge grade={h.grade} /></td>
                      <td className="num"><ReturnValue pct={h.one_year_return_pct} /></td>
                      <td className="num">
                        {h.quant_composite_score !== null
                          ? `${h.quant_composite_score >= 0 ? "+" : ""}${h.quant_composite_score.toFixed(2)}`
                          : "n/a"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <Explain title="How is this calculated?">
              <p>
                Each score is a weighted average: a holding that is 40% of the portfolio counts for 40%
                of the result. The ESG and quant results are kept separate on purpose.
              </p>
              <p>
                The return-ESG gap is a rough placeholder (weighted return minus weighted ESG score),
                not a risk-adjusted measure. Use it as a conversation starter, not a verdict.
              </p>
            </Explain>
          </section>
        </>
      )}
    </>
  );
}
