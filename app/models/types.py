"""Tipos Enum de SQLAlchemy compartidos.

Se definen UNA sola vez y se reutilizan entre tablas. Si dos columnas usaran
`Enum(MiEnum, name="x")` por separado, Postgres intentaría `CREATE TYPE x` dos
veces y fallaría la migración. Compartir la instancia evita ese gotcha.
"""

from sqlalchemy import Enum

from app.models.enums import (
    BetKind,
    BetMode,
    BetStatus,
    CompetitionKind,
    Confederation,
    DataSource,
    MarketType,
    MatchStage,
    MatchStatus,
)

confederation_type = Enum(Confederation, name="confederation")
competition_kind_type = Enum(CompetitionKind, name="competition_kind")
data_source_type = Enum(DataSource, name="data_source")
match_status_type = Enum(MatchStatus, name="match_status")
match_stage_type = Enum(MatchStage, name="match_stage")
market_type_type = Enum(MarketType, name="market_type")
bet_mode_type = Enum(BetMode, name="bet_mode")
bet_status_type = Enum(BetStatus, name="bet_status")
bet_kind_type = Enum(BetKind, name="bet_kind")
