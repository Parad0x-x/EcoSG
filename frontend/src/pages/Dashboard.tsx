import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { ApiError, fetchCompanies, fetchSectors, type CompanySummary } from "../api";
import { Explain, GradeBadge, ReturnValue, SortHeader, Term } from "../components";
import { correlationTakeaway, pearson } from "../insights";
import { AXIS, GRID, SECTOR_COLORS } from "../sectors";

type SortKey = "ticker" | "composite_score" | "one_year_return_pct";

export default function Dashboard() {
  const [companies, setCompanies] = useState<CompanySummary[] | null>(null);
  const [sectors, setSectors] = useState<string[]>([]);
  const [sector, setSector] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("composite_score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchSectors().then(setSectors).catch(() => {});
  }, []);

  useEffect(() => {
    let stale = false;
    fetchCompanies(sector || undefined)
      .then((data) => {
        if (stale) return;
        setCompanies(data);
        setError(null);
      })
      .catch((e) => {
        if (!stale) setError(e instanceof ApiError ? e.message : "Failed to load companies");
      });
    return () => {
      stale = true;
    };
  }, [sector]);

  const sorted = useMemo(() => {
    const copy = [...(companies ?? [])];
    copy.sort((a, b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      if (sortKey === "ticker") return a.ticker.localeCompare(b.ticker) * dir;
      return (a[sortKey] - b[sortKey]) * dir;
    });
    return copy;
  }, [companies, sortKey, sortDir]);

  const takeaway = useMemo(() => {
    if (!companies) return null;
    const r = pearson(
      companies.map((c) => c.composite_score),
      companies.map((c) => c.one_year_return_pct),
    );
    return correlationTakeaway(r, companies.length);
  }, [companies]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "ticker" ? "asc" : "desc");
    }
  }

  return (
    <>
      <div className="page-head">
        <p className="eyebrow">Explore</p>
        <h1>Does doing good cost you returns?</h1>
        <p className="takeaway">{takeaway ?? (error ? "" : "Loading companies…")}</p>
        <p className="subtitle" style={{ marginBottom: 0 }}>
          Every dot is a company. Compare its <Term id="esg">ESG score</Term> with its{" "}
          <Term id="return1y">1-year return</Term>, then open any company to see why.
        </p>
      </div>

      {error && <div className="callout error">{error}. Is the backend running on port 8000?</div>}

      <section className="card">
        <div className="chips" role="group" aria-label="Filter by sector">
          <button type="button" className="chip" aria-pressed={sector === ""} onClick={() => setSector("")}>
            All sectors
          </button>
          {sectors.map((s) => (
            <button key={s} type="button" className="chip" aria-pressed={sector === s} onClick={() => setSector(s)}>
              <span className="swatch" style={{ background: SECTOR_COLORS[s] }} aria-hidden="true" />
              {s}
            </button>
          ))}
        </div>

        <ResponsiveContainer width="100%" height={340}>
          <ScatterChart margin={{ top: 10, right: 16, bottom: 24, left: 0 }}>
            <CartesianGrid stroke={GRID} />
            <XAxis
              type="number"
              dataKey="composite_score"
              name="ESG score"
              domain={[0, 100]}
              {...AXIS}
              label={{ value: "ESG score (more accountable →)", position: "insideBottom", offset: -14, fill: AXIS.stroke, fontSize: 12 }}
            />
            <YAxis
              type="number"
              dataKey="one_year_return_pct"
              name="1Y return"
              unit="%"
              {...AXIS}
              label={{ value: "1-year return", angle: -90, position: "insideLeft", fill: AXIS.stroke, fontSize: 12 }}
            />
            <ZAxis range={[90, 90]} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} content={<CompanyTip />} />
            {Object.entries(SECTOR_COLORS).map(([sec, color]) => (
              <Scatter
                key={sec}
                name={sec}
                data={sorted.filter((c) => c.sector === sec)}
                fill={color}
                cursor="pointer"
                onClick={(d) => {
                  const ticker = (d as { payload?: CompanySummary }).payload?.ticker;
                  if (ticker) navigate(`/lookup/${ticker}`);
                }}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>

        <Explain title="How to read this chart">
          <p>
            Further right means a higher ESG score. Higher up means the stock did better over the
            last year. If doing good always cost returns, the dots would slope down to the right; if
            it always paid, they would slope up.
          </p>
          <p>
            One year is a short window and these are only 30 companies, so treat any pattern as a
            question to dig into, not a rule. Click a dot to see the company.
          </p>
        </Explain>
      </section>

      <section className="card">
        <div className="card-head">
          <h2>All companies</h2>
          <span className="muted small">Click a column to sort</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <SortHeader label="Company" k="ticker" sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} />
                <th>Sector</th>
                <SortHeader label="ESG score" k="composite_score" sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} />
                <th>Grade</th>
                <SortHeader label="1Y return" k="one_year_return_pct" sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} className="num" />
              </tr>
            </thead>
            <tbody>
              {sorted.map((c) => (
                <tr key={c.ticker} className="clickable" onClick={() => navigate(`/lookup/${c.ticker}`)}>
                  <td>
                    <Link className="row-link" to={`/lookup/${c.ticker}`} onClick={(e) => e.stopPropagation()}>
                      {c.ticker}
                    </Link>
                    <span className="cell-sub">{c.name}</span>
                  </td>
                  <td className="muted">{c.sector}</td>
                  <td className="lens-esg" style={{ whiteSpace: "nowrap" }}>
                    {c.composite_score.toFixed(0)}
                    <span className="mini-bar" aria-hidden="true"><span style={{ width: `${c.composite_score}%` }} /></span>
                  </td>
                  <td><GradeBadge grade={c.grade} /></td>
                  <td className="num"><ReturnValue pct={c.one_year_return_pct} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function CompanyTip({ active, payload }: { active?: boolean; payload?: { payload: CompanySummary }[] }) {
  if (!active || !payload?.length) return null;
  const c = payload[0].payload;
  return (
    <div className="chart-tip">
      <strong>{c.ticker} · {c.name}</strong>
      ESG {c.composite_score.toFixed(0)} ({c.grade}) · 1Y <ReturnValue pct={c.one_year_return_pct} />
    </div>
  );
}
