/**
 * Integration tests — ModelPage
 * QueryClient wrapper + mocked fetchAPI → Brier, semáforo beats_baselines
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ModelPage from './ModelPage'

vi.mock('../api/client', () => ({
  fetchAPI: vi.fn(),
}))

import { fetchAPI } from '../api/client'
const mockFetchAPI = vi.mocked(fetchAPI)

function renderWithQuery(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

const MODEL_FIXTURE = {
  name: 'Dixon-Coles',
  params_summary: { alpha: 1.2, beta: 0.8 },
  calibration: null,
  backtest: {
    brier: 0.21,
    logloss: 0.89,
    beats_baselines: true,
    baselines: { random: 0.33, uniform: 0.25 },
    eval_n: 1200,
    eval_window: '2018-2026',
    calibration_table: [],
  },
}

describe('ModelPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('muestra el Brier score del modelo', async () => {
    mockFetchAPI.mockResolvedValue(MODEL_FIXTURE)

    renderWithQuery(<ModelPage />)

    await waitFor(() => {
      expect(screen.getByText('0.2100')).toBeInTheDocument()
    })
  })

  it('muestra semáforo verde cuando beats_baselines=true', async () => {
    mockFetchAPI.mockResolvedValue(MODEL_FIXTURE)

    renderWithQuery(<ModelPage />)

    await waitFor(() => {
      expect(screen.getByText('✅ Supera baselines')).toBeInTheDocument()
    })
  })

  it('muestra semáforo rojo cuando beats_baselines=false', async () => {
    mockFetchAPI.mockResolvedValue({
      ...MODEL_FIXTURE,
      backtest: { ...MODEL_FIXTURE.backtest, beats_baselines: false },
    })

    renderWithQuery(<ModelPage />)

    await waitFor(() => {
      expect(screen.getByText('❌ No supera baselines')).toBeInTheDocument()
    })
  })
})
