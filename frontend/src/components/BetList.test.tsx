/**
 * Tests para BetList — TDD RED antes de implementar.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import BetList from './BetList'
import type { BetItem } from '../api/types'

vi.mock('../api/client', () => ({
  fetchAPI: vi.fn(),
}))

import { fetchAPI } from '../api/client'
const mockFetchAPI = vi.mocked(fetchAPI)

const makeBet = (overrides: Partial<BetItem> = {}): BetItem => ({
  id: 1,
  mode: 'real',
  status: 'pending',
  match_id: 42,
  outcome_code: 'HOME',
  odds_taken: 1.85,
  stake: '12000',
  pnl: null,
  settled_result: null,
  settled_at: null,
  placed_at: '2026-06-15T10:00:00',
  note: null,
  value_signal_id: null,
  ...overrides,
})

function renderList(bets: BetItem[] = [], onRefresh = vi.fn()) {
  return render(
    <MemoryRouter>
      <BetList bets={bets} onRefresh={onRefresh} />
    </MemoryRouter>,
  )
}

describe('BetList (4.6)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('muestra mensaje cuando no hay apuestas', () => {
    renderList([])
    expect(screen.getByText(/no hay apuestas/i)).toBeInTheDocument()
  })

  it('muestra cuota y stake de cada apuesta', () => {
    renderList([makeBet()])
    expect(screen.getByText('1.85')).toBeInTheDocument()
    expect(screen.getByText(/12\.000/)).toBeInTheDocument()
  })

  it('badge PENDING aparece en gris para apuesta pendiente', () => {
    renderList([makeBet({ status: 'pending' })])
    expect(screen.getByText('PENDIENTE')).toBeInTheDocument()
  })

  it('badge WON aparece en verde para apuesta ganada', () => {
    renderList([makeBet({ status: 'won', pnl: '4800' })])
    expect(screen.getByText('GANADA')).toBeInTheDocument()
  })

  it('badge LOST aparece en rojo para apuesta perdida', () => {
    renderList([makeBet({ status: 'lost', pnl: '-12000' })])
    expect(screen.getByText('PERDIDA')).toBeInTheDocument()
  })

  it('botón Eliminar solo visible para REAL PENDING', () => {
    const bets = [
      makeBet({ id: 1, mode: 'real', status: 'pending' }),
      makeBet({ id: 2, mode: 'real', status: 'won', pnl: '4800' }),
      makeBet({ id: 3, mode: 'paper', status: 'pending' }),
    ]
    renderList(bets)

    const deleteButtons = screen.queryAllByRole('button', { name: /eliminar/i })
    // Solo id=1 es REAL PENDING
    expect(deleteButtons).toHaveLength(1)
  })

  it('DELETE /api/v1/bets/{id} llamado al confirmar eliminar (REAL PENDING)', async () => {
    mockFetchAPI.mockResolvedValueOnce(null as never)
    const onRefresh = vi.fn()

    // Simular window.confirm retornando true
    vi.stubGlobal('confirm', () => true)

    renderList([makeBet({ id: 5, mode: 'real', status: 'pending' })], onRefresh)

    fireEvent.click(screen.getByRole('button', { name: /eliminar/i }))

    await waitFor(() => {
      expect(mockFetchAPI).toHaveBeenCalledWith(
        '/v1/bets/5',
        expect.objectContaining({ method: 'DELETE' }),
      )
    })

    vi.unstubAllGlobals()
  })

  it('pnl positivo formateado con +$ para apuesta WON', () => {
    renderList([makeBet({ status: 'won', pnl: '4800' })])
    expect(screen.getByText(/\+\$4\.800/)).toBeInTheDocument()
  })

  it('pnl negativo formateado con −$ para apuesta LOST', () => {
    renderList([makeBet({ status: 'lost', pnl: '-12000' })])
    // Unicode minus −
    expect(screen.getByText(/−\$12\.000/)).toBeInTheDocument()
  })
})
