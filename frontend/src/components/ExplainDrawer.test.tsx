/**
 * Tests for ExplainDrawer — lazy fetch, open/close/Escape/click-outside,
 * loading skeleton, error banner, glossary tooltip inline.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ExplainDrawer from './ExplainDrawer'

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

const EXPLAIN_FIXTURE = {
  sections: [
    {
      key: 'apuesta',
      titulo: '¿Qué apostamos?',
      steps: [
        {
          key: 'outcome_label',
          label_es: 'Resultado apostado',
          raw: 'Mexico',
          formatted: 'Mexico',
          glossary_term: null,
        },
        {
          key: 'cuota',
          label_es: 'Cuota decimal',
          raw: 1.47,
          formatted: '1.47',
          glossary_term: null,
        },
        {
          key: 'bookmaker',
          label_es: 'Casa de apuestas',
          raw: 'gtbets',
          formatted: 'gtbets',
          glossary_term: null,
        },
        {
          key: 'home_team',
          label_es: 'Equipo local',
          raw: 'Mexico',
          formatted: 'Mexico',
          glossary_term: null,
        },
        {
          key: 'away_team',
          label_es: 'Equipo visitante',
          raw: 'South Africa',
          formatted: 'South Africa',
          glossary_term: null,
        },
        {
          key: 'match_date',
          label_es: 'Fecha del partido',
          raw: '2026-06-11',
          formatted: '11/06/2026',
          glossary_term: null,
        },
      ],
      note: null,
    },
    {
      key: 'edge',
      titulo: 'Cálculo del edge',
      steps: [
        {
          key: 'p_model',
          label_es: 'Probabilidad del modelo',
          raw: 0.83394,
          formatted: '83.4%',
          glossary_term: null,
        },
        {
          key: 'edge',
          label_es: 'Ventaja (edge)',
          raw: 0.14724,
          formatted: '14.7%',
          glossary_term: 'edge',
        },
      ],
      note: null,
    },
    {
      key: 'stake',
      titulo: 'Stake sugerido',
      steps: [
        {
          key: 'recommended_stake',
          label_es: 'Stake recomendado',
          raw: '120.16',
          formatted: '$120.16',
          glossary_term: 'kelly',
        },
      ],
      note: null,
    },
  ],
}

describe('ExplainDrawer', () => {
  beforeEach(() => vi.clearAllMocks())

  describe('cuando signalId es null — no renderiza', () => {
    it('no renderiza nada cuando signalId=null', () => {
      renderWithQuery(<ExplainDrawer signalId={null} onClose={vi.fn()} />)
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })

  describe('apertura — cuando signalId es un número', () => {
    it('renderiza el drawer con role=dialog', () => {
      mockFetchAPI.mockReturnValue(new Promise(() => {})) // never resolves
      renderWithQuery(<ExplainDrawer signalId={10} onClose={vi.fn()} />)
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    it('muestra skeleton de carga mientras fetch está pendiente', () => {
      mockFetchAPI.mockReturnValue(new Promise(() => {})) // never resolves
      renderWithQuery(<ExplainDrawer signalId={10} onClose={vi.fn()} />)
      expect(screen.getByLabelText('Cargando')).toBeInTheDocument()
    })

    it('muestra el contenido cuando la query resuelve', async () => {
      mockFetchAPI.mockResolvedValue(EXPLAIN_FIXTURE)
      renderWithQuery(<ExplainDrawer signalId={10} onClose={vi.fn()} />)
      await waitFor(() => {
        expect(screen.getByText('Cálculo del edge')).toBeInTheDocument()
      })
      expect(screen.getByText('83.4%')).toBeInTheDocument()
      expect(screen.getByText('14.7%')).toBeInTheDocument()
    })

    it('renderiza la sección apuesta PRIMERO con título y campos clave', async () => {
      mockFetchAPI.mockResolvedValue(EXPLAIN_FIXTURE)
      renderWithQuery(<ExplainDrawer signalId={10} onClose={vi.fn()} />)
      await waitFor(() => {
        expect(screen.getByText('¿Qué apostamos?')).toBeInTheDocument()
      })
      // apuesta aparece antes que edge en el DOM
      const titles = screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)
      expect(titles[0]).toBe('¿Qué apostamos?')
      expect(titles[1]).toBe('Cálculo del edge')
      // campos de la sección apuesta (Mexico aparece en outcome_label y home_team — 2+ instancias OK)
      expect(screen.getAllByText('Mexico').length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText('gtbets')).toBeInTheDocument()
      expect(screen.getByText('11/06/2026')).toBeInTheDocument()
    })
  })

  describe('cierre del drawer', () => {
    it('llama onClose al presionar Escape', () => {
      mockFetchAPI.mockReturnValue(new Promise(() => {}))
      const onClose = vi.fn()
      renderWithQuery(<ExplainDrawer signalId={10} onClose={onClose} />)
      // Sheet usa document.addEventListener — disparar en document.body
      fireEvent.keyDown(document.body, { key: 'Escape' })
      expect(onClose).toHaveBeenCalledOnce()
    })

    it('llama onClose al pulsar el botón X', () => {
      mockFetchAPI.mockReturnValue(new Promise(() => {}))
      const onClose = vi.fn()
      renderWithQuery(<ExplainDrawer signalId={10} onClose={onClose} />)
      fireEvent.click(screen.getByRole('button', { name: /cerrar/i }))
      expect(onClose).toHaveBeenCalledOnce()
    })

    it('llama onClose al hacer click en el backdrop (afuera del panel)', () => {
      mockFetchAPI.mockReturnValue(new Promise(() => {}))
      const onClose = vi.fn()
      renderWithQuery(<ExplainDrawer signalId={10} onClose={onClose} />)
      // Sheet usa data-testid="sheet-backdrop"
      fireEvent.click(screen.getByTestId('sheet-backdrop'))
      expect(onClose).toHaveBeenCalledOnce()
    })
  })

  describe('estado de error', () => {
    it('muestra "Error al cargar explicación" cuando el fetch falla', async () => {
      mockFetchAPI.mockRejectedValue(new Error('500 Internal Server Error'))
      renderWithQuery(<ExplainDrawer signalId={10} onClose={vi.fn()} />)
      await waitFor(() => {
        expect(screen.getByText('Error al cargar explicación')).toBeInTheDocument()
      })
    })

    it('el error se muestra DENTRO del drawer (role=dialog sigue presente)', async () => {
      mockFetchAPI.mockRejectedValue(new Error('500'))
      renderWithQuery(<ExplainDrawer signalId={10} onClose={vi.fn()} />)
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
        expect(screen.getByText('Error al cargar explicación')).toBeInTheDocument()
      })
    })
  })

  describe('glosario inline', () => {
    it('renderiza GlossaryTerm con ícono ? para paso con glossary_term="edge"', async () => {
      mockFetchAPI.mockResolvedValue(EXPLAIN_FIXTURE)
      renderWithQuery(<ExplainDrawer signalId={10} onClose={vi.fn()} />)
      await waitFor(() => {
        expect(screen.getByText('Cálculo del edge')).toBeInTheDocument()
      })
      // El paso "edge" tiene glossary_term="edge" → debe mostrar GlossaryTerm con ?
      expect(screen.getAllByText('?').length).toBeGreaterThanOrEqual(1)
    })

    it('no muestra ? para pasos sin glossary_term', async () => {
      const noGlossaryFixture = {
        sections: [{
          key: 'edge',
          titulo: 'Sin glosario',
          steps: [{
            key: 'p_model',
            label_es: 'Probabilidad del modelo',
            raw: 0.83394,
            formatted: '83.4%',
            glossary_term: null,
          }],
          note: null,
        }],
      }
      mockFetchAPI.mockResolvedValue(noGlossaryFixture)
      renderWithQuery(<ExplainDrawer signalId={10} onClose={vi.fn()} />)
      await waitFor(() => {
        expect(screen.getByText('Sin glosario')).toBeInTheDocument()
      })
      expect(screen.queryByText('?')).not.toBeInTheDocument()
    })
  })
})
