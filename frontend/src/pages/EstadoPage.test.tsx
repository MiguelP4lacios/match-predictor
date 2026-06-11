/**
 * TDD — EstadoPage
 * RED tests escritos ANTES de la implementación.
 * Cubre: render métricas, tiempo relativo, veredicto coloreado.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import EstadoPage from './EstadoPage'

vi.mock('../api/health', () => ({
  getHealthFull: vi.fn(),
}))

import { getHealthFull } from '../api/health'
const mockGetHealthFull = vi.mocked(getHealthFull)

function renderEstado() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <EstadoPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const HEALTH_ALL_OK = {
  overall: 'ok' as const,
  last_odds_capture: { value: '2026-06-11T04:00:00Z', verdict: 'ok' as const, threshold: '<6h' },
  odds_age: { value: '2026-06-11T04:00:00Z', verdict: 'ok' as const, threshold: '<6h' },
  credits_remaining: { value: 200, verdict: 'ok' as const, threshold: '>50' },
  model_version: { value: 'dixon-coles-v1', verdict: 'ok' as const, threshold: 'exists' },
  last_finished: { value: '2026-06-10', verdict: 'ok' as const, threshold: 'info' },
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('EstadoPage — render métricas', () => {
  it('muestra el título de la página', async () => {
    mockGetHealthFull.mockResolvedValue(HEALTH_ALL_OK)
    renderEstado()
    await waitFor(() => {
      expect(screen.getByText(/estado del sistema/i)).toBeInTheDocument()
    })
  })

  it('muestra el label de créditos restantes (español hincha)', async () => {
    mockGetHealthFull.mockResolvedValue(HEALTH_ALL_OK)
    renderEstado()
    await waitFor(() => {
      expect(screen.getByText(/créditos/i)).toBeInTheDocument()
    })
  })

  it('muestra el valor de créditos restantes', async () => {
    mockGetHealthFull.mockResolvedValue(HEALTH_ALL_OK)
    renderEstado()
    await waitFor(() => {
      expect(screen.getByText('200')).toBeInTheDocument()
    })
  })

  it('muestra la versión del modelo', async () => {
    mockGetHealthFull.mockResolvedValue(HEALTH_ALL_OK)
    renderEstado()
    await waitFor(() => {
      expect(screen.getByText('dixon-coles-v1')).toBeInTheDocument()
    })
  })
})

describe('EstadoPage — veredictos coloreados', () => {
  it('muestra badge ok cuando el overall es ok', async () => {
    mockGetHealthFull.mockResolvedValue(HEALTH_ALL_OK)
    renderEstado()
    await waitFor(() => {
      expect(screen.getAllByText(/ok/i).length).toBeGreaterThan(0)
    })
  })

  it('muestra badge stale cuando credits son stale', async () => {
    mockGetHealthFull.mockResolvedValue({
      ...HEALTH_ALL_OK,
      credits_remaining: { value: 5, verdict: 'stale' as const, threshold: '≤10' },
      overall: 'stale' as const,
    })
    renderEstado()
    await waitFor(() => {
      // badge con texto 'stale' visible en la página
      const badges = screen.getAllByText(/stale/i)
      expect(badges.length).toBeGreaterThan(0)
    })
  })
})

describe('EstadoPage — estado de carga y error', () => {
  it('muestra indicador de carga inicialmente', () => {
    mockGetHealthFull.mockReturnValue(new Promise(() => {})) // never resolves
    renderEstado()
    expect(screen.getByRole('status', { name: /cargando/i })).toBeInTheDocument()
  })

  it('muestra error cuando getHealthFull falla', async () => {
    mockGetHealthFull.mockRejectedValue(new Error('Error de red'))
    renderEstado()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })
})
