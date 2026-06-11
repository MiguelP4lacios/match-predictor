/**
 * Integration tests — Routing
 * MemoryRouter + AppRoutes → 404 "Página no encontrada"
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppRoutes } from '../App'

// Las páginas hacen useQuery; mock fetchAPI para no causar errores de red
vi.mock('../api/client', () => ({
  fetchAPI: vi.fn().mockResolvedValue({ items: [], total: 0 }),
}))

function renderAtPath(path: string) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Router', () => {
  it('muestra "Página no encontrada" para rutas desconocidas', () => {
    renderAtPath('/ruta-inexistente')
    expect(screen.getByText('Página no encontrada')).toBeInTheDocument()
  })

  it('renderiza la barra de navegación con los 5 links', () => {
    renderAtPath('/')
    expect(screen.getByRole('link', { name: 'Señales' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Grupos' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Partidos' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Modelo' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Apuestas' })).toBeInTheDocument()
  })

  it('/paper redirige a /apuestas', () => {
    renderAtPath('/paper')
    // La redirección navega a /apuestas — BetsPage debe renderizarse (tiene h1 "Apuestas")
    expect(screen.getByRole('heading', { name: /apuestas/i })).toBeInTheDocument()
  })
})
