"""Motor de predicción 1X2: escribe 3 filas Prediction por partido (point-in-time).

Lookup anti-look-ahead:
  SELECT rating WHERE team_id=:t AND rating_date < :d ORDER BY rating_date DESC LIMIT 1
  Si no hay fila previa → rating=1500, low_confidence=True.

Upsert idempotente sobre uq_prediction_identity
  (model_version_id, match_id, market_type, outcome_code).
"""

from sqlalchemy.dialects.postgresql import insert as pg_insert
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
        stmt = (
            pg_insert(Prediction)
            .values(
                match_id=match_id,
                competition_id=match.competition_id,
                model_version_id=model_version_id,
                market_type=MarketType.MATCH_1X2,
                outcome_code=outcome_code,
                probability=round(probability, 5),
                low_confidence=low_confidence,
            )
            .on_conflict_do_update(
                constraint="uq_prediction_identity",
                set_={
                    "probability": round(probability, 5),
                    "low_confidence": low_confidence,
                },
            )
            .returning(Prediction.id)
        )
        row_id = session.execute(stmt).scalar_one()
        ids.append(row_id)

    session.flush()
    return ids
