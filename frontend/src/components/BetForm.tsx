/**
 * BetForm — formulario de registro de apuesta REAL.
 * - Dropdown de partidos SCHEDULED desde /matches/upcoming (recibido como prop)
 * - Outcome select con nombres de equipos
 * - Cuota (>1.01), stake COP (>0), nota opcional
 * - Prefill desde ?match_id=&outcome=&odds=
 * - POST /api/v1/bets → success: clear + onSuccess(); error 422/409: inline
 */
import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { fetchAPI, ApiError, type FieldErrors } from '../api/client'
import type { UpcomingMatch, BetCreate, BetItem } from '../api/types'

interface BetFormProps {
  matches: UpcomingMatch[]
  onSuccess: () => void
}

const OUTCOME_LABELS: Record<string, string> = {
  HOME: 'home',  // will be replaced with team names dynamically
  DRAW: 'Empate',
  AWAY: 'away',  // will be replaced with team names dynamically
}

export default function BetForm({ matches, onSuccess }: BetFormProps) {
  const location = useLocation()
  const params = new URLSearchParams(location.search)

  const prefillMatchId = params.get('match_id') ? Number(params.get('match_id')) : null
  const prefillOutcome = params.get('outcome') ?? ''
  const prefillOdds = params.get('odds') ?? ''

  const [matchId, setMatchId] = useState<string>(prefillMatchId ? String(prefillMatchId) : '')
  const [outcome, setOutcome] = useState<string>(prefillOutcome)
  const [odds, setOdds] = useState<string>(prefillOdds)
  const [stake, setStake] = useState<string>('')
  const [note, setNote] = useState<string>('')
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [globalError, setGlobalError] = useState<string>('')
  const [submitting, setSubmitting] = useState(false)

  // Cuando llega prefill de matchId, seleccionar automáticamente el partido
  useEffect(() => {
    if (prefillMatchId) {
      setMatchId(String(prefillMatchId))
    }
  }, [prefillMatchId])

  const selectedMatch = matches.find((m) => m.id === Number(matchId))

  function getOutcomeLabel(code: string): string {
    if (!selectedMatch) return OUTCOME_LABELS[code] ?? code
    if (code === 'HOME') return `${selectedMatch.home_team} gana`
    if (code === 'DRAW') return 'Empate'
    if (code === 'AWAY') return `${selectedMatch.away_team} gana`
    return code
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setFieldErrors({})
    setGlobalError('')
    setSubmitting(true)

    const body: BetCreate = {
      match_id: Number(matchId),
      outcome_code: outcome as BetCreate['outcome_code'],
      odds_taken: Number(odds),
      stake: Number(stake),
    }
    if (note.trim()) body.note = note.trim()

    try {
      await fetchAPI<BetItem>('/v1/bets', {
        method: 'POST',
        body: JSON.stringify(body),
      })
      // Limpiar formulario
      setMatchId('')
      setOutcome('')
      setOdds('')
      setStake('')
      setNote('')
      onSuccess()
    } catch (err) {
      // Duck-type check: ApiError tiene .status + .fieldErrors
      if (err && typeof err === 'object' && 'status' in err) {
        const apiErr = err as ApiError
        if (apiErr.fieldErrors && Object.keys(apiErr.fieldErrors).length > 0) {
          setFieldErrors(apiErr.fieldErrors)
        } else {
          setGlobalError(apiErr.message ?? 'Error del servidor')
        }
      } else {
        setGlobalError('Error inesperado. Intentá de nuevo.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-lg border bg-white p-4 shadow-sm">
      <h2 className="text-base font-semibold text-gray-800">Registrar apuesta</h2>

      {globalError && (
        <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{globalError}</p>
      )}

      {/* Partido */}
      <div>
        <label htmlFor="bet-match" className="block text-sm font-medium text-gray-700">
          Partido
        </label>
        <select
          id="bet-match"
          aria-label="Partido"
          value={matchId}
          onChange={(e) => {
            setMatchId(e.target.value)
            setOutcome('')
          }}
          required
          className="mt-1 block w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">— seleccioná un partido —</option>
          {matches.map((m) => (
            <option key={m.id} value={m.id}>
              {m.match_date} · {m.home_team} vs {m.away_team}
            </option>
          ))}
        </select>
        {fieldErrors.match_id && (
          <p className="mt-1 text-xs text-red-600">{fieldErrors.match_id}</p>
        )}
      </div>

      {/* Resultado */}
      {selectedMatch && (
        <div>
          <label htmlFor="bet-outcome" className="block text-sm font-medium text-gray-700">
            Resultado
          </label>
          <select
            id="bet-outcome"
            aria-label="Resultado"
            value={outcome}
            onChange={(e) => setOutcome(e.target.value)}
            required
            className="mt-1 block w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">— elegí resultado —</option>
            <option value="HOME">{getOutcomeLabel('HOME')}</option>
            <option value="DRAW">{getOutcomeLabel('DRAW')}</option>
            <option value="AWAY">{getOutcomeLabel('AWAY')}</option>
          </select>
          {fieldErrors.outcome_code && (
            <p className="mt-1 text-xs text-red-600">{fieldErrors.outcome_code}</p>
          )}
        </div>
      )}

      {/* Cuota */}
      <div>
        <label htmlFor="bet-odds" className="block text-sm font-medium text-gray-700">
          Cuota
        </label>
        <input
          id="bet-odds"
          type="number"
          step="0.01"
          min="1.01"
          aria-label="Cuota"
          value={odds}
          onChange={(e) => setOdds(e.target.value)}
          placeholder="ej. 1.85"
          required
          className="mt-1 block w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        {fieldErrors.odds_taken && (
          <p className="mt-1 text-xs text-red-600">{fieldErrors.odds_taken}</p>
        )}
      </div>

      {/* Stake COP */}
      <div>
        <label htmlFor="bet-stake" className="block text-sm font-medium text-gray-700">
          Stake (COP)
        </label>
        <input
          id="bet-stake"
          type="number"
          step="100"
          min="1"
          aria-label="Stake"
          value={stake}
          onChange={(e) => setStake(e.target.value)}
          placeholder="ej. 12000"
          required
          className="mt-1 block w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        {fieldErrors.stake && (
          <p className="mt-1 text-xs text-red-600">{fieldErrors.stake}</p>
        )}
      </div>

      {/* Nota opcional */}
      <div>
        <label htmlFor="bet-note" className="block text-sm font-medium text-gray-700">
          Nota (opcional)
        </label>
        <input
          id="bet-note"
          type="text"
          aria-label="Nota"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="ej. valor detectado por modelo"
          className="mt-1 block w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <button
        type="submit"
        disabled={submitting}
        className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        {submitting ? 'Registrando…' : 'Registrar apuesta'}
      </button>
    </form>
  )
}
