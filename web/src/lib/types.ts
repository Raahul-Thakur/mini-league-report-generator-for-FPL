// Mirrors the API's report JSON (app/models.py in the backend).

export interface ManagerRef {
  entry_id: number;
  team_name: string;
  manager_name: string;
}

export interface PointsAward { manager: ManagerRef; points: number }
export interface CaptainAward {
  manager: ManagerRef;
  player_name: string;
  points: number;
  multiplier: number;
  used_vice: boolean;
  triple_captain: boolean;
}
export interface BenchAward { manager: ManagerRef; points: number }
export interface HitAward { manager: ManagerRef; cost: number; transfers: number }
export interface RankMoveAward {
  manager: ManagerRef;
  previous_rank: number;
  rank: number;
  places: number;
}
export interface DifferentialAward {
  manager: ManagerRef;
  player_name: string;
  points: number;
  owned_by: number;
}
export interface ChipPlay { manager: ManagerRef; chip: string; chip_name: string }
export interface Ownership { player_name: string; owners: number; percent: number }

export interface Report {
  league_id: number;
  league_name: string;
  gameweek: number;
  is_latest_gameweek: boolean;
  latest_gameweek: number | null;
  managers_analysed: number;
  total_managers: number | null;
  truncated: boolean;
  max_entries: number;
  winner: PointsAward | null;
  wooden_spoon: PointsAward | null;
  best_captain: CaptainAward | null;
  worst_captain: CaptainAward | null;
  bench_regret: BenchAward | null;
  biggest_hit: HitAward | null;
  rank_climber: RankMoveAward | null;
  rank_faller: RankMoveAward | null;
  differential_hero: DifferentialAward | null;
  chips_played: ChipPlay[];
  template: Ownership[];
  disclaimer: string;
}

export type ApiErrorCode =
  | "league_not_found"
  | "gameweek_not_started"
  | "invalid_gameweek"
  | "fpl_unavailable"
  | "api_unreachable"
  | "unknown";

export type ReportResult =
  | { ok: true; report: Report }
  | { ok: false; code: ApiErrorCode; message: string };
