import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import PaperStats from './PaperStats'
import type { PaperStats as PaperStatsType } from '../api/types'

describe('PaperStats', () => {
  it('muestra "—" cuando roi=null (invariante de honestidad)', () => {
    const stats: PaperStatsType = { total: 10, open: 3, settled: 7, roi: null }
    render(<PaperStats stats={stats} />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('NUNCA muestra "0%" cuando roi=null', () => {
    const stats: PaperStatsType = { total: 10, open: 3, settled: 7, roi: null }
    render(<PaperStats stats={stats} />)
    expect(screen.queryByText('0%')).not.toBeInTheDocument()
    expect(screen.queryByText('0.0%')).not.toBeInTheDocument()
  })

  it('muestra "+12.5%" cuando roi=0.125', () => {
    const stats: PaperStatsType = { total: 10, open: 3, settled: 7, roi: 0.125 }
    render(<PaperStats stats={stats} />)
    expect(screen.getByText('+12.5%')).toBeInTheDocument()
  })

  it('muestra los totales de apuestas', () => {
    const stats: PaperStatsType = { total: 15, open: 5, settled: 10, roi: null }
    render(<PaperStats stats={stats} />)
    expect(screen.getByText('15')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
  })
})
