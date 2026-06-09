"""Fuente martj42: resultados históricos de selecciones (1872 -> hoy).

CSV de dominio público (CC0). Implementa ResultsSource + GoalSource + ShootoutSource.
Usa solo stdlib (csv, urllib) para no sumar dependencias en esta fase.
"""

import csv
import urllib.request
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from app.ingestion.dto import RawGoal, RawMatch, RawShootout
from app.models.enums import DataSource

DEFAULT_BASE_URL = "https://raw.githubusercontent.com/martj42/international_results/master"
DEFAULT_DATA_DIR = Path("data/raw/martj42")
_FILES = ("results.csv", "goalscorers.csv", "shootouts.csv")


def _parse_int(raw: str | None) -> int | None:
    """Robusto ante datos reales: '', 'NA', 'NaN' -> None."""
    raw = (raw or "").strip()
    try:
        return int(raw)
    except ValueError:
        return None


def _parse_bool(raw: str | None) -> bool:
    return (raw or "").strip().upper() == "TRUE"


def _parse_minute(raw: str | None) -> int | None:
    """'44' -> 44, '90+3' -> 90, '' -> None."""
    raw = (raw or "").strip()
    digits = ""
    for ch in raw:
        if ch.isdigit():
            digits += ch
        else:
            break
    return int(digits) if digits else None


def _parse_date(raw: str) -> date:
    return date.fromisoformat(raw.strip())


class Martj42Source:
    source = DataSource.MARTJ42

    def __init__(
        self,
        data_dir: Path = DEFAULT_DATA_DIR,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        self._data_dir = data_dir
        self._base_url = base_url

    def download(self) -> None:
        """Baja los CSV si faltan (idempotente)."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        for name in _FILES:
            target = self._data_dir / name
            if target.exists():
                continue
            urllib.request.urlretrieve(f"{self._base_url}/{name}", target)  # noqa: S310

    def _rows(self, filename: str) -> Iterator[dict[str, str]]:
        path = self._data_dir / filename
        with path.open(encoding="utf-8", newline="") as fh:
            yield from csv.DictReader(fh)

    def fetch_matches(self) -> Iterator[RawMatch]:
        for r in self._rows("results.csv"):
            yield RawMatch(
                source=self.source,
                match_date=_parse_date(r["date"]),
                home_team=r["home_team"].strip(),
                away_team=r["away_team"].strip(),
                home_score=_parse_int(r["home_score"]),
                away_score=_parse_int(r["away_score"]),
                tournament=r["tournament"].strip(),
                city=(r["city"].strip() or None),
                country=(r["country"].strip() or None),
                neutral=_parse_bool(r["neutral"]),
            )

    def fetch_goals(self) -> Iterator[RawGoal]:
        for r in self._rows("goalscorers.csv"):
            yield RawGoal(
                source=self.source,
                match_date=_parse_date(r["date"]),
                home_team=r["home_team"].strip(),
                away_team=r["away_team"].strip(),
                scoring_team=r["team"].strip(),
                scorer=(r["scorer"].strip() or None),
                minute=_parse_minute(r["minute"]),
                own_goal=_parse_bool(r["own_goal"]),
                penalty=_parse_bool(r["penalty"]),
            )

    def fetch_shootouts(self) -> Iterator[RawShootout]:
        for r in self._rows("shootouts.csv"):
            yield RawShootout(
                source=self.source,
                match_date=_parse_date(r["date"]),
                home_team=r["home_team"].strip(),
                away_team=r["away_team"].strip(),
                winner=r["winner"].strip(),
            )
