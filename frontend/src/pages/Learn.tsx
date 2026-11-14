import { Link } from "react-router-dom";
import { GLOSSARY, type GlossaryEntry } from "../glossary";

const LESSONS = [
  {
    title: "What an ESG score measures",
    body: "It rates how responsibly a company is run across environment, social and governance. It does not predict whether the stock will go up.",
    to: "/lookup/MSFT",
    cta: "See a breakdown",
  },
  {
    title: "Why industries are scored differently",
    body: "Emissions matter more for an oil company than for a bank, so each sector weights E, S and G differently before they are combined.",
    to: "/lookup/XOM",
    cta: "Compare an energy company",
  },
  {
    title: "What a quant factor is",
    body: "Funds rank stocks on traits like cheapness and recent price trend that have gone with higher returns in the past. That ranking ignores ESG.",
    to: "/quant",
    cta: "Meet the five factors",
  },
  {
    title: "Why we never blend the two",
    body: "One combined number would hide the trade-off. Seeing both side by side lets you decide how much each one matters to you.",
    to: "/",
    cta: "Explore the trade-off",
  },
  {
    title: "How to read a backtest",
    body: "A backtest replays a strategy on old prices. It is a useful sanity check, but it is easy to overfit, and past results never promise future ones.",
    to: "/quant",
    cta: "See one, with caveats",
  },
  {
    title: "Check what you own",
    body: "A portfolio's score is the weighted average of its holdings. Bigger positions move the result more.",
    to: "/portfolio",
    cta: "Try the checker",
  },
];

const GROUPS: GlossaryEntry["group"][] = ["ESG", "Quant", "Returns and risk", "Portfolio"];

export default function Learn() {
  const entries = Object.entries(GLOSSARY) as [string, GlossaryEntry][];
  return (
    <>
      <div className="page-head">
        <p className="eyebrow">Learn</p>
        <h1>The ideas behind the numbers</h1>
        <p className="subtitle">
          Six short ideas, each a minute or two to read, then a glossary of every term on the site.
          Each lesson links to a live example.
        </p>
      </div>

      <div className="lesson-grid">
        {LESSONS.map((l, i) => (
          <article className="card" key={l.title}>
            <span className="lesson-num">{String(i + 1).padStart(2, "0")}</span>
            <h2 style={{ marginTop: "0.25rem" }}>{l.title}</h2>
            <p>{l.body}</p>
            <p><Link to={l.to} style={{ fontWeight: 500 }}>{l.cta} →</Link></p>
          </article>
        ))}
      </div>

      <h2 id="glossary" style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>Glossary</h2>
      {GROUPS.map((g) => (
        <section className="card" key={g} aria-labelledby={`group-${g.replace(/\W+/g, "-")}`}>
          <h3 id={`group-${g.replace(/\W+/g, "-")}`} className="eyebrow">{g}</h3>
          <dl className="glossary">
            {entries
              .filter(([, e]) => e.group === g)
              .map(([id, e]) => (
                <div key={id} style={{ display: "contents" }}>
                  <dt id={`term-${id}`}>{e.term}</dt>
                  <dd>{e.short}</dd>
                </div>
              ))}
          </dl>
        </section>
      ))}
    </>
  );
}
