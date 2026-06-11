/**
 * Integration tests — Routing
 * MemoryRouter + AppRoutes → 404 "Página no encontrada"
 * Actualizado en Phase 3 (centro-de-control): AppShell requiere ThemeProvider
 * y CuponProvider; StatusBadge se mockea para evitar fetch de /health/full.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppRoutes } from '../App'
import { ThemeProvider } from '../context/ThemeContext'
import { CuponProvider } from '../context/CuponContext'

// Las páginas hacen useQuery; mock fetchAPI para no causar errores de red
vi.mock('../api/client', () => ({
  fetchAPI: vi.fn().mockResolvedValue({ items: [], total: 0 }),
}))

// StatusBadge hace poll a /health/full — mock para tests de routing
vi.mock('../ui/StatusBadge', () => ({
  StatusBadge: () => <span data-testid="status-badge-mock">🟢</span>,
}))

function mockMatchMedia() {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((q: string) => ({
      matches: false,
      media: q,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
    })),
  })
}

function renderAtPath(path: string) {
  mockMatchMedia()
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <ThemeProvider>
        <CuponProvider>
          <MemoryRouter initialEntries={[path]}>
            <AppRoutes />
          </MemoryRouter>
        </CuponProvider>
      </ThemeProvider>
    </QueryClientProvider>,
  )
}

describe('Router', () => {
  it('muestra "Página no encontrada" para rutas desconocidas', () => {
    renderAtPath('/ruta-inexistente')
    expect(screen.getByText('Página no encontrada')).toBeInTheDocument()
  })

  it('renderiza la barra de navegación con los 7 links (incluyendo Futuros y Estado)', () => {
    renderAtPath('/')
    // Nav top y nav bottom tienen los links — getByRole puede devolver múltiples
    const topNav = screen.getByTestId('nav-top')
    expect(topNav).toHaveTextContent('Señales')
    expect(topNav).toHaveTextContent('Grupos')
    expect(topNav).toHaveTextContent('Partidos')
    expect(topNav).toHaveTextContent('Modelo')
    expect(topNav).toHaveTextContent('Apuestas')
    expect(topNav).toHaveTextContent('Futuros')
    expect(topNav).toHaveTextContent('Estado')
  })

  it('/futures renderiza FuturesDashboard (h1 "Futuros WC2026")', async () => {
    renderAtPath('/futures')
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /futuros wc2026/i })).toBeInTheDocument()
    })
  })

  it('/paper redirige a /apuestas', () => {
    renderAtPath('/paper')
    // La redirección navega a /apuestas — BetsPage debe renderizarse (tiene h1 "Apuestas")
    expect(screen.getByRole('heading', { name: /apuestas/i })).toBeInTheDocument()
  })
})
