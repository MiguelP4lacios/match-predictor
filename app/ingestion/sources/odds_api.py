"""Fuente The Odds API: cotizaciones en vivo (implementa OddsSource).

Free tier = 500 créditos/mes. costo = nº markets × nº regions. UNA request trae
TODOS los partidos del sport. Listar /sports es gratis (para verificar sport key).
"""

from collections.abc import Iterator
from datetime import UTC, datetime

import httpx

from app.ingestion.dto import RawOdds
from app.models.enums import DataSource


def _parse_dt(raw: str) -> datetime:
    """ISO con 'Z' -> datetime naive en UTC (consistente con el resto de la BD)."""
    return (
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
        .astimezone(UTC)
        .replace(tzinfo=None)
    )


class OddsApiSource:
    source = DataSource.ODDS_API

    def __init__(
        self,
        api_key: str | None,
        base_url: str,
        sport_key: str,
        regions: str,
        markets: str,
        timeout: float = 20.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._sport_key = sport_key
        self._regions = regions
        self._markets = markets
        self._timeout = timeout
        self.last_remaining: str | None = None  # cuota restante (header)

    def list_sports(self) -> list[dict]:
        """No cuenta cuota. Sirve para descubrir/confirmar la sport key del Mundial."""
        resp = httpx.get(
            f"{self._base_url}/sports",
            params={"apiKey": self._api_key},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def fetch_odds(self) -> Iterator[RawOdds]:
        if not self._api_key:
            raise RuntimeError("ODDS_API_KEY no configurada (ponela en .env)")

        captured_at = datetime.now(UTC).replace(tzinfo=None)
        resp = httpx.get(
            f"{self._base_url}/sports/{self._sport_key}/odds",
            params={
                "apiKey": self._api_key,
                "regions": self._regions,
                "markets": self._markets,
                "oddsFormat": "decimal",
            },
            timeout=self._timeout,
        )
        resp.raise_for_status()
        self.last_remaining = resp.headers.get("x-requests-remaining")

        for event in resp.json():
            home = event["home_team"]
            away = event["away_team"]
            commence = _parse_dt(event["commence_time"])
            for bm in event.get("bookmakers", []):
                book = bm["key"]
                for market in bm.get("markets", []):
                    mkey = market["key"]
                    for outcome in market.get("outcomes", []):
                        yield RawOdds(
                            source=self.source,
                            event_id=event["id"],
                            commence_time=commence,
                            home_team=home,
                            away_team=away,
                            bookmaker=book,
                            market_key=mkey,
                            outcome_name=outcome["name"],
                            price=float(outcome["price"]),
                            line=(
                                float(outcome["point"])
                                if outcome.get("point") is not None
                                else None
                            ),
                            captured_at=captured_at,
                        )
