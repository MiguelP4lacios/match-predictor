/**
 * CuponDrawer — bet-slip flotante estilo BetPlay para parlays +EV.
 *
 * Comportamiento:
 * - Botón flotante "Cupón (N)" visible cuando hay legs; oculto si 0.
 * - Drawer lateral: legs con inputs de cuota, stats EV live vía preview,
 *   stake COP, "Registrar cupón" → POST /parlays → 201 limpia.
 *
 * INVARIANTE: el front NUNCA calcula cuota combinada ni EV.
 * Todo math es server-side (POST /parlays/preview).
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { useCupon } from '../context/CuponContext'
import { previewParlay, createParlay } from '../api/parlays'
import { formatCop, formatProbability } from '../lib/formatters'
import type { ParlayPreview } from '../api/types'
import CuponLegRow from './CuponLegRow'

const DEBOUNCE_MS = 300

/** Formatea EV float como "+126.3%" o "−3.6%" */
function formatEV(ev: number): string {
  const pct = (ev * 100).toFixed(1)
  return ev >= 0 ? `+${pct}%` : `${pct}%`
}

export default function CuponDrawer() {
  const { legs, removeLeg, updateOdds, clear } = useCupon()
  const [open, setOpen] = useState(false)
  const [stake, setStake] = useState('')
  const [preview, setPreview] = useState<ParlayPreview | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // ─── Auto-cerrar si quedan 0 legs ────────────────────────────────────────
  useEffect(() => {
    if (legs.length === 0) {
      setOpen(false)
      setPreview(null)
    }
  }, [legs.length])

  // ─── Debounced preview ────────────────────────────────────────────────────
  const triggerPreview = useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    const legsWithOdds = legs.filter((l) => l.odds !== null && l.odds > 1)
    if (legsWithOdds.length < 2) {
      setPreview(null)
      return
    }
    debounceRef.current = setTimeout(async () => {
      try {
        const stakeNum = stake ? Number(stake) : undefined
        const result = await previewParlay({
          legs: legsWithOdds.map((l) => ({
            match_id: l.match_id,
            outcome_code: l.outcome_code,
            odds: l.odds!,
          })),
          stake: stakeNum,
        })
        setPreview(result)
      } catch {
        // preview errors don't block the form
      }
    }, DEBOUNCE_MS)
  }, [legs, stake])

  useEffect(() => {
    if (open) triggerPreview()
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [open, triggerPreview])

  // ─── Submit ───────────────────────────────────────────────────────────────
  const legsWithOdds = legs.filter((l) => l.odds !== null && l.odds > 1)
  const canSubmit = legsWithOdds.length >= 2 && Number(stake) > 0 && !submitting

  async function handleSubmit() {
    if (!canSubmit) return
    setSubmitting(true)
    setError(null)
    try {
      await createParlay({
        legs: legsWithOdds.map((l) => ({
          match_id: l.match_id,
          outcome_code: l.outcome_code,
          odds: l.odds!,
        })),
        stake: Number(stake),
      })
      clear()
      setStake('')
      setPreview(null)
      setOpen(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al registrar el cupón')
    } finally {
      setSubmitting(false)
    }
  }

  // ─── Render ───────────────────────────────────────────────────────────────

  if (legs.length === 0) return null

  return (
    <>
      {/* Botón flotante */}
      {!open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-40 rounded-full bg-blue-600 px-5 py-3 font-semibold text-white shadow-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Cupón ({legs.length})
        </button>
      )}

      {/* Drawer overlay */}
      {open && (
        <div className="fixed inset-0 z-50 flex justify-end">
          {/* Backdrop */}
          <button
            type="button"
            aria-label="Cerrar cupón"
            onClick={() => setOpen(false)}
            className="absolute inset-0 bg-black/30"
          />

          {/* Panel */}
          <div className="relative flex h-full w-full max-w-sm flex-col bg-white shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between border-b px-4 py-3">
              <h2 className="text-base font-bold text-gray-900">Cupón ({legs.length})</h2>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded p-1 text-gray-500 hover:text-gray-700"
                aria-label="Cerrar"
              >
                ✕
              </button>
            </div>

            {/* Scroll area */}
            <div className="flex-1 space-y-2 overflow-y-auto p-4">
              {legs.map((leg) => {
                const diag = preview?.legs.find(
                  (d) => d.match_id === leg.match_id && d.outcome_code === leg.outcome_code,
                )
                return (
                  <CuponLegRow
                    key={`${leg.match_id}-${leg.outcome_code}`}
                    leg={leg}
                    diagnostic={diag}
                    onOddsChange={(mid, oc, odds) => {
                      updateOdds(mid, oc, odds)
                    }}
                    onRemove={removeLeg}
                  />
                )
              })}

              {/* Banner independencia — OBLIGATORIO por spec */}
              <p className="rounded bg-amber-50 px-3 py-2 text-xs text-amber-700">
                ⚠ EV calculado bajo independencia — puede sobreestimar el edge en partidos del mismo torneo
              </p>

              {/* Stats preview */}
              {preview && (
                <div className="rounded border border-blue-100 bg-blue-50 p-3 text-sm space-y-1">
                  <p>
                    <span className="text-gray-500">Cuota combinada:</span>{' '}
                    <span className="font-semibold">{Number(preview.combined_odds).toFixed(3)}</span>
                  </p>
                  {preview.model_prob !== null && (
                    <p>
                      <span className="text-gray-500">Prob. modelo:</span>{' '}
                      <span className="font-semibold">{formatProbability(preview.model_prob)}</span>
                    </p>
                  )}
                  {preview.ev !== null && (
                    <p>
                      <span className="text-gray-500">EV:</span>{' '}
                      <span
                        className={`font-semibold ${preview.ev >= 0 ? 'text-green-700' : 'text-red-600'}`}
                      >
                        {formatEV(preview.ev)}
                      </span>
                    </p>
                  )}
                  {Number(stake) > 0 && (
                    <p>
                      <span className="text-gray-500">Retorno potencial:</span>{' '}
                      <span className="font-semibold">{formatCop(Number(preview.retorno))}</span>
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Footer: stake + botón */}
            <div className="border-t p-4 space-y-3">
              <div>
                <label htmlFor="cupon-stake" className="block text-sm font-medium text-gray-700">
                  Stake (COP)
                </label>
                <input
                  id="cupon-stake"
                  type="number"
                  step="100"
                  min="1"
                  placeholder="5000"
                  value={stake}
                  onChange={(e) => setStake(e.target.value)}
                  className="mt-1 block w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              {error && (
                <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
              )}

              <button
                type="button"
                disabled={!canSubmit}
                onClick={handleSubmit}
                className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {submitting ? 'Registrando…' : 'Registrar cupón'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
