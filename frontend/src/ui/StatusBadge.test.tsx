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

import type { HealthFull } from '../api/health'

/** StatusBadge solo lee `overall`; el resto cumple el contrato anidado real. */
function health(overall: HealthFull['overall']): HealthFull {
  return {
    overall,
    odds_capture: { last_at: '2026-06-11T07:00:00', age_hours: 2, verdict: 'ok' },
    odds_credits: { remaining: 200, verdict: 'ok' },
    model: { name: '1x2-olm-v1', verdict: 'ok' },
    results: { latest_date: '2026-06-09', verdict: 'ok' },
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('StatusBadge — veredictos', () => {
  it('muestra 🟢 cuando overall=ok', async () => {
    mockGetHealthFull.mockResolvedValue(health('ok'))
    render(<StatusBadge />)
    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent('🟢')
    })
  })

  it('muestra 🟡 cuando overall=warn', async () => {
    mockGetHealthFull.mockResolvedValue(health('warn'))
    render(<StatusBadge />)
    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent('🟡')
    })
  })

  it('muestra 🔴 cuando overall=stale', async () => {
    mockGetHealthFull.mockResolvedValue(health('stale'))
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
