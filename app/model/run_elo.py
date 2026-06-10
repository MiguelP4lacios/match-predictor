"""Runner del motor de Elo. Recalcula elo_rating desde cero.

docker compose run --rm api python -m app.model.run_elo
"""

from app.core.database import SessionLocal
from app.model.elo_engine import EloEngine


def main() -> None:
    print("Calculando Elo sobre los partidos jugados...")
    with SessionLocal() as session:
        result = EloEngine(session).compute()
    print("Resultado:")
    for key, value in result.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
