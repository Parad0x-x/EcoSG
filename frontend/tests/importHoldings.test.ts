import assert from "node:assert/strict";
import { test } from "node:test";
import { cleanTicker, parseHoldings, parseNumber, splitRow, toWeights } from "../src/importHoldings.ts";

test("finds the header below broker preamble and uses market value", () => {
  const csv = [
    '"Positions for account Individual ...123 as of 11/13/2026"',
    "",
    '"Symbol","Description","Quantity","Price","Market Value"',
    '"AAPL","APPLE INC","10","$245.00","$2,450.00"',
    '"XOM","EXXON MOBIL","8","$117.50","$940.00"',
    '"Cash & Cash Investments","--","--","--","$1,200.00"',
    '"Account Total","--","--","--","$4,590.00"',
  ].join("\n");

  const r = parseHoldings(csv);

  assert.equal(r.basis, "value");
  assert.deepEqual(r.holdings, [
    { ticker: "AAPL", amount: 2450 },
    { ticker: "XOM", amount: 940 },
  ]);
  assert.deepEqual(r.skipped, []);
});

test("multiplies shares by price when there is no value column", () => {
  const r = parseHoldings("Ticker,Shares,Last Price\nMSFT,2,400\nNEE,10,70");
  assert.equal(r.basis, "value");
  assert.deepEqual(r.holdings, [
    { ticker: "MSFT", amount: 800 },
    { ticker: "NEE", amount: 700 },
  ]);
});

test("falls back to share counts, merges duplicates across accounts and strips footnote stars", () => {
  const r = parseHoldings("Symbol,Quantity\nAAPL,5\nSPAXX**,100\nAAPL,5");
  assert.equal(r.basis, "shares");
  assert.deepEqual(r.holdings, [
    { ticker: "AAPL", amount: 10 },
    { ticker: "SPAXX", amount: 100 },
  ]);
});

test("reads tab-separated text pasted from a web table", () => {
  const r = parseHoldings("Symbol\tName\tMarket value\nV\tVisa\t1,000.50\nPG\tProcter\t500");
  assert.deepEqual(r.holdings, [
    { ticker: "V", amount: 1000.5 },
    { ticker: "PG", amount: 500 },
  ]);
});

test("reads headerless 'TICKER amount' lines and reports what it skipped", () => {
  const r = parseHoldings("aapl 40\nXOM, 30%\nNEE 30\nBRK.B 5\n???? 3\nTSLA n/a");
  assert.equal(r.basis, "number");
  assert.deepEqual(r.holdings.map((h) => h.ticker), ["AAPL", "XOM", "NEE", "BRK.B"]);
  assert.deepEqual(r.skipped, ["????", "TSLA"]);
});

test("helpers", () => {
  assert.equal(parseNumber("$1,234.50"), 1234.5);
  assert.equal(parseNumber("(12.5)"), -12.5);
  assert.equal(parseNumber("--"), null);
  assert.deepEqual(splitRow('"a, b","c ""q""",d', ","), ["a, b", 'c "q"', "d"]);
  assert.equal(cleanTicker("Cash"), null);
  assert.equal(cleanTicker(" brk.b "), "BRK.B");
  assert.deepEqual(toWeights([{ ticker: "A", amount: 1 }, { ticker: "B", amount: 3 }]), [
    { ticker: "B", weight: 75 },
    { ticker: "A", weight: 25 },
  ]);
  assert.deepEqual(toWeights([]), []);
});
