/**
 * Tipos hand-written que reflejan los shapes reales de la API.
 *
 * CRÍTICO verificado con curl:
 *   - recommended_stake → STRING (Pydantic serializa Decimal → string)
 *   - kickoff_at puede ser null
 *   - /signals envuelve { items, total }
 *   - /matches/upcoming y /groups son arrays pelados
 *   - standings en minúscula: pj, g, e, p, gf, gc, dg, pts
 *   - calibración en backtest.calibration_table (model.calibration top-level = null)
 */

export type ISODate = string
export type ISODateTime = string

export interface SignalItem {
  id: number
  match_id: number | null
  match_date: ISODate
  kickoff_at: ISODateTime | null
  home_team: string
  away_team: string
  market_type: string
  outcome_code: string
  p_model: number
  best_odds: number
  bookmaker: string
  edge: number
  ev: number
  kelly_fraction: number
  /** Decimal serializado como string por Pydantic */
  recommended_stake: string
  captured_at: ISODateTime
}

export interface SignalsResponse {
  items: SignalItem[]
  total: number
}

export interface UpcomingMatch {
  id: number
  match_date: ISODate
  kickoff_at: ISODateTime | null
  home_team: string
  away_team: string
  neutral_site: boolean
  stage: string
  p_home: number | null
  p_draw: number | null
  p_away: number | null
  low_confidence: boolean
}

export interface StandingRow {
  team_name: string
  pj: number
  g: number
  e: number
  p: number
  gf: number
  gc: number
  dg: number
  pts: number
}

export interface GroupFixture {
  id: number
  match_date: ISODate
  home_team: string
  away_team: string
  status: string
  p_home: number | null
  p_draw: number | null
  p_away: number | null
}

export interface GroupItem {
  name: string
  teams: string[]
  standings: StandingRow[]
}

/** Detalle de grupo (endpoint /groups/:name) — GroupItem + fixtures */
export interface GroupDetail extends GroupItem {
  fixtures: GroupFixture[]
}

export interface CalibrationBin {
  bin_low: number
  bin_high: number
  mean_predicted: number
  observed_freq: number
  count: number
}

export interface Backtest {
  brier: number
  logloss: number
  beats_baselines: boolean
  baselines: Record<string, number>
  eval_n: number
  eval_window: string
  calibration_table: CalibrationBin[]
}

export interface ModelInfo {
  name: string
  params_summary: Record<string, number>
  backtest: Backtest
  /** null en top-level — la tabla real vive en backtest.calibration_table */
  calibration: unknown | null
}

export interface PaperStats {
  total: number
  open: number
  settled: number
  roi: number | null
}

// ─── Apuestas (bet-settlement-real) ──────────────────────────────────────────

export interface BetCreate {
  match_id: number
  outcome_code: 'HOME' | 'DRAW' | 'AWAY'
  odds_taken: number
  stake: number
  note?: string
}

export interface BetItem {
  id: number
  /** StrEnum minúscula — API retorna 'real' | 'paper' */
  mode: 'real' | 'paper' | string
  /** StrEnum minúscula — API retorna 'pending' | 'won' | 'lost' | 'void' */
  status: 'pending' | 'won' | 'lost' | 'void' | string
  match_id: number | null
  outcome_code: string | null
  odds_taken: number
  /** Decimal serializado como string por Pydantic */
  stake: string
  pnl: string | null
  settled_result: string | null
  settled_at: ISODateTime | null
  placed_at: ISODateTime | null
  note: string | null
  value_signal_id: number | null
}

export interface ModeStats {
  total: number
  pending: number
  settled: number
  won: number
  lost: number
  /** Decimal serializado como string */
  staked: string | null
  /** Decimal serializado como string */
  returns: string | null
  roi: number | null
}

export interface BetsPageStats {
  paper: ModeStats
  real: ModeStats
}

// ─── Parlays (cupón de bloques) ───────────────────────────────────────────────

/**
 * Una pierna enviada al endpoint preview/create.
 * CRÍTICO: el campo es `odds` (no `odds_taken`) — verificado con curl.
 */
export interface ParlayLegInput {
  match_id: number
  outcome_code: 'HOME' | 'DRAW' | 'AWAY'
  /** Cuota decimal > 1 — campo `odds` en la API */
  odds: number
  label?: string
}

/**
 * Diagnóstico de una pierna en la respuesta preview.
 * `odds` viene como string (Decimal serializado por Pydantic).
 */
export interface LegDiagnostic {
  match_id: number
  outcome_code: string
  /** Decimal serializado como string */
  odds: string
  p_model: number | null
  ev: number | null
  is_negative_ev: boolean
}

/**
 * Respuesta de POST /parlays/preview.
 * CRÍTICO: `retorno` (no `potential_return`) y `legs` (no `legs_diagnostics`) — verificado con curl.
 */
export interface ParlayPreview {
  /** Decimal serializado como string */
  combined_odds: string
  model_prob: number | null
  ev: number | null
  /** Decimal serializado como string */
  stake: string
  /** stake × combined_odds — Decimal serializado como string */
  retorno: string
  legs: LegDiagnostic[]
  suggested_without_negatives: LegDiagnostic[]
}

/** Body para POST /parlays */
export interface ParlayCreate {
  legs: ParlayLegInput[]
  stake: number
  note?: string
}

/** Ítem de parlay en respuesta de lista GET /parlays */
export interface ParlayItem {
  id: number
  mode: 'real' | 'paper' | string
  status: 'pending' | 'won' | 'lost' | string
  bet_kind: string
  /** Decimal serializado como string */
  stake: string
  odds_taken: number
  pnl: string | null
  settled_at: string | null
  placed_at: string | null
  note: string | null
}

// ─── Futuros Monte Carlo (WC2026) ────────────────────────────────────────────

/**
 * Probabilidades de futuros para un equipo (model=montecarlo-v1).
 * group: letra del grupo (A–L), puede ser null si no hay datos de grupo.
 */
export interface FutureTeamRow {
  team_id: number
  team: string
  group: string | null
  p_champion: number
  p_advance_group: number
  p_reach_sf: number
  p_reach_final: number
}

/** Respuesta de GET /api/v1/futures/probabilities. */
export interface FuturesList {
  /** Champions rankeados por p_champion DESC */
  champions: FutureTeamRow[]
}

/** Señal +EV sobre OUTRIGHT_WINNER (pre-computada por futures_signals.py). */
export interface FutureSignal {
  signal_id: number
  team_id: number
  team: string
  p_champion: number
  edge: number
  best_odds: number
  bookmaker: string
}

/** Respuesta de GET /api/v1/futures/signals. */
export interface FuturesSignalResponse {
  items: FutureSignal[]
}

// ─── Explain endpoint types (espejo del schema Pydantic del backend) ───────────

export interface ExplainStep {
  key: string
  label_es: string
  /** Valor canónico raw: null → front aplica formatter; string → render verbatim */
  raw: number | string | boolean | null
  /** null → front formatea `raw` con formatters.ts; string → render verbatim */
  formatted: string | null
  /** Clave del glosario para mostrar ícono de ayuda; null → sin ícono */
  glossary_term?: string | null
}

export interface ExplainSection {
  key: string
  titulo: string
  steps: ExplainStep[]
  /** Caveat ilustrativo o "no reconstruible desde el snapshot" */
  note?: string | null
}

export interface SignalExplanation {
  sections: ExplainSection[]
}
