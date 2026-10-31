export interface FixtureSummary {
  id: number;
  league_id: number | null;
  league_name: string | null;
  country: string | null;
  round: string | null;
  home: string;
  away: string;
  status: string;
  elapsed: number | null;
  extra: number | null;
  home_goals: number;
  away_goals: number;
  kickoff: string | null;
  n_opportunities?: number;
  n_quotes?: number;
  has_stats?: boolean;
  model?: string | null;
  p_more_goals?: number | null;
  analysable?: boolean;
  not_analysable_reason?: string | null;
}

export interface EvaluationRow {
  key: string;
  market: string;
  pick: string;
  line: number | null;
  label: string;
  odds: number;
  source: string;
  bookmaker: string | null;
  p_model: number;
  p_low: number;
  p_high: number;
  p_cons: number;
  p_push: number;
  implied: number;
  p_market_fair: number | null;
  overround: number | null;
  ev: number;
  ev_cons: number;
  edge: number;
  margin: number;
  passed: boolean;
  fail_reasons: string[];
  confidence: number;
  confidence_label: "alta" | "media" | "bassa";
  rank_score: number;
  reasons: string[];
  risks: string[];
  odds_age_s: number | null;
}

export interface Opportunity extends EvaluationRow {
  id: number;
  fixture_id: number;
  fixture: FixtureSummary;
  model: {
    goal_model: string;
    exp_goals_home: number;
    exp_goals_away: number;
    p_more_goals: number;
    minutes_left_est: number;
  };
  first_seen: string;
  last_seen: string;
  odds_at_detection: number;
  minute_at_detection: number | null;
}

export interface Invalidated {
  id: number;
  fixture_id: number;
  match: string;
  label: string;
  odds_at_detection: number;
  closing_odds: number | null;
  invalidated_at: string | null;
  reason: string | null;
  status: string;
  result: string | null;
}

export interface ProviderInfo {
  configured: boolean;
  last_ok: string | null;
  last_error: string | null;
  quota: Record<string, string | null>;
}

export interface Providers {
  api_football: ProviderInfo;
  the_odds_api: ProviderInfo;
  scanner: {
    cycles: number;
    last_cycle_at: string | null;
    last_cycle_ms: number | null;
    last_error: string | null;
    poll_interval_s: number;
    paused: boolean;
  };
  model: { loaded: boolean; version: string | null };
  unmapped_markets: [string, number][];
}

export interface LiveState {
  updated_at: string | null;
  n_live: number;
  n_opportunities: number;
  fixtures: FixtureSummary[];
  opportunities: Opportunity[];
  invalidated: Invalidated[];
  message: string | null;
  providers: Providers;
  filters?: { min_odds: number; min_ev: number; min_edge: number };
}

export type SideStats = Record<string, number | null>;

export interface FixtureDetail {
  fixture: FixtureSummary;
  analysable: boolean;
  not_analysable_reason?: string;
  error?: string;
  note?: string;
  stats: { home: SideStats; away: SideStats } | null;
  availability: { provided: string[]; missing: string[]; not_provided_by_source: Record<string, string> };
  events: { minute: number | null; extra: number | null; side: string | null; type: string; detail: string | null; player: string | null }[];
  form: { home?: TeamForm | null; away?: TeamForm | null };
  windows?: {
    w5: Record<"home" | "away", SideStats> | null;
    w10: Record<"home" | "away", SideStats> | null;
    w15: Record<"home" | "away", SideStats> | null;
    coverage_min: number | null;
  };
  model?: {
    goal_model: string;
    minutes_left_est: number;
    exp_goals_home: number;
    exp_goals_away: number;
    p_more_goals: number;
    p_next_home: number;
    p_next_away: number;
    p_next_none: number;
    p_goal_next10: number;
    fair_odds_goal_next10: number | null;
    corners_expected_rest: number | null;
    main_markets: { key: string; label: string; p_model: number; p_low: number; p_high: number; fair_odds: number | null }[];
  };
  evaluations: EvaluationRow[];
  data_quality?: Record<string, unknown>;
  timeline: { status: string; elapsed: number | null; extra: number | null; home_goals: number; away_goals: number; home: SideStats; away: SideStats }[];
}

export interface TeamForm {
  team_id: number;
  matches: number;
  goals_for: number;
  goals_against: number;
  over15: number;
  over25: number;
  over35: number;
  btts: number;
  home_matches: number;
  home_gf: number;
  home_ga: number;
  away_matches: number;
  away_gf: number;
  away_ga: number;
  last5_gf: number;
  last5_ga: number;
  last5_n: number;
  results: string[];
}

export interface Agg {
  n: number;
  wins?: number;
  pushes?: number;
  losses?: number;
  hit_rate?: number;
  avg_p_model?: number;
  staked?: number;
  profit?: number;
  yield?: number;
  roi_bankroll?: number;
  avg_odds?: number;
  avg_ev_cons_expected?: number;
  clv?: number | null;
}

export interface CalBin {
  p_mean: number;
  obs: number;
  n: number;
  se?: number;
}

export interface Backtest {
  note: string;
  overall: Agg;
  max_drawdown: number;
  by_market: Record<string, Agg>;
  by_league: Record<string, Agg>;
  by_odds_band: Record<string, Agg>;
  by_confidence: Record<string, Agg>;
  equity: { t: string; profit: number }[];
  calibration_predictions: { n: number; bins: CalBin[]; brier?: number; logloss?: number };
  calibration_opportunities: { n: number; bins: CalBin[]; brier?: number; logloss?: number };
  pending: number;
}
