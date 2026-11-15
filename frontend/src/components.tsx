import { useId, type ReactNode } from "react";
import { GLOSSARY, type TermId } from "./glossary";

export function GradeBadge({ grade }: { grade: string }) {
  return <span className={`badge badge-${grade}`}>{grade}</span>;
}

export function ReturnValue({ pct }: { pct: number }) {
  const cls = pct >= 0 ? "positive" : "negative";
  const sign = pct >= 0 ? "+" : "";
  return <span className={cls}>{sign}{pct.toFixed(1)}%</span>;
}

/** A word with a dotted underline; hover, focus or tap shows its plain-English definition. */
export function Term({ id, children }: { id: TermId; children?: ReactNode }) {
  const tipId = useId();
  const entry = GLOSSARY[id];
  return (
    <button type="button" className="term" aria-describedby={tipId} onClick={(e) => e.currentTarget.focus()}>
      {children ?? entry.term}
      <span role="tooltip" id={tipId} className="term-tip">
        {entry.short}
      </span>
    </button>
  );
}

/** Collapsed "What does this mean?" layer under a number. */
export function Explain({ title = "What does this mean?", children }: { title?: string; children: ReactNode }) {
  return (
    <details className="explain">
      <summary>{title}</summary>
      <div className="explain-body">{children}</div>
    </details>
  );
}

export function PillarBar({ label, value }: { label: ReactNode; value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="bar-row">
      <span>{label}</span>
      <div className="meter" role="img" aria-label={`${value.toFixed(0)} out of 100`}>
        <span style={{ width: `${pct}%` }} />
      </div>
      <span className="num">{value.toFixed(0)}</span>
    </div>
  );
}

const Z_RANGE = 2.5;

/** Bar for a cross-sectional z-score, centered on the average (0). */
export function FactorBar({ label, value }: { label: ReactNode; value: number | null }) {
  if (value === null || value === undefined) {
    return (
      <div className="bar-row">
        <span>{label}</span>
        <div className="diverge" />
        <span className="num">n/a</span>
      </div>
    );
  }
  const clamped = Math.max(-Z_RANGE, Math.min(Z_RANGE, value));
  const half = (Math.abs(clamped) / Z_RANGE) * 50;
  const positive = value >= 0;
  return (
    <div className="bar-row">
      <span>{label}</span>
      <div className="diverge" role="img" aria-label={`${positive ? "above" : "below"} average by ${Math.abs(value).toFixed(2)}`}>
        <span className={positive ? "" : "neg"} style={{ left: positive ? "50%" : `${50 - half}%`, width: `${half}%` }} />
      </div>
      <span className="num">{positive ? "+" : ""}{value.toFixed(2)}</span>
    </div>
  );
}

export function SortHeader<K extends string>({
  label,
  k,
  sortKey,
  sortDir,
  onSort,
  className,
}: {
  label: ReactNode;
  k: K;
  sortKey: K;
  sortDir: "asc" | "desc";
  onSort: (k: K) => void;
  className?: string;
}) {
  const active = sortKey === k;
  return (
    <th className={className} aria-sort={active ? (sortDir === "asc" ? "ascending" : "descending") : "none"}>
      <button type="button" className="sort" onClick={() => onSort(k)}>
        {label} {active ? (sortDir === "asc" ? "↑" : "↓") : ""}
      </button>
    </th>
  );
}

/**
 * Both lenses on one 0 to 100 line: a green circle for ESG, a blue diamond for the
 * quant percentile, and a neutral hatch for the gap. The scores share a scale but are never combined.
 */
export function GapTrack({ esg, quant, large = false }: { esg: number; quant: number | null; large?: boolean }) {
  const label =
    quant === null
      ? `ESG score ${esg.toFixed(0)}, no quant coverage`
      : `ESG score ${esg.toFixed(0)}, quant percentile ${quant.toFixed(0)}`;
  // Keep the big labels inside the card when a score sits at either end.
  const labelAt = (v: number) => `${Math.max(5, Math.min(95, v))}%`;
  return (
    <div className={`gap-track${large ? " gap-lg" : ""}`} role="img" aria-label={label}>
      {quant !== null && (
        <span className="gap-span" style={{ left: `${Math.min(esg, quant)}%`, width: `${Math.abs(esg - quant)}%` }} />
      )}
      <span className="gap-esg" style={{ left: `${esg}%` }} />
      {quant !== null && <span className="gap-quant" style={{ left: `${quant}%` }} />}
      {large && <span className="gap-label esg" style={{ left: labelAt(esg) }}>ESG {esg.toFixed(0)}</span>}
      {large && quant !== null && (
        <span className="gap-label quant" style={{ left: labelAt(quant) }}>Quant {quant.toFixed(0)}</span>
      )}
    </div>
  );
}

/** What the two marker shapes mean, shown once above any table of gap tracks. */
export function GapLegend() {
  return (
    <p className="gap-legend">
      <span><i className="lens-dot" aria-hidden="true" />ESG score</span>
      <span><i className="lens-dot quant" aria-hidden="true" />Quant percentile</span>
      <span>Both run 0 to 100; the hatched stretch is the gap.</span>
    </p>
  );
}

export const PAGE_SIZE = 25;

/** Footer for long tables: how many rows are showing and a button for the next batch. */
export function ShowMore({ shown, total, onMore }: { shown: number; total: number; onMore: () => void }) {
  const left = total - shown;
  if (total === 0) return null; // still loading, or the page shows its own empty message
  return (
    <div className="table-foot">
      <p className="muted small">Showing {Math.min(shown, total)} of {total}</p>
      {left > 0 && (
        <button type="button" className="btn-ghost" onClick={onMore}>
          Show {Math.min(PAGE_SIZE, left)} more
        </button>
      )}
    </div>
  );
}
