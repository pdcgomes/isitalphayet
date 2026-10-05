import { Shell } from "../components/Shell";
import { story } from "../lib/data";
import { pct } from "../lib/format";
import { Link } from "../lib/router";

export default function NotFound() {
  return (
    <Shell title="Not found">
      <h1>Not found</h1>
      <p>
        This page doesn't exist, unlike Bitcoin's {pct(-story.buy_and_hold.max_drawdown)} drawdown.{" "}
        <Link to="/">Back to the story</Link> or <Link to="/claims">see every claim</Link>.
      </p>
    </Shell>
  );
}
