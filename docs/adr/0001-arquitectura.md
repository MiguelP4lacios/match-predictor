# ADR 0001 — Arquitectura de Stats + Diagnóstico con Agentes (Mundial 2026)

- **Estado:** ⚠️ Supersedida por [ADR 0002](0002-sistema-apuestas-ev.md) (2026-06-08)
- **Fecha:** 2026-06-08

> **Nota:** Este ADR describía un dashboard/demo descriptivo. El proyecto pivotó a
> un sistema de predicción +EV para apuestas reales sobre selecciones. Se conserva
> por trazabilidad de decisiones. Varios invariantes (separación determinista/LLM,
> provider-agnostic, no llamar al API en el request, datos vía tools) siguen
> vigentes y fueron reafirmados en el ADR 0002.

## Contexto

Queremos una app que muestre estadísticas del Mundial 2026 y use agentes de IA
para diagnosticar partidos y grupos, usando exclusivamente APIs gratuitas.

Restricciones relevantes:

- La API gratuita más rica es **API-Football** (api-sports.io): standings,
  fixtures, estadísticas de partido, eventos, alineaciones y jugadores. El
  Mundial es `league=1`, `season=2026`.
- El plan free de API-Football da **100 requests/día** (todos los endpoints,
  pero sin xG ni métricas avanzadas, que son de pago).
- **openfootball/worldcup.json** es dominio público, sin API key, ideal para el
  esqueleto estático (equipos, grupos, calendario).

Esa cuota de 100 req/día es la restricción que define toda la arquitectura.

## Decisión

1. **Capa de ingesta + caché.** Nunca se llama al API externo dentro del request
   del usuario. Un scheduler con cadencia adaptativa sincroniza hacia Postgres:
   estático (equipos/grupos/calendario) al arranque + refresco diario u
   openfootball; en vivo solo los partidos con estado `live`, cada 2–3 min y solo
   mientras duran. Una tabla `sync_log` con `last_fetched_at` por recurso evita
   pedir lo que ya está fresco.

2. **Backend FastAPI** que sirve grupos, partidos y stats desde Postgres, con
   endpoints de diagnóstico vía SSE para streaming.

3. **Lógica determinista separada del LLM.** Tabla de posiciones, criterios de
   desempate FIFA y probabilidades de avance (Monte Carlo sobre fixtures
   restantes) se calculan en código. El LLM únicamente narra/explica esos
   resultados; no calcula ni inventa números.

4. **Capa de agentes provider-agnostic** (igual que el sistema de trading
   previo): interfaz `LLMProvider` con implementaciones Anthropic / OpenAI /
   Ollama, configuración por agente. Roles:
   - Orquestador (router de intención).
   - Agente de partido (diagnóstico sobre stats + eventos).
   - Agente de grupo (escenarios de clasificación).
   - Agente de proyección (opcional, explica probabilidades ya calculadas).
   Los agentes obtienen datos vía tools que consultan la BD, no inyectando datos
   crudos en el prompt.

5. **Frontend React + Vite** que consume la API y muestra el diagnóstico en
   streaming.

## Consecuencias

**Positivas**
- 100 req/día alcanzan de sobra para uso personal/demo gracias al caché.
- La separación determinista/LLM hace confiable el producto (sin alucinación de
  estadísticas).
- La capa provider-agnostic permite cambiar de modelo sin tocar la lógica.

**Negativas / a vigilar**
- Sin xG en el plan free: el diagnóstico de partido es descriptivo, no de calidad
  de tiro.
- Para usuarios reales, 100 req/día se queda corto; el upgrade natural es Pro
  (~$19/mes, 7.500 req/día). La arquitectura no cambia: solo sube la cadencia del
  scheduler.
- La lógica determinista (desempates FIFA, Monte Carlo) es trabajo inicial extra.

## Alternativas consideradas

- **football-data.org**: 10 req/min en free, pero cobertura y profundidad de stats
  menores. Descartada como fuente principal.
- **Llamar al API en cada request con caché HTTP corto**: más simple, pero frágil
  frente a la cuota y a los picos de tráfico en vivo. Descartada.
- **Solo openfootball (sin API-Football)**: gratis e ilimitado, pero sin stats de
  partido en vivo suficientemente ricas para el diagnóstico. Se usa como
  complemento, no como única fuente.

## Orden de construcción

1. Esqueleto + modelos de datos (BD).
2. Ingesta (cliente API-Football + loader openfootball + scheduler).
3. API REST de lectura.
4. Lógica determinista (tabla, desempates, Monte Carlo).
5. Capa de agentes (LLMProvider + tools + roles + SSE).
6. Dashboard React.
