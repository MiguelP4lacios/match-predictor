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
  })

  describe('cierre del drawer', () => {
    it('llama onClose al presionar Escape', () => {
      mockFetchAPI.mockReturnValue(new Promise(() => {}))
      const onClose = vi.fn()
      renderWithQuery(<ExplainDrawer signalId={10} onClose={onClose} />)
      fireEvent.keyDown(window, { key: 'Escape' })
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
      fireEvent.click(screen.getByTestId('drawer-backdrop'))
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
