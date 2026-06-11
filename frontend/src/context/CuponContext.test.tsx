/**
 * TDD — CuponContext
 * RED tests escritos ANTES de la implementación.
 *
 * Cubre: addLeg, removeLeg, clear, deduplicación, persistencia sessionStorage.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'
import { CuponProvider, useCupon } from './CuponContext'
import type { CuponLeg } from './CuponContext'

const LEG_A: Omit<CuponLeg, 'odds'> = {
  match_id: 42,
  outcome_code: 'HOME',
  home_team: 'Mexico',
  away_team: 'South Africa',
  match_date: '2026-06-11',
}

const LEG_B: Omit<CuponLeg, 'odds'> = {
  match_id: 99,
  outcome_code: 'AWAY',
  home_team: 'Brazil',
  away_team: 'Argentina',
  match_date: '2026-06-15',
}

/** Componente auxiliar que expone el estado del contexto como atributos data-* */
function Inspector() {
  const { legs } = useCupon()
  return <span data-testid="count" data-legs={JSON.stringify(legs)}>{legs.length}</span>
}

/** Componente auxiliar que llama addLeg al montar */
function Adder({ leg }: { leg: Omit<CuponLeg, 'odds'> }) {
  const { addLeg } = useCupon()
  return (
    <button data-testid="add" onClick={() => addLeg(leg)}>
      add
    </button>
  )
}

/** Componente auxiliar que llama removeLeg */
function Remover({ matchId, outcomeCode }: { matchId: number; outcomeCode: string }) {
  const { removeLeg } = useCupon()
  return (
    <button data-testid="remove" onClick={() => removeLeg(matchId, outcomeCode)}>
      remove
    </button>
  )
}

/** Componente auxiliar que llama clear */
function Clearer() {
  const { clear } = useCupon()
  return (
    <button data-testid="clear" onClick={() => clear()}>
      clear
    </button>
  )
}

function wrapper(...elements: React.ReactElement[]) {
  return (
    <CuponProvider>
      <Inspector />
      {elements}
    </CuponProvider>
  )
}

beforeEach(() => {
  sessionStorage.clear()
})

describe('CuponContext — addLeg', () => {
  it('addLeg incrementa el conteo de legs', () => {
    render(wrapper(<Adder leg={LEG_A} />))
    expect(screen.getByTestId('count')).toHaveTextContent('0')
    fireEvent.click(screen.getByTestId('add'))
    expect(screen.getByTestId('count')).toHaveTextContent('1')
  })

  it('addLeg agrega el leg con odds null por defecto', () => {
    render(wrapper(<Adder leg={LEG_A} />))
    fireEvent.click(screen.getByTestId('add'))
    const legs: CuponLeg[] = JSON.parse(screen.getByTestId('count').dataset.legs!)
    expect(legs[0].match_id).toBe(42)
    expect(legs[0].outcome_code).toBe('HOME')
    expect(legs[0].odds).toBeNull()
  })

  it('addLeg NO agrega duplicado con mismo match_id + outcome_code', () => {
    render(wrapper(<Adder leg={LEG_A} />))
    fireEvent.click(screen.getByTestId('add'))
    fireEvent.click(screen.getByTestId('add'))
    expect(screen.getByTestId('count')).toHaveTextContent('1')
  })

  it('addLeg SÍ agrega el mismo match_id con distinto outcome_code', () => {
    const LEG_A_DRAW: Omit<CuponLeg, 'odds'> = { ...LEG_A, outcome_code: 'DRAW' }
    const { rerender } = render(wrapper(<Adder leg={LEG_A} />))
    fireEvent.click(screen.getByTestId('add'))
    rerender(wrapper(<Adder leg={LEG_A_DRAW} />))
    fireEvent.click(screen.getByTestId('add'))
    expect(screen.getByTestId('count')).toHaveTextContent('2')
  })
})

describe('CuponContext — removeLeg', () => {
  it('removeLeg elimina el leg correspondiente', () => {
    render(wrapper(<Adder leg={LEG_A} />, <Remover matchId={42} outcomeCode="HOME" />))
    fireEvent.click(screen.getByTestId('add'))
    expect(screen.getByTestId('count')).toHaveTextContent('1')
    fireEvent.click(screen.getByTestId('remove'))
    expect(screen.getByTestId('count')).toHaveTextContent('0')
  })

  it('removeLeg no afecta otras legs', () => {
    render(wrapper(<Adder leg={LEG_A} />, <Remover matchId={42} outcomeCode="DRAW" />))
    fireEvent.click(screen.getByTestId('add'))
    fireEvent.click(screen.getByTestId('remove')) // intenta borrar distinto outcome_code
    expect(screen.getByTestId('count')).toHaveTextContent('1')
  })
})

describe('CuponContext — clear', () => {
  it('clear vacía todos los legs', () => {
    render(wrapper(<Adder leg={LEG_A} />, <Adder leg={LEG_B} />, <Clearer />))
    // Aquí los dos adders son instancias distintas → no son duplicados (match_ids distintos)
    const [addA, addB] = screen.getAllByTestId('add')
    fireEvent.click(addA)
    fireEvent.click(addB)
    expect(screen.getByTestId('count')).toHaveTextContent('2')
    fireEvent.click(screen.getByTestId('clear'))
    expect(screen.getByTestId('count')).toHaveTextContent('0')
  })
})

describe('CuponContext — sessionStorage', () => {
  it('persiste los legs en sessionStorage al agregar', () => {
    render(wrapper(<Adder leg={LEG_A} />))
    fireEvent.click(screen.getByTestId('add'))
    const stored = sessionStorage.getItem('cupon_legs')
    expect(stored).not.toBeNull()
    const parsed: CuponLeg[] = JSON.parse(stored!)
    expect(parsed).toHaveLength(1)
    expect(parsed[0].match_id).toBe(42)
  })

  it('carga los legs desde sessionStorage al montar', () => {
    const existingLegs: CuponLeg[] = [{ ...LEG_A, odds: 1.85 }]
    sessionStorage.setItem('cupon_legs', JSON.stringify(existingLegs))
    render(
      <CuponProvider>
        <Inspector />
      </CuponProvider>,
    )
    expect(screen.getByTestId('count')).toHaveTextContent('1')
    const legs: CuponLeg[] = JSON.parse(screen.getByTestId('count').dataset.legs!)
    expect(legs[0].odds).toBe(1.85)
  })

  it('persiste después de clear (guarda array vacío)', () => {
    render(wrapper(<Adder leg={LEG_A} />, <Clearer />))
    fireEvent.click(screen.getByTestId('add'))
    fireEvent.click(screen.getByTestId('clear'))
    const stored = sessionStorage.getItem('cupon_legs')
    expect(stored).not.toBeNull()
    expect(JSON.parse(stored!)).toHaveLength(0)
  })
})
