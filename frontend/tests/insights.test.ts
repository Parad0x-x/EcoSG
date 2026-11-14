// Runs on Node's built-in test runner with native TypeScript stripping: `npm test`.
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  ageText,
  companyTakeaway,
  trendText,
  correlationTakeaway,
  factorSummary,
  joinWords,
  lensGap,
  pearson,
  pillarSummary,
} from "../src/insights.ts";

test("company takeaway names both lenses, or says quant coverage is missing", () => {
  assert.equal(
    companyTakeaway("Microsoft", "AA", 40),
    "Microsoft is strong on accountability and in the middle of the pack on the traits quants use to pick returns.",
  );
  assert.equal(companyTakeaway("Acme", "CCC", null), "Acme is weak on accountability. We don't have quant coverage for it yet.");
  assert.equal(companyTakeaway("Mid", "BB", 90), "Mid is middling on accountability and near the top on the traits quants use to pick returns.");
});

test("lens gap only calls a winner past 15 points", () => {
  assert.equal(lensGap(60, 50).text, "The two lenses roughly agree on this one.");
  assert.deepEqual(lensGap(76, 40), { points: 36, text: "Accountability is ahead of the return signal by 36 points." });
  assert.equal(lensGap(30, 90).text, "The return signal is ahead of accountability by 60 points.");
});

test("pillar summary picks the strongest and weakest", () => {
  assert.equal(
    pillarSummary({ Environmental: 81, Social: 72, Governance: 70 }),
    "Strongest pillar: Environmental (81). Weakest: Governance (70).",
  );
});

test("factor summary ignores small and missing scores", () => {
  assert.equal(
    factorSummary({ value_score: -0.8, quality_score: 0.1, momentum_score: 1.2, growth_score: 0.6, low_vol_score: null }),
    "The model likes its rising price and fast growth, but it is put off by its expensive price.",
  );
  assert.equal(
    factorSummary({ value_score: 0.2, quality_score: null, momentum_score: -0.1, growth_score: 0, low_vol_score: 0.4 }),
    "No factor stands out much in either direction.",
  );
});

test("trend text uses the 3-point threshold", () => {
  assert.equal(trendText(6, 75.1), "Improving: up 6.0 from 75 a year ago.");
  assert.equal(trendText(-12.6, 62.7), "Worsening: down 12.6 from 63 a year ago.");
  assert.equal(trendText(-1.5, 50), "Stable: down 1.5 from 50 a year ago.");
});

test("event age reads in months, then years", () => {
  assert.equal(ageText(0.4), "this month");
  assert.equal(ageText(1), "1 month ago");
  assert.equal(ageText(7.2), "7 months ago");
  assert.equal(ageText(30), "2.5 years ago");
});

test("joinWords reads like English", () => {
  assert.equal(joinWords(["a"]), "a");
  assert.equal(joinWords(["a", "b", "c"]), "a, b and c");
});

test("pearson and its takeaway", () => {
  assert.equal(pearson([1, 2, 3], [2, 4, 6]), 1);
  assert.equal(pearson([1, 2], [1, 2]), null);
  assert.equal(pearson([1, 1, 1], [1, 2, 3]), null);
  assert.equal(correlationTakeaway(-0.3, 30), "Across these 30 companies, companies with higher ESG scores have earned slightly lower returns over the last year.");
  assert.equal(correlationTakeaway(0.05, 30), "Across these 30 companies, a higher ESG score has had almost nothing to do with last year's return.");
});
