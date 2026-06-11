# Proposal: Cupón de Bloques (Parlay +EV estilo BetPlay)

## Intent

El usuario apuesta combinadas ("bloques"/parlays) en BetPlay, pero hoy el sistema
solo evalúa apuestas simples. Falta una calculadora **determinista** que combine N
legs, calcule cuota combinada, probabilidad del modelo y EV del cupón, y detecte
los legs que arrastran el ticket a −EV (el "detector de Scotland"). La cuota la
tipea el usuario (BetPlay = Kambi white-label, sin histórico libre). Captura
automática de Kambi se explora como experimento **apagado por defecto** (el VPS
recibe 429 por IP de datacenter — confirmado). Manual es el camino real.

## Scope

### In Scope
- `app/model/parlay.py` — núcleo PURO: `combined_odds=Π(odds_i)`,
  `model_prob=Π(p_i)` (independencia, documentada), `ev=prob×odds−1` (reusa patrón
  `compute_ev`), diagnóstico por-leg (flag legs −EV + sugerir ticket sin ellos).
- Modelo de datos: tabla nueva `bet_leg` (FK `bet_log_id`, `match_id`,
  `outcome_code`, `odds_taken`) vía **migración m7**. Un parlay = 1 `BetLog`
  (stake total, `odds_taken`=combinada) + N `bet_leg`.
- Settlement de parlay (extiende `settle.py`): WON sii TODOS los legs WON; LOST si
  ALGÚN leg LOST; `pnl=stake×(odds−1)` o `−stake`.
- API: `POST /api/v1/parlays/preview` (sin persistir → math + diagnóstico por-leg),
  `POST /api/v1/parlays` (persiste), `GET /api/v1/parlays`.
- UI estilo BetPlay: drawer "cupón" lateral; botón "Agregar al cupón" en
  `SignalCard` y en filas de Partidos; legs con input de cuota BetPlay; cuota
  combinada + prob modelo + EV en vivo (vía preview) + warnings de legs −EV;
  "Registrar cupón" → POST. Stake en COP. Responsive.
- `KambiOddsSource` (`app/ingestion/sources/kambi.py`) flag-gated tras `OddsSource`:
  milli-odds/1000, `lang=en_US`, `_KAMBI_NAME_OVERRIDES`, `Full Time→h2h`,
  `DataSource.KAMBI`, `KAMBI_ENABLED=false`. NO en el daily loop. Test con fixture
  JSON (no live call).

### Out of Scope
- Futures / Monte Carlo del bracket (ese es el "futures" real del ADR, change aparte).
- Captura Kambi en producción / live; cash-out; system/combo más allá de parlay recto.
- Modelado de correlación (se asume independencia + se documenta el sesgo).

## Capabilities

### New Capabilities
- `parlay-math`: calculadora pura de parlay (cuota combinada, prob bajo
  independencia, EV del cupón, detector de legs −EV).
- `parlay-bets`: modelo `bet_leg` + endpoints preview/POST/GET de parlays.
- `kambi-odds`: adapter `KambiOddsSource` flag-gated (OFF por defecto) tras
  `OddsSource`.

### Modified Capabilities
- `bet-settlement`: `settle()` resuelve parlays (WON sii todos los legs WON).
- `dashboard-frontend`: drawer "cupón" + botones "Agregar al cupón".

## Approach

Núcleo determinista primero (`parlay.py` puro, mismo patrón que `probabilities.py`).
El front NUNCA calcula: el endpoint `preview` computa todo server-side y el UI lo
pinta. Persistencia: `BetLog` + `bet_leg` (un parlay agrupa N match/outcome bajo un
stake). Kambi entra limpio por el Protocol existente pero desconectado del scheduler.

**Verificación numérica (3 legs):** odds `1.40×2.75×1.84=7.084`;
prob `0.834×0.491×0.780=0.3194`; EV `0.3194×7.084−1=+1.2627` (+126.3%).
EV por-leg: +16.8% / +35.0% / +43.5% → sin leg −EV en este caso.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/model/parlay.py` | New | Núcleo puro del parlay + diagnóstico por-leg |
| `app/model/settle.py` | Modified | Settlement de parlay (all-legs-WON) |
| `app/models/betting.py` | Modified | Modelo `BetLeg` + relación con `BetLog` |
| `migrations/versions/m7_*.py` | New | Tabla `bet_leg` |
| `app/api/routers/parlays.py` | New | preview / POST / GET parlays |
| `app/api/schemas.py` | Modified | Schemas de parlay + legs |
| `app/models/enums.py` | Modified | `DataSource.KAMBI = "kambi"` |
| `app/ingestion/sources/kambi.py` | New | Adapter flag-gated + fixture test |
| `app/core/config.py` | Modified | `KAMBI_ENABLED` (default false) |
| `frontend/src/components/CuponDrawer*.tsx` | New | Bet-slip estilo BetPlay |
| `frontend/src/components/SignalCard.tsx` + `pages/MatchesPage.tsx` | Modified | Botón "Agregar al cupón" |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Independencia sobreestima el EV del parlay (correlación intra-torneo) | High | Documentar prominentemente en spec y UI; banner de advertencia; correlación fuera de scope explícito |
| Kambi 429 desde IP datacenter / slug `betplay` sin confirmar | High | OFF por defecto; manual es el core; doc honesto; adapter no es dependencia |
| `bet_leg` rompe settlement de simples existentes | Med | Settlement de simples intacto (path sin legs); parlay = rama nueva; tests de no-regresión |
| Front calculando aritmética (rompe invariante) | Low | `preview` server-side es la única fuente; front solo pinta |

## Rollback Plan

`alembic downgrade -1` revierte m7 (drop `bet_leg`). El router `parlays` y el drawer
son aditivos: quitar su registro/import los desactiva sin tocar simples. `KAMBI_ENABLED`
ya nace en `false`; no requiere rollback. Settlement: la rama parlay solo aplica a
`BetLog` con legs, los simples no se afectan.

## Dependencies

- Extiende specs ya archivadas: `bet-settlement`, `real-bets`, `dashboard-frontend`.
- Kambi (opcional, OFF): requiere IP residencial CO para siquiera probar el slug.

## Success Criteria

- [ ] `parlay.py` puro: cuota combinada, prob (independencia), EV y detector de legs
      −EV con verificación numérica (7.084 / 0.3194 / +1.2627) en tests.
- [ ] Flujo end-to-end con cuotas manuales: agregar al cupón → preview EV en vivo →
      registrar → settle correcto (WON sii todos los legs WON).
- [ ] Migración m7 aplica y revierte limpio; settlement de simples sin regresión.
- [ ] `KambiOddsSource` con test de fixture, `KAMBI_ENABLED=false`, fuera del daily loop.
