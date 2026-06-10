/**
 * Integration tests — PaperPage
 * QueryClient wrapper + mocked fetchAPI → ROI null → "—", positivo formateado
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import PaperPage from './PaperPage'

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

describe('PaperPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('muestra "—" para ROI null (sin apuestas cerradas)', async () => {
    mockFetchAPI.mockResolvedValue({ total: 3, open: 3, settled: 0, roi: null })

    renderWithQuery(<PaperPage />)

    await waitFor(() => {
      expect(screen.getByText('—')).toBeInTheDocument()
    })
    // Verifica que formatROI(null) NO devuelve "0%" ni "0.0%"
    expect(screen.queryByText('0%')).not.toBeInTheDocument()
    expect(screen.queryByText('0.0%')).not.toBeInTheDocument()
  })

  it('muestra ROI positivo con signo + y %', async () => {
    mockFetchAPI.mockResolvedValue({ total: 10, open: 2, settled: 8, roi: 0.125 })

    renderWithQuery(<PaperPage />)

    await waitFor(() => {
      expect(screen.getByText('+12.5%')).toBeInTheDocument()
    })
  })
})
