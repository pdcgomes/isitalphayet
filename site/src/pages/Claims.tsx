import { Shell, Stat, Verdict } from "../components/Shell";
import { data } from "../lib/data";
import { longDate } from "../lib/format";
import { Link } from "../lib/router";

export default function Claims() {
  const { meta, claims } = data;
  return (
    <Shell title="Every claim we tested">
      <header className="page-head">
        <p className="kicker">The tracker</p>
        <h1>Is it alpha yet? Not for any of these.</h1>
        <p className="prose muted">
          Every claim was tested the same way: rules written down before the test, real prices, real fees and every attempt
          counted. A claim earns “alpha” only by beating the honest alternative (simply holding, cash, or a coin flip) on data
          it never saw.
        </p>
        <div className="stats">
          <Stat value={meta.claims_tested} label="Claims tested" />
          <Stat value={meta.claims_passed} label="Passed" />
          <Stat value={meta.trials + meta.polymarket_trials} label="Strategy versions counted" />
        </div>
      </header>
      <ol className="claim-list">
        {claims.map((c) => (
          <li key={c.slug} className="card claim-card">
            <div className="claim-card-top">
              <Verdict verdict={c.verdict} />
              <span className="muted small">
                {c.kind} · tested {longDate(c.tested_on)}
              </span>
            </div>
            <h2>
              <Link to={`/claims/${c.slug}`}>{c.title}</Link>
            </h2>
            <p className="claim-headline">{c.headline}</p>
            <p className="muted">{c.summary}</p>
            <Link to={`/claims/${c.slug}`} className="small">
              See the evidence
            </Link>
          </li>
        ))}
      </ol>
    </Shell>
  );
}
