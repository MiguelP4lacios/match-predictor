"""Motor de predicción 1X2: escribe 3 filas Prediction por partido (point-in-time).

Lookup anti-look-ahead:
  SELECT rating WHERE team_id=:t AND rating_date < :d ORDER BY rating_date DESC LIMIT 1
  Si no hay fila previa → rating=1500, low_confidence=True.

Idempotencia mediante SELECT + UPDATE / INSERT explícito.
Nota: el constraint uq_prediction_identity incluye outcome_team_id (nullable) desde m9.
PostgreSQL trata NULLs como distintos en UNIQUE, por lo que el ON CONFLICT clásico
no funciona para 1X2 (outcome_team_id=NULL). Se usa SELECT-before-write en su lugar.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model.probabilities import predict_proba
from app.model.ratings import HOME_ADVANTAGE, lookup_rating
from app.models import Match, ModelVersion
from app.models.enums import MarketType
from app.models.model import Prediction


def predict_match(
    session: Session,
    match_id: int,
    model_version_id: int,
) -> list[int]:
    """Escribe 3 Prediction rows para el partido dado y devuelve sus IDs.

    Usa upsert (INSERT ... ON CONFLICT DO UPDATE) para idempotencia.

    Returns:
        Lista de IDs de las 3 predicciones (HOME, DRAW, AWAY).
    """
    match: Match = session.get(Match, match_id)
    if match is None:
        raise ValueError(f"match_id={match_id} no encontrado")

    mv: ModelVersion = session.get(ModelVersion, model_version_id)
    if mv is None:
        raise ValueError(f"model_version_id={model_version_id} no encontrado")

    # Lookup point-in-time para cada equipo
    home_rating, home_lc = lookup_rating(session, match.home_team_id, match.match_date)
    away_rating, away_lc = lookup_rating(session, match.away_team_id, match.match_date)

    # low_confidence si CUALQUIERA de los dos equipos no tiene rating previo
    low_confidence = home_lc or away_lc

    # Diferencia de Elo con ventaja de localía (0 si sede neutral)
    advantage = 0.0 if match.neutral_site else HOME_ADVANTAGE
    elo_diff = (home_rating + advantage) - away_rating

    probs = predict_proba(mv.params_json, elo_diff=elo_diff, neutral=match.neutral_site)

    outcomes = [
        ("HOME", probs["home"]),
        ("DRAW", probs["draw"]),
        ("AWAY", probs["away"]),
    ]

    ids: list[int] = []
    for outcome_code, probability in outcomes:
        # SELECT primero para idempotencia (ON CONFLICT no funciona con outcome_team_id NULL)
        existing = session.scalar(
            select(Prediction).where(
                Prediction.model_version_id == model_version_id,
                Prediction.match_id == match_id,
                Prediction.market_type == MarketType.MATCH_1X2,
                Prediction.outcome_code == outcome_code,
                Prediction.outcome_team_id.is_(None),
            )
        )
        if existing is not None:
            existing.probability = round(probability, 5)
            existing.low_confidence = low_confidence
            session.flush()
            ids.append(existing.id)
        else:
            pred = Prediction(
                match_id=match_id,
                competition_id=match.competition_id,
                model_version_id=model_version_id,
                market_type=MarketType.MATCH_1X2,
                outcome_code=outcome_code,
                probability=round(probability, 5),
                low_confidence=low_confidence,
                outcome_team_id=None,
            )
            session.add(pred)
            session.flush()
            ids.append(pred.id)

    return ids
