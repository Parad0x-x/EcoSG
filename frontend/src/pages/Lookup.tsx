import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, fetchCompany, fetchQuantCompany, type CompanyDetail, type QuantCompanyDetail } from "../api";
import CompanySearch from "../CompanySearch";
import { Explain, FactorBar, GapTrack, GradeBadge, PillarBar, ReturnValue, Term } from "../components";
import { ageText, companyTakeaway, factorSummary, lensGap, pillarSummary, trendText } from "../insights";

interface LookupResult {
  ticker: string;
  company: CompanyDetail | null;
  quant: QuantCompanyDetail | null;
  error: string | null;
}

const QUICK_PICKS = ["AAPL", "MSFT", "XOM", "NEE", "V", "PG"];

const CONFIDENCE_CLASS = { high: "ok", medium: "no", low: "warn" } as const;
const TREND_CLASS = { improving: "positive", stable: "muted", worsening: "negative" } as const;
const TREND_ARROW = { improving: "↑", stable: "→", worsening: "↓" } as const;

export default function Lookup() {
  const ticker = useParams().ticker?.trim().toUpperCase();
  const [result, setResult] = useState<LookupResult | null>(null);

  // The URL is the only trigger: submitting navigates, and this effect loads.
  useEffect(() => {
    if (!ticker) return;
    let stale = false;
    // Quant coverage is best-effort: a ticker can exist on the ESG side
    // without quant coverage, so its failure must not block the page.
    Promise.allSettled([fetchCompany(ticker), fetchQuantCompany(ticker)]).then(([c, q]) => {
      if (stale) return;
      setResult({
        ticker,
        company: c.status === "fulfilled" ? c.value : null,
        quant: q.status === "fulfilled" ? q.value : null,
        error:
          c.status === "rejected"
            ? c.reason instanceof ApiError
              ? c.reason.message
              : "Failed to look up ticker"
            : null,
      });
    });
    return () => {
      stale = true;
    };
  }, [ticker]);

  const current = result && result.ticker === ticker ? result : null;
  const loading = Boolean(ticker) && !current;
  const company = current?.company ?? null;
  const quant = current?.quant ?? null;
  const error = current?.error ?? null;

  if (!company) {
    return (
      <div className="page-head">
        <h1>Look up a company</h1>
        <p className="subtitle">
          See how one company scores on accountability and on the traits quants use to pick
          returns, with every number explained.
        </p>
        <CompanySearch large />
        {loading && <p className="muted" style={{ margin: "1rem 0 0" }}>Loading {ticker}…</p>}
        {error && (
          <div className="callout error" style={{ margin: "1rem 0 0", maxWidth: "34rem" }}>
            {error}. We cover the S&amp;P 500; search by name above or try one of these.
          </div>
        )}
        {!loading && (
          <div className="quick-picks">
            <span className="muted small">Try:</span>
            {QUICK_PICKS.map((t) => (
              <Link key={t} className="chip" to={`/lookup/${t}`}>
                {t}
              </Link>
            ))}
          </div>
        )}
      </div>
    );
  }

  const esg = company.esg_score;
  const gap = quant ? lensGap(esg.composite_score, quant.percentile) : null;
  const pillars = {
    Environmental: esg.environmental_score,
    Social: esg.social_score,
    Governance: esg.governance_score,
  };

  return (
    <>
      <div className="page-head">
        <p className="kicker">{company.sector}, {company.ticker}</p>
        <h1>{company.name}</h1>
        <p className="takeaway">{companyTakeaway(company.name, esg.grade, quant ? quant.percentile : null)}</p>
      </div>

      <div className="grid-2">
        <section className="lens-card lens-esg" aria-label="ESG accountability">
          <div className="field">
            <div className="field-label"><Term id="esg">ESG accountability</Term></div>
            <div className="field-value">
              <span className="field-number">{esg.composite_score.toFixed(0)}</span>
              <span className="field-of">out of 100</span>
              <GradeBadge grade={esg.grade} />
            </div>
          </div>
          <div className="lens-body">
          <div className="signal-row">
            <span className={`status ${CONFIDENCE_CLASS[esg.confidence]}`}>
              <Term id="confidence">{esg.confidence} confidence</Term>
            </span>
            <span className={TREND_CLASS[esg.trend_label]}>
              <span aria-hidden="true">{TREND_ARROW[esg.trend_label]} </span>
              <Term id="esgTrend">{trendText(esg.trend, esg.prior_composite_score)}</Term>
            </span>
          </div>
          <p className="muted" style={{ margin: "0.75rem 0 0" }}>
            <Term id="sectorPercentile">Sector percentile</Term>: better than{" "}
            {esg.sector_percentile.toFixed(0)}% of {company.sector} peers.
          </p>
          {esg.grade_cap_reason && (
            <div className="callout warn" style={{ margin: "0.75rem 0 0" }}>
              <strong>Grade capped at {esg.grade}</strong> (the score alone would earn {esg.grade_before_cap}).{" "}
              {esg.grade_cap_reason}
            </div>
          )}
          <Explain>
            <p>
              This measures how responsibly {company.name} is run, not whether its stock will go up.
              It blends three pillars, environmental, social and governance, weighted for what
              matters most in {company.sector}, compares the result with what is typical for the
              industry, then subtracts points for recent controversies.
            </p>
            <p>The <Term id="grade">grade</Term> is the same score as a letter, AAA best to CCC worst.</p>
            <p>
              Confidence and trend sit beside the score and never change it. Confidence is{" "}
              {esg.confidence} because this company reports about {company.esg_raw.data_coverage_pct.toFixed(0)}% of
              the data we look for, and rating agencies' scores for it spread by about{" "}
              {company.esg_raw.rater_spread.toFixed(0)} points.
            </p>
          </Explain>
          </div>
        </section>

        <section className="lens-card lens-quant" aria-label="Quant return signal">
          <div className="field">
            <div className="field-label"><Term id="quant">Quant return signal</Term></div>
            <div className="field-value">
              <span className="field-number">{quant ? quant.percentile.toFixed(0) : "n/a"}</span>
              {quant && <span className="field-of"><Term id="percentile">percentile</Term>, rank #{quant.rank}</span>}
            </div>
          </div>
          <div className="lens-body">
          {quant ? (
            <>
              <p className="muted">
                100 is the stock the model wants most. Ranked against all covered companies on
                five <Term id="factor">factors</Term>.
              </p>
              <Explain>
                <p>
                  This is how a hedge-fund-style model would rank the stock if it only cared about
                  returns. It looks at five traits linked to past performance and ignores ESG
                  completely.
                </p>
                <p>A high percentile means "the model would want to own this", not "this is a good company".</p>
              </Explain>
            </>
          ) : (
            <p className="muted">
              We don't have quant coverage for {company.ticker} yet, so only the ESG side is shown.
            </p>
          )}
          </div>
        </section>
      </div>

      {quant && gap && (
        <section className="card">
          <h2>The gap</h2>
          <p className="muted" style={{ margin: 0 }}>
            {gap.text} Both scores run 0 to 100, so they can share a line, but ecosg never blends them into one number.
          </p>
          <GapTrack large esg={esg.composite_score} quant={quant.percentile} />
        </section>
      )}

      <div className="grid-2">
        <section className="card lens-esg">
          <h2>Why the ESG score is {esg.composite_score.toFixed(0)}</h2>
          <p className="muted">{pillarSummary(pillars)}</p>
          <PillarBar label={<Term id="environmental">Environmental</Term>} value={esg.environmental_score} />
          <PillarBar label={<Term id="social">Social</Term>} value={esg.social_score} />
          <PillarBar label={<Term id="governance">Governance</Term>} value={esg.governance_score} />
          <ol className="score-steps">
            <li>
              Weighted for {company.sector} (<Term id="sectorWeights">sector weighting</Term>), the pillars
              come to <strong>{esg.weighted_pillar_score.toFixed(1)}</strong>.
            </li>
            <li>
              {company.sector} companies typically land between {esg.benchmark_low.toFixed(0)} and{" "}
              {esg.benchmark_high.toFixed(0)}, so that is{" "}
              <strong>{esg.industry_adjusted_score.toFixed(1)}</strong> out of 100{" "}
              (<Term id="industryAdjusted">industry-adjusted</Term>).
            </li>
            <li>
              {esg.controversy_penalty > 0 ? (
                <>
                  Minus <strong>{esg.controversy_penalty.toFixed(1)}</strong> points{" "}
                  <Term id="controversy">controversy penalty</Term> gives{" "}
                  <strong>{esg.composite_score.toFixed(1)}</strong>.
                </>
              ) : (
                <>No controversy penalty, so the score stays at <strong>{esg.composite_score.toFixed(1)}</strong>.</>
              )}
            </li>
          </ol>
          {esg.controversy_events.length > 0 && (
            <div className="table-wrap">
              <table>
                <caption className="muted small" style={{ textAlign: "left", paddingBottom: "0.4rem" }}>
                  Simulated events, not real allegations. Each one{" "}
                  <Term id="decay">fades out after 3 years</Term>
                </caption>
                <thead>
                  <tr>
                    <th>Event</th>
                    <th className="num"><Term id="controversyCategory">Category</Term></th>
                    <th className="num">When</th>
                    <th className="num">Counts now</th>
                  </tr>
                </thead>
                <tbody>
                  {esg.controversy_events.map((e, i) => (
                    <tr key={i}>
                      <td>{e.title}</td>
                      <td className="num">{e.category} of 5</td>
                      <td className="num" style={{ whiteSpace: "nowrap" }}>{ageText(e.age_months)}</td>
                      <td className="num">
                        −{e.penalty_points.toFixed(1)}{" "}
                        <span className="muted small">({Math.round(e.decay_factor * 100)}%)</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <Explain title="Why don't the pillars just average out?">
            <p>
              Each industry weights the pillars by what matters most for it, and governance always
              counts for at least a third. The result is then compared with the typical range for
              the industry, so an oil company is judged against oil companies. That is why two
              companies with similar pillar scores can end up with different totals.
            </p>
          </Explain>
        </section>

        <section className="card lens-quant">
          <h2>What the quant model sees</h2>
          {quant ? (
            <>
              <p className="muted">{factorSummary(quant.families)}</p>
              <FactorBar label={<Term id="value">Value</Term>} value={quant.families.value_score} />
              <FactorBar label={<Term id="quality">Quality</Term>} value={quant.families.quality_score} />
              <FactorBar label={<Term id="momentum">Momentum</Term>} value={quant.families.momentum_score} />
              <FactorBar label={<Term id="growth">Growth</Term>} value={quant.families.growth_score} />
              <FactorBar label={<Term id="lowVol">Low volatility</Term>} value={quant.families.low_vol_score} />
              <Explain title="How do I read these bars?">
                <p>
                  The center line is the average company in the same sector. Bars to the right are
                  better than average, bars to the left worse. The numbers are{" "}
                  <Term id="zscore">z-scores</Term>: +1 is well above average.
                </p>
              </Explain>
            </>
          ) : (
            <p className="muted">No factor data for this company.</p>
          )}
        </section>
      </div>

      <section className="card">
        <h2>The basics</h2>
        <div className="stat-grid" style={{ marginTop: "0.75rem" }}>
          <div className="stat">
            <div className="stat-label">Share price</div>
            <div className="stat-value">${company.financials.price.toFixed(2)}</div>
          </div>
          <div className="stat">
            <div className="stat-label"><Term id="return1y">1-year return</Term></div>
            <div className="stat-value"><ReturnValue pct={company.financials.one_year_return_pct} /></div>
          </div>
          <div className="stat">
            <div className="stat-label">3-year return</div>
            <div className="stat-value"><ReturnValue pct={company.financials.three_year_annualized_return_pct} /></div>
            <div className="stat-note">per year, on average</div>
          </div>
          <div className="stat">
            <div className="stat-label"><Term id="volatility">Volatility</Term></div>
            <div className="stat-value">{company.financials.volatility_pct.toFixed(1)}%</div>
          </div>
          <div className="stat">
            <div className="stat-label"><Term id="marketCap">Market cap</Term></div>
            <div className="stat-value">${company.financials.market_cap_b.toFixed(0)}B</div>
          </div>
        </div>
      </section>
    </>
  );
}
