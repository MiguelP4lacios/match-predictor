from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# SQLAlchemy SÍNCRONO a propósito: la ingesta es batch (CSV, scraping) y el
# scheduler es sync; async añadiría complejidad sin beneficio en esta fase.
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Dependencia FastAPI: una sesión por request, siempre cerrada."""
    with SessionLocal() as session:
        yield session
