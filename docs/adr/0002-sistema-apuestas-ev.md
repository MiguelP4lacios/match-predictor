# ADR 0002 — Sistema de Predicción +EV para Apuestas (Selecciones)

- **Estado:** Aceptada
- **Fecha:** 2026-06-08
- **Supersede a:** [ADR 0001](0001-arquitectura.md)

## Contexto

El proyecto deja de ser un dashboard/demo descriptivo y pasa a ser un **sistema de
predicción para apostar con valor esperado positivo (+EV)** sobre fútbol de
**selecciones nacionales** (Mundial 2026 y competiciones de selecciones).

Premisas que definen la arquitectura:

- **No existe "la fija".** El objetivo no es acertar el ganador, sino detectar
  cuándo la cuota paga **más** que la probabilidad real (edge) y gestionar el
  bankroll. `edge = prob_modelo − prob_implícita_en_la_cuota`. Sin cuota, no hay
  edge medible.
- **Fútbol de selecciones es difícil de modelar**: pocos partidos, alta varianza,
  equipos con poca química. El predictor individual más fuerte y barato es el
  **Elo**; el xG fino casi no existe gratis a nivel selección.
- **Fuentes gratis primero**, con migración a pago una vez validado el edge. Exige
  una capa de fuente **intercambiable**.

### Hallazgos de la investigación de fuentes (verificados 2026-06-08)

- **Resultados históricos**: Kaggle `martj42` (1872→hoy, todas las confederaciones,
  clasificatorias, Nations League, amistosos). CSV, CC0. Sin xG, sin odds.
- **Elo**: `eloratings.net` (scraping TSV / mirror CSV en Kaggle).
- **xG (parcial)**: StatsBomb Open Data — solo torneos grandes; uso no comercial.
- **Vivo 2026**: API-Football free (100 req/día) + openfootball fallback.
- **Odds — el gran agujero**: NO hay histórico gratis y limpio de closing odds de
  selecciones. `football-data.co.uk` solo cubre clubes; The Odds API tiene
  histórico pero pago. **FBref** tiene xG de selecciones pero su ToS prohíbe
  scraping para productos (403 a bots) → descartado para ingesta persistente.

## Decisión

1. **Capa `DataSource` provider-agnostic.** Cada fuente (martj42, eloratings,
   StatsBomb, API-Football, The Odds API) implementa una interfaz común. El modelo,
   la API y el front no conocen la fuente concreta. Migrar gratis → pago = cambiar
   una implementación. Mismo criterio que `LLMProvider`.

2. **Captura propia de closing odds.** Como no hay histórico gratis, capturamos
   snapshots de cuotas en vivo (The Odds API free) hacia una tabla `odds_snapshot`
   desde ya, construyendo nuestro propio dataset limpio para medir edge. Prioridad
   alta por la ventana temporal del Mundial 2026.

3. **Modelo estadístico determinista, separado del LLM.**
   - **1X2 y Over/Under**: Dixon-Coles / Poisson bivariado sobre tasas de gol,
     ajustadas por fuerza (Elo) y ventaja de campo/neutralidad.
   - **Futures (avance/campeón)**: Monte Carlo sobre el bracket usando las
     probabilidades por partido.
   - Features primarias: **Elo + forma + goles**; xG como feature parcial donde
     StatsBomb lo provea.

4. **Backtesting y calibración obligatorios.** Antes de confiar en el modelo se
   reporta **Brier score**, **log-loss** y **curva de calibración** sobre histórico.
   Un modelo sin backtest no se usa para apostar.

5. **EV + staking.** Sobre prob. del modelo vs cuota se calcula EV; el stake se
   define con **Kelly fraccionado** (≈¼ Kelly), con límites de exposición por
   partido y jornada. Cada apuesta se registra para medir ROI y calibración real.

6. **Agentes que narran, no predicen.** El LLM explica las señales y el diagnóstico
   del modelo vía tools (`get_match_probabilities`, `get_value_signals`...). Nunca
   calcula ni inventa probabilidades, stats o edge.

7. **Backend FastAPI** sirve datos, probabilidades y señales desde Postgres
   (jamás API externa en caliente); SSE para el diagnóstico en streaming.

8. **Frontend React + Vite** consume la API y muestra señales y narración.

## Consecuencias

**Positivas**
- Arranque 100% gratis y honesto; escalado a pago sin reescribir arquitectura.
- Separación determinista/LLM → cero alucinación de números; señales auditables.
- Captura propia de odds = dataset limpio que pocos tienen.

**Negativas / a vigilar**
- **Sin odds históricas gratis**, el backtest de edge se apoya en datos que
  empezamos a capturar ahora → al inicio hay poca muestra. Se complementa con
  backtest de *calibración del modelo* (que sí se puede con histórico de resultados)
  aunque el backtest de *rentabilidad* tarde en madurar.
- xG de selecciones escaso → el modelo descansa en Elo/forma/goles.
- Selecciones = alta varianza; exige Kelly fraccionado y disciplina estricta.
- Más trabajo inicial: modelado estadístico + backtesting + pipeline de odds.

## Orden de construcción

1. Esqueleto + modelos de BD (incluye `odds_snapshot`, `bet_log`, `sync_log`).
2. Capa `DataSource` + ingesta histórica (martj42 + eloratings + StatsBomb).
3. 🔴 Capturador de odds en vivo (The Odds API) — prioridad por la ventana del Mundial.
4. Modelo determinista (Dixon-Coles/Poisson + Elo; Monte Carlo del bracket).
5. Backtesting + calibración (Brier/log-loss) + EV + Kelly.
6. API REST de lectura (datos, probabilidades, señales).
7. Capa de agentes (LLMProvider + tools + SSE) — narran el modelo.
8. Dashboard React.

## Roadmap de features predictivas (post-base, medidas por backtest)

Cada feature debe GANARSE su lugar demostrando que mejora el backtest (Brier/
log-loss). No se agregan "porque sí". Orden: modelo base de equipo (Elo) →
features de equipo (localía, descanso, forma) → features de jugador.

**Features de jugador** (avanzadas; requieren datos que NO existen gratis y
completos — son justo lo que las casas de apuestas pagan caro):

- **Forma reciente / rating** de jugadores clave (tipo SofaScore). Fuente de pago.
- **Disponibilidad**: lesiones, suspensiones, convocatoria y alineación probable.
  Lo más predictivo y lo más difícil: time-sensitive, de pago o manual.
- **Aporte goleador**: parcialmente disponible hoy (`goal_event`), pero incompleto
  (faltan goles) y con `scorer_name` como texto libre — sin entidad `player`
  normalizada (habría que crearla).
- **Forma en clubes**: xG/goles del jugador en su liga. Requiere ingestar datos de
  clubes (FBref/Understat) — una ingesta grande aparte.

Con datos gratis el modelo descansa en señales de EQUIPO. Estas features se evalúan
tras validar el edge de la base, con presupuesto de fuente en mano.

## Alternativas consideradas

- **Pagar fuentes desde el día uno** (StatsBomb/Opta, The Odds API histórico):
  mejor calidad de datos, pero sin validar primero que el sistema tiene edge.
  Descartada hasta validar gratis.
- **Usar FBref para xG de selecciones**: técnicamente posible, pero su ToS lo
  prohíbe para productos y bloquea bots. Descartada por riesgo legal/operativo.
- **Modelo basado solo en xG**: inviable gratis a nivel selección. Se usa Elo como
  predictor central.
- **Confiar la predicción al LLM**: rechazada de plano. El LLM no calibra
  probabilidades; sería teatro con plata real. El LLM solo narra.
