import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, fetchCompany, fetchQuantCompany, type CompanyDetail, type QuantCompanyDetail } from "../api";
import { Explain, FactorBar, GradeBadge, PillarBar, ReturnValue, Term } from "../components";
import { companyTakeaway, factorSummary, lensGap, pillarSummary } from "../insights";

interface LookupResult {
  ticker: string;
  company: CompanyDetail | null;
  quant: QuantCompanyDetail | null;
  error: string | null;
}

const QUICK_PICKS = ["AAPL", "MSFT", "XOM", "NEE", "V", "PG"];

export default function Lookup() {
  const ticker = useParams().ticker?.trim().toUpperCase();
  const navigate = useNavigate();
  const [input, setInput] = useState(ticker || "");
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

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const next = input.trim().toUpperCase();
    if (next) navigate(`/lookup/${encodeURIComponent(next)}`);
  }

  const search = (
    <form className="field-row" onSubmit={onSubmit} role="search">
      <label htmlFor="ticker-input" className="muted">Ticker</label>
      <input
        id="ticker-input"
        type="text"
        placeholder="e.g. AAPL"
        value={input}
        onChange={(e) => setInput(e.target.value.toUpperCase())}
        style={{ textTransform: "uppercase", width: 140 }}
      />
      <button type="submit" className="btn" disabled={loading}>
        {loading ? "Looking up…" : "Look up"}
      </button>
    </form>
  );

  if (!company) {
    return (
      <>
        <div className="page-head">
          <p className="eyebrow">Company</p>
          <h1>Look up a company</h1>
          <p className="subtitle">
            See how one company scores on accountability and on the traits quants use to pick
            returns, with every number explained.
          </p>
        </div>
        <div className="card">
          {search}
          {loading && <p className="muted" style={{ margin: "0.75rem 0 0" }}>Loading {ticker}…</p>}
          {error && (
            <div className="callout error" style={{ margin: "0.75rem 0 0" }}>
              {error}. We cover 30 large US companies; try one of these.
            </div>
          )}
          {!loading && (
            <div className="quick-picks">
              <span className="muted small">Try:</span>
              {QUICK_PICKS.map((t) => (
                <Link key={t} className="chip" to={`/lookup/${t}`} onClick={() => setInput(t)}>
                  {t}
                </Link>
              ))}
            </div>
          )}
        </div>
      </>
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
        <div className="card-head" style={{ marginBottom: "1rem" }}>
          <p className="eyebrow" style={{ margin: 0 }}>{company.sector} · {company.ticker}</p>
          {search}
        </div>
        <h1>{company.name}</h1>
        <p className="takeaway">{companyTakeaway(company.name, esg.grade, quant ? quant.percentile : null)}</p>
      </div>

      <div className="grid-2">
        <section className="card lens lens-esg" aria-label="ESG accountability">
          <span className="lens-label"><Term id="esg">ESG accountability</Term></span>
          <div className="lens-value">
            <span className="lens-number">{esg.composite_score.toFixed(0)}</span>
            <span className="lens-of">out of 100</span>
            <GradeBadge grade={esg.grade} />
          </div>
          <div className="meter"><span style={{ width: `${esg.composite_score}%` }} /></div>
          <div className="meter-scale"><span>0 weak</span><span>100 strong</span></div>
          <p className="muted" style={{ margin: "0.75rem 0 0" }}>
            <Term id="sectorPercentile">Sector percentile</Term>: better than{" "}
            {esg.sector_percentile.toFixed(0)}% of {company.sector} peers.
          </p>
          <Explain>
            <p>
              This measures how responsibly {company.name} is run, not whether its stock will go up.
              It blends three pillars, environmental, social and governance, weighted for what
              matters most in {company.sector}, then subtracts points for any recent controversies.
            </p>
            <p>The <Term id="grade">grade</Term> is the same score as a letter, AAA best to CCC worst.</p>
          </Explain>
        </section>

        <section className="card lens lens-quant" aria-label="Quant return signal">
          <span className="lens-label"><Term id="quant">Quant return signal</Term></span>
          {quant ? (
            <>
              <div className="lens-value">
                <span className="lens-number">{quant.percentile.toFixed(0)}</span>
                <span className="lens-of"><Term id="percentile">percentile</Term> · rank #{quant.rank}</span>
              </div>
              <div className="meter"><span style={{ width: `${quant.percentile}%` }} /></div>
              <div className="meter-scale"><span>0 least favored</span><span>100 most favored</span></div>
              <p className="muted" style={{ margin: "0.75rem 0 0" }}>
                Ranked against all covered companies on five <Term id="factor">factors</Term>.
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
            <p className="muted" style={{ marginTop: "0.75rem" }}>
              We don't have quant coverage for {company.ticker} yet, so only the ESG side is shown.
            </p>
          )}
        </section>
      </div>

      {gap && (
        <div className="callout" style={{ margin: "0 0 1rem" }}>
          <strong>The gap: </strong>
          {gap.text} The two scores sit side by side on purpose; ecosg never blends them into one number.
        </div>
      )}

      <div className="grid-2">
        <section className="card lens-esg">
          <h2>Why the ESG score is {esg.composite_score.toFixed(0)}</h2>
          <p className="muted">{pillarSummary(pillars)}</p>
          <PillarBar label={<Term id="environmental">Environmental</Term>} value={esg.environmental_score} />
          <PillarBar label={<Term id="social">Social</Term>} value={esg.social_score} />
          <PillarBar label={<Term id="governance">Governance</Term>} value={esg.governance_score} />
          {esg.controversy_penalty > 0 ? (
            <div className="callout warn">
              −{esg.controversy_penalty.toFixed(1)} points <Term id="controversy">controversy penalty</Term>{" "}
              (severity {company.esg_raw.controversy_severity.toFixed(1)} of 10).
            </div>
          ) : (
            <p className="muted small" style={{ marginBottom: 0 }}>No controversy penalty applied.</p>
          )}
          <Explain title="Why don't the pillars just average out?">
            <p>
              Each industry weights the pillars differently (<Term id="sectorWeights">sector weighting</Term>).
              That is why two companies with similar pillar scores can end up with different totals.
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
