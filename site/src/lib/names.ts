/** Short names for narrow charts, e.g. "trend(n=50)" becomes "Trend 50d". */
export function variantShortName(id: string): string {
  const match = id.match(/^(\w+)\((\w+)=([\d.]+)\)$/);
  if (!match) return id;
  const [, family, , raw] = match;
  const n = Number(raw);
  switch (family) {
    case "trend":
      return `Trend ${n}d`;
    case "tsmom":
      return `Momentum ${n}d`;
    case "vol_target":
      return `Vol-target ${Math.round(n * 100)}%`;
    case "rsi":
      return `RSI below ${n}`;
    case "grid":
      return `Grid ±${Math.round(n * 100)}%`;
    default:
      return id;
  }
}

/** The rule in a phrase for prose, e.g. "trend(n=50)" becomes "a 50-day trend filter". */
export function variantPhrase(id: string): string {
  const match = id.match(/^(\w+)\((\w+)=([\d.]+)\)$/);
  if (!match) return id;
  const [, family, , raw] = match;
  const n = Number(raw);
  switch (family) {
    case "trend":
      return `a ${n}-day trend filter`;
    case "tsmom":
      return `a ${n}-day momentum rule`;
    case "vol_target":
      return `a trend filter sized to ${Math.round(n * 100)}% volatility`;
    case "rsi":
      return `an RSI rule that buys below ${n}`;
    case "grid":
      return `a ±${Math.round(n * 100)}% grid`;
    default:
      return id;
  }
}

/** Plain-English names for the lab's variant ids, e.g. "trend(n=50)" becomes "Trend filter, 50-day". */
export function variantName(id: string): string {
  const match = id.match(/^(\w+)\((\w+)=([\d.]+)\)$/);
  if (!match) return id;
  const [, family, , raw] = match;
  const n = Number(raw);
  switch (family) {
    case "trend":
      return `Trend filter, ${n}-day`;
    case "tsmom":
      return `Momentum, ${n}-day`;
    case "vol_target":
      return `Vol-targeted trend, ${Math.round(n * 100)}%`;
    case "rsi":
      return `RSI dip-buying, below ${n}`;
    case "grid":
      return `Grid bot, ±${Math.round(n * 100)}%`;
    default:
      return id;
  }
}
