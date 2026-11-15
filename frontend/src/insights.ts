// Turns scores into the one-sentence, plain-English takeaways that open each page.
// Only type imports here, so `node --test` can run this file without a bundler.
import type { QuantFactorFamilyScores } from "./api";

// Follows the backend's letter-grade bands so the sentence never disagrees with the badge.
export function esgPhrase(grade: string): string {
  if (grade === "AAA" || grade === "AA") return "strong";
  if (grade === "A" || grade === "BBB") return "solid";
  if (grade === "BB" || grade === "B") return "middling";
  return "weak";
}

export function quantPhrase(percentile: number): string {
  if (percentile >= 67) return "near the top";
  if (percentile >= 34) return "in the middle of the pack";
  return "near the bottom";
}

export function companyTakeaway(name: string, esgGrade: string, quantPercentile: number | null): string {
  const esg = `${name} is ${esgPhrase(esgGrade)} on accountability`;
  if (quantPercentile === null) return `${esg}. We don't have quant coverage for it yet.`;
  return `${esg} and ${quantPhrase(quantPercentile)} on the traits quants use to pick returns.`;
}

// Both inputs run 0 to 100, so their difference is readable without blending them.
const AGREE_WITHIN = 15;

export function lensGap(esgScore: number, quantPercentile: number): { points: number; text: string } {
  const points = Math.round(esgScore - quantPercentile);
  if (Math.abs(points) < AGREE_WITHIN) return { points, text: "The two lenses roughly agree on this one." };
  if (points > 0) return { points, text: `Accountability is ahead of the return signal by ${points} points.` };
  return { points, text: `The return signal is ahead of accountability by ${-points} points.` };
}

// Matches the backend's trend label, which uses the same 3-point threshold.
export function trendText(change: number, prior: number): string {
  const from = `from ${prior.toFixed(0)} a year ago`;
  if (change >= 3) return `Improving: up ${change.toFixed(1)} ${from}.`;
  if (change <= -3) return `Worsening: down ${(-change).toFixed(1)} ${from}.`;
  return `Stable: ${change >= 0 ? "up" : "down"} ${Math.abs(change).toFixed(1)} ${from}.`;
}

export function ageText(months: number): string {
  if (months < 1) return "this month";
  if (months < 24) return `${Math.round(months)} month${Math.round(months) === 1 ? "" : "s"} ago`;
  return `${(months / 12).toFixed(1)} years ago`;
}

export function pillarSummary(pillars: Record<string, number>): string {
  const sorted = Object.entries(pillars).sort((a, b) => b[1] - a[1]);
  const [best, worst] = [sorted[0], sorted[sorted.length - 1]];
  return `Strongest pillar: ${best[0]} (${best[1].toFixed(0)}). Weakest: ${worst[0]} (${worst[1].toFixed(0)}).`;
}

// How each factor reads when it is a strength vs. a weakness.
const FAMILY_WORDS: Record<keyof QuantFactorFamilyScores, [good: string, bad: string]> = {
  value_score: ["cheap price", "expensive price"],
  quality_score: ["strong business", "weaker business"],
  momentum_score: ["rising price", "sliding price"],
  growth_score: ["fast growth", "slow growth"],
  low_vol_score: ["steady price", "bumpy price"],
};

// A family counts as liked or disliked once it is half a standard deviation from average.
const NOTABLE_Z = 0.5;

export function factorSummary(families: QuantFactorFamilyScores): string {
  const keys = Object.keys(FAMILY_WORDS) as (keyof QuantFactorFamilyScores)[];
  const liked = keys.filter((k) => (families[k] ?? 0) >= NOTABLE_Z).map((k) => FAMILY_WORDS[k][0]);
  const disliked = keys.filter((k) => (families[k] ?? 0) <= -NOTABLE_Z).map((k) => FAMILY_WORDS[k][1]);
  if (!liked.length && !disliked.length) return "No factor stands out much in either direction.";
  const parts = [];
  if (liked.length) parts.push(`the model likes its ${joinWords(liked)}`);
  if (disliked.length) parts.push(`it is put off by its ${joinWords(disliked)}`);
  const sentence = parts.join(", but ");
  return sentence[0].toUpperCase() + sentence.slice(1) + ".";
}

export function joinWords(words: string[]): string {
  if (words.length <= 1) return words.join("");
  return `${words.slice(0, -1).join(", ")} and ${words[words.length - 1]}`;
}

export function pearson(xs: number[], ys: number[]): number | null {
  const n = xs.length;
  if (n < 3 || n !== ys.length) return null;
  const mx = xs.reduce((a, b) => a + b, 0) / n;
  const my = ys.reduce((a, b) => a + b, 0) / n;
  let sxy = 0;
  let sxx = 0;
  let syy = 0;
  for (let i = 0; i < n; i++) {
    sxy += (xs[i] - mx) * (ys[i] - my);
    sxx += (xs[i] - mx) ** 2;
    syy += (ys[i] - my) ** 2;
  }
  if (sxx === 0 || syy === 0) return null;
  return sxy / Math.sqrt(sxx * syy);
}

export function correlationTakeaway(r: number | null, n: number): string {
  if (r === null) return "Not enough companies here to see a pattern yet.";
  const strength = Math.abs(r) < 0.15 ? null : Math.abs(r) < 0.4 ? "slightly" : "clearly";
  const body =
    strength === null
      ? "a higher ESG score has had almost nothing to do with last year's return"
      : `companies with higher ESG scores have earned ${strength} ${r > 0 ? "higher" : "lower"} returns over the last year`;
  return `Across these ${n} companies, ${body}.`;
}

/** Least-squares line through the points, for a chart's trend line. Null when there is nothing to fit. */
export function trendLine(xs: number[], ys: number[]): { slope: number; intercept: number } | null {
  const n = xs.length;
  if (n < 3 || n !== ys.length) return null;
  const mx = xs.reduce((a, b) => a + b, 0) / n;
  const my = ys.reduce((a, b) => a + b, 0) / n;
  let sxy = 0;
  let sxx = 0;
  for (let i = 0; i < n; i++) {
    sxy += (xs[i] - mx) * (ys[i] - my);
    sxx += (xs[i] - mx) ** 2;
  }
  if (sxx === 0) return null;
  const slope = sxy / sxx;
  return { slope, intercept: my - slope * mx };
}
