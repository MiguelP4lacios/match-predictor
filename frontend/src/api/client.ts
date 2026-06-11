/**
 * Thin fetch wrapper — write-capable, retrocompatible.
 * Base URL: VITE_API_URL env var (prod override) ?? '/api' (proxy Vite en dev).
 * Normaliza errores HTTP y de red en un mismo throw para que React Query
 * los trate uniformemente como estado de error.
 *
 * Errores:
 *   422 → ApiError { status: 422, fieldErrors: { campo: mensaje } }
 *   409 → ApiError { status: 409, message: string }
 *   otro !ok → ApiError { status, message }
 *   red → Error (TypeError/etc pasados al exterior sin wrapping)
 */

const BASE = import.meta.env.VITE_API_URL ?? '/api'

/** Campo → mensaje; parseado de detail:[{loc,msg}] de FastAPI 422. */
export type FieldErrors = Record<string, string>

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly fieldErrors?: FieldErrors,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function fetchAPI<T>(
  path: string,
  opts?: RequestInit,
): Promise<T> {
  const url = path.startsWith('http') ? path : `${BASE}${path.replace(/^\/api/, '')}`

  // Si hay body, agrega Content-Type: application/json
  const headers: Record<string, string> = {}
  if (opts?.body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  const finalOpts: RequestInit = {
    ...opts,
    headers: { ...headers, ...(opts?.headers as Record<string, string> | undefined) },
  }

  let res: Response
  try {
    res = await fetch(url, finalOpts)
  } catch (err) {
    // Error de red (sin conexión, DNS, etc.)
    throw err instanceof Error ? err : new Error(String(err))
  }

  if (!res.ok) {
    let body: unknown
    try {
      body = await res.json()
    } catch {
      throw new ApiError(res.status, `${res.status} ${res.statusText}`)
    }

    if (res.status === 422) {
      // FastAPI detail: [{loc: [..., campo], msg: "..."}]
      const detail = (body as { detail?: Array<{ loc: string[]; msg: string }> }).detail
      const fieldErrors: FieldErrors = {}
      if (Array.isArray(detail)) {
        for (const item of detail) {
          const campo = item.loc[item.loc.length - 1]
          fieldErrors[campo] = item.msg
        }
      }
      throw new ApiError(422, 'Validation error', fieldErrors)
    }

    if (res.status === 409) {
      const detail = (body as { detail?: string }).detail ?? `${res.status} Conflict`
      throw new ApiError(409, detail)
    }

    const message =
      (body as { detail?: string }).detail ?? `${res.status} ${res.statusText}`
    throw new ApiError(res.status, typeof message === 'string' ? message : String(message))
  }

  // 204 No Content → retornar null
  if (res.status === 204) {
    return null as T
  }

  return res.json() as Promise<T>
}
