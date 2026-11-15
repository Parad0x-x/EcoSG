import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { ApiError, fetchCompanies, fetchQuantFactors, type CompanySummary } from "../api";
import { Explain, GapLegend, GapTrack, GradeBadge, PAGE_SIZE, ReturnValue, ShowMore, SortHeader, Term } from "../components";
import { correlationTakeaway, pearson } from "../insights";
import { searchCompanies } from "../search";
import { AXIS, GRID, SECTOR_COLORS } from "../sectors";

type SortKey = "ticker" | "composite_score" | "quant" | "gap" | "one_year_return_pct";

interface Row extends CompanySummary {
  quant: number | null;
}

// Missing quant coverage sorts last in either direction's "best first" view.
const sortValue = (r: Row, key: Exclude<SortKey, "ticker">): number => {
  if (key === "quant") return r.quant ?? -1;
  if (key === "gap") return r.quant === null ? -1 : Math.abs(r.composite_score - r.quant);
  return r[key];
};

export default function Dashboard() {
  const [companies, setCompanies] = useState<CompanySummary[] | null>(null);
  const [quantByTicker, setQuantByTicker] = useState<Map<string, number>>(new Map());
  const [sector, setSector] = useState("");
  const [filter, setFilter] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("composite_score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchCompanies()
      .then(setCompanies)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load companies"));
    // Best-effort: without quant data the table still works, showing the ESG marker alone.
    fetchQuantFactors()
      .then((qs) => setQuantByTicker(new Map(qs.map((q) => [q.ticker, q.percentile]))))
      .catch(() => {});
  }, []);

  const sectors = useMemo(() => [...new Set((companies ?? []).map((c) => c.sector))].sort(), [companies]);

  const inSector = useMemo<Row[]>(
    () =>
      (companies ?? [])
        .filter((c) => !sector || c.sector === sector)
        .map((c) => ({ ...c, quant: quantByTicker.get(c.ticker) ?? null })),
    [companies, sector, quantByTicker],
  );

  const rows = useMemo(() => {
    // An empty filter keeps everything; otherwise reuse the header search's ranking with no cap.
    const copy = filter.trim() ? (searchCompanies(inSector, filter, inSector.length) as Row[]) : [...inSector];
    const dir = sortDir === "asc" ? 1 : -1;
    copy.sort((a, b) =>
      sortKey === "ticker" ? a.ticker.localeCompare(b.ticker) * dir : (sortValue(a, sortKey) - sortValue(b, sortKey)) * dir,
    );
    return copy;
  }, [inSector, filter, sortKey, sortDir]);

  const takeaway = useMemo(() => {
    if (!companies) return null;
    const r = pearson(
      inSector.map((c) => c.composite_score),
      inSector.map((c) => c.one_year_return_pct),
    );
    return correlationTakeaway(r, inSector.length);
  }, [companies, inSector]);

  function toggleSort(key: SortKey) {
    setLimit(PAGE_SIZE);
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "ticker" ? "asc" : "desc");
    }
  }

  function pickSector(s: string) {
    setSector(s);
    setLimit(PAGE_SIZE);
  }

  const sortProps = { sortKey, sortDir, onSort: toggleSort };

  return (
    <>
      <div className="page-head">
        <h1>Does doing good cost you returns?</h1>
        <p className="takeaway">{takeaway ?? (error ? "" : "Loading companies…")}</p>
        <p className="subtitle" style={{ marginBottom: 0 }}>
          Every dot is a company. Compare its <Term id="esg">ESG score</Term> with its{" "}
          <Term id="return1y">1-year return</Term>, then open any company to see why.
        </p>
      </div>

      {error && <div className="callout error">{error}. Is the backend running on port 8000?</div>}

      <div className="chips" role="group" aria-label="Filter by sector">
        <button type="button" className="chip" aria-pressed={sector === ""} onClick={() => pickSector("")}>
          All sectors
        </button>
        {sectors.map((s) => (
          <button key={s} type="button" className="chip" aria-pressed={sector === s} onClick={() => pickSector(s)}>
            <span className="swatch" style={{ background: SECTOR_COLORS[s] }} aria-hidden="true" />
            {s}
          </button>
        ))}
      </div>

      <section className="card">
        <ResponsiveContainer width="100%" height={380}>
          <ScatterChart margin={{ top: 10, right: 16, bottom: 24, left: 0 }}>
            <CartesianGrid stroke={GRID} />
            <XAxis
              type="number"
              dataKey="composite_score"
              name="ESG score"
              domain={[0, 100]}
              {...AXIS}
              label={{ value: "ESG score (more accountable to the right)", position: "insideBottom", offset: -14, fill: AXIS.stroke, fontSize: 12 }}
            />
            <YAxis
              type="number"
              dataKey="one_year_return_pct"
              name="1Y return"
              unit="%"
              {...AXIS}
              label={{ value: "1-year return", angle: -90, position: "insideLeft", fill: AXIS.stroke, fontSize: 12 }}
            />
            {/* Small, slightly see-through dots: 500 of them overlap. */}
            <ZAxis range={[38, 38]} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} content={<CompanyTip />} />
            {Object.entries(SECTOR_COLORS).map(([sec, color]) => (
              <Scatter
                key={sec}
                name={sec}
                data={inSector.filter((c) => c.sector === sec)}
                fill={color}
                fillOpacity={0.75}
                isAnimationActive={false}
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
            One year is a short window and every number here is mock data, so treat any pattern as a
            question to dig into, not a rule. Click a dot to see the company.
          </p>
        </Explain>
      </section>

      <section className="card">
        <div className="card-head">
          <div>
            <h2>{sector || "All companies"}, on both lenses</h2>
            <GapLegend />
          </div>
          <input
            type="search"
            aria-label="Filter this table by company name or ticker"
            placeholder="Filter by name or ticker"
            value={filter}
            onChange={(e) => {
              setFilter(e.target.value);
              setLimit(PAGE_SIZE);
            }}
          />
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <SortHeader label="Company" k="ticker" {...sortProps} />
                <th className="hide-sm">Sector</th>
                <SortHeader label="ESG" k="composite_score" {...sortProps} className="num" />
                <SortHeader label="Gap" k="gap" {...sortProps} />
                <SortHeader label="Quant" k="quant" {...sortProps} />
                <th className="hide-sm">Grade</th>
                <SortHeader label="1Y return" k="one_year_return_pct" {...sortProps} className="num" />
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, limit).map((c) => (
                <tr key={c.ticker} className="clickable" onClick={() => navigate(`/lookup/${c.ticker}`)}>
                  <td>
                    <Link className="row-link" to={`/lookup/${c.ticker}`} onClick={(e) => e.stopPropagation()}>
                      {c.ticker}
                    </Link>
                    <span className="cell-sub">{c.name}</span>
                  </td>
                  <td className="muted hide-sm">{c.sector}</td>
                  <td className="num esg-num">{c.composite_score.toFixed(0)}</td>
                  <td className="gap-cell"><GapTrack esg={c.composite_score} quant={c.quant} /></td>
                  <td className="quant-num">{c.quant === null ? "" : c.quant.toFixed(0)}</td>
                  <td className="hide-sm"><GradeBadge grade={c.grade} /></td>
                  <td className="num"><ReturnValue pct={c.one_year_return_pct} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {companies && rows.length === 0 ? (
          <p className="muted" style={{ margin: "1rem 0 0" }}>
            No company here matches "{filter.trim()}". Clear the filter or pick another sector.
          </p>
        ) : (
          <ShowMore shown={limit} total={rows.length} onMore={() => setLimit((n) => n + PAGE_SIZE)} />
        )}
      </section>
    </>
  );
}

function CompanyTip({ active, payload }: { active?: boolean; payload?: { payload: CompanySummary }[] }) {
  if (!active || !payload?.length) return null;
  const c = payload[0].payload;
  return (
    <div className="chart-tip">
      <strong>{c.ticker}, {c.name}</strong>
      ESG {c.composite_score.toFixed(0)} ({c.grade}), 1Y <ReturnValue pct={c.one_year_return_pct} />
    </div>
  );
}
