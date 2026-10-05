const gb = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });

/** $84,465 or $296,080,470: every digit, for headlines. */
export function moneyFull(v: number): string {
  return `${v < 0 ? "-" : ""}$${gb.format(Math.abs(v))}`;
}

/** $296M, $84K, $1K: compact, for axes and bar labels. */
export function moneyShort(v: number): string {
  const a = Math.abs(v);
  const sign = v < 0 ? "-" : "";
  const short = (x: number, unit: string) => `${sign}$${x.toFixed(x >= 10 ? 0 : 1).replace(/\.0$/, "")}${unit}`;
  if (a >= 1e9) return short(a / 1e9, "B");
  if (a >= 1e6) return short(a / 1e6, "M");
  if (a >= 1e3) return short(a / 1e3, "K");
  return `${sign}$${Math.round(a)}`;
}

/** "$296 million" for prose; smaller amounts keep every digit. */
export function moneyWords(v: number): string {
  if (Math.abs(v) >= 1e9) return `$${Math.round(v / 1e9).toLocaleString("en-GB")} billion`;
  if (Math.abs(v) >= 1e6) return `$${Math.round(v / 1e6).toLocaleString("en-GB")} million`;
  return moneyFull(v);
}

export function pct(x: number, digits = 0): string {
  return `${(x * 100).toFixed(digits)}%`;
}

export function signedPct(x: number | null, digits = 1): string {
  if (x === null) return "pending";
  const v = (x * 100).toFixed(digits);
  return x > 0 ? `+${v}%` : `${v}%`;
}

export function longDate(iso: string): string {
  return new Date(`${iso.slice(0, 10)}T00:00:00Z`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

/** Ease for count-ups and reveals: fast start, gentle landing. */
export function easeOut(t: number): number {
  const c = Math.min(Math.max(t, 0), 1);
  return 1 - Math.pow(1 - c, 3);
}

export function clamp01(t: number): number {
  return Math.min(Math.max(t, 0), 1);
}

/** Map overall progress onto a sub-range: segment(p, 0.2, 0.6) runs 0 to 1 while p goes 0.2 to 0.6. */
export function segment(p: number, start: number, end: number): number {
  return clamp01((p - start) / (end - start));
}
