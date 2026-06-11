/**
 * TDD — UI Primitives
 * RED tests escritos ANTES de la implementación.
 * Cubre: Card, Badge, Stat, Button, Tabs, Sheet, FlagLabel,
 *         ThemeToggle, Spinner, ErrorState.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Card } from './Card'
import { Badge } from './Badge'
import { Stat } from './Stat'
import { Button } from './Button'
import { Tabs } from './Tabs'
import { Sheet } from './Sheet'
import { FlagLabel } from './FlagLabel'
import { ThemeToggle } from './ThemeToggle'
import { Spinner } from './Spinner'
import { ErrorState } from './ErrorState'
import { ThemeProvider } from '../context/ThemeContext'
import type { ReactElement } from 'react'

// ── Helpers ───────────────────────────────────────────────────────────────────

function withTheme(el: ReactElement) {
  return <ThemeProvider>{el}</ThemeProvider>
}

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

// ── Card ──────────────────────────────────────────────────────────────────────

describe('Card', () => {
  it('renderiza children', () => {
    render(<Card>Contenido</Card>)
    expect(screen.getByText('Contenido')).toBeInTheDocument()
  })

  it('renderiza title cuando se pasa', () => {
    render(<Card title="Mi tarjeta">Cuerpo</Card>)
    expect(screen.getByText('Mi tarjeta')).toBeInTheDocument()
    expect(screen.getByText('Cuerpo')).toBeInTheDocument()
  })

  it('renderiza footer cuando se pasa', () => {
    render(<Card footer={<span>Pie</span>}>Cuerpo</Card>)
    expect(screen.getByText('Pie')).toBeInTheDocument()
  })
})

// ── Badge ─────────────────────────────────────────────────────────────────────

describe('Badge', () => {
  it('renderiza el texto del children', () => {
    render(<Badge variant="neutral">Etiqueta</Badge>)
    expect(screen.getByText('Etiqueta')).toBeInTheDocument()
  })

  it('renderiza texto de success', () => {
    render(<Badge variant="success">OK</Badge>)
    expect(screen.getByText('OK')).toBeInTheDocument()
  })

  it('renderiza texto de warn', () => {
    render(<Badge variant="warn">Aviso</Badge>)
    expect(screen.getByText('Aviso')).toBeInTheDocument()
  })

  it('renderiza texto de danger', () => {
    render(<Badge variant="danger">Error</Badge>)
    expect(screen.getByText('Error')).toBeInTheDocument()
  })
})

// ── Stat ──────────────────────────────────────────────────────────────────────

describe('Stat', () => {
  it('renderiza label y value', () => {
    render(<Stat label="Señales" value={42} />)
    expect(screen.getByText('Señales')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('renderiza hint cuando se pasa', () => {
    render(<Stat label="ROI" value="12%" hint="últimos 30 días" />)
    expect(screen.getByText('ROI')).toBeInTheDocument()
    expect(screen.getByText('12%')).toBeInTheDocument()
    expect(screen.getByText('últimos 30 días')).toBeInTheDocument()
  })
})

// ── Button ────────────────────────────────────────────────────────────────────

describe('Button', () => {
  it('renderiza children', () => {
    render(<Button variant="primary">Aceptar</Button>)
    expect(screen.getByRole('button')).toHaveTextContent('Aceptar')
  })

  it('llama onClick al hacer click', () => {
    const onClick = vi.fn()
    render(<Button variant="secondary" onClick={onClick}>Cancelar</Button>)
    fireEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('muestra indicador de carga y deshabilita cuando loading=true', () => {
    render(<Button variant="primary" loading>Guardando</Button>)
    expect(screen.getByRole('button')).toBeDisabled()
  })
})

// ── Tabs ──────────────────────────────────────────────────────────────────────

describe('Tabs', () => {
  const tabs = [
    { id: 'a', label: 'Tab A' },
    { id: 'b', label: 'Tab B' },
  ]

  it('renderiza todos los tabs', () => {
    const onChange = vi.fn()
    render(<Tabs tabs={tabs} value="a" onChange={onChange} />)
    expect(screen.getByText('Tab A')).toBeInTheDocument()
    expect(screen.getByText('Tab B')).toBeInTheDocument()
  })

  it('llama onChange con el id del tab al hacer click', () => {
    const onChange = vi.fn()
    render(<Tabs tabs={tabs} value="a" onChange={onChange} />)
    fireEvent.click(screen.getByText('Tab B'))
    expect(onChange).toHaveBeenCalledWith('b')
  })
})

// ── Sheet ─────────────────────────────────────────────────────────────────────

describe('Sheet', () => {
  it('no muestra contenido cuando open=false', () => {
    render(
      <Sheet open={false} onClose={() => {}} title="Panel">
        <span>Contenido oculto</span>
      </Sheet>,
    )
    expect(screen.queryByText('Contenido oculto')).not.toBeInTheDocument()
  })

  it('muestra contenido y título cuando open=true', () => {
    render(
      <Sheet open={true} onClose={() => {}} title="Panel">
        <span>Contenido visible</span>
      </Sheet>,
    )
    expect(screen.getByText('Panel')).toBeInTheDocument()
    expect(screen.getByText('Contenido visible')).toBeInTheDocument()
  })

  it('llama onClose al presionar Escape', () => {
    const onClose = vi.fn()
    render(
      <Sheet open={true} onClose={onClose} title="Panel">
        <span>Contenido</span>
      </Sheet>,
    )
    fireEvent.keyDown(document.body, { key: 'Escape', code: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('llama onClose al hacer click en el backdrop', () => {
    const onClose = vi.fn()
    render(
      <Sheet open={true} onClose={onClose} title="Panel">
        <span>Contenido</span>
      </Sheet>,
    )
    fireEvent.click(screen.getByTestId('sheet-backdrop'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})

// ── FlagLabel ─────────────────────────────────────────────────────────────────

describe('FlagLabel', () => {
  it('renderiza el nombre del equipo', () => {
    render(<FlagLabel team="Mexico" />)
    expect(screen.getByText(/Mexico/)).toBeInTheDocument()
  })

  it('renderiza la bandera emoji', () => {
    render(<FlagLabel team="Mexico" />)
    expect(screen.getByText(/🇲🇽/)).toBeInTheDocument()
  })

  it('usa 🏳 para equipos desconocidos', () => {
    render(<FlagLabel team="Equipo Fantasma" />)
    expect(screen.getByText(/🏳/)).toBeInTheDocument()
  })
})

// ── ThemeToggle ───────────────────────────────────────────────────────────────

describe('ThemeToggle', () => {
  it('renderiza un botón', () => {
    render(withTheme(<ThemeToggle />))
    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it('al hacer click cambia el tema', () => {
    render(withTheme(<ThemeToggle />))
    const before = localStorage.getItem('theme')
    fireEvent.click(screen.getByRole('button'))
    const after = localStorage.getItem('theme')
    expect(after).not.toBe(before)
  })
})

// ── Spinner ───────────────────────────────────────────────────────────────────

describe('Spinner', () => {
  it('renderiza elemento accesible de carga', () => {
    render(<Spinner />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('tiene aria-label descriptivo', () => {
    render(<Spinner />)
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Cargando')
  })
})

// ── ErrorState ────────────────────────────────────────────────────────────────

describe('ErrorState', () => {
  it('renderiza mensaje de error', () => {
    render(<ErrorState />)
    expect(screen.getByRole('alert')).toBeInTheDocument()
  })

  it('renderiza botón Reintentar cuando se pasa onRetry', () => {
    const onRetry = vi.fn()
    render(<ErrorState onRetry={onRetry} />)
    expect(screen.getByRole('button', { name: /reintentar/i })).toBeInTheDocument()
  })

  it('llama onRetry al hacer click en Reintentar', () => {
    const onRetry = vi.fn()
    render(<ErrorState onRetry={onRetry} />)
    fireEvent.click(screen.getByRole('button', { name: /reintentar/i }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('no muestra botón Reintentar si no se pasa onRetry', () => {
    render(<ErrorState />)
    expect(screen.queryByRole('button', { name: /reintentar/i })).not.toBeInTheDocument()
  })
})
