/**
 * TDD — EstadoPage. Forma anidada REAL del backend (fix C1 del verify).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import EstadoPage from './EstadoPage'
import type { HealthFull } from '../api/health'

vi.mock('../api/health', () => ({
  getHealthFull: vi.fn(),
}))

import { getHealthFull } from '../api/health'
const mockGetHealthFull = vi.mocked(getHealthFull)

function renderEstado() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <EstadoPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const HEALTH_ALL_OK: HealthFull = {
  overall: 'ok',
  odds_capture: { last_at: '2026-06-11T07:00:00', age_hours: 2, verdict: 'ok' },
  odds_credits: { remaining: 486, verdict: 'ok' },
  model: { name: '1x2-olm-v1', verdict: 'ok' },
  results: { latest_date: '2026-06-09', verdict: 'ok' },
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

  it('muestra el label de créditos (español hincha) y su valor', async () => {
    mockGetHealthFull.mockResolvedValue(HEALTH_ALL_OK)
    renderEstado()
    await waitFor(() => {
      expect(screen.getByText(/créditos/i)).toBeInTheDocument()
    })
    expect(screen.getByText('486 / 500')).toBeInTheDocument()
  })

  it('muestra la versión del modelo', async () => {
    mockGetHealthFull.mockResolvedValue(HEALTH_ALL_OK)
    renderEstado()
    await waitFor(() => {
      expect(screen.getByText('1x2-olm-v1')).toBeInTheDocument()
    })
  })

  it('muestra la antigüedad de la captura como tiempo relativo', async () => {
    mockGetHealthFull.mockResolvedValue(HEALTH_ALL_OK)
    renderEstado()
    await waitFor(() => {
      expect(screen.getByText('hace 2h')).toBeInTheDocument()
    })
  })
})

describe('EstadoPage — veredictos coloreados', () => {
  it('muestra "Al día" cuando overall es ok', async () => {
    mockGetHealthFull.mockResolvedValue(HEALTH_ALL_OK)
    renderEstado()
    await waitFor(() => {
      expect(screen.getAllByText(/al día/i).length).toBeGreaterThan(0)
    })
  })

  it('muestra "Desactualizado" cuando la captura está stale', async () => {
    mockGetHealthFull.mockResolvedValue({
      ...HEALTH_ALL_OK,
      odds_capture: { last_at: null, age_hours: null, verdict: 'stale' },
      overall: 'stale',
    })
    renderEstado()
    await waitFor(() => {
      expect(screen.getAllByText(/desactualizado/i).length).toBeGreaterThan(0)
    })
  })
})

describe('EstadoPage — carga y error', () => {
  it('muestra indicador de carga inicialmente', () => {
    mockGetHealthFull.mockReturnValue(new Promise(() => {}))
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
