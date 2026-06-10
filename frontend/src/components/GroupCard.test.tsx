import { describe, it, expect } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import GroupCard from './GroupCard'
import type { StandingRow } from '../api/types'

const makeRow = (team_name: string, overrides: Partial<StandingRow> = {}): StandingRow => ({
  team_name,
  pj: 0, g: 0, e: 0, p: 0, gf: 0, gc: 0, dg: 0, pts: 0,
  ...overrides,
})

describe('GroupCard', () => {
  it('respeta el orden de standings tal-cual del servidor (sin reordenar)', () => {
    const standings = [
      makeRow('Colombia', { pj: 3, g: 2, pts: 6 }),
      makeRow('DR Congo', { pj: 3, g: 1, pts: 4 }),
      makeRow('Portugal', { pj: 3, g: 1, pts: 3 }),
      makeRow('Uzbekistan', { pj: 3, g: 0, pts: 1 }),
    ]
    render(<GroupCard name="Grupo K" standings={standings} />)

    const rows = screen.getAllByRole('row')
    // 4 filas de datos + 1 encabezado = 5
    expect(rows).toHaveLength(5)

    // Verifica orden exacto
    expect(within(rows[1]).getByText('Colombia')).toBeInTheDocument()
    expect(within(rows[2]).getByText('DR Congo')).toBeInTheDocument()
    expect(within(rows[3]).getByText('Portugal')).toBeInTheDocument()
    expect(within(rows[4]).getByText('Uzbekistan')).toBeInTheDocument()
  })

  it('muestra todas las columnas requeridas: Pos, Equipo, PJ, G, E, P, GF, GC, DG, Pts', () => {
    const standings = [makeRow('España')]
    render(<GroupCard name="Grupo A" standings={standings} />)

    expect(screen.getByText('Pos')).toBeInTheDocument()
    expect(screen.getByText('Equipo')).toBeInTheDocument()
    expect(screen.getByText('PJ')).toBeInTheDocument()
    expect(screen.getByText('G')).toBeInTheDocument()
    expect(screen.getByText('E')).toBeInTheDocument()
    expect(screen.getByText('P')).toBeInTheDocument()
    expect(screen.getByText('GF')).toBeInTheDocument()
    expect(screen.getByText('GC')).toBeInTheDocument()
    expect(screen.getByText('DG')).toBeInTheDocument()
    expect(screen.getByText('Pts')).toBeInTheDocument()
  })

  it('muestra todos ceros cuando el torneo no ha iniciado (pj=0 todos) sin crash', () => {
    const standings = [
      makeRow('Colombia'),
      makeRow('DR Congo'),
      makeRow('Portugal'),
      makeRow('Uzbekistan'),
    ]
    render(<GroupCard name="Grupo K" standings={standings} />)
    // 4 equipos con todos ceros — debe renderizar sin crash
    const rows = screen.getAllByRole('row')
    expect(rows).toHaveLength(5)
    // Todos los valores numéricos son 0
    const allCells = screen.getAllByRole('cell')
    const numericCells = allCells.filter((cell) => cell.textContent === '0')
    // Cada fila tiene 8 columnas numéricas (pj, g, e, p, gf, gc, dg, pts)
    expect(numericCells.length).toBeGreaterThanOrEqual(8)
  })
})
