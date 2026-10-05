import { useEffect, useState, type CSSProperties } from "react";
import { Footer } from "../components/Footer";
import { segment } from "../lib/format";
import { Beat } from "./Beat";
import {
  AiScene,
  FeeBarsScene,
  FeedScene,
  FeesScene,
  HindsightScene,
  HoldScene,
  LuckScene,
  PeekScene,
  PitchScene,
  SpotScene,
  VerdictScene,
} from "./scenes";

type Rgb = [number, number, number];
const VOID: Rgb = [4, 6, 10];
const PAPER: Rgb = [244, 241, 234];
const HYPE_TEXT: Rgb = [230, 255, 240];
const INK: Rgb = [22, 24, 29];

function mix(a: Rgb, b: Rgb, t: number): string {
  return `rgb(${a.map((v, i) => Math.round(v + (b[i] - v) * t)).join(", ")})`;
}

/** The turn: the neon screen sobers up into paper as the first cheat is revealed. */
function turn(p: number): CSSProperties {
  const t = segment(p, 0, 0.16);
  return { background: mix(VOID, PAPER, t), color: mix(HYPE_TEXT, INK, t) };
}

function KeepScrolling() {
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    const update = () => setVisible(window.scrollY < window.innerHeight * 2.6);
    update();
    window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, []);
  return (
    <div className={`keep-scrolling${visible ? "" : " gone"}`} aria-hidden={!visible}>
      Keep scrolling. It's not what it looks like.
    </div>
  );
}

export default function Story() {
  useEffect(() => {
    document.title = "Is It Alpha Yet? Viral trading bots, tested honestly";
  }, []);
  return (
    <main className="story">
      <Beat id="pitch" length={2.4} mood="hype">
        {(p) => <PitchScene p={p} />}
      </Beat>
      <Beat id="peek" length={2.3} style={turn}>
        {(p) => <PeekScene p={p} />}
      </Beat>
      <Beat id="fees" length={2}>
        {(p) => <FeesScene p={p} />}
      </Beat>
      <Beat id="all-fees" length={1.8}>
        {(p) => <FeeBarsScene p={p} />}
      </Beat>
      <Beat id="hindsight" length={2}>
        {(p) => <HindsightScene p={p} />}
      </Beat>
      <Beat id="luck" length={2}>
        {(p) => <LuckScene p={p} />}
      </Beat>
      <Beat id="hold" length={2}>
        {(p) => <HoldScene p={p} />}
      </Beat>
      <Beat id="ai" length={2.2}>
        {(p) => <AiScene p={p} />}
      </Beat>
      <Beat id="feed" length={1}>
        {() => <FeedScene />}
      </Beat>
      <Beat id="spot" length={1}>
        {() => <SpotScene />}
      </Beat>
      <Beat id="verdict" length={1}>
        {(p) => <VerdictScene p={p} />}
      </Beat>
      <KeepScrolling />
      <Footer />
    </main>
  );
}
