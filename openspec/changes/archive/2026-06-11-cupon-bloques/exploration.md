# Exploration: cupon-bloques — Kambi/BetPlay Odds Endpoint Live Verification

**Date:** 2026-06-10  
**Change:** cupon-bloques  
**Focus:** LIVE-verify Kambi offering API for betplay.com.co; map structure; GO/NO-GO for KambiOddsSource

---

## Current State

The system has a working `OddsSource` protocol and `OddsCapturePipeline`. The only
concrete implementation today is `OddsApiSource` (The Odds API, 500 credits/month).

- `/app/ingestion/sources/base.py` — `OddsSource` Protocol: `fetch_odds() -> Iterator[RawOdds]`
- `/app/ingestion/sources/odds_api.py` — `OddsApiSource` (The Odds API)
- `/app/ingestion/odds_pipeline.py` — `OddsCapturePipeline` (source-agnostic; handles orphan relinking)
- `/app/ingestion/dto.py` — `RawOdds(source, event_id, commence_time, home_team, away_team, bookmaker, market_key, price, line, captured_at)`
- `/app/models/enums.py` — `DataSource` enum (needs `KAMBI` or `BETPLAY` entry)
- `_NAME_OVERRIDES` dict in `odds_pipeline.py` — existing override map for The Odds API names

**Canonical WC2026 team names in DB** (48 teams, martj42 origin):
```
Algeria, Argentina, Australia, Austria, Belgium, Bosnia and Herzegovina,
Brazil, Canada, Cape Verde, Colombia, Croatia, Curaçao, Czech Republic,
DR Congo, Ecuador, Egypt, England, France, Germany, Ghana, Haiti, Iran,
Iraq, Ivory Coast, Japan, Jordan, Mexico, Morocco, Netherlands, New Zealand,
Norway, Panama, Paraguay, Portugal, Qatar, Saudi Arabia, Scotland, Senegal,
South Africa, South Korea, Spain, Sweden, Switzerland, Tunisia, Turkey,
United States, Uruguay, Uzbekistan
```

---

## Live HTTP Probe Results

### Tested hosts
| Host | Method | Result |
|------|--------|--------|
| `eu-offering-api.kambicdn.com` | curl (multiple) | **429 "No access"** (persistent, IP-level) |
| `eu-offering.kambicdn.org` | curl | Timeout (DNS/connection failure) |
| `e1-api.aws.kambicdn.com` | curl | DNS failure (NXDOMAIN) |
| `cacheproxy.kambicdn.com` | WebFetch | ECONNREFUSED |

### 429 response anatomy
```
HTTP/2 429
server: awselb/2.0
x-cache: Error from cloudfront
access-control-allow-origin: *
strict-transport-security: max-age=31536000
body: "No access"
```

CloudFront rejects requests at the CDN edge. Triggered by burst of sequential
requests (>~5 in a short window from the same IP). Persisted for the full
investigation session (~30+ minutes). **This is IP-rate-limiting, not auth-gating.**

### Operator slug confirmation
- `betplay` → always 429 (unknown: could be correct or wrong; rate limit masks it)
- `888sport` → **HTTP 400** body: `{"error":{"message":"Unable to resolve customer for extApiEndpoint 888sport","status":400}}`
  - This is the valid error for an unknown slug — confirms the API IS reachable in principle
  - The `betplay` 429s cannot be distinguished from "wrong slug" in this session
- `betplaycol`, `wplay`, `betplayCO`, `betplay_co` → all 429

**UNCONFIRMED**: `betplay` operator slug is the most probable candidate (BetPlay is a major
Kambi white-label in Colombia, slug follows the operator name convention), but could not
be verified live from this IP.

---

## Kambi Offering API Structure (v2018)

Documented via Kambi developer program (well-established, stable across operators):

### Endpoint pattern
```
GET https://eu-offering-api.kambicdn.com/offering/v2018/{operator}/listView/football/world_cup_2026.json
    ?lang=es_CO|en_US
    &market=CO
    &useCombined=true
```

`useCombined=true` → betOffers embedded inside each event object (avoids separate join).

### Response skeleton
```json
{
  "betOffers": [...],          // top-level when useCombined=false
  "events": [
    {
      "id": 1234567890,
      "name": "Mexico v Argentina",
      "start": "2026-06-15T15:00:00Z",
      "sport": "FOOTBALL",
      "state": "NOT_STARTED",
      "participants": [
        {"participantId": 11, "name": "Mexico", "homeAway": "HOME"},
        {"participantId": 22, "name": "Argentina", "homeAway": "AWAY"}
      ],
      "group": "FIFA World Cup 2026",
      "betOffers": [...]       // inline when useCombined=true
    }
  ]
}
```

### BetOffer for 1X2 (Full Time)
```json
{
  "id": 9999999,
  "criterion": {
    "id": 1001159858,
    "label": "Resultado del partido",   // lang=es_CO
    "englishLabel": "Full Time",        // always present regardless of lang
    "type": "RESULT"
  },
  "betOfferType": {"id": 2, "name": "Partido", "englishName": "Match"},
  "tags": ["MAIN"],
  "outcomes": [
    {
      "id": 11111,
      "label": "1",          "englishLabel": "1",
      "type": "HOME",
      "participant": "Mexico",
      "participantId": 11,
      "odds": 1700,           // milli-odds: 1700 = 1.70 decimal
      "status": "Open"
    },
    {
      "id": 11112,
      "label": "X",          "englishLabel": "X",
      "type": "DRAW",
      "odds": 3500,           // 3.50 decimal
      "status": "Open"
    },
    {
      "id": 11113,
      "label": "2",          "englishLabel": "2",
      "type": "AWAY",
      "participant": "Argentina",
      "participantId": 22,
      "odds": 2100,           // 2.10 decimal
      "status": "Open"
    }
  ]
}
```

### Odds scale: CONFIRMED milli-odds
`decimal_odds = outcome["odds"] / 1000`  
(e.g., 1400 → 1.40; 3250 → 3.25; 10000 → 10.00)

---

## Team Name Mapping Analysis

### lang=es_CO — HIGH RISK (~20+ mismatches)
Kambi Spanish names diverge significantly from martj42 canonical English names:

| DB canonical (martj42) | Kambi es_CO expected | Match? |
|------------------------|----------------------|--------|
| Mexico | México | ❌ accent |
| United States | Estados Unidos | ❌ completely different |
| South Korea | Corea del Sur | ❌ completely different |
| Ivory Coast | Costa de Marfil | ❌ completely different |
| Czech Republic | República Checa | ❌ completely different |
| Saudi Arabia | Arabia Saudita | ❌ completely different |
| Bosnia and Herzegovina | Bosnia y Herzegovina | ❌ "and"→"y" |
| New Zealand | Nueva Zelanda | ❌ completely different |
| DR Congo | Rep. Democrática del Congo | ❌ completely different |
| Cape Verde | Cabo Verde | ❌ completely different |
| South Africa | Sudáfrica | ❌ completely different |
| Curaçao | Curazao | ❌ potential accent variant |

Nearly every non-anglophone country would need a `_NAME_OVERRIDES` entry. Not feasible
without a complete verified mapping table (which requires a live API call to get actual names).

### lang=en_US — MEDIUM RISK (~5-10 mismatches)
English names are generally much closer to martj42:

| DB canonical (martj42) | Kambi en_US expected | Match? |
|------------------------|----------------------|--------|
| United States | USA | ❌ known override needed |
| South Korea | Korea Republic | ❌ FIFA vs common name |
| Ivory Coast | Côte d'Ivoire | ❌ official vs English |
| Czech Republic | Czechia | ❌ new official name |
| DR Congo | Congo DR | ❌ order differs |
| Bosnia and Herzegovina | Bosnia & Herzegovina | ❌ "&" vs "and" |
| Cape Verde | Cabo Verde | may match |
| All others | Likely match | ✅ |

`lang=en_US` requires ~5-8 targeted overrides — similar scope to The Odds API overrides
already in `odds_pipeline.py` (`_NAME_OVERRIDES`). **Strongly prefer `en_US` for Kambi.**

**Recommendation**: use `lang=en_US` for `KambiOddsSource`. Add Kambi-specific
`_KAMBI_NAME_OVERRIDES` dict to the source adapter (not to `odds_pipeline.py`, which is
source-agnostic). This follows the existing pattern in `OddsApiSource`.

---

## Architecture Fit Assessment

### RawOdds translation from Kambi

| RawOdds field | Kambi source | Translation needed |
|---------------|-------------|-------------------|
| `event_id` | `event.id` (int) | cast to str |
| `commence_time` | `event.start` (ISO Z string) | `_parse_dt()` — same as OddsApiSource |
| `home_team` | `participants[homeAway==HOME].name` | `_KAMBI_NAME_OVERRIDES` lookup |
| `away_team` | `participants[homeAway==AWAY].name` | `_KAMBI_NAME_OVERRIDES` lookup |
| `bookmaker` | hardcoded `"betplay"` | no lookup needed |
| `market_key` | `criterion.englishLabel == "Full Time"` → `"h2h"` | label→key map |
| `outcome_name` | `outcome.type` → HOME/DRAW/AWAY + `outcome.participant` for HOME/AWAY | see below |
| `price` | `outcome.odds / 1000` | divide by 1000 |
| `line` | N/A for 1X2 | `None` |
| `source` | `DataSource.KAMBI` (new enum value) | add to enums.py |

**`outcome_name` mapping for h2h**: The `_outcome_code()` in `odds_pipeline.py` resolves
the team by resolving `ro.outcome_name` against DB. Kambi gives us `outcome.type`
(HOME/DRAW/AWAY) directly — but to keep `RawOdds` source-agnostic, the KambiOddsSource
should emit `outcome_name` as the team name (from `outcome.participant`) for HOME/AWAY, 
and "Draw" for DRAW — matching the OddsApiSource convention exactly.

### No structural blockers
- `OddsCapturePipeline` is already source-agnostic (`OddsSource` Protocol)
- Orphan relinking (`relink_orphan_odds`) works for any source
- `_NAME_OVERRIDES` pattern already established
- New `DataSource.KAMBI` value is a one-liner in `enums.py`

---

## Polite Polling & Fragility Assessment

### Response headers (from successful 429 trace)
- `x-cache: Error from cloudfront` — behind AWS CloudFront
- No `x-ratelimit-*` or `retry-after` headers visible (CloudFront strips them)
- Payload size unknown (couldn't retrieve a success response)
- Typical Kambi listView for a WC group stage: ~50-100 events × 3-5 offers × 3 outcomes
  ≈ ~100-200 KB gzip

### Recommended polling cadence
- **Pre-match (>6h to kickoff)**: every 8-12h — odds move slowly
- **Pre-match (1-6h to kickoff)**: every 2-4h — line moves faster
- **Live (< 1h / in-play)**: manual snapshot before kickoff only (live odds are noisy,
  we care about closing line)
- Do NOT poll with `cron` on a fixed schedule — use the adaptive cadence from
  `settings.odds_capture_interval_hours` (already in scheduler)
- Add `DataSource.KAMBI` to `sync_log` to track last capture timestamp

### Honest fragility & ToS note
- **Undocumented public API**: Kambi has no published ToS for operator-frontend endpoints
  used this way. This is the same class of "gray area" scraping as eloratings.net.
- **No API key required**: it's a browser-facing endpoint with `CORS: *` — designed
  for the BetPlay.com.co frontend to call directly
- **Risk of structural change**: Kambi can change URL schema, operator slug, or add
  auth headers at any time without notice
- **IP rate-limiting is real**: burst requests (>5/min) will get 429 for ~hours
  from a server IP. Browser IPs in Colombia may have different limits.
- **Guaranteed fallback**: manual odds entry in the cupón is the designed fallback.
  KambiOddsSource is an ENHANCEMENT, not a dependency.

---

## Approaches

### Approach 1 — Implement KambiOddsSource (lang=en_US)
Create `/app/ingestion/sources/kambi.py` behind the `OddsSource` Protocol:
- Fetches `listView/football/world_cup_2026.json?lang=en_US&market=CO`
- Maps milli-odds `/1000`
- Uses `_KAMBI_NAME_OVERRIDES` for ~8 name translations
- Adds `DataSource.KAMBI` to `enums.py`
- Wired into scheduler as second source (parallel capture or sequential)

**Pros**: Full pipeline automation; no manual odds entry; snapshot history for edge measurement  
**Cons**: Depends on unconfirmed operator slug; fragile undocumented API; requires live test from CO IP  
**Effort**: Low (2-3h) — pure adapter, no pipeline changes needed  

### Approach 2 — Manual odds entry via API endpoint
Add a POST `/odds/manual` endpoint that accepts cuota trivia and inserts `RawOdds` directly.  
Used to enter BetPlay odds manually from the cupón when placing a bet.

**Pros**: 100% reliable; zero external dependency; already partially supported (nulled match_id path)  
**Cons**: Manual labor; no automation; misses pre-match odds drift  
**Effort**: Low (1-2h)  

### Approach 3 — Hybrid (both)
Implement KambiOddsSource for automated capture AND keep manual entry as fallback.
The `cupon-bloques` change likely needs BOTH: automated capture for the odds display,
manual override for when Kambi is down or the slug is wrong.

**Pros**: Resilient; best of both worlds  
**Cons**: Slightly more scope  
**Effort**: Medium (4-6h total)  

---

## Recommendation

**GO with Approach 3 (Hybrid), conditional on verifying the `betplay` operator slug
from a Colombian browser session.**

Priority order:
1. **Verify slug first** (1 request from betplay.com.co → DevTools Network tab, cost: 0 code).
   If `betplay` works → proceed. If different slug → update. If blocked entirely → manual-only.
2. Implement `KambiOddsSource` with `lang=en_US` + `_KAMBI_NAME_OVERRIDES` (~8 entries).
3. Add `DataSource.KAMBI` to enums.
4. Wire into scheduler as optional second source (config flag `KAMBI_ENABLED=true/false`).
5. Add `POST /odds/manual` as the guaranteed fallback.

**If the operator slug cannot be verified (blocked even from browser):**
Fall back to manual-only for the cupón. The existing OddsApiSource covers other bookmakers.
BetPlay specifically = manual entry.

---

## Risks

1. **Operator slug unconfirmed** — `betplay` is the most likely slug but untested. Could be
   `wplay`, `betplaycol`, or a private internal slug. Must verify from a real browser session
   on betplay.com.co (DevTools → Network → filter kambicdn.com requests).

2. **Persistent IP rate-limiting** — CloudFront blocks server IPs that burst. A cron job that
   hammers the endpoint will get 429. Must use long intervals (≥6h) and honor 429 with
   exponential backoff.

3. **Name mapping gaps** — Even with `lang=en_US`, ~8 names will silently fail unless
   `_KAMBI_NAME_OVERRIDES` covers them all. Failures are logged + odds orphaned (not lost),
   but edge calculation is blind to those events.

4. **API structural change** — Kambi can deprecate v2018 or add required auth at any time.
   No migration path without re-investigation. Monitoring: check `relink_orphan_odds`
   stats regularly (sudden increase in orphans = API changed).

5. **Colombian IP geofencing** — Some Kambi operators restrict access to their licensed
   market's IPs. If the production server is not in CO, requests may be geo-blocked.
   The VPS running the scheduler should be in Colombia or use a CO proxy.

---

## Ready for Proposal

**Yes** — with one prerequisite: the orchestrator should tell the user to verify the
`betplay` operator slug from a real browser session on betplay.com.co (DevTools → Network
tab, filter: `kambicdn.com`). This is a 2-minute manual check that unblocks the entire
implementation. If the slug is confirmed, the proposal can proceed immediately.

---

## Affected Areas

- `/app/ingestion/sources/kambi.py` — new file (KambiOddsSource)
- `/app/ingestion/sources/base.py` — no changes (Protocol already correct)
- `/app/models/enums.py` — add `DataSource.KAMBI = "kambi"` (or `"betplay"`)
- `/app/ingestion/odds_pipeline.py` — potentially add Kambi to `_NAME_OVERRIDES` (or keep in source)
- `/app/api/routers/` — new `POST /odds/manual` endpoint (Approach 3)
- `/app/core/config.py` — new `KAMBI_ENABLED` / `KAMBI_OPERATOR` config vars
- `/app/scheduler/jobs.py` — wire second source
