import { clamp01 } from "../lib/format";

interface Props {
  /** TradingAgents' directional calls, in date order: true if the call was right. */
  calls: boolean[];
  /** Seeded fair coin flips: true for heads, counted as "right". */
  coins: boolean[];
  /** 0 to 1: how many have been revealed. */
  progress?: number;
  seed: number;
}

function Row({ label, results, shown, kind }: { label: string; results: boolean[]; shown: number; kind: "ai" | "flip" }) {
  const right = results.slice(0, shown).filter(Boolean).length;
  return (
    <div className="coin-row">
      <div className="coin-row-head">
        <span>{label}</span>
        <span className="coin-tally">
          {right} right of {shown}
        </span>
      </div>
      <div className="coin-dots" aria-hidden="true">
        {results.map((ok, i) => (
          <span key={i} className={`coin ${kind} ${i < shown ? (ok ? "right" : "wrong") : "hidden"}`} />
        ))}
      </div>
    </div>
  );
}

export function CoinFlips({ calls, coins, progress = 1, seed }: Props) {
  const shown = Math.round(clamp01(progress) * calls.length);
  const aiRight = calls.filter(Boolean).length;
  const coinRight = coins.filter(Boolean).length;
  return (
    <figure className="coins" role="img" aria-label={`TradingAgents got ${aiRight} of ${calls.length} calls right; ${calls.length} fair coin flips got ${coinRight}.`}>
      <Row label="TradingAgents' weekly calls" results={calls} shown={shown} kind="ai" />
      <Row label={`A fair coin (seed ${seed})`} results={coins} shown={shown} kind="flip" />
      <figcaption className="caption">Filled: right. Hollow: wrong. Bitcoin and Ether, weekly from June to September 2026.</figcaption>
    </figure>
  );
}
