/**
 * Integration tests — GroupsPage
 * QueryClient wrapper + mocked fetchAPI → 12 grupos del WC2026
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import GroupsPage from './GroupsPage'

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

const makeGroup = (name: string) => ({
  name,
  teams: ['Team A', 'Team B', 'Team C', 'Team D'],
  standings: [],
})

const WC2026_GROUPS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'].map(
  (l) => makeGroup(`Grupo ${l}`),
)

describe('GroupsPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renderiza los 12 grupos cuando la query resuelve', async () => {
    mockFetchAPI.mockResolvedValue(WC2026_GROUPS)

    renderWithQuery(<GroupsPage />)

    await waitFor(() => {
      expect(screen.getByText('Grupo A')).toBeInTheDocument()
    })
    // Primer y último grupo
    expect(screen.getByText('Grupo L')).toBeInTheDocument()
    // Exactamente 12 encabezados de grupo
    const headers = screen.getAllByText(/^Grupo [A-L]$/)
    expect(headers).toHaveLength(12)
  })

  it('muestra ErrorBanner cuando falla la carga', async () => {
    mockFetchAPI.mockRejectedValue(new Error('500'))

    renderWithQuery(<GroupsPage />)

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })
})
