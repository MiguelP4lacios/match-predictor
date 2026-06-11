import { describe, it, expect } from 'vitest'
import { render, screen, within, fireEvent } from '@testing-library/react'
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
    // Cada fila tiene columnas numéricas (pj, g, e, p, gf, gc, dg, pts)
    expect(numericCells.length).toBeGreaterThanOrEqual(8)
  })

  it('NO tiene overflow-x-auto ni overflow-x-scroll (fix de scroll lateral)', () => {
    const { container } = render(<GroupCard name="Grupo K" standings={[makeRow('España')]} />)
    expect(container.innerHTML).not.toContain('overflow-x-auto')
    expect(container.innerHTML).not.toContain('overflow-x-scroll')
  })

  it('tap en fila revela detalles expandidos (G/E/P/GF/GC) para esa fila', () => {
    const standings = [makeRow('Colombia', { g: 2, e: 1, p: 0, gf: 5, gc: 2 })]
    render(<GroupCard name="Grupo A" standings={standings} />)

    // Inicialmente no hay fila expandida
    expect(screen.queryByTestId('expanded-0')).not.toBeInTheDocument()

    // Click en la primera fila de datos
    const rows = screen.getAllByRole('row')
    fireEvent.click(rows[1])

    // Ahora aparece la fila expandida con los datos de detalle
    expect(screen.getByTestId('expanded-0')).toBeInTheDocument()
  })

  it('segundo click en la misma fila colapsa el detalle', () => {
    const standings = [makeRow('Colombia', { g: 2 })]
    render(<GroupCard name="Grupo A" standings={standings} />)

    const rows = screen.getAllByRole('row')
    fireEvent.click(rows[1])
    expect(screen.getByTestId('expanded-0')).toBeInTheDocument()

    // Segundo click colapsa
    fireEvent.click(rows[1])
    expect(screen.queryByTestId('expanded-0')).not.toBeInTheDocument()
  })

  it('solo una fila expandida a la vez — tap en otra colapsa la anterior', () => {
    const standings = [
      makeRow('Colombia', { g: 2 }),
      makeRow('DR Congo', { g: 1 }),
    ]
    render(<GroupCard name="Grupo K" standings={standings} />)

    const rows = screen.getAllByRole('row')
    // Expandir fila 0
    fireEvent.click(rows[1])
    expect(screen.getByTestId('expanded-0')).toBeInTheDocument()
    expect(screen.queryByTestId('expanded-1')).not.toBeInTheDocument()

    // Tap en fila 1 colapsa la 0 y expande la 1
    fireEvent.click(rows[2])
    expect(screen.queryByTestId('expanded-0')).not.toBeInTheDocument()
    expect(screen.getByTestId('expanded-1')).toBeInTheDocument()
  })

  it('top-2 filas tienen atributo data-qualify="true" (zona de clasificación)', () => {
    const standings = [
      makeRow('Colombia', { pts: 9 }),
      makeRow('DR Congo', { pts: 6 }),
      makeRow('Portugal', { pts: 3 }),
      makeRow('Uzbekistan', { pts: 0 }),
    ]
    render(<GroupCard name="Grupo K" standings={standings} />)

    const rows = screen.getAllByRole('row')
    // rows[0] es header, rows[1-4] son datos
    expect(rows[1]).toHaveAttribute('data-qualify', 'true')
    expect(rows[2]).toHaveAttribute('data-qualify', 'true')
    expect(rows[3]).not.toHaveAttribute('data-qualify')
    expect(rows[4]).not.toHaveAttribute('data-qualify')
  })

  it('muestra FlagLabel con bandera para cada equipo', () => {
    render(<GroupCard name="Grupo A" standings={[makeRow('Mexico')]} />)
    // nameToFlag('Mexico') = '🇲🇽'
    expect(screen.getByText('🇲🇽')).toBeInTheDocument()
    expect(screen.getByText('Mexico')).toBeInTheDocument()
  })
})
