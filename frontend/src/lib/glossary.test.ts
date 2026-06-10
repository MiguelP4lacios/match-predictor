import { describe, it, expect } from 'vitest'
import { glossary } from './glossary'

describe('glossary', () => {
  it('glossary["edge"] contiene "Ventaja"', () => {
    expect(glossary['edge']).toContain('Ventaja')
  })

  it('tiene exactamente 6 entradas (edge, de-vig, kelly, elo, brier, calibración)', () => {
    const keys = Object.keys(glossary)
    expect(keys).toHaveLength(6)
    expect(keys).toContain('edge')
    expect(keys).toContain('de-vig')
    expect(keys).toContain('kelly')
    expect(keys).toContain('elo')
    expect(keys).toContain('brier')
    expect(keys).toContain('calibración')
  })

  it('glossary["de-vig"] describe quitar el margen de la casa', () => {
    expect(glossary['de-vig']).toContain('margen')
  })

  it('glossary["kelly"] describe apostar según la ventaja', () => {
    expect(glossary['kelly']).toContain('ventaja')
  })

  it('glossary["elo"] describe puntaje de fuerza del equipo', () => {
    expect(glossary['elo']).toContain('fuerza')
  })

  it('glossary["brier"] describe error cuadrático de predicciones', () => {
    expect(glossary['brier']).toContain('cuadrático')
  })

  it('glossary["calibración"] describe qué tan seguido se cumple lo predicho', () => {
    expect(glossary['calibración']).toContain('modelo predice')
  })
})
