/**
 * TDD — StatusBadge
 * RED tests escritos ANTES de la implementación.
 * Cubre: veredicto ok/warn/stale/error via getHealthFull mockeado.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { StatusBadge } from './StatusBadge'

vi.mock('../api/health', () => ({
  getHealthFull: vi.fn(),
}))

import { getHealthFull } from '../api/health'
const mockGetHealthFull = vi.mocked(getHealthFull)

beforeEach(() => {
  vi.clearAllMocks()
})

describe('StatusBadge — veredictos', () => {
  it('muestra 🟢 cuando overall=ok', async () => {
    mockGetHealthFull.mockResolvedValue({
      overall: 'ok',
      last_odds_capture: { value: '2h', verdict: 'ok', threshold: '<6h' },
      odds_age: { value: '2h', verdict: 'ok', threshold: '<6h' },
      credits_remaining: { value: 200, verdict: 'ok', threshold: '>50' },
      model_version: { value: 'v1', verdict: 'ok', threshold: 'exists' },
      last_finished: { value: '2026-06-10', verdict: 'ok', threshold: 'info' },
    })
    render(<StatusBadge />)
    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent('🟢')
    })
  })

  it('muestra 🟡 cuando overall=warn', async () => {
    mockGetHealthFull.mockResolvedValue({
      overall: 'warn',
      last_odds_capture: { value: '8h', verdict: 'warn', threshold: '<24h' },
      odds_age: { value: '8h', verdict: 'warn', threshold: '<24h' },
      credits_remaining: { value: 80, verdict: 'ok', threshold: '>50' },
      model_version: { value: 'v1', verdict: 'ok', threshold: 'exists' },
      last_finished: { value: '2026-06-10', verdict: 'ok', threshold: 'info' },
    })
    render(<StatusBadge />)
    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent('🟡')
    })
  })

  it('muestra 🔴 cuando overall=stale', async () => {
    mockGetHealthFull.mockResolvedValue({
      overall: 'stale',
      last_odds_capture: { value: '30h', verdict: 'stale', threshold: '≥24h' },
      odds_age: { value: '30h', verdict: 'stale', threshold: '≥24h' },
      credits_remaining: { value: 5, verdict: 'stale', threshold: '≤10' },
      model_version: { value: null, verdict: 'stale', threshold: 'exists' },
      last_finished: { value: '2026-06-08', verdict: 'ok', threshold: 'info' },
    })
    render(<StatusBadge />)
    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent('🔴')
    })
  })

  it('muestra 🔴 cuando getHealthFull lanza error', async () => {
    mockGetHealthFull.mockRejectedValue(new Error('Network error'))
    render(<StatusBadge />)
    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent('🔴')
    })
  })
})
