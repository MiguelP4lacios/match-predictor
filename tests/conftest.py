"""Fixtures compartidas para todos los tests.

DB isolation: cada test que use `db_session` corre dentro de un SAVEPOINT de
Postgres y hace ROLLBACK al terminar — la BD queda limpia sin necesidad de
truncar tablas.
"""

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

# La DATABASE_URL viene de la variable de entorno inyectada por docker compose
# (db:5432 dentro de la red).  En CI usa la misma env var.
from app.core.database import engine


@pytest.fixture()
def db_session():
    """Session SQLAlchemy aislada por SAVEPOINT.

    Patrón: connection → BEGIN → SAVEPOINT → yield → ROLLBACK (al SAVEPOINT) →
    ROLLBACK (al BEGIN) → close. La base de datos queda intacta para el próximo test.
    """
    connection = engine.connect()
    outer_tx = connection.begin()
    session = Session(bind=connection, autoflush=False, expire_on_commit=False)

    # Reiniciar el SAVEPOINT cada vez que un nested transaction termina, de modo
    # que el código bajo test pueda llamar session.flush() / session.commit() sin
    # romper el aislamiento.
    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, tx):
        if tx.nested and not tx._parent.nested:
            sess.begin_nested()

    session.begin_nested()  # SAVEPOINT inicial

    yield session

    session.close()
    outer_tx.rollback()
    connection.close()
