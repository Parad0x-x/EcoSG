import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
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
import { Explain, GradeBadge, PAGE_SIZE, ShowMore, SortHeader, Term } from "../components";
import { GLOSSARY, type TermId } from "../glossary";
import { AXIS, GRID } from "../sectors";

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

const FACTORS: TermId[] = ["value", "quality", "momentum", "growth", "lowVol"];
const ESG_LOW = 50;

export default function QuantFactors() {
  const [esg, setEsg] = useState<CompanySummary[]>([]);
  const [quant, setQuant] = useState<QuantFactorSummary[]>([]);
  const [picks, setPicks] = useState<QuantTopPick[]>([]);
  const [backtest, setBacktest] = useState<BacktestSummary | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("quant_rank");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [limit, setLimit] = useState(PAGE_SIZE);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([fetchCompanies(), fetchQuantFactors(), fetchQuantTopPicks(), fetchQuantBacktest()])
      .then(([esgData, quantData, picksData, backtestData]) => {
        setEsg(esgData);
        setQuant(quantData);
        setPicks(picksData);
        setBacktest(backtestData);
        setLoaded(true);
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

  const esgByTicker = useMemo(() => new Map(combined.map((r) => [r.ticker, r])), [combined]);

  const sorted = useMemo(() => {
    const copy = [...combined];
    copy.sort((a, b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      return (a[sortKey] - b[sortKey]) * dir;
    });
    return copy;
  }, [combined, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    setLimit(PAGE_SIZE);
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "quant_rank" ? "asc" : "desc");
    }
  }

  const equityData = useMemo(
    () =>
      // Thin to every 3rd day, but always keep the last day so the chart ends where the metrics do.
      (backtest?.equity_curve || []).filter((_, i, all) => i % 3 === 0 || i === all.length - 1).map((p) => ({
        date: p.date,
        Strategy: Number((p.portfolio * 100 - 100).toFixed(2)),
        Benchmark: Number((p.benchmark * 100 - 100).toFixed(2)),
        "Equal weight": Number((p.equal_weight * 100 - 100).toFixed(2)),
      })),
    [backtest]
  );

  const pickTickers = new Set(picks.map((p) => p.ticker));

  function openCompany(d: unknown) {
    const ticker = (d as { payload?: CombinedRow }).payload?.ticker;
    if (ticker) navigate(`/lookup/${ticker}`);
  }

  const lowEsgPicks = picks.filter((p) => (esgByTicker.get(p.ticker)?.esg_score ?? 100) < ESG_LOW).length;
  const m = backtest?.metrics;

  return (
    <>
      <div className="page-head">
        <h1>How a quant fund would pick from the same companies</h1>
        <p className="takeaway">
          {loaded
            ? `The model's ${picks.length} top picks include ${lowEsgPicks} with an ESG score below ${ESG_LOW}. It chases returns and never looks at accountability.`
            : error
              ? ""
              : "Loading the model…"}
        </p>
      </div>

      {error && <div className="callout error">{error}. Is the backend running on port 8000?</div>}

      <section className="card">
        <h2>The five things the model looks at</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Each is a <Term id="factor">factor</Term>: a trait that has historically gone with higher returns.
        </p>
        <div className="stat-grid">
          {FACTORS.map((id) => (
            <div className="stat" key={id}>
              <div className="stat-title">{GLOSSARY[id].term}</div>
              <div className="stat-note">{GLOSSARY[id].short}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="card">
        <h2>Accountability vs. what the model wants</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Bottom right is the tension ecosg exists to show: companies the model likes that score poorly on ESG.
        </p>
        <ResponsiveContainer width="100%" height={380}>
          <ScatterChart margin={{ top: 10, right: 16, bottom: 24, left: 0 }}>
            <CartesianGrid stroke={GRID} />
            <XAxis
              type="number"
              dataKey="quant_percentile"
              name="Quant percentile"
              domain={[0, 100]}
              {...AXIS}
              label={{ value: "Quant percentile (model wants it more to the right)", position: "insideBottom", offset: -14, fill: AXIS.stroke, fontSize: 12 }}
            />
            <YAxis
              type="number"
              dataKey="esg_score"
              name="ESG score"
              domain={[0, 100]}
              {...AXIS}
              label={{ value: "ESG score", angle: -90, position: "insideLeft", fill: AXIS.stroke, fontSize: 12 }}
            />
            <ZAxis range={[38, 38]} />
            <ZAxis zAxisId="pick" range={[130, 130]} />
            {/* The corner the page is about: wanted by the model, weak on accountability. */}
            <ReferenceArea
              x1={50}
              x2={100}
              y1={0}
              y2={ESG_LOW}
              fill="var(--warning)"
              fillOpacity={0.09}
              stroke="none"
              label={{ value: "Model wants it, weak on ESG", position: "insideBottomRight", fill: "var(--warning)", fontSize: 12, fontWeight: 600 }}
            />
            <ReferenceLine x={50} stroke={AXIS.stroke} strokeDasharray="4 4" />
            <ReferenceLine y={ESG_LOW} stroke={AXIS.stroke} strokeDasharray="4 4" />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} content={<RowTip />} />
            <Scatter
              name="Companies"
              data={combined.filter((c) => !pickTickers.has(c.ticker))}
              fill="var(--text-secondary)"
              fillOpacity={0.4}
              isAnimationActive={false}
              cursor="pointer"
              onClick={openCompany}
            />
            <Scatter
              name="The model's picks"
              zAxisId="pick"
              data={combined.filter((c) => pickTickers.has(c.ticker))}
              fill="var(--quant)"
              stroke="var(--container)"
              shape="diamond"
              isAnimationActive={false}
              cursor="pointer"
              onClick={openCompany}
            />
          </ScatterChart>
        </ResponsiveContainer>
        <div className="legend">
          <span><i className="dot" style={{ ["--c" as string]: "var(--text-secondary)" }} />One company</span>
          <span><i className="diamond" style={{ ["--c" as string]: "var(--quant)" }} />One of the model's {picks.length} picks</span>
        </div>
        <Explain title="How to read the four corners">
          <p><strong>Top right:</strong> strong on both. The model wants it and it is run responsibly.</p>
          <p><strong>Bottom right:</strong> the model wants it, but it scores poorly on ESG. This is where returns and accountability pull apart.</p>
          <p><strong>Top left:</strong> responsible, but the model is not interested right now.</p>
          <p><strong>Bottom left:</strong> weak on both.</p>
        </Explain>
      </section>

      <section className="card">
        <h2>The model's picks</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          The top-ranked names, sized with <Term id="invVol">inverse-volatility sizing</Term> and capped so no
          single stock dominates. This is what the model would buy today.
        </p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Company</th>
                <th className="num"><Term id="weight">Weight</Term></th>
                <th>ESG</th>
              </tr>
            </thead>
            <tbody>
              {picks.map((p) => {
                const e = esgByTicker.get(p.ticker);
                return (
                  <tr key={p.ticker} className="clickable" onClick={() => navigate(`/lookup/${p.ticker}`)}>
                    <td className="muted">#{p.rank}</td>
                    <td>
                      <Link className="row-link" to={`/lookup/${p.ticker}`} onClick={(ev) => ev.stopPropagation()}>{p.ticker}</Link>
                      <span className="cell-sub">{p.name}, {p.sector}</span>
                    </td>
                    <td className="num lens-quant" style={{ whiteSpace: "nowrap" }}>
                      {p.target_weight_pct.toFixed(1)}%
                      <span className="mini-bar" aria-hidden="true"><span style={{ width: `${Math.min(100, p.target_weight_pct * 4)}%` }} /></span>
                    </td>
                    <td>{e ? <><GradeBadge grade={e.esg_grade} /> <span className="muted small">{e.esg_score.toFixed(0)}</span></> : "n/a"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {backtest && m && (
        <section className="card">
          <h2>Would it have worked? A <Term id="backtest">backtest</Term></h2>
          <p className="takeaway" style={{ fontSize: "1.05rem", marginTop: "0.5rem" }}>
            {m.excess_cagr_vs_benchmark === null
              ? "Not enough history to compare with the market."
              : m.excess_cagr_vs_benchmark >= 0
                ? `On past prices, the strategy beat the market by ${fmtPct(m.excess_cagr_vs_benchmark)} a year.`
                : `On past prices, the strategy trailed the market by ${fmtPct(-m.excess_cagr_vs_benchmark).replace("+", "")} a year.`}
          </p>
          <div className="stat-grid" style={{ margin: "0.75rem 0 1rem" }}>
            <div className="stat">
              <div className="stat-label"><Term id="cagr">Yearly return (CAGR)</Term></div>
              <div className="stat-value">{fmtPct(m.cagr)}</div>
              <div className="stat-note">Market: {fmtPct(m.benchmark_cagr)}. <Term id="equalWeight">Equal weight</Term>: {fmtPct(m.equal_weight_cagr)}</div>
            </div>
            <div className="stat">
              <div className="stat-label"><Term id="sharpe">Sharpe ratio</Term></div>
              <div className="stat-value">{fmtNum(m.sharpe_ratio)}</div>
              <div className="stat-note">return per unit of risk</div>
            </div>
            <div className="stat">
              <div className="stat-label"><Term id="drawdown">Max drawdown</Term></div>
              <div className="stat-value">{fmtPct(m.max_drawdown)}</div>
              <div className="stat-note">worst drop from a peak</div>
            </div>
            <div className="stat">
              <div className="stat-label">vs. <Term id="benchmark">benchmark</Term></div>
              <div className="stat-value">{fmtPct(m.excess_cagr_vs_benchmark)}</div>
              <div className="stat-note">per year</div>
            </div>
            <div className="stat">
              <div className="stat-label"><Term id="ic">Information coefficient (IC)</Term></div>
              <div className="stat-value">{fmtNum(m.mean_ic)}</div>
              <div className="stat-note">
                t-stat {fmtNum(m.ic_t_stat)} over {m.ic_periods} months. Unproven if t is below 3.
              </div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={equityData} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid stroke={GRID} />
              <XAxis dataKey="date" {...AXIS} tick={{ ...AXIS.tick, fontSize: 11 }} minTickGap={48} />
              <YAxis {...AXIS} tickFormatter={(v) => `${v}%`} />
              <Tooltip
                contentStyle={{ background: "var(--container)", border: "none", borderRadius: 8, boxShadow: "0 0 0 1px var(--border)" }}
                formatter={(value, name) => [`${value}%`, name]}
              />
              <Line type="monotone" dataKey="Strategy" stroke="var(--quant)" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="Benchmark" stroke={AXIS.stroke} dot={false} strokeWidth={2} strokeDasharray="4 3" />
              <Line type="monotone" dataKey="Equal weight" stroke="var(--text-secondary)" dot={false} strokeWidth={1.5} strokeDasharray="1 3" />
            </LineChart>
          </ResponsiveContainer>
          <div className="legend">
            <span><i style={{ ["--c" as string]: "var(--quant)" }} />Strategy, cumulative return</span>
            <span><i style={{ ["--c" as string]: AXIS.stroke }} />Market benchmark</span>
            <span><i style={{ ["--c" as string]: "var(--text-secondary)" }} />Every company, equal weight</span>
          </div>
          <Explain title="Why you should be skeptical of any backtest">
            <p>
              A backtest replays a strategy on old prices. It cannot account for everything that
              changes in real markets, and it is easy to tune a strategy until the past looks great.
              Past results never promise future ones.
            </p>
            <p>
              The information coefficient (IC) checks the ranking itself: each month, does a higher score
              go with a higher return the next month? 1 is a perfect ranking, 0 is no link. A t-stat
              below 3 means the result could easily be luck, so treat the signal as unproven.
              Beating the equal-weight line matters more than beating the market: it shows the model
              did better than simply owning every company in equal amounts.
            </p>
            <p>{backtest.methodology_note}</p>
          </Explain>
        </section>
      )}

      <section className="card">
        <div className="card-head">
          <h2>Every company, ranked by the model</h2>
          <span className="muted small">Click a column to sort</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <SortHeader label="Rank" k="quant_rank" sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} />
                <th>Company</th>
                <SortHeader label="Quant z-score" k="quant_score" sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} className="num" />
                <th className="num"><Term id="percentile">Percentile</Term></th>
                <SortHeader label="ESG score" k="esg_score" sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} className="num" />
                <th>Grade</th>
              </tr>
            </thead>
            <tbody>
              {sorted.slice(0, limit).map((r) => (
                <tr key={r.ticker} className="clickable" onClick={() => navigate(`/lookup/${r.ticker}`)}>
                  <td className="muted">#{r.quant_rank}</td>
                  <td>
                    <Link className="row-link" to={`/lookup/${r.ticker}`} onClick={(ev) => ev.stopPropagation()}>{r.ticker}</Link>
                    <span className="cell-sub">{r.name}</span>
                  </td>
                  <td className="num">{r.quant_score >= 0 ? "+" : ""}{r.quant_score.toFixed(2)}</td>
                  <td className="num">{r.quant_percentile.toFixed(0)}</td>
                  <td className="num">{r.esg_score.toFixed(0)}</td>
                  <td><GradeBadge grade={r.esg_grade} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <ShowMore shown={limit} total={sorted.length} onMore={() => setLimit((n) => n + PAGE_SIZE)} />
      </section>
    </>
  );
}

function RowTip({ active, payload }: { active?: boolean; payload?: { payload: CombinedRow }[] }) {
  if (!active || !payload?.length) return null;
  const r = payload[0].payload;
  return (
    <div className="chart-tip">
      <strong>{r.ticker}, {r.name}</strong>
      Quant {r.quant_percentile.toFixed(0)}th percentile, ESG {r.esg_score.toFixed(0)} ({r.esg_grade})
    </div>
  );
}

function fmtPct(v: number | null): string {
  if (v === null || v === undefined) return "n/a";
  return `${v >= 0 ? "+" : ""}${(v * 100).toFixed(1)}%`;
}

function fmtNum(v: number | null): string {
  if (v === null || v === undefined) return "n/a";
  return v.toFixed(2);
}
