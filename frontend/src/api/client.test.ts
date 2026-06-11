import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fetchAPI, ApiError } from './client'

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
      json: async () => ({ detail: 'server error' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    await expect(fetchAPI('/api/v1/signals')).rejects.toThrow()
  })

  it('lanza un error ante error de red (TypeError: failed to fetch)', async () => {
    const mockFetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
    vi.stubGlobal('fetch', mockFetch)

    await expect(fetchAPI('/api/v1/signals')).rejects.toThrow('Failed to fetch')
  })
})

describe('fetchAPI — write support (4.1)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('POST con body envía Content-Type: application/json y el body serializado', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 1 }),
    })
    vi.stubGlobal('fetch', mockFetch)

    await fetchAPI('/api/v1/bets', {
      method: 'POST',
      body: JSON.stringify({ stake: 1000 }),
    })

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/bets',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ stake: 1000 }),
      }),
    )
  })

  it('DELETE sin body no envía Content-Type: application/json', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => null,
    })
    vi.stubGlobal('fetch', mockFetch)

    await fetchAPI('/api/v1/bets/1', { method: 'DELETE' })

    const callArgs = mockFetch.mock.calls[0][1] as RequestInit & { headers?: Record<string, string> }
    expect(callArgs.headers?.['Content-Type']).toBeUndefined()
  })

  it('422 → lanza ApiError con fieldErrors {campo: mensaje} parseados de detail[].loc+msg', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({
        detail: [{ loc: ['body', 'stake'], msg: 'must be > 0' }],
      }),
    })
    vi.stubGlobal('fetch', mockFetch)

    let caught: unknown
    try {
      await fetchAPI('/api/v1/bets', { method: 'POST' })
    } catch (err) {
      caught = err
    }

    expect(caught).toBeInstanceOf(ApiError)
    const apiErr = caught as ApiError
    expect(apiErr.status).toBe(422)
    expect(apiErr.fieldErrors).toEqual({ stake: 'must be > 0' })
  })

  it('409 → lanza ApiError con message del detail string', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ detail: 'Cannot delete settled bet' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    let caught: unknown
    try {
      await fetchAPI('/api/v1/bets/5', { method: 'DELETE' })
    } catch (err) {
      caught = err
    }

    expect(caught).toBeInstanceOf(ApiError)
    const apiErr = caught as ApiError
    expect(apiErr.status).toBe(409)
    expect(apiErr.message).toBe('Cannot delete settled bet')
  })
})
