import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { ApiError, fetchCompanies, fetchSectors, type CompanySummary } from "../api";
import { GradeBadge, ReturnValue } from "../components";
import { SECTOR_COLORS } from "../sectors";

type SortKey = "ticker" | "composite_score" | "one_year_return_pct";

export default function Dashboard() {
  const [companies, setCompanies] = useState<CompanySummary[]>([]);
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
    const copy = [...companies];
    copy.sort((a, b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      if (sortKey === "ticker") return a.ticker.localeCompare(b.ticker) * dir;
      return (a[sortKey] - b[sortKey]) * dir;
    });
    return copy;
  }, [companies, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  return (
    <>
      <h1>Dashboard</h1>
      <p className="subtitle">
        ESG score vs. 1-year return across covered companies. Composite score is computed live
        from the ECOSG scoring framework (sector-weighted E/S/G + controversy penalty).
      </p>

      {error && <div className="error-box">{error}</div>}

      <div className="panel">
        <div className="field-row">
          <label htmlFor="sector-filter" style={{ color: "var(--text-dim)", fontSize: "0.85rem" }}>
            Sector
          </label>
          <select id="sector-filter" value={sector} onChange={(e) => setSector(e.target.value)}>
            <option value="">All sectors</option>
            {sectors.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <ResponsiveContainer width="100%" height={340}>
          <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
            <CartesianGrid stroke="#2a3a30" />
            <XAxis
              type="number"
              dataKey="composite_score"
              name="ESG score"
              domain={[0, 100]}
              stroke="#9db2a5"
              tick={{ fill: "#9db2a5", fontSize: 12 }}
              label={{ value: "ESG composite score", position: "insideBottom", offset: -5, fill: "#9db2a5" }}
            />
            <YAxis
              type="number"
              dataKey="one_year_return_pct"
              name="1Y return"
              stroke="#9db2a5"
              tick={{ fill: "#9db2a5", fontSize: 12 }}
              label={{ value: "1Y return (%)", angle: -90, position: "insideLeft", fill: "#9db2a5" }}
            />
            <ZAxis range={[80, 80]} />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              contentStyle={{ background: "#1c2a21", border: "1px solid #2a3a30", borderRadius: 8 }}
              formatter={(value, name) => [
                name === "1Y return" ? `${Number(value).toFixed(1)}%` : Number(value).toFixed(1),
                name,
              ]}
              labelFormatter={() => ""}
            />
            {Object.entries(SECTOR_COLORS).map(([sec, color]) => (
              <Scatter
                key={sec}
                name={sec}
                data={sorted.filter((c) => c.sector === sec)}
                fill={color}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      <div className="panel">
        <table>
          <thead>
            <tr>
              <th onClick={() => toggleSort("ticker")} style={{ cursor: "pointer" }}>
                Ticker
              </th>
              <th>Company</th>
              <th>Sector</th>
              <th onClick={() => toggleSort("composite_score")} style={{ cursor: "pointer" }}>
                ESG Score
              </th>
              <th>Grade</th>
              <th onClick={() => toggleSort("one_year_return_pct")} style={{ cursor: "pointer" }}>
                1Y Return
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((c) => (
              <tr key={c.ticker} className="clickable" onClick={() => navigate(`/lookup/${c.ticker}`)}>
                <td><strong>{c.ticker}</strong></td>
                <td>{c.name}</td>
                <td>{c.sector}</td>
                <td>{c.composite_score.toFixed(1)}</td>
                <td><GradeBadge grade={c.grade} /></td>
                <td><ReturnValue pct={c.one_year_return_pct} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
