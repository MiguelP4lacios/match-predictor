"""Runner de ingesta histórica. Uso:

    uv run python -m app.ingestion.run            # baja CSV (si faltan) y carga
    uv run python -m app.ingestion.run --force    # recarga aunque ya esté sincronizado
    uv run python -m app.ingestion.run --no-download
"""

import argparse

from app.core.database import SessionLocal
from app.ingestion.pipeline import ResultsIngestionPipeline
from app.ingestion.sources.martj42 import Martj42Source


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingesta histórica de selecciones")
    parser.add_argument("--force", action="store_true", help="recargar aunque exista")
    parser.add_argument("--no-download", action="store_true", help="no bajar CSV")
    args = parser.parse_args()

    source = Martj42Source()
    if not args.no_download:
        print("Descargando CSV de martj42 (si faltan)...")
        source.download()

    print("Cargando resultados históricos...")
    with SessionLocal() as session:
        pipeline = ResultsIngestionPipeline(session, source)
        result = pipeline.run(force=args.force)

    print("Resultado:")
    for key, value in result.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
