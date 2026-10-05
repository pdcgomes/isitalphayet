export type Scale = (v: number) => number;

export function linearScale(d0: number, d1: number, r0: number, r1: number): Scale {
  const k = d1 === d0 ? 0 : (r1 - r0) / (d1 - d0);
  return (v) => r0 + (v - d0) * k;
}

export function logScale(d0: number, d1: number, r0: number, r1: number): Scale {
  const l0 = Math.log10(d0);
  const k = (r1 - r0) / (Math.log10(d1) - l0);
  return (v) => r0 + (Math.log10(Math.max(v, d0)) - l0) * k;
}

export function niceTicks(min: number, max: number, count = 5): number[] {
  const span = max - min;
  if (span <= 0) return [min];
  const raw = span / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const norm = raw / mag;
  const step = (norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10) * mag;
  const ticks: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + step * 1e-9; v += step) ticks.push(Number(v.toPrecision(12)));
  return ticks;
}

export function logTicks(min: number, max: number): number[] {
  const ticks: number[] = [];
  for (let e = Math.ceil(Math.log10(min)); e <= Math.floor(Math.log10(max)); e++) ticks.push(10 ** e);
  return ticks;
}

/** The first index of each calendar year in a list of ISO dates. */
export function yearTicks(dates: string[]): { index: number; label: string }[] {
  const out: { index: number; label: string }[] = [];
  let last = "";
  dates.forEach((d, i) => {
    const year = d.slice(0, 4);
    if (year !== last) {
      out.push({ index: i, label: year });
      last = year;
    }
  });
  return out;
}

/** Year labels for a time axis, dropping any that would sit closer than `minGap` pixels to the previous one. */
export function spacedYearTicks(dates: string[], x: Scale, minGap = 44): { index: number; label: string }[] {
  const ticks = yearTicks(dates);
  // A stub first year (2017 has 19 weeks) gives way to the first full year.
  if (ticks.length > 1 && x(ticks[1].index) - x(ticks[0].index) < minGap) ticks.shift();
  const out: { index: number; label: string }[] = [];
  for (const t of ticks) {
    const prev = out[out.length - 1];
    if (!prev || x(t.index) - x(prev.index) >= minGap) out.push(t);
  }
  return out;
}

/** Clip-path ids must be valid inside url(#...). */
export function safeId(id: string): string {
  return id.replace(/[^a-zA-Z0-9_-]/g, "");
}
