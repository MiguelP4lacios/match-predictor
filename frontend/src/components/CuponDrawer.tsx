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
import { Sheet } from '../ui/Sheet'
import { Button } from '../ui/Button'

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

  const drawerFooter = (
    <div className="space-y-3">
      <div>
        <label htmlFor="cupon-stake" className="block text-sm font-medium text-text">
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
          className="mt-1 block w-full rounded border border-border bg-surface px-3 py-1.5 text-sm text-text focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>

      {error && (
        <p className="rounded bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}

      <Button
        variant="primary"
        size="md"
        disabled={!canSubmit}
        loading={submitting}
        onClick={handleSubmit}
        className="w-full"
      >
        Registrar cupón
      </Button>
    </div>
  )

  return (
    <>
      {/* Botón flotante FAB */}
      {!open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-40 rounded-full bg-primary px-5 py-3 font-semibold text-primary-fg shadow-lg hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-primary"
        >
          Cupón ({legs.length})
        </button>
      )}

      <Sheet
        open={open}
        onClose={() => setOpen(false)}
        title={`Cupón (${legs.length})`}
        side="right"
        footer={drawerFooter}
      >
        <div className="space-y-2">
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
          <p className="rounded bg-warn/10 px-3 py-2 text-xs text-warn">
            ⚠ EV calculado bajo independencia — puede sobreestimar el edge en partidos del mismo torneo
          </p>

          {/* Stats preview */}
          {preview && (
            <div className="rounded border border-primary/20 bg-primary/5 p-3 text-sm space-y-1">
              <p>
                <span className="text-text-muted">Cuota combinada:</span>{' '}
                <span className="font-semibold text-text">{Number(preview.combined_odds).toFixed(3)}</span>
              </p>
              {preview.model_prob !== null && (
                <p>
                  <span className="text-text-muted">Prob. modelo:</span>{' '}
                  <span className="font-semibold text-text">{formatProbability(preview.model_prob)}</span>
                </p>
              )}
              {preview.ev !== null && (
                <p>
                  <span className="text-text-muted">EV:</span>{' '}
                  <span
                    className={`font-semibold ${preview.ev >= 0 ? 'text-success' : 'text-danger'}`}
                  >
                    {formatEV(preview.ev)}
                  </span>
                </p>
              )}
              {Number(stake) > 0 && (
                <p>
                  <span className="text-text-muted">Retorno potencial:</span>{' '}
                  <span className="font-semibold text-text">{formatCop(Number(preview.retorno))}</span>
                </p>
              )}
            </div>
          )}
        </div>
      </Sheet>
    </>
  )
}
