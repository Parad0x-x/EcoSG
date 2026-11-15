// Company search ranking. Only type imports, so `node --test` can run it without a bundler.
import type { CompanySummary } from "./api";

/** Ticker prefix matches first, then company-name matches, each in ticker order. */
export function searchCompanies(companies: CompanySummary[], query: string, limit = 8): CompanySummary[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  const byTicker: CompanySummary[] = [];
  const byName: CompanySummary[] = [];
  for (const c of companies) {
    if (c.ticker.toLowerCase().startsWith(q)) byTicker.push(c);
    else if (c.name.toLowerCase().includes(q)) byName.push(c);
  }
  return [...byTicker, ...byName].slice(0, limit);
}
