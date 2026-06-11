/**
 * TDD — AppShell
 * RED tests escritos ANTES de la implementación.
 * Cubre: ambos navs en DOM con links correctos, StatusBadge en header.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AppShell } from './AppShell'
import { ThemeProvider } from '../context/ThemeContext'
import { CuponProvider } from '../context/CuponContext'

// Mock StatusBadge y ThemeToggle para no depender del endpoint de salud
vi.mock('./StatusBadge', () => ({
  StatusBadge: () => <span data-testid="status-badge-mock">🟢</span>,
}))
vi.mock('./ThemeToggle', () => ({
  ThemeToggle: () => <button data-testid="theme-toggle-mock">🌙</button>,
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

beforeEach(() => {
  localStorage.clear()
  document.documentElement.classList.remove('dark')
  mockMatchMedia()
})

function renderShell() {
  return render(
    <ThemeProvider>
      <CuponProvider>
        <MemoryRouter>
          <AppShell>
            <div data-testid="page-content">Contenido</div>
          </AppShell>
        </MemoryRouter>
      </CuponProvider>
    </ThemeProvider>,
  )
}

describe('AppShell — estructura', () => {
  it('renderiza el contenido hijo', () => {
    renderShell()
    expect(screen.getByTestId('page-content')).toBeInTheDocument()
  })

  it('renderiza el wordmark WC26 en el header', () => {
    renderShell()
    expect(screen.getByText(/WC.?26/i)).toBeInTheDocument()
  })

  it('renderiza StatusBadge en el header', () => {
    renderShell()
    expect(screen.getByTestId('status-badge-mock')).toBeInTheDocument()
  })

  it('renderiza ThemeToggle en el header', () => {
    renderShell()
    expect(screen.getByTestId('theme-toggle-mock')).toBeInTheDocument()
  })
})

describe('AppShell — navegación', () => {
  const NAV_LABELS = ['Señales', 'Grupos', 'Partidos', 'Modelo', 'Apuestas', 'Estado']

  it('el nav-top contiene todos los links de navegación', () => {
    renderShell()
    const topNav = screen.getByTestId('nav-top')
    NAV_LABELS.forEach((label) => {
      expect(topNav).toHaveTextContent(label)
    })
  })

  it('el nav-bottom contiene todos los links de navegación', () => {
    renderShell()
    const bottomNav = screen.getByTestId('nav-bottom')
    NAV_LABELS.forEach((label) => {
      expect(bottomNav).toHaveTextContent(label)
    })
  })
})
