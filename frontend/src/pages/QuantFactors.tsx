import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import {
  ApiError,
  fetchCompanies,
  fetchQuantBacktest,
  fetchQuantFactors,
  fetchQuantTopPicks,
  type BacktestSummary,
  type CompanySummary,
  type QuantFactorSummary,
  type QuantTopPick,
} from "../api";
import { GradeBadge } from "../components";
import { SECTOR_COLORS } from "../sectors";

interface CombinedRow {
  ticker: string;
  name: string;
  sector: string;
  esg_score: number;
  esg_grade: string;
  quant_score: number;
  quant_percentile: number;
  quant_rank: number;
}

type SortKey = "quant_rank" | "quant_score" | "esg_score";

export default function QuantFactors() {
  const [esg, setEsg] = useState<CompanySummary[]>([]);
  const [quant, setQuant] = useState<QuantFactorSummary[]>([]);
  const [picks, setPicks] = useState<QuantTopPick[]>([]);
  const [backtest, setBacktest] = useState<BacktestSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("quant_rank");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  useEffect(() => {
    Promise.all([fetchCompanies(), fetchQuantFactors(), fetchQuantTopPicks(), fetchQuantBacktest()])
      .then(([esgData, quantData, picksData, backtestData]) => {
        setEsg(esgData);
        setQuant(quantData);
        setPicks(picksData);
        setBacktest(backtestData);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load quant data"));
  }, []);

  const combined = useMemo<CombinedRow[]>(() => {
    const esgByTicker = new Map(esg.map((c) => [c.ticker, c]));
    return quant
      .map((q) => {
        const e = esgByTicker.get(q.ticker);
        if (!e) return null;
        return {
          ticker: q.ticker,
          name: q.name,
          sector: q.sector,
          esg_score: e.composite_score,
          esg_grade: e.grade,
          quant_score: q.composite_score,
          quant_percentile: q.percentile,
          quant_rank: q.rank,
        };
      })
      .filter((r): r is CombinedRow => r !== null);
  }, [esg, quant]);

  const sorted = useMemo(() => {
    const copy = [...combined];
    copy.sort((a, b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      return (a[sortKey] - b[sortKey]) * dir;
    });
    return copy;
  }, [combined, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "quant_rank" ? "asc" : "desc");
    }
  }

  const equityData = useMemo(
    () =>
      (backtest?.equity_curve || []).filter((_, i) => i % 3 === 0).map((p) => ({
        date: p.date,
        Portfolio: Number((p.portfolio * 100 - 100).toFixed(2)),
        Benchmark: Number((p.benchmark * 100 - 100).toFixed(2)),
      })),
    [backtest]
  );

  return (
    <>
      <h1>Quant Factors</h1>
      <p className="subtitle">
        A hedge-fund-style multi-factor model (Value, Quality, Momentum, Growth, Low-Volatility)
        scored alongside ESG accountability for the same companies — the gap this platform exists
        to make visible. Composite score is a cross-sectional z-score (sector-neutral), not a
        0–100 scale.
      </p>

      {error && <div className="error-box">{error}</div>}

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>ESG accountability vs. quant factor attractiveness</h3>
        <p style={{ color: "var(--text-dim)", fontSize: "0.85rem", marginTop: "-0.5rem" }}>
          Top-right: strong on both. Bottom-right: factor-favored but ESG-weak — the crux of the
          "returns vs. accountability" gap.
        </p>
        <ResponsiveContainer width="100%" height={340}>
          <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
            <CartesianGrid stroke="#2a3a30" />
            <XAxis
              type="number"
              dataKey="esg_score"
              name="ESG score"
              domain={[0, 100]}
              stroke="#9db2a5"
              tick={{ fill: "#9db2a5", fontSize: 12 }}
              label={{ value: "ESG composite score", position: "insideBottom", offset: -5, fill: "#9db2a5" }}
            />
            <YAxis
              type="number"
              dataKey="quant_score"
              name="Quant score"
              stroke="#9db2a5"
              tick={{ fill: "#9db2a5", fontSize: 12 }}
              label={{ value: "Quant factor composite (z-score)", angle: -90, position: "insideLeft", fill: "#9db2a5" }}
            />
            <ZAxis range={[80, 80]} />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              contentStyle={{ background: "#1c2a21", border: "1px solid #2a3a30", borderRadius: 8 }}
              formatter={(value, name) => [Number(value).toFixed(2), name]}
              labelFormatter={() => ""}
            />
            {Object.entries(SECTOR_COLORS).map(([sec, color]) => (
              <Scatter key={sec} name={sec} data={combined.filter((c) => c.sector === sec)} fill={color} />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Auto-generated top picks</h3>
        <p style={{ color: "var(--text-dim)", fontSize: "0.85rem", marginTop: "-0.5rem" }}>
          The top-ranked names by composite factor score, inverse-volatility sized and capped —
          what a scheduled scan of this model would flag as BUY.
        </p>
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Ticker</th>
              <th>Company</th>
              <th>Sector</th>
              <th>Target Weight</th>
              <th>Composite Score</th>
            </tr>
          </thead>
          <tbody>
            {picks.map((p) => (
              <tr key={p.ticker}>
                <td>{p.rank}</td>
                <td><strong>{p.ticker}</strong></td>
                <td>{p.name}</td>
                <td>{p.sector}</td>
                <td>{p.target_weight_pct.toFixed(1)}%</td>
                <td>{p.composite_score.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {backtest && (
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>Backtest (synthetic price history)</h3>
          <p style={{ color: "var(--text-dim)", fontSize: "0.85rem" }}>{backtest.methodology_note}</p>
          <div className="stat-grid">
            <div className="stat">
              <div className="stat-label">CAGR</div>
              <div className="stat-value">{fmtPct(backtest.metrics.cagr)}</div>
            </div>
            <div className="stat">
              <div className="stat-label">Sharpe</div>
              <div className="stat-value">{fmtNum(backtest.metrics.sharpe_ratio)}</div>
            </div>
            <div className="stat">
              <div className="stat-label">Max Drawdown</div>
              <div className="stat-value">{fmtPct(backtest.metrics.max_drawdown)}</div>
            </div>
            <div className="stat">
              <div className="stat-label">vs. Benchmark CAGR</div>
              <div className="stat-value">{fmtPct(backtest.metrics.excess_cagr_vs_benchmark)}</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={equityData} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="#2a3a30" />
              <XAxis dataKey="date" stroke="#9db2a5" tick={{ fill: "#9db2a5", fontSize: 11 }} minTickGap={40} />
              <YAxis
                stroke="#9db2a5"
                tick={{ fill: "#9db2a5", fontSize: 12 }}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip
                contentStyle={{ background: "#1c2a21", border: "1px solid #2a3a30", borderRadius: 8 }}
                formatter={(value) => [`${value}%`, ""]}
              />
              <Line type="monotone" dataKey="Portfolio" stroke="#5fd28f" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="Benchmark" stroke="#9db2a5" dot={false} strokeWidth={2} strokeDasharray="4 3" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Full ranked list</h3>
        <table>
          <thead>
            <tr>
              <th onClick={() => toggleSort("quant_rank")} style={{ cursor: "pointer" }}>Rank</th>
              <th>Ticker</th>
              <th>Company</th>
              <th>Sector</th>
              <th onClick={() => toggleSort("quant_score")} style={{ cursor: "pointer" }}>Quant Score</th>
              <th>Percentile</th>
              <th onClick={() => toggleSort("esg_score")} style={{ cursor: "pointer" }}>ESG Score</th>
              <th>ESG Grade</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => (
              <tr key={r.ticker}>
                <td>{r.quant_rank}</td>
                <td><strong>{r.ticker}</strong></td>
                <td>{r.name}</td>
                <td>{r.sector}</td>
                <td>{r.quant_score.toFixed(2)}</td>
                <td>{r.quant_percentile.toFixed(0)}th</td>
                <td>{r.esg_score.toFixed(1)}</td>
                <td><GradeBadge grade={r.esg_grade} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function fmtPct(v: number | null): string {
  if (v === null || v === undefined) return "—";
  return `${v >= 0 ? "+" : ""}${(v * 100).toFixed(1)}%`;
}

function fmtNum(v: number | null): string {
  if (v === null || v === undefined) return "—";
  return v.toFixed(2);
}
