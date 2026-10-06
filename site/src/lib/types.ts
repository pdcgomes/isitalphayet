// Shape of site/src/data/site.json, written by experiments/export_site_data.py.

export type FeeKey = "article" | "kraken_maker" | "kraken_taker";

export interface Step {
  label: string;
  variant: string;
  final_value: number;
  total_return: number;
  cagr: number;
  sharpe: number;
  max_drawdown: number;
  win_rate: number;
  holding_spells: number;
  trades: number;
  explain: string;
  growth_weekly: number[];
}

export interface Call {
  date: string;
  ticker: string;
  rating: string;
  return: number | null;
  outcome: "right" | "wrong" | "no call" | "pending";
}

export interface AiAsset {
  ticker: string;
  settled: number;
  ratings: Record<string, number>;
  average_exposure: number;
  agent_return: number;
  buy_and_hold_return: number;
  constant_exposure_return: number;
  timing_skill: number;
  hits: number;
  calls: number;
  p_value: number;
}

export interface Ai {
  calls: number;
  hits: number;
  hit_rate: number;
  p_value: number;
  needed_for_significance: number;
  usd_per_decision: number;
  minutes_per_decision: number;
  total_usd: number;
  decisions: number;
  repeat_ratings: string[];
  /** "BTC-USD 2026-09-28": ticker and date of the repeated decision. */
  repeat_cell: string;
  /** Seeded fair coin flips, one per directional call, for the coin-versus-AI comparison. */
  coin_seed: number;
  coin_flips: boolean[];
  assets: AiAsset[];
  weekly_calls: Call[];
  biggest_miss: Call | null;
  window: string[];
}

export interface RandomStrategy {
  name: string;
  final_value: number;
  sharpe: number;
  growth_weekly: number[];
}

export interface Story {
  since: string;
  until: string;
  weeks: string[];
  buy_and_hold: {
    final_value: number;
    final_value_article_fees: number;
    cagr: number;
    sharpe: number;
    max_drawdown: number;
    longest_drawdown_days: number;
    growth_weekly: number[];
    underwater_weekly: number[];
  };
  steps: Step[];
  hindsight: {
    variant: string;
    explain: string;
    test_period: string[];
    strategy_final_value: number;
    buy_and_hold_final_value: number;
    strategy_sharpe: number;
    buy_and_hold_sharpe: number;
    strategy_growth_weekly: number[];
    buy_and_hold_growth_weekly: number[];
    weeks: string[];
  };
  luck: {
    deflated_sharpe: number;
    lenient_deflated_sharpe: number;
    trials: number;
    seed: number;
    fee: string;
    strategy_final_value_article_fees: number;
    random: RandomStrategy[];
  };
  fees: {
    scenarios: Record<FeeKey, number>;
    selected: string;
    selected_cagr: Record<FeeKey, number>;
    variants: { name: string; trades: number; cagr_article: number; cagr_taker: number }[];
  };
  look_ahead: Record<"honest" | "leaky", { cagr: number; sharpe: number; max_drawdown: number }>;
  ai: Ai;
  feed: { views: number; bookmarks: number; likes: number; followers: number };
  sources: { tradingagents_stars: number };
}

export interface FamilyBlock {
  family: string;
  name: string;
  selected: string;
  full_cagr: Record<FeeKey, number>;
  full_max_drawdown: number;
  test: { cagr: number; sharpe: number; calmar: number; max_drawdown: number; total_return: number };
  test_benchmark: { cagr: number; sharpe: number; calmar: number; max_drawdown: number; total_return: number };
  deflated_sharpe: number;
  lenient_deflated_sharpe: number;
  positive_fold_share: number;
  eth_sharpe: number;
  eth_benchmark_sharpe: number;
  gates: Record<"out_of_sample" | "deflated_sharpe" | "walk_forward" | "eth_holdout", boolean>;
  gates_passed: number;
  trades: number;
  annual_fee_drag: number;
  growth_weekly: Record<FeeKey, number[]>;
  walk_forward: { start: string; end: string; chosen: string; return: number; benchmark_return: number }[];
  regimes: Record<string, number>;
  variants: { name: string; trades: number; cagr: Record<FeeKey, number> }[];
}

export interface Audit {
  trials: number;
  deflated_sharpe_gate: Record<string, { article: number; correct: number }>;
  walk_forward_defaults: {
    train_days: number;
    test_days: number;
    metrics_minimum_observations: number;
    crashes: boolean;
    error: string | null;
  };
  costs: { article_per_side: number; kraken_taker_per_side: number; ratio: number };
}

export interface WalletGroup {
  wallets: number;
  share_loss: number;
  median: number;
  total: number;
  top_1pct_share_of_profit: number;
  top_01pct_share_of_profit: number;
}

export interface PriceBand {
  band: string;
  tokens: number;
  price: number;
  won: number;
  before_fees: number;
  /** Return per $1 after today's fees and one tick, with its 95% interval. */
  after: number;
  lo: number;
  hi: number;
}

export interface BondRun {
  cagr: number;
  cagr_lo: number;
  cagr_hi: number;
  win_rate: number;
  max_drawdown: number;
  final_equity: number;
  positions: number;
  losses: number;
  equity_weekly: number[];
  sports_pnl: number;
}

export interface LatencyRegime {
  windows: number;
  traded: number;
  hit_rate: number;
  mean_return: number;
  lo95: number;
  hi95: number;
}

export interface Polymarket {
  preregistered_at: string;
  preregistration_sha256: string;
  preregistration_changes: number;
  trials: number;
  wallets: {
    groups: Record<"all" | "automated" | "human" | "human_maker_heavy" | "human_taker_heavy", WalletGroup>;
    by_volume: (WalletGroup & { band: string })[];
  };
  persistence: {
    splits: { label: string; beats_null: boolean; wallets: number; top_mean_next: number; null_p025: number; null_p975: number; spearman: number }[];
    splits_beating_null: number;
  };
  calibration: { markets: number; recorded_close: PriceBand[]; scheduled_end: PriceBand[] };
  bonds: {
    cash_rate: number;
    weeks: string[];
    registered: Record<"D=7" | "D=30", BondRun>;
    open_at_end_of_day: Record<"D=7" | "D=30", BondRun>;
  };
  latency: {
    variants: { name: string; eligible: boolean; passes: boolean; before: LatencyRegime; after: LatencyRegime }[];
    works_for_retail: boolean;
    forecast: { seconds_left: number; windows: number; model: number; market: number }[];
  };
  viral: {
    fee_changes: Record<string, string>;
    wallets: { address: string; label: string; months: { month: string; volume: number; trading_profit: number; trades: number }[] }[];
  };
}

export interface Claim {
  slug: string;
  order: number;
  title: string;
  kind: string;
  claim: string;
  source: string;
  source_url: string;
  tested_on: string;
  experiment: "backtest" | "tradingagents" | "article_audit" | "polymarket";
  polymarket_test?: "latency" | "bonds" | "copy";
  verdict: "alpha" | "not_alpha";
  summary: string;
  what_we_tested: string;
  headline: string;
  families?: FamilyBlock[];
  ai?: Ai;
  audit?: Audit;
  look_ahead?: Story["look_ahead"];
}

export interface PaperRow {
  bar_open: string;
  close: string;
  trade: string;
  equity: string;
  buy_and_hold_equity: string;
  decided_target: string;
}

export interface SiteData {
  generated_at: string;
  meta: {
    preregistration_sha256: string;
    preregistered_at: string;
    preregistration_changes: number;
    trials: number;
    polymarket_trials: number;
    runs_logged: number;
    fees: Record<FeeKey, number>;
    design_period: string;
    test_period: string;
    data_range: string[];
    claims_tested: number;
    claims_passed: number;
  };
  story: Story;
  claims: Claim[];
  polymarket: Polymarket;
  live: {
    forward_test: { start: string; end: string; weeks: number; calls: Call[] };
    paper: {
      config: { variant: string; label: string; pair: string; capital_gbp: number; fee_per_side: number; started_at: string };
      rows: PaperRow[];
    };
  };
  method: {
    gates: { name: string; detail: string }[];
    limitations: string[];
    corrections: { date: string; text: string }[];
    preregistration_text: string;
    polymarket_preregistration_text: string;
  };
}
