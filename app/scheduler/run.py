"""Worker del scheduler. Uso:

    python -m app.scheduler.run            # loop: captura cada N horas
    python -m app.scheduler.run --once     # captura una vez y sale (para probar)

Cadencia base por intervalo. Mejora futura: adaptativa (más seguido cerca de los
kickoffs para clavar la closing line), respetando la cuota de 500 créditos/mes.
"""

import argparse
import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from app.core.config import settings
from app.scheduler.jobs import capture_odds_job, make_odds_source

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
# Seguridad: httpx loguea la URL completa (incluye ?apiKey=...). Lo silenciamos
# para que la API key NUNCA quede en logs.
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("scheduler")


def main() -> None:
    parser = argparse.ArgumentParser(description="Worker de captura de odds")
    parser.add_argument(
        "--once", action="store_true", help="capturar una vez y salir (para probar)"
    )
    parser.add_argument(
        "--list-sports",
        action="store_true",
        help="listar sports de fútbol disponibles (GRATIS, no gasta cuota)",
    )
    args = parser.parse_args()

    if not settings.odds_api_key:
        log.warning(
            "ODDS_API_KEY no configurada — el capturador no hará nada hasta ponerla "
            "en .env y reiniciar este servicio."
        )

    if args.list_sports:
        source = make_odds_source()
        for s in source.list_sports():
            key, title = s.get("key", ""), s.get("title", "")
            if "soccer" in key or "world cup" in title.lower():
                print(f"{key:42} | {title} | active={s.get('active')}")
        return

    if args.once:
        log.info("Captura única: %s", capture_odds_job())
        return

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        capture_odds_job,
        "interval",
        hours=settings.odds_capture_interval_hours,
        id="capture_odds",
        next_run_time=None,
    )
    log.info(
        "Scheduler iniciado: captura cada %sh (sport=%s, regions=%s, markets=%s)",
        settings.odds_capture_interval_hours,
        settings.odds_sport_key,
        settings.odds_regions,
        settings.odds_markets,
    )
    scheduler.start()


if __name__ == "__main__":
    main()
