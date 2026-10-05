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

export interface Claim {
  slug: string;
  order: number;
  title: string;
  kind: string;
  claim: string;
  source: string;
  source_url: string;
  tested_on: string;
  experiment: "backtest" | "tradingagents" | "article_audit";
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
  };
}
