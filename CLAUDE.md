# Mundial 2026 — Sistema de Predicción +EV (Selecciones)

## WHY
Sistema de predicción de resultados de fútbol de **selecciones nacionales** para
apostar con **valor esperado positivo (+EV)** sobre el Mundial 2026 y competiciones
de selecciones. No busca "acertar el ganador": busca detectar cuándo la cuota de la
casa paga **más** de lo que vale la probabilidad real, y gestionar el bankroll con
disciplina. La "fija" no existe; el edge sostenido + Kelly fraccionado, sí.

## WHAT
- Ingesta de datos de selecciones (histórico + vivo) hacia una BD local, vía una
  capa `DataSource` **provider-agnostic** (la fuente es un detalle intercambiable).
- Captura propia de **closing odds** en vivo (no existe gratis un histórico limpio
  de cuotas de selecciones) para poder **medir edge**.
- Modelo estadístico **determinista** (Dixon-Coles / Poisson + Elo) que estima
  probabilidades de 1X2, Over/Under y avance/campeón. **Backtesteado** (Brier,
  log-loss, calibración) antes de confiar en él.
- Cálculo de **EV vs cuota** y staking con **Kelly fraccionado**.
- API REST que sirve datos, probabilidades y señales **desde la BD**.
- Capa de agentes provider-agnostic (Anthropic / OpenAI / Ollama) que **narran** el
  diagnóstico del modelo — nunca lo calculan ni lo inventan.
- Dashboard React que consume la API y muestra señales y diagnóstico en streaming.

## Mercados objetivo
- **1X2** (gana local / empate / visita).
- **Over/Under** de goles.
- **Futures**: avance de grupo y campeón (Monte Carlo sobre el bracket).

## Stack
- Backend: Python 3.12, FastAPI, SQLAlchemy, PostgreSQL
- Modelado: NumPy / SciPy / pandas (Dixon-Coles, Poisson, Elo, Monte Carlo)
- Ingesta/scheduler: APScheduler (alternativa: Celery beat)
- Agentes: capa propia con interfaz `LLMProvider` + function calling (tools)
- Frontend: React + Vite, SSE para el streaming del diagnóstico

## Fuentes de datos (detrás de `DataSource`, intercambiables)
- **Histórico de resultados** (backbone): Kaggle `martj42/international-football-results`
  — todas las confederaciones, clasificatorias, Nations League, amistosos. CC0.
- **Fuerza de equipo**: `eloratings.net` (Elo de selecciones). Predictor individual
  más fuerte gratis; compensa la ausencia de xG.
- **xG (parcial, legal)**: StatsBomb Open Data — solo torneos grandes (WC 18/22,
  Euro 20/24, Copa América 24). Uso no comercial + atribución.
- **Vivo Mundial 2026**: API-Football free (100 req/día, `league=1&season=2026`);
  `openfootball/worldcup.json` como fallback de esqueleto.
- **Odds**: The Odds API free (live, 500 créditos/mes) → capturamos snapshots
  propios. El histórico de odds es pago; se evalúa al validar el edge.
- ❌ FBref: tiene xG de selecciones pero su ToS prohíbe scraping para construir
  productos (403 a bots). NO usar para ingesta persistente.
- ❌ football-data.co.uk: odds excelentes pero **solo clubes**, cero selecciones.

## Invariantes de arquitectura (NO romper)
- **El LLM NUNCA calcula ni inventa probabilidades, stats ni edge.** SOLO narra
  números ya calculados por el modelo determinista. Sagrado.
- **Determinista separado del LLM.** Tabla, desempates FIFA, Dixon-Coles/Poisson/Elo,
  Monte Carlo, EV y Kelly se calculan en código, son testeables y backtesteables.
- **Sin edge medido, no hay apuesta.** Toda señal +EV exige odds contra qué
  compararse. Ninguna recomendación de stake sin EV calculado vs cuota real.
- **NUNCA llamar a una API externa dentro del request del usuario.** Todo se sirve
  desde Postgres.
- **`DataSource` provider-agnostic.** Cambiar de fuente = cambiar una implementación
  detrás de la interfaz, sin tocar modelo, API ni front. Igual criterio que
  `LLMProvider`.
- **Cuotas free = recursos limitados.** API-Football 100 req/día; The Odds API 500
  créditos/mes. Polling adaptativo (solo `live`, cadencia mayor pa' estáticos),
  control vía tabla `sync_log`.
- Agentes acceden a datos vía **tools** (`get_match_probabilities`,
  `get_group_standings`, `get_value_signals`...), no metiendo datos crudos al prompt.
- **Honestidad de calibración.** Un modelo sin backtest reportado (Brier/log-loss)
  no se usa para apostar. La "confiabilidad" de una señal sale de la calibración del
  modelo, jamás de un número inventado.

## Gestión de riesgo
- Staking con **Kelly fraccionado** (típicamente ¼ Kelly), nunca Kelly pleno.
- Límites de exposición por partido y por jornada.
- Registro de cada apuesta (prob. modelo, cuota, stake, resultado) para medir ROI y
  calibración en producción.

## Comandos (rellenar al inicializar)
- Instalar deps: `uv sync`  (o `pip install -e .`)
- Backend dev: `uvicorn app.main:app --reload`
- Frontend dev: `npm run dev`
- Tests: `pytest`
- Lint / format: `ruff check .` y `ruff format .`

## Convenciones
- Estilo de código delegado a ruff / prettier — no documentar reglas de estilo aquí.
- Secrets (API keys) SOLO por variables de entorno; nunca commitearlos.
- Decisiones de diseño se documentan como ADRs en `docs/adr/`.

## Estado
Fase actual: scaffolding inicial, pivote a sistema +EV recién decidido. Ver
`docs/adr/0002-sistema-apuestas-ev.md` (el ADR 0001 queda *Supersedido*). Orden de
construcción y contexto completo en ese ADR.
