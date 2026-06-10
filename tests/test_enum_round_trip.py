"""Test de round-trip ORM para CompetitionKind.OTHER.

PRE-TASK 4.0: Verifica que 'OTHER' (UPPERCASE) es un label válido en el enum
PG competition_kind y que el ORM puede escribir y leer Competition.kind = OTHER.

ROJO hasta que M4 agregue el label 'OTHER'.  Después de `alembic upgrade head`
(que incluye M4) este test queda VERDE permanentemente.
"""


from app.models.competition import Competition
from app.models.enums import CompetitionKind


def test_competition_kind_other_round_trip(db_session):
    """ORM escribe CompetitionKind.OTHER → PG acepta → ORM lee el valor correcto."""
    comp = Competition(name="CONIFA World Football Cup TEST", kind=CompetitionKind.OTHER)
    db_session.add(comp)
    db_session.flush()  # lanza INSERT — falla si 'OTHER' no es un label PG válido

    db_session.refresh(comp)
    assert comp.kind == CompetitionKind.OTHER


def test_competition_kind_other_distinct_from_world_cup(db_session):
    """CompetitionKind.OTHER != CompetitionKind.WORLD_CUP — no hay confusión de labels."""
    comp = Competition(name="Viva World Cup TEST", kind=CompetitionKind.OTHER)
    db_session.add(comp)
    db_session.flush()

    db_session.refresh(comp)
    assert comp.kind != CompetitionKind.WORLD_CUP
    assert comp.kind == CompetitionKind.OTHER
