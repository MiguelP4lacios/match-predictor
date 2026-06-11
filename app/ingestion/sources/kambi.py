"""Fuente Kambi: cotizaciones de apuestas (implementa OddsSource).

FLAG-GATED: solo se instancia cuando KAMBI_ENABLED=true en config.
Por defecto OFF — el endpoint devuelve 429 desde IPs de datacenter.
NUNCA hacer requests live en tests; usar fixtures.

Fragilidad conocida (429):
  Kambi aplica rate-limiting agresivo por IP. Desde IPs de datacenter
  el 429 es casi inmediato. Se recomienda ejecutar solo desde IPs residenciales
  o configurar un proxy. Este adaptador es un enhancement, no una dependencia
  del pipeline principal.

Estructura del JSON Kambi (operator/events.json):
  events[].event.{id, name, start, homeName, awayName}
  events[].betOffers[].{criterion.id, betOfferType.id, status, outcomes[]}
  outcomes[].{id, label, englishLabel, odds (milli), participant}

Solo se procesan betOffers con:
  - criterion.id == 1001374577 (Full Time — 1X2 estándar)
  - status == "OPEN"
"""

from collections.abc import Iterator
from datetime import UTC, datetime

import httpx

from app.ingestion.dto import RawOdds
from app.models.enums import DataSource

# ---------------------------------------------------------------------------
# Overrides de nombres de equipos (canonical → Kambi participant name)
# Mínimo 6 entradas según design.
# ---------------------------------------------------------------------------

_KAMBI_NAME_OVERRIDES: dict[str, str] = {
    "USA": "United States",
    "EE.UU.": "United States",
    "Corea del Sur": "South Korea",
    "Korea Republic": "South Korea",
    "Irán": "Iran",
    "Bosnia": "Bosnia & Herzegovina",
}

# Full Time criterion ID de Kambi (invariante del proveedor)
_FULL_TIME_CRITERION_ID = 1001374577


class KambiOddsSource:
    """OddsSource de Kambi para 1X2 Full Time.

    Solo Full Time (criterion_id=1001374577) + OPEN son procesados.
    odds milli se dividen por 1000 para obtener cuota decimal.
    participant se normaliza vía _KAMBI_NAME_OVERRIDES.

    Uso:
        source = KambiOddsSource(operator="betplay", base_url="https://eu.sb-odds.kambi.com")
        for odd in source.fetch_odds():
            ...
    """

    source = DataSource.KAMBI

    def __init__(
        self,
        operator: str,
        base_url: str,
        timeout: float = 20.0,
    ) -> None:
        self._operator = operator
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def fetch_odds(self) -> Iterator[RawOdds]:
        """Descarga eventos del operador y emite RawOdds para cada outcome Full Time/OPEN.

        Warning: puede devolver 429 desde IPs de datacenter (ver docstring del módulo).
        """
        url = f"{self._base_url}/{self._operator}/events.json"
        resp = httpx.get(url, params={"lang": "en_US"}, timeout=self._timeout)
        if resp.status_code >= 400:
            raise RuntimeError(f"Kambi {resp.status_code} {resp.reason_phrase} — {url}")

        data = resp.json()
        yield from self._parse_events(data.get("events", []))

    def _parse_events(self, events: list[dict]) -> Iterator[RawOdds]:
        """Parsea la lista de events del JSON Kambi y emite RawOdds.

        Método separado para facilitar tests con fixtures (sin httpx live).
        """
        captured_at = datetime.now(UTC).replace(tzinfo=None)

        for item in events:
            event = item.get("event", {})
            event_id = str(event.get("id", ""))
            home_team = event.get("homeName", "")
            away_team = event.get("awayName", "")

            # Parse start time
            raw_start = event.get("start", "")
            try:
                commence_time = (
                    datetime.fromisoformat(raw_start.replace("Z", "+00:00"))
                    .astimezone(UTC)
                    .replace(tzinfo=None)
                )
            except (ValueError, AttributeError):
                commence_time = captured_at

            for offer in item.get("betOffers", []):
                criterion = offer.get("criterion", {})
                # Only Full Time
                if criterion.get("id") != _FULL_TIME_CRITERION_ID:
                    continue
                # Only OPEN
                if offer.get("status") != "OPEN":
                    continue

                for outcome in offer.get("outcomes", []):
                    milli_odds = outcome.get("odds", 0)
                    price = milli_odds / 1000.0

                    participant = outcome.get("participant", "")
                    # Apply name override if available
                    canonical = _KAMBI_NAME_OVERRIDES.get(participant, participant)
                    outcome_name = canonical or outcome.get("englishLabel", "")

                    yield RawOdds(
                        source=self.source,
                        event_id=event_id,
                        commence_time=commence_time,
                        home_team=home_team,
                        away_team=away_team,
                        bookmaker=self._operator,
                        market_key="h2h",
                        outcome_name=outcome_name,
                        price=price,
                        line=None,
                        captured_at=captured_at,
                    )
