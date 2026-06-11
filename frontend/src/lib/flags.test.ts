/**
 * TDD — lib/flags.ts
 * RED tests escritos ANTES de la implementación.
 * Cubre: países canónicos WC26, overrides UK, fallback desconocido.
 */

import { describe, it, expect } from 'vitest'
import { nameToFlag } from './flags'

describe('nameToFlag — países canónicos', () => {
  it('Mexico → 🇲🇽', () => {
    expect(nameToFlag('Mexico')).toBe('🇲🇽')
  })

  it('South Korea → 🇰🇷', () => {
    expect(nameToFlag('South Korea')).toBe('🇰🇷')
  })

  it('Ivory Coast → 🇨🇮', () => {
    expect(nameToFlag('Ivory Coast')).toBe('🇨🇮')
  })

  it('United States → 🇺🇸', () => {
    expect(nameToFlag('United States')).toBe('🇺🇸')
  })

  it('DR Congo → 🇨🇩', () => {
    expect(nameToFlag('DR Congo')).toBe('🇨🇩')
  })

  it('Czech Republic → 🇨🇿', () => {
    expect(nameToFlag('Czech Republic')).toBe('🇨🇿')
  })

  it('Brazil → 🇧🇷', () => {
    expect(nameToFlag('Brazil')).toBe('🇧🇷')
  })

  it('Argentina → 🇦🇷', () => {
    expect(nameToFlag('Argentina')).toBe('🇦🇷')
  })
})

describe('nameToFlag — overrides UK (tag emoji)', () => {
  it('England → flag de England (tag sequence)', () => {
    const result = nameToFlag('England')
    // 🏴󠁧󠁢󠁥󠁮󠁧󠁿 = U+1F3F4 + gbeng tag sequence
    expect(result).toBe('\u{1F3F4}\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}')
  })

  it('Scotland → flag de Scotland (tag sequence)', () => {
    const result = nameToFlag('Scotland')
    // 🏴󠁧󠁢󠁳󠁣󠁴󠁿 = U+1F3F4 + gbsct tag sequence
    expect(result).toBe('\u{1F3F4}\u{E0067}\u{E0062}\u{E0073}\u{E0063}\u{E0074}\u{E007F}')
  })
})

describe('nameToFlag — fallback', () => {
  it('nombre desconocido → 🏳', () => {
    expect(nameToFlag('Wakanda')).toBe('🏳')
  })

  it('cadena vacía → 🏳', () => {
    expect(nameToFlag('')).toBe('🏳')
  })
})
