from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la app, leída de variables de entorno / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/match_predictor"
    )
    app_name: str = "match-predictor"
    debug: bool = False

    # --- The Odds API (capturador de odds) ---
    odds_api_key: str | None = None
    odds_api_base_url: str = "https://api.the-odds-api.com/v4"
    # Sport key del Mundial: a CONFIRMAR vía /v4/sports (gratis) cuando haya key.
    odds_sport_key: str = "soccer_fifa_world_cup"
    odds_regions: str = "eu"  # eu incluye Pinnacle (closing line = benchmark de edge)
    odds_markets: str = "h2h,totals"  # 1X2 + Over/Under (2 créditos/snapshot)
    odds_capture_interval_hours: int = 8


settings = Settings()
