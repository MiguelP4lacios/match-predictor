/**
 * TDD — AddToCuponButton
 * RED tests escritos ANTES de la implementación.
 *
 * Cubre: botón agrega leg al contexto desde SignalCard y desde MatchesPage.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CuponProvider, useCupon } from '../context/CuponContext'
import AddToCuponButton from './AddToCuponButton'
import type { CuponLeg } from '../context/CuponContext'

/** Inspector del contexto para verificar estado */
function Inspector() {
  const { legs } = useCupon()
  return (
    <span data-testid="legs" data-count={legs.length} data-legs={JSON.stringify(legs)}>
      {legs.length}
    </span>
  )
}

beforeEach(() => {
  sessionStorage.clear()
})

describe('AddToCuponButton — comportamiento base', () => {
  it('renderiza un botón con el texto "Agregar al cupón"', () => {
    render(
      <CuponProvider>
        <AddToCuponButton
          matchId={42}
          outcomeCode="HOME"
          homeTeam="Mexico"
          awayTeam="South Africa"
          matchDate="2026-06-11"
        />
      </CuponProvider>,
    )
    expect(screen.getByRole('button', { name: /agregar al cupón/i })).toBeInTheDocument()
  })

  it('agrega un leg al cupón al hacer click', () => {
    render(
      <CuponProvider>
        <Inspector />
        <AddToCuponButton
          matchId={42}
          outcomeCode="HOME"
          homeTeam="Mexico"
          awayTeam="South Africa"
          matchDate="2026-06-11"
        />
      </CuponProvider>,
    )
    expect(screen.getByTestId('legs')).toHaveTextContent('0')
    fireEvent.click(screen.getByRole('button', { name: /agregar al cupón/i }))
    expect(screen.getByTestId('legs')).toHaveTextContent('1')
  })

  it('el leg agregado tiene los datos del partido correctos', () => {
    render(
      <CuponProvider>
        <Inspector />
        <AddToCuponButton
          matchId={42}
          outcomeCode="HOME"
          homeTeam="Mexico"
          awayTeam="South Africa"
          matchDate="2026-06-11"
        />
      </CuponProvider>,
    )
    fireEvent.click(screen.getByRole('button', { name: /agregar al cupón/i }))
    const legs: CuponLeg[] = JSON.parse(screen.getByTestId('legs').dataset.legs!)
    expect(legs[0].match_id).toBe(42)
    expect(legs[0].outcome_code).toBe('HOME')
    expect(legs[0].home_team).toBe('Mexico')
    expect(legs[0].away_team).toBe('South Africa')
    expect(legs[0].match_date).toBe('2026-06-11')
    expect(legs[0].odds).toBeNull()
  })

  it('no agrega duplicado si ya existe el mismo leg', () => {
    render(
      <CuponProvider>
        <Inspector />
        <AddToCuponButton
          matchId={42}
          outcomeCode="HOME"
          homeTeam="Mexico"
          awayTeam="South Africa"
          matchDate="2026-06-11"
        />
      </CuponProvider>,
    )
    fireEvent.click(screen.getByRole('button', { name: /agregar al cupón/i }))
    fireEvent.click(screen.getByRole('button', { name: /agregar al cupón/i }))
    expect(screen.getByTestId('legs')).toHaveTextContent('1')
  })
})

describe('AddToCuponButton — soporte de distintos outcomes', () => {
  it('agrega leg HOME con los datos correctos', () => {
    render(
      <CuponProvider>
        <Inspector />
        <AddToCuponButton matchId={10} outcomeCode="HOME" homeTeam="Brazil" awayTeam="Argentina" matchDate="2026-06-20" />
      </CuponProvider>,
    )
    fireEvent.click(screen.getByRole('button'))
    const legs: CuponLeg[] = JSON.parse(screen.getByTestId('legs').dataset.legs!)
    expect(legs[0].outcome_code).toBe('HOME')
    expect(legs[0].match_id).toBe(10)
  })

  it('agrega leg AWAY con los datos correctos', () => {
    render(
      <CuponProvider>
        <Inspector />
        <AddToCuponButton matchId={20} outcomeCode="AWAY" homeTeam="France" awayTeam="Germany" matchDate="2026-06-22" />
      </CuponProvider>,
    )
    fireEvent.click(screen.getByRole('button'))
    const legs: CuponLeg[] = JSON.parse(screen.getByTestId('legs').dataset.legs!)
    expect(legs[0].outcome_code).toBe('AWAY')
    expect(legs[0].match_id).toBe(20)
  })
})

describe('AddToCuponButton — etiqueta del pick (fix UX: 3 botones idénticos)', () => {
  it('HOME muestra el equipo local, no "Agregar al cupón" genérico', () => {
    render(
      <CuponProvider>
        <AddToCuponButton matchId={1} outcomeCode="HOME" homeTeam="Mexico" awayTeam="South Africa" matchDate="2026-06-11" />
      </CuponProvider>,
    )
    expect(screen.getByRole('button')).toHaveTextContent('+ Mexico')
  })

  it('DRAW muestra "Empate"', () => {
    render(
      <CuponProvider>
        <AddToCuponButton matchId={1} outcomeCode="DRAW" homeTeam="Mexico" awayTeam="South Africa" matchDate="2026-06-11" />
      </CuponProvider>,
    )
    expect(screen.getByRole('button')).toHaveTextContent('+ Empate')
  })

  it('AWAY muestra el equipo visitante', () => {
    render(
      <CuponProvider>
        <AddToCuponButton matchId={1} outcomeCode="AWAY" homeTeam="Mexico" awayTeam="South Africa" matchDate="2026-06-11" />
      </CuponProvider>,
    )
    expect(screen.getByRole('button')).toHaveTextContent('+ South Africa')
  })

  it('los tres botones del mismo partido tienen textos DISTINTOS', () => {
    render(
      <CuponProvider>
        <AddToCuponButton matchId={1} outcomeCode="HOME" homeTeam="Mexico" awayTeam="South Africa" matchDate="2026-06-11" />
        <AddToCuponButton matchId={1} outcomeCode="DRAW" homeTeam="Mexico" awayTeam="South Africa" matchDate="2026-06-11" />
        <AddToCuponButton matchId={1} outcomeCode="AWAY" homeTeam="Mexico" awayTeam="South Africa" matchDate="2026-06-11" />
      </CuponProvider>,
    )
    const texts = screen.getAllByRole('button').map((b) => b.textContent)
    expect(new Set(texts).size).toBe(3)
  })
})
