import enum


class Confederation(enum.StrEnum):
    UEFA = "UEFA"
    CONMEBOL = "CONMEBOL"
    CONCACAF = "CONCACAF"
    CAF = "CAF"
    AFC = "AFC"
    OFC = "OFC"


class CompetitionKind(enum.StrEnum):
    WORLD_CUP = "world_cup"
    CONTINENTAL = "continental"
    QUALIFIER = "qualifier"
    NATIONS_LEAGUE = "nations_league"
    FRIENDLY = "friendly"
    OTHER = "other"


class DataSource(enum.StrEnum):
    """Fuentes detrás de la capa DataSource provider-agnostic."""

    MARTJ42 = "martj42"
    ELORATINGS = "eloratings"
    API_FOOTBALL = "api_football"
    STATSBOMB = "statsbomb"
    ODDS_API = "odds_api"
    KAMBI = "kambi"


class MatchStatus(enum.StrEnum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"


class MatchStage(enum.StrEnum):
    GROUP = "group"
    ROUND_OF_32 = "R32"
    ROUND_OF_16 = "R16"
    QUARTER_FINAL = "QF"
    SEMI_FINAL = "SF"
    THIRD_PLACE = "third_place"
    FINAL = "final"
    QUALIFIER = "qualifier"
    FRIENDLY = "friendly"


class MarketType(enum.StrEnum):
    MATCH_1X2 = "MATCH_1X2"
    OVER_UNDER = "OVER_UNDER"
    OUTRIGHT_WINNER = "OUTRIGHT_WINNER"
    GROUP_ADVANCE = "GROUP_ADVANCE"


class BetMode(enum.StrEnum):
    PAPER = "paper"
    REAL = "real"


class BetStatus(enum.StrEnum):
    PENDING = "pending"
    WON = "won"
    LOST = "lost"
    VOID = "void"


class BetKind(enum.StrEnum):
    SINGLE = "single"
    PARLAY = "parlay"
