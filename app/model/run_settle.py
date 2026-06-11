"""Runner del motor de liquidación. Liquida apuestas PENDING contra partidos FINISHED.

docker compose run --rm api python -m app.model.run_settle
"""

import sys

from app.core.database import SessionLocal
from app.model.settle import settle_bets


def main() -> None:
    print("Liquidando apuestas PENDING contra partidos FINISHED...")
    with SessionLocal() as session:
        result = settle_bets(session)
    print(f"Settled: {result['settled']} bets")
    if result["settled"] > 0:
        print(f"  WON:  {result['won']}")
        print(f"  LOST: {result['lost']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
