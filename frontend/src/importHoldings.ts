// Parses a broker holdings export (CSV) or text pasted from a positions page into
// ticker + amount rows. Runs entirely in the browser; nothing here touches the network.

export type WeightBasis = "value" | "shares" | "number";

export interface ImportedHolding {
  ticker: string;
  amount: number;
}

export interface ImportResult {
  holdings: ImportedHolding[];
  basis: WeightBasis;
  skipped: string[];
}

const TICKER_HEADER = /^(symbol|ticker|security symbol|instrument|stock symbol)$/;
const VALUE_HEADER = /(market value|current value|total value|^value|value \$|^mkt val|market val)/;
const SHARES_HEADER = /(quantity|^qty|shares|units)/;
const PRICE_HEADER = /(last price|^price|current price|last)/;

// Plain tickers like AAPL, BRK.B, BF-B. Rejects words such as "Cash" via the length check below.
const TICKER = /^[A-Z][A-Z0-9]{0,4}([.-][A-Z])?$/;
const NOT_A_HOLDING = /^(cash|total|account|pending|subtotal|grand total|core|margin)/i;

export function parseNumber(raw: string | undefined): number | null {
  if (raw === undefined) return null;
  const s = raw.trim();
  if (!s || s === "--" || s.toLowerCase() === "n/a") return null;
  const negative = /^\(.*\)$/.test(s) || s.startsWith("-");
  const digits = s.replace(/[^0-9.]/g, "");
  if (!digits || digits === ".") return null;
  const n = Number(digits);
  if (!Number.isFinite(n)) return null;
  return negative ? -n : n;
}

/** Splits one line of CSV or tab-separated text, honoring double-quoted fields. */
export function splitRow(line: string, delimiter: string): string[] {
  const out: string[] = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (quoted) {
      if (ch === '"' && line[i + 1] === '"') {
        field += '"';
        i++;
      } else if (ch === '"') {
        quoted = false;
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === delimiter) {
      out.push(field.trim());
      field = "";
    } else {
      field += ch;
    }
  }
  out.push(field.trim());
  return out;
}

export function cleanTicker(raw: string): string | null {
  const t = raw.trim().toUpperCase().replace(/\*+$/, "").replace(/\s+/g, "");
  if (NOT_A_HOLDING.test(raw.trim())) return null;
  return TICKER.test(t) ? t : null;
}

function pickDelimiter(lines: string[]): string {
  const sample = lines.slice(0, 20).join("\n");
  if (sample.includes("\t")) return "\t";
  return sample.includes(",") ? "," : ";";
}

function findColumn(header: string[], pattern: RegExp): number {
  return header.findIndex((h) => pattern.test(h.toLowerCase().trim()));
}

export function parseHoldings(text: string): ImportResult {
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  const delimiter = pickDelimiter(lines);
  const rows = lines.map((l) => splitRow(l, delimiter));

  // Brokers often put account details above the real header row, so search for it.
  const headerIndex = rows.findIndex((r) => r.some((c) => TICKER_HEADER.test(c.toLowerCase().trim())));
  const amounts = new Map<string, number>();
  const skipped: string[] = [];
  let basis: WeightBasis = "number";

  const add = (rawTicker: string, amount: number | null) => {
    const ticker = cleanTicker(rawTicker);
    if (!ticker) {
      // Footnotes and disclaimers also land here; only report short, symbol-like leftovers.
      const leftover = rawTicker.trim();
      if (leftover && leftover.length <= 12 && !NOT_A_HOLDING.test(leftover)) skipped.push(leftover);
      return;
    }
    if (amount === null || amount <= 0) {
      skipped.push(ticker);
      return;
    }
    // The same ticker held in two accounts becomes one combined position.
    amounts.set(ticker, (amounts.get(ticker) ?? 0) + amount);
  };

  if (headerIndex >= 0) {
    const header = rows[headerIndex];
    const tickerCol = findColumn(header, TICKER_HEADER);
    const valueCol = findColumn(header, VALUE_HEADER);
    const sharesCol = findColumn(header, SHARES_HEADER);
    const priceCol = findColumn(header, PRICE_HEADER);
    basis = valueCol >= 0 || (sharesCol >= 0 && priceCol >= 0) ? "value" : sharesCol >= 0 ? "shares" : "number";

    for (const r of rows.slice(headerIndex + 1)) {
      const raw = r[tickerCol] ?? "";
      let amount: number | null = null;
      if (valueCol >= 0) amount = parseNumber(r[valueCol]);
      if (amount === null && sharesCol >= 0 && priceCol >= 0) {
        const shares = parseNumber(r[sharesCol]);
        const price = parseNumber(r[priceCol]);
        amount = shares !== null && price !== null ? shares * price : null;
      }
      if (amount === null && basis === "shares") amount = parseNumber(r[sharesCol]);
      add(raw, amount);
    }
  } else {
    // No header: treat each line as "TICKER amount", e.g. "AAPL 40" or "AAPL, 40%".
    for (const line of lines) {
      const parts = line.trim().split(/[\s,;\t]+/);
      if (parts.length < 2) continue;
      add(parts[0], parseNumber(parts[1]));
    }
  }

  return {
    holdings: [...amounts].map(([ticker, amount]) => ({ ticker, amount })),
    basis,
    skipped: [...new Set(skipped)],
  };
}

/** Turns amounts into percentages that sum to 100 (rounded to 0.1). */
export function toWeights(holdings: ImportedHolding[]): { ticker: string; weight: number }[] {
  const total = holdings.reduce((s, h) => s + h.amount, 0);
  if (total <= 0) return [];
  return holdings
    // Floor at 0.1% so a tiny position never rounds to 0, which the API rejects.
    .map((h) => ({ ticker: h.ticker, weight: Math.max(0.1, Math.round((h.amount / total) * 1000) / 10) }))
    .sort((a, b) => b.weight - a.weight);
}
