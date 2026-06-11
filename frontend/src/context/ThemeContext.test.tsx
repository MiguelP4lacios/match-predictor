/**
 * TDD — ThemeContext
 * RED tests escritos ANTES de la implementación.
 * Cubre: resolución system, toggle, persistencia localStorage.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import type { ReactNode } from 'react'
import { ThemeProvider, useTheme } from './ThemeContext'

function Inspector() {
  const { theme, resolved } = useTheme()
  return (
    <div>
      <span data-testid="pref">{theme}</span>
      <span data-testid="resolved">{resolved}</span>
    </div>
  )
}

function Toggler({ target }: { target: 'light' | 'dark' | 'system' }) {
  const { setTheme } = useTheme()
  return (
    <button data-testid="toggle" onClick={() => setTheme(target)}>
      toggle
    </button>
  )
}

function Wrapper({ children }: { children?: ReactNode }) {
  return (
    <ThemeProvider>
      <Inspector />
      {children}
    </ThemeProvider>
  )
}

function mockMatchMedia(prefersDark: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((q: string) => ({
      matches: prefersDark && q === '(prefers-color-scheme: dark)',
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
  mockMatchMedia(false)
})

describe('ThemeContext — system default', () => {
  it('resolved=light cuando el sistema prefiere light', () => {
    render(<Wrapper />)
    expect(screen.getByTestId('resolved')).toHaveTextContent('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('resolved=dark cuando el sistema prefiere dark', () => {
    mockMatchMedia(true)
    render(<Wrapper />)
    expect(screen.getByTestId('resolved')).toHaveTextContent('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })
})

describe('ThemeContext — setTheme', () => {
  it('setTheme(dark) overrides la preferencia system', () => {
    render(
      <Wrapper>
        <Toggler target="dark" />
      </Wrapper>,
    )
    expect(screen.getByTestId('resolved')).toHaveTextContent('light')
    fireEvent.click(screen.getByTestId('toggle'))
    expect(screen.getByTestId('resolved')).toHaveTextContent('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('setTheme(light) fuerza light aunque matchMedia prefiera dark', () => {
    mockMatchMedia(true)
    render(
      <ThemeProvider>
        <Inspector />
        <Toggler target="light" />
      </ThemeProvider>,
    )
    expect(screen.getByTestId('resolved')).toHaveTextContent('dark')
    fireEvent.click(screen.getByTestId('toggle'))
    expect(screen.getByTestId('resolved')).toHaveTextContent('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('setTheme persiste en localStorage', () => {
    render(
      <Wrapper>
        <Toggler target="dark" />
      </Wrapper>,
    )
    fireEvent.click(screen.getByTestId('toggle'))
    expect(localStorage.getItem('theme')).toBe('dark')
  })
})

describe('ThemeContext — persistencia desde localStorage', () => {
  it('carga dark desde localStorage al montar', () => {
    localStorage.setItem('theme', 'dark')
    render(<Wrapper />)
    expect(screen.getByTestId('pref')).toHaveTextContent('dark')
    expect(screen.getByTestId('resolved')).toHaveTextContent('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('carga light desde localStorage al montar', () => {
    localStorage.setItem('theme', 'light')
    render(<Wrapper />)
    expect(screen.getByTestId('resolved')).toHaveTextContent('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })
})
