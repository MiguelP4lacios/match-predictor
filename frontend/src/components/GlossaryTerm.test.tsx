import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import GlossaryTerm from './GlossaryTerm'

describe('GlossaryTerm', () => {
  describe('término con entrada en glosario (edge)', () => {
    it('renderiza el texto del término y el ícono ?', () => {
      render(<GlossaryTerm term="edge">edge</GlossaryTerm>)
      expect(screen.getByText('edge')).toBeInTheDocument()
      expect(screen.getByText('?')).toBeInTheDocument()
    })

    it('muestra la definición al expandir (click en summary)', () => {
      render(<GlossaryTerm term="edge">edge</GlossaryTerm>)
      const details = document.querySelector('details')
      expect(details).not.toHaveAttribute('open')

      // Abrir con click en el summary
      const summary = document.querySelector('summary')!
      fireEvent.click(summary)
      expect(details).toHaveAttribute('open')
    })

    it('colapsa al hacer click nuevamente', () => {
      render(<GlossaryTerm term="edge">edge</GlossaryTerm>)
      const details = document.querySelector('details')!
      // Abrir
      fireEvent.click(document.querySelector('summary')!)
      expect(details).toHaveAttribute('open')

      // Colapsar
      fireEvent.click(document.querySelector('summary')!)
      expect(details).not.toHaveAttribute('open')
    })

    it('la definición contiene "Ventaja"', () => {
      render(<GlossaryTerm term="edge">edge</GlossaryTerm>)
      expect(screen.getByText(/Ventaja/)).toBeInTheDocument()
    })
  })

  describe('término sin entrada en glosario', () => {
    it('renderiza sólo los children, sin ícono ?', () => {
      render(<GlossaryTerm term="termino-desconocido">Mi etiqueta</GlossaryTerm>)
      expect(screen.getByText('Mi etiqueta')).toBeInTheDocument()
      expect(screen.queryByText('?')).not.toBeInTheDocument()
    })

    it('no renderiza elemento <details>', () => {
      render(<GlossaryTerm term="xyz">Texto</GlossaryTerm>)
      expect(document.querySelector('details')).toBeNull()
    })
  })
})
