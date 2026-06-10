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
