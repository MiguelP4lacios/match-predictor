"""Runner del motor de liquidación. Liquida apuestas PENDING contra partidos FINISHED.

docker compose run --rm api python -m app.model.run_settle
"""

import sys

from app.core.database import SessionLocal
from app.model.settle import settle_bets, settle_parlays


def main() -> None:
    print("Liquidando apuestas PENDING contra partidos FINISHED...")
    with SessionLocal() as session:
        result_bets = settle_bets(session)
        result_parlays = settle_parlays(session)

    total_settled = result_bets["settled"] + result_parlays["settled"]
    won_s, lost_s = result_bets["won"], result_bets["lost"]
    won_p, lost_p = result_parlays["won"], result_parlays["lost"]
    print(f"Simples settled:  {result_bets['settled']} (WON={won_s}, LOST={lost_s})")
    print(f"Parlays settled:  {result_parlays['settled']} (WON={won_p}, LOST={lost_p})")
    print(f"Total settled: {total_settled}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
