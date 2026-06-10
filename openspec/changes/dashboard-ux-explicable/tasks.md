# Tasks: Dashboard UX explicable — tarjetas + panel trazable

## Phase 1: Backend (strict TDD, docker-only)

- [x] 1.1 RED `tests/unit/model/test_ratings.py`: tests de `lookup_rating(session, team, before_date)` — verifica puntaje point-in-time y fallback a `DEFAULT_RATING` (refs spec signal-explanation escenario id=10: Mexico 1980.33, South Africa 1662.98)
- [x] 1.2 GREEN `app/model/ratings.py`: extraer `lookup_rating`, `DEFAULT_RATING=1500`, `HOME_ADVANTAGE=100` de `predict_1x2.py`; actualizar `predict_1x2.py` para importarlos; confirmar suite existente verde (`docker compose run --rm api pytest`)
- [x] 1.3 RED `tests/unit/model/test_explain.py`: (a) propiedad reconciliación — cada raw canónico == columna persistida verbatim (edge, ev, kelly_fraction, recommended_stake, p_model); p_fair == p_model − edge; (b) escenario numérico signal id=10 verbatim (p_model=0.83394, edge=0.14724, p_fair=0.68670, overround=0.99064, |reconstruido−derivado|≤0.0001); (c) fixture triple incompleto → `note` presente, no excepción
- [x] 1.4 GREEN `app/model/explain.py`: `ExplainStep/Section/Explanation` dataclasses + `build_explanation(session, signal_id)` — de-vig best-per-outcome fijado al `captured_at` del `odds_id`; `p_fair = p_model − edge` siempre; campos canónicos raw+formatted=null; intermedios formatted string; triple incompleto → note sin fallar
- [x] 1.5 RED `tests/integration/test_signals_explain.py`: GET `/api/v1/signals/10/explain` → 200 con secciones esperadas; GET `/api/v1/signals/9999/explain` → 404 `{"detail": "Signal not found"}`
- [x] 1.6 GREEN `app/api/routers/signals.py` + `app/api/schemas.py`: agregar `GET /signals/{id}/explain`; schemas `ExplainStep`, `ExplainSection`, `SignalExplanation`; router thin (mapea dataclasses → Pydantic, 404 si `build_explanation` retorna None)
- [x] 1.7 Suite completa verde: `docker compose run --rm api pytest` (125+ tests + nuevos); `docker compose run --rm api ruff check . && ruff format .`

## Phase 2: Frontend core (strict TDD, docker-only vitest)

- [x] 2.1 RED→GREEN `frontend/src/lib/glossary.ts`: exportar `glossary` con 6 entradas exactas (edge, de-vig, kelly, elo, brier, calibración); test unitario `glossary["edge"]` contiene "Ventaja"
- [x] 2.2 RED→GREEN `frontend/src/components/GlossaryTerm.tsx`: término expandible `<details>`-style, touch-friendly; tests: expand/collapse, sin entrada → sin ícono
- [x] 2.3 Actualizar `frontend/src/api/types.ts`: agregar `SignalExplanation`, `ExplainSection`, `ExplainStep` espejo del schema Pydantic
- [x] 2.4 RED→GREEN `frontend/src/components/SignalCard.tsx`: muestra fecha·partido, "Apostale a X", cuota+bookmaker, badge edge, stake, botón "¿Por qué? →"; usa formatters.ts existentes (sin aritmética); tests: escenario id=10 badge="14.7%", stake="$120.16", cuota="1.47 (gtbets)", texto "Apostale a México"
- [x] 2.5 RED→GREEN `frontend/src/components/SignalCardGroup.tsx`: agrupa con `groupSignals`; hint "⚠ {n} señales sobre este partido — exposición correlacionada" solo si ≥2; tests: escenario Haiti(2 señales)+Brasil(1); orden server intacto

## Phase 3: Frontend drawer (strict TDD, docker-only vitest)

- [x] 3.1 RED→GREEN `frontend/src/components/ExplainDrawer.tsx`: `role=dialog aria-modal`, `fixed inset-0 z-50`; lazy `useQuery(['explain', id], enabled=open)`; skeleton de carga DENTRO del drawer; "Error al cargar explicación" en fallo; cierre X/Escape(keydown effect)/click-outside(backdrop onClick); autofocus en botón X (ref+useEffect); responsive bottom sheet en mobile (`< 640px`); renderiza secciones con `label_es` + `GlossaryTerm` inline; tests: open/close/Escape, skeleton, error banner, tooltip glosario

## Phase 4: Integración

- [x] 4.1 `frontend/src/pages/SignalsPage.tsx`: reemplazar `SignalsTable` por `SignalCardGroup` + `ExplainDrawer`; conservar filtro `min_edge`; empty state "Sin señales con ese filtro"
- [x] 4.2 Eliminar `frontend/src/components/SignalsTable.tsx` y `SignalsTable.test.tsx`; verificar cero imports rotos: `docker compose run --rm frontend rg SignalsTable src/`
- [x] 4.3 Actualizar/agregar tests de integración de `SignalsPage` con explain mockeado; suite frontend completa verde + `npm run build` limpio (sin errores TS)

## Phase 5: Cierre

- [x] 5.1 Smoke real desde contenedor: `curl http://localhost:8000/api/v1/signals/10/explain` (verificar secciones); abrir `http://localhost:5173` y pulsar "¿Por qué? →" en signal id=10 — documentar resultado en apply-progress
- [x] 5.2 Backend suite verde + ruff; frontend suite verde + build; commits conventional por unidad lógica (feat/refactor/test/chore)
- [x] 5.3 Marcar checkboxes en tasks.md; salvar apply-progress en engram (merge si existe `sdd/dashboard-ux-explicable/apply-progress`)
