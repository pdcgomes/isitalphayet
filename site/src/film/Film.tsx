import { useEffect, useState, type ReactNode } from "react";
import { flushSync } from "react-dom";
import { Waterfall } from "../charts/Waterfall";
import { SITE_HOST } from "../config";
import { data, story } from "../lib/data";
import { moneyShort } from "../lib/format";
import { FrameHeight } from "../story/hooks";
import {
  AiScene,
  FeeBarsScene,
  FeesScene,
  HindsightScene,
  LuckScene,
  PeekScene,
  PitchScene,
  VerdictScene,
  WATERFALL_BARS,
} from "../story/scenes";

/** Scenes are laid out in a 600x750 frame, then scaled to fill the output (1080x1350 at 1.8x), so text stays legible. */
export const FRAME = { width: 600, height: 750 };
const FADE_MS = 450;
const MARQUEE_MS = 28000;

interface FilmScene {
  id: string;
  ms: number;
  hype?: boolean;
  render: (p: number, t: number) => ReactNode;
}

export const FILM_SCENES: FilmScene[] = [
  { id: "pitch", ms: 9000, hype: true, render: (p, t) => <PitchScene p={p} film marquee={(t / MARQUEE_MS) % 1} /> },
  { id: "peek", ms: 8000, render: (p) => <PeekScene p={p} film /> },
  { id: "fees", ms: 7000, render: (p) => <FeesScene p={p} film /> },
  { id: "hindsight", ms: 7500, render: (p) => <HindsightScene p={p} film /> },
  { id: "luck", ms: 7500, render: (p) => <LuckScene p={p} film /> },
  { id: "ai", ms: 8000, render: (p) => <AiScene p={p} film /> },
  { id: "verdict", ms: 6000, render: (p) => <VerdictScene p={p} film /> },
];
export const FILM_DURATION = FILM_SCENES.reduce((n, s) => n + s.ms, 0);

function WaterfallStill() {
  const bh = story.buy_and_hold;
  return (
    <div className="scene">
      <div className="kicker">How the number was made</div>
      <h2>$1,000 into {moneyShort(WATERFALL_BARS[0].value)}? Switch off the cheats.</h2>
      <p>Same code, same Bitcoin prices. Remove the peek at tomorrow, then charge the fees a UK account really pays.</p>
      <Waterfall
        bars={WATERFALL_BARS}
        height={300}
        reference={{ value: bh.final_value, label: `Just buying and holding: ${moneyShort(bh.final_value)}`, color: "var(--ink)" }}
        ariaLabel="Final value of $1,000 with every cheat on, without peeking, and at real fees, against buying and holding."
      />
    </div>
  );
}

/** Extra stills for the thread that are not in the film. */
const STILLS: Record<string, FilmScene> = {
  waterfall: { id: "waterfall", ms: 1, render: () => <WaterfallStill /> },
  "all-fees": { id: "all-fees", ms: 1, render: (p) => <FeeBarsScene p={p} film /> },
};

declare global {
  interface Window {
    __filmSeek?: (ms: number) => void;
    __filmDuration?: number;
  }
}

function useFitScale(width: number, height: number): number {
  const [viewport, setViewport] = useState(() => [window.innerWidth, window.innerHeight]);
  useEffect(() => {
    const update = () => setViewport([window.innerWidth, window.innerHeight]);
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);
  return Math.min(viewport[0] / width, viewport[1] / height);
}

function Layer({ scene, p, t, opacity = 1 }: { scene: FilmScene; p: number; t: number; opacity?: number }) {
  return (
    <div className={`film-layer ${scene.hype ? "film-hype" : "film-calm"}`} style={{ opacity }}>
      <div className="film-inner">{scene.render(p, t)}</div>
    </div>
  );
}

/** The film at time t: the current scene, with the previous one underneath while it fades in. */
export function FilmFrame({ t }: { t: number }) {
  const layers: ReactNode[] = [];
  const closing = t >= FILM_DURATION - FILM_SCENES[FILM_SCENES.length - 1].ms;
  let start = 0;
  FILM_SCENES.forEach((scene, i) => {
    const end = start + scene.ms;
    const isLast = i === FILM_SCENES.length - 1;
    if (t >= start && (t < end || isLast)) {
      const sinceStart = t - start;
      if (i > 0 && sinceStart < FADE_MS) layers.push(<Layer key={FILM_SCENES[i - 1].id} scene={FILM_SCENES[i - 1]} p={1} t={t} />);
      layers.push(
        <Layer key={scene.id} scene={scene} p={Math.min(1, sinceStart / scene.ms)} t={t} opacity={i === 0 ? 1 : Math.min(1, sinceStart / FADE_MS)} />,
      );
    }
    start = end;
  });
  return (
    <FrameHeight.Provider value={FRAME.height}>
      {layers}
      {/* The closing card shows the address itself. */}
      {!closing && <div className="film-watermark">{SITE_HOST}</div>}
    </FrameHeight.Provider>
  );
}

function Stage({ children, width, height, controlled }: { children: ReactNode; width: number; height: number; controlled: boolean }) {
  const scale = useFitScale(width, height);
  return (
    <div className={`film-stage${controlled ? " film-controlled" : ""}`}>
      <div style={{ width: width * scale, height: height * scale, position: "relative" }}>
        <div className="film-frame" style={{ width, height, transform: `scale(${scale})` }}>
          {children}
        </div>
      </div>
    </div>
  );
}

export default function Film() {
  const controlled = new URLSearchParams(window.location.search).has("controlled");
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    document.title = "Is It Alpha Yet? The film";
    window.__filmDuration = FILM_DURATION;
    window.__filmSeek = (ms: number) => flushSync(() => setT(ms));
  }, []);

  useEffect(() => {
    if (controlled || !playing) return;
    let raf = 0;
    const begin = performance.now();
    const tick = (now: number) => {
      const elapsed = now - begin;
      setT(Math.min(elapsed, FILM_DURATION));
      if (elapsed < FILM_DURATION) raf = requestAnimationFrame(tick);
      else setPlaying(false);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [controlled, playing]);

  return (
    <Stage width={FRAME.width} height={FRAME.height} controlled={controlled}>
      <FilmFrame t={t} />
      {!controlled && !playing && (
        <button className="film-play" onClick={() => setPlaying(true)}>
          {t === 0 ? "Play" : "Play again"} ({Math.round(FILM_DURATION / 1000)}s)
        </button>
      )}
    </Stage>
  );
}

/** Link-preview card: the verdict, never the hype, so a shared link can't spread the myth. */
function OgCard() {
  const bh = story.buy_and_hold;
  return (
    <div className="og">
      <div className="og-text">
        <div className="og-q">Is it alpha yet?</div>
        <div className="og-a">No.</div>
        <p>
          We tested viral trading-bot claims honestly: real prices, real UK fees, no peeking. {data.meta.claims_tested} tested,{" "}
          {data.meta.claims_passed} passed.
        </p>
        <div className="og-url">{SITE_HOST}</div>
      </div>
      <div className="og-chart">
        <div className="og-chart-title">How a $1,000 backtest becomes {moneyShort(WATERFALL_BARS[0].value)}</div>
        <Waterfall
          bars={WATERFALL_BARS}
          height={230}
          reference={{ value: bh.final_value, label: `Just holding: ${moneyShort(bh.final_value)}`, color: "var(--ink)" }}
          ariaLabel="Final value of $1,000 with every cheat on, without peeking, and at real fees, against buying and holding."
        />
      </div>
    </div>
  );
}

/** A single still: `?shot=og` for the link preview, or `?shot=<scene id>` for a scene at its end state. */
export function Shot({ name }: { name: string }) {
  if (name === "og") {
    return (
      <Stage width={600} height={315} controlled>
        <OgCard />
      </Stage>
    );
  }
  const scene = FILM_SCENES.find((s) => s.id === name) ?? STILLS[name];
  if (!scene) return <p>Unknown shot: {name}</p>;
  return (
    <Stage width={FRAME.width} height={FRAME.height} controlled>
      <FrameHeight.Provider value={FRAME.height}>
        <Layer scene={scene} p={1} t={0} />
        <div className="film-watermark">{SITE_HOST}</div>
      </FrameHeight.Provider>
    </Stage>
  );
}
