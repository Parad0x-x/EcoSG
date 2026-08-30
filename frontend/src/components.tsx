export function GradeBadge({ grade }: { grade: string }) {
  return <span className={`badge badge-${grade}`}>{grade}</span>;
}

export function ReturnValue({ pct }: { pct: number }) {
  const cls = pct >= 0 ? "positive" : "negative";
  const sign = pct >= 0 ? "+" : "";
  return <span className={cls}>{sign}{pct.toFixed(1)}%</span>;
}

export function PillarBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="pillar-bar-label">
        <span>{label}</span>
        <span>{value.toFixed(0)} / 100</span>
      </div>
      <div className="pillar-bar-track">
        <div className="pillar-bar-fill" style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </div>
    </div>
  );
}

/** Bar for a cross-sectional z-score (roughly -2.5..+2.5), centered at 0. */
export function FactorBar({ label, value }: { label: string; value: number | null }) {
  if (value === null || value === undefined) {
    return (
      <div>
        <div className="pillar-bar-label">
          <span>{label}</span>
          <span>n/a</span>
        </div>
        <div className="pillar-bar-track" />
      </div>
    );
  }
  const clamped = Math.max(-2.5, Math.min(2.5, value));
  const pct = ((clamped + 2.5) / 5) * 100;
  const positive = value >= 0;
  return (
    <div>
      <div className="pillar-bar-label">
        <span>{label}</span>
        <span>{value >= 0 ? "+" : ""}{value.toFixed(2)}</span>
      </div>
      <div className="pillar-bar-track" style={{ position: "relative" }}>
        <div
          className="pillar-bar-fill"
          style={{
            position: "absolute",
            background: positive ? "var(--accent)" : "var(--grade-ccc)",
            left: positive ? "50%" : `${pct}%`,
            width: `${Math.abs(pct - 50)}%`,
          }}
        />
        <div style={{ position: "absolute", left: "50%", top: 0, bottom: 0, width: 1, background: "var(--border)" }} />
      </div>
    </div>
  );
}
