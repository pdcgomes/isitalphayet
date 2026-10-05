import { REPO_URL } from "../config";
import { data } from "../lib/data";
import { longDate } from "../lib/format";
import { Link } from "../lib/router";

export function Footer() {
  return (
    <footer className="footer">
      <p>
        <strong>Is It Alpha Yet?</strong> Viral trading-bot claims, tested honestly. Education, not financial advice:
        nothing here tells you to buy, sell or hold anything.
      </p>
      <p>
        <Link to="/">The story</Link> · <Link to="/claims">Claims</Link> · <Link to="/live">Live test</Link> ·{" "}
        <Link to="/method">Method</Link>
        {REPO_URL && (
          <>
            {" "}
            · <a href={REPO_URL}>Code and data</a>
          </>
        )}
        {" "}· Updated {longDate(data.generated_at)}
      </p>
    </footer>
  );
}
