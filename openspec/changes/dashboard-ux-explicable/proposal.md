# Proposal: Dashboard UX explicable — señales como tarjetas + panel de explicación trazable

## Intent

La vista Señales hoy es una tabla técnica (P(model), edge, stake) ilegible para un
hincha. El usuario quiere UX intuitiva y no-técnica, pero con la traza completa de
CÓMO se calculó cada número disponible bajo demanda. Solución: señales como tarjetas
en lenguaje natural + panel lateral (drawer) que abre al click "¿Por qué?" con el
desglose paso a paso. El server arma el desglose desde Postgres (invariante: el front
JAMÁS calcula).

## Scope

### In Scope
- **Endpoint** `GET /api/v1/signals/{id}/explain` (read-only, serve-from-DB). Devuelve
  pasos numerados **render-ready** (raw + string ya formateable) de: (a) edge —
  de-vig del triple H/D/A del best price → margen casa → prob justa; `p_fair` se
  DERIVA por resta `p_model − edge` (sin recomputar el signal); (b) origen `p_model` —
  Elo point-in-time de ambos equipos, diff ajustado, neutral flag, modelo+versión,
  `low_confidence`; (c) stake ¼-Kelly con valores sustituidos; (d) calidad del modelo
  — Brier vs baselines + `beats_baselines`; (e) metadata — bookmaker, snapshot,
  `captured_at`.
- **SignalCard** reemplaza la tabla (estilo aprobado: "🎯 Apostale a X — paga 5.80
  (Betfair) / Ventaja 6.4% / Sugerido $18.93 / [¿Por qué? →]"). Orden cronológico del
  server intacto. Hint de exposición correlacionada se conserva agrupando cards del
  mismo partido. Empty state.
- **Drawer** reusable: abre al click, cierra con X/escape/click-afuera, responsive
  mobile, secciones colapsables.
- **Glosario inline** estático (`lib/glossary.ts`, español de hincha): edge, de-vig,
  Kelly, Elo, Brier, calibración. Reusable.

### Out of Scope
- Auth, SSE, agentes LLM. **La narrativa del drawer es TEMPLATE determinista del
  server, NO LLM.** En la fase 7 el LLM narrará ENCIMA de estos números, jamás los
  calculará.
- Charts. Rediseño de Grupos/Partidos/Modelo/Paper. La tabla actual se RETIRA (no
  toggle). Drawer/glosario en otras páginas → siguiente iteración (este change cubre
  SEÑALES end-to-end + glosario reusable).

## Capabilities

### New Capabilities
- `signal-explanation`: contrato del endpoint explain — estructura de pasos
  render-ready, derivación `p_fair = p_model − edge`, secciones edge/p_model/stake/
  calidad/metadata, 404 si el signal no existe. Numeric scenarios obligatorios.

### Modified Capabilities
- `dashboard-frontend`: R2/R2A reescritos — cards reemplazan tabla, drawer reusable,
  glosario `lib/glossary.ts`, agrupación correlacionada en cards (no filas).

## Approach

Aditivo. Backend: nuevo router method que lee `value_signal` + `prediction` +
`odds` triple (best-per-outcome) + `model_version.params_json` y compone pasos
formateables. **Decisión clave**: el server entrega valores ya formateables (string +
raw); el front SOLO formatea/maqueta, nunca hace aritmética. `p_fair` derivado por
resta garantiza consistencia con el `edge` persistido; los intermedios de-vig
(1/odds, overround) se reconstruyen del triple persistido, etiquetados como ilustración
y reconciliados con `p_fair`. Front: `SignalCard`, `ExplainDrawer`, `glossary.ts`;
`SignalsTable` y `groupSignals` se reemplazan/adaptan a cards.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/api/routers/signals.py` | Modified | `+ GET /signals/{id}/explain` |
| `app/api/schemas.py` | Modified | schema `SignalExplanation` (pasos render-ready) |
| `frontend/src/components/SignalsTable.tsx` | Removed | reemplazado por cards |
| `frontend/src/components/SignalCard.tsx` | New | tarjeta lenguaje natural |
| `frontend/src/components/ExplainDrawer.tsx` | New | panel lateral reusable |
| `frontend/src/lib/glossary.ts` | New | mini-glosario de hincha |
| `frontend/src/lib/groupSignals.ts` | Modified | agrupación → cards |
| `frontend/src/pages/SignalsPage.tsx` | Modified | render de cards + drawer |
| `frontend/src/api/types.ts` | Modified | tipo `SignalExplanation` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Triple de-vig en explain difiere del snapshot original (nuevas odds) | Med | Reconstruir triple point-in-time vía `odds_id` del signal / snapshot; reconciliar con `p_fair` derivado |
| Front "calcula" al reconstruir de-vig | Med | Server entrega TODO formateable; front solo formatea — spec lo prohíbe |
| Drawer mobile/a11y (escape, focus trap) frágil | Med | Componente reusable testeado; scenarios de cierre |
| Glosario percibido como técnico | Low | Lenguaje de hincha, validado en spec |

## Rollback Plan

Aditivo: endpoint y componentes nuevos. Único borrado destructivo = `SignalsTable`.
Rollback = `git revert` del merge; restaura tabla previa. El endpoint explain no tiene
side-effects (read-only), su retiro no afecta datos.

## Dependencies

- Ninguna externa. Reusa `value_signal`, `prediction`, `odds`, `model_version`,
  `elo_rating` ya persistidos. Sin migración de BD.

## Success Criteria

- [ ] `GET /signals/{id}/explain` devuelve los 5 bloques con valores que reconcilian
      exactamente con los persistidos (`p_fair = p_model − edge`, edge/ev/stake verbatim).
- [ ] Vista Señales muestra cards en orden cronológico del server; tabla retirada.
- [ ] Drawer abre/cierra (X/escape/afuera), responsive, glosario inline por término.
- [ ] Front no ejecuta aritmética alguna sobre los números del modelo.
- [ ] Tests (pytest + vitest) cubren numeric scenarios y estados de UI.
