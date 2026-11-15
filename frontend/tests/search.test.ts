import assert from "node:assert/strict";
import { test } from "node:test";
import type { CompanySummary } from "../src/api.ts";
import { searchCompanies } from "../src/search.ts";

const co = (ticker: string, name: string): CompanySummary => ({
  ticker,
  name,
  sector: "Technology",
  one_year_return_pct: 0,
  composite_score: 50,
  grade: "A",
});

const LIST = [co("A", "Agilent"), co("AAPL", "Apple"), co("MA", "Mastercard"), co("MSFT", "Microsoft"), co("PAYX", "Paychex")];

test("ticker prefix matches rank ahead of name matches", () => {
  assert.deepEqual(searchCompanies(LIST, "ma").map((c) => c.ticker), ["MA"]);
  assert.deepEqual(searchCompanies(LIST, "a").map((c) => c.ticker), ["A", "AAPL", "MA", "PAYX"]);
});

test("matches company names case-insensitively", () => {
  assert.deepEqual(searchCompanies(LIST, "  micro ").map((c) => c.ticker), ["MSFT"]);
});

test("empty query returns nothing and limit caps the list", () => {
  assert.deepEqual(searchCompanies(LIST, "  "), []);
  assert.equal(searchCompanies(LIST, "a", 2).length, 2);
});
