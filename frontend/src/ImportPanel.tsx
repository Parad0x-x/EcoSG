import { useEffect, useState } from "react";
import { fetchCompanies } from "./api";
import { Explain } from "./components";
import { parseHoldings, toWeights, type ImportResult } from "./importHoldings";

// A holdings export is a few KB; anything this big is the wrong file.
const MAX_FILE_BYTES = 2 * 1024 * 1024;

const BASIS_NOTE: Record<ImportResult["basis"], string> = {
  value: "Weighted by market value.",
  shares: "No value column found, so this is weighted by share count. Treat the weights as rough.",
  number: "Weighted by the numbers next to each ticker.",
};

export default function ImportPanel({ onImport }: { onImport: (rows: { ticker: string; weight: number }[]) => void }) {
  const [covered, setCovered] = useState<Set<string> | null>(null);
  const [parsed, setParsed] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pasting, setPasting] = useState(false);
  const [pasted, setPasted] = useState("");
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    fetchCompanies()
      .then((cs) => setCovered(new Set(cs.map((c) => c.ticker))))
      .catch(() => setError("Couldn't load the list of covered companies. Is the backend running?"));
  }, []);

  function read(text: string) {
    const result = parseHoldings(text);
    if (result.holdings.length === 0) {
      setParsed(null);
      setError("We couldn't find any holdings. Check that it has a Symbol or Ticker column, or use lines like \"AAPL 40\".");
      return;
    }
    setError(null);
    setParsed(result);
  }

  async function readFile(file: File | undefined) {
    if (!file) return;
    if (file.size > MAX_FILE_BYTES) {
      setError("That file is too large to be a holdings export. Try the positions or holdings CSV.");
      return;
    }
    read(await file.text());
  }

  const isCovered = (t: string) => covered?.has(t) ?? false;
  const scored = parsed ? toWeights(parsed.holdings.filter((h) => isCovered(h.ticker))) : [];
  const weightOf = new Map(scored.map((s) => [s.ticker, s.weight]));
  const uncovered = parsed ? parsed.holdings.filter((h) => !isCovered(h.ticker)) : [];
  const notCovered = uncovered.length;
  const totalAmount = parsed ? parsed.holdings.reduce((s, h) => s + h.amount, 0) : 0;
  const uncoveredShare = totalAmount > 0 ? (uncovered.reduce((s, h) => s + h.amount, 0) / totalAmount) * 100 : 0;
  const money = (n: number) =>
    parsed?.basis === "value" ? n.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 }) : n.toLocaleString();

  return (
    <section className="card">
      <div className="card-head">
        <h2>Import from your broker</h2>
        <span className="muted small">Your file is read in this browser and never uploaded.</span>
      </div>

      <label
        className={`dropzone${dragging ? " dragging" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          readFile(e.dataTransfer.files[0]);
        }}
      >
        <input
          type="file"
          accept=".csv,.tsv,.txt,text/csv,text/plain"
          className="sr-only"
          onChange={(e) => {
            readFile(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
        <strong>Drop your holdings CSV here</strong>
        <span className="muted">or <span className="link-like">choose a file</span></span>
      </label>

      <div className="field-row" style={{ marginTop: "0.75rem" }}>
        <button type="button" className="btn-ghost" onClick={() => setPasting((p) => !p)} aria-expanded={pasting}>
          {pasting ? "Hide paste box" : "Paste instead"}
        </button>
      </div>

      {pasting && (
        <div style={{ marginTop: "0.75rem" }}>
          <label htmlFor="paste-box" className="muted small">
            Paste your positions table from your broker's website, or type one holding per line like "AAPL 40".
          </label>
          <textarea
            id="paste-box"
            rows={6}
            value={pasted}
            onChange={(e) => setPasted(e.target.value)}
            placeholder={"AAPL 2450\nXOM 940\nNEE 1200"}
          />
          <button type="button" className="btn" onClick={() => read(pasted)} disabled={!pasted.trim()}>
            Read pasted holdings
          </button>
        </div>
      )}

      {error && <div className="callout error" style={{ margin: "1rem 0 0" }}>{error}</div>}

      {parsed && (
        <div style={{ marginTop: "1.25rem" }}>
          <h3>
            Found {parsed.holdings.length} holding{parsed.holdings.length === 1 ? "" : "s"}
            {notCovered > 0 && <span className="muted">, {notCovered} not covered by ecosg yet</span>}
          </h3>
          <p className="muted small" style={{ marginTop: 0 }}>
            {BASIS_NOTE[parsed.basis]} Only covered companies are scored, so their weights are rescaled to add up to 100%.
          </p>
          {uncoveredShare >= 1 && (
            <div className="callout warn" style={{ margin: "0 0 0.75rem" }}>
              {uncoveredShare.toFixed(0)}% of what you imported isn't covered by ecosg yet, so the results
              describe only the other {(100 - uncoveredShare).toFixed(0)}%.
            </div>
          )}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th className="num">{parsed.basis === "value" ? "Value" : parsed.basis === "shares" ? "Shares" : "Amount"}</th>
                  <th className="num">Weight</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {parsed.holdings.map((h) => (
                  <tr key={h.ticker}>
                    <td><strong>{h.ticker}</strong></td>
                    <td className="num">{money(h.amount)}</td>
                    <td className="num">{weightOf.has(h.ticker) ? `${weightOf.get(h.ticker)!.toFixed(1)}%` : ""}</td>
                    <td>
                      {isCovered(h.ticker) ? (
                        <span className="status ok">Will be scored</span>
                      ) : (
                        <span className="status no">Not covered</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {parsed.skipped.length > 0 && (
            <p className="muted small">Skipped rows we couldn't read: {parsed.skipped.join(", ")}.</p>
          )}
          <div className="field-row" style={{ marginTop: "0.75rem" }}>
            <button type="button" className="btn" disabled={scored.length === 0} onClick={() => onImport(scored)}>
              {scored.length === 0 ? "None of these are covered yet" : `Check these ${scored.length} holdings`}
            </button>
            <button type="button" className="btn-ghost" onClick={() => setParsed(null)}>
              Start over
            </button>
          </div>
        </div>
      )}

      <Explain title="How do I export my holdings?">
        <p>
          Most brokers have a Download or Export button (often a CSV icon) on their Positions or
          Holdings page. Save that file and drop it above.
        </p>
        <p>
          No export option? Open your positions on the broker's website, select the table, copy it,
          and use Paste instead. ecosg looks for a Symbol or Ticker column plus a market value,
          quantity or shares column.
        </p>
        <p>Only tickers and their weights are sent to ecosg's server for scoring. Account numbers and dollar amounts stay in your browser.</p>
      </Explain>
    </section>
  );
}
