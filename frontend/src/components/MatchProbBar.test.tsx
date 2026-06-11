import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import MatchProbBar from './MatchProbBar'
import type { UpcomingMatch } from '../api/types'

const makeMatch = (overrides: Partial<UpcomingMatch> = {}): UpcomingMatch => ({
  id: 1,
  match_date: '2026-06-15',
  kickoff_at: null,
  home_team: 'España',
  away_team: 'Brasil',
  neutral_site: false,
  stage: 'group',
  p_home: 0.5,
  p_draw: 0.25,
  p_away: 0.25,
  low_confidence: false,
  ...overrides,
})

describe('MatchProbBar', () => {
  it('muestra las 3 barras de probabilidad cuando p_home/p_draw/p_away son números', () => {
    render(<MatchProbBar match={makeMatch({ p_home: 0.6, p_draw: 0.25, p_away: 0.15 })} />)
    expect(screen.getByText('60.0%')).toBeInTheDocument()
    expect(screen.getByText('25.0%')).toBeInTheDocument()
    expect(screen.getByText('15.0%')).toBeInTheDocument()
  })

  it('muestra el badge "⚠ datos limitados" cuando low_confidence=true', () => {
    render(<MatchProbBar match={makeMatch({ low_confidence: true })} />)
    expect(screen.getByText('⚠ datos limitados')).toBeInTheDocument()
  })

  it('NO muestra el badge cuando low_confidence=false', () => {
    render(<MatchProbBar match={makeMatch({ low_confidence: false })} />)
    expect(screen.queryByText('⚠ datos limitados')).not.toBeInTheDocument()
  })

  it('NO renderiza barras cuando p_home es null (partido sin predicciones)', () => {
    render(
      <MatchProbBar
        match={makeMatch({ p_home: null, p_draw: null, p_away: null })}
      />,
    )
    // Los porcentajes no deben aparecer
    expect(screen.queryByText(/\d+\.\d+%/)).not.toBeInTheDocument()
  })

  it('muestra los nombres de los equipos del partido en todo caso', () => {
    render(<MatchProbBar match={makeMatch({ p_home: null, p_draw: null, p_away: null })} />)
    // With FlagLabel, team names are in separate spans but still in the DOM
    const header = screen.getByTestId('match-header')
    expect(header).toHaveTextContent('España')
    expect(header).toHaveTextContent('Brasil')
  })
})
