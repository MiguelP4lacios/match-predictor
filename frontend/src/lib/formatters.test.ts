import { describe, it, expect } from 'vitest'
import {
  formatEdge,
  formatProbability,
  formatStake,
  formatOdds,
  formatROI,
} from './formatters'

// Escenarios VERBATIM del spec (R2, R6, R10)
// Aritmética verificada:
//   formatEdge(0.0832):     0.0832 * 100 = 8.32  → toFixed(1) = "8.3"  → "8.3%"  ✓
//   formatProbability(0.4202): 0.4202 * 100 = 42.02 → toFixed(1) = "42.0" → "42.0%" ✓
//   formatStake("112.7345"): parseFloat → 112.7345 → toFixed(2) = "112.73"          ✓
//   formatOdds(3.9):         3.9 → toFixed(2) = "3.90"                              ✓
//   formatROI(null):         → "—"                                                   ✓
//   formatROI(0.125):        0.125 * 100 = 12.5 → "+12.5%"                          ✓

describe('formatEdge', () => {
  it('formats 0.0832 as "8.3%"', () => {
    expect(formatEdge(0.0832)).toBe('8.3%')
  })

  it('formats 0.2 as "20.0%"', () => {
    expect(formatEdge(0.2)).toBe('20.0%')
  })
})

describe('formatProbability', () => {
  it('formats 0.4202 as "42.0%"', () => {
    expect(formatProbability(0.4202)).toBe('42.0%')
  })

  it('formats 0.5 as "50.0%"', () => {
    expect(formatProbability(0.5)).toBe('50.0%')
  })
})

describe('formatStake', () => {
  it('formats "112.7345" as "112.73" (string input — Decimal serializado por Pydantic)', () => {
    expect(formatStake('112.7345')).toBe('112.73')
  })

  it('formats "120.16" as "120.16"', () => {
    expect(formatStake('120.16')).toBe('120.16')
  })
})

describe('formatOdds', () => {
  it('formats 3.9 as "3.90"', () => {
    expect(formatOdds(3.9)).toBe('3.90')
  })

  it('formats 1.47 as "1.47"', () => {
    expect(formatOdds(1.47)).toBe('1.47')
  })
})

describe('formatROI', () => {
  it('formats null as "—" (invariante de honestidad)', () => {
    expect(formatROI(null)).toBe('—')
  })

  it('formats 0.125 as "+12.5%"', () => {
    expect(formatROI(0.125)).toBe('+12.5%')
  })

  it('formats -0.05 as "-5.0%"', () => {
    expect(formatROI(-0.05)).toBe('-5.0%')
  })
})
