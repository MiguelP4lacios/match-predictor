import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fetchAPI } from './client'

describe('fetchAPI', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('retorna data cuando la respuesta es ok', async () => {
    const mockData = { items: [], total: 0 }
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    })
    vi.stubGlobal('fetch', mockFetch)

    const result = await fetchAPI<typeof mockData>('/api/v1/signals')

    expect(result).toEqual(mockData)
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/signals',
      expect.objectContaining({}),
    )
  })

  it('lanza un error cuando la respuesta es HTTP 500', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
    })
    vi.stubGlobal('fetch', mockFetch)

    await expect(fetchAPI('/api/v1/signals')).rejects.toThrow('500')
  })

  it('lanza un error ante error de red (TypeError: failed to fetch)', async () => {
    const mockFetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
    vi.stubGlobal('fetch', mockFetch)

    await expect(fetchAPI('/api/v1/signals')).rejects.toThrow('Failed to fetch')
  })
})
