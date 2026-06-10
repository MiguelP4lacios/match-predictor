/**
 * Thin fetch wrapper.
 * Base URL: VITE_API_URL env var (prod override) ?? '/api' (proxy Vite en dev).
 * Normaliza errores HTTP y de red en un mismo throw para que React Query
 * los trate uniformemente como estado de error.
 */

const BASE = import.meta.env.VITE_API_URL ?? '/api'

export async function fetchAPI<T>(
  path: string,
  opts?: RequestInit,
): Promise<T> {
  const url = path.startsWith('http') ? path : `${BASE}${path.replace(/^\/api/, '')}`

  let res: Response
  try {
    res = await fetch(url, { ...opts })
  } catch (err) {
    // Error de red (sin conexión, DNS, etc.)
    throw err instanceof Error ? err : new Error(String(err))
  }

  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`)
  }

  return res.json() as Promise<T>
}
