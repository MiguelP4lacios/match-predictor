"""Cálculo de Elo — fórmula World Football Elo Ratings.

Funciones PURAS: sin BD, sin estado global, sin LLM (invariante de arquitectura:
el cómputo determinista vive separado). Por eso son trivialmente testeables.

Fórmula:  R_nuevo = R_viejo + K · G · (W − We)
  We (esperado) = 1 / (1 + 10^(−dr/400)),  dr = (Ra − Rb) + ventaja de localía
  K  = peso por importancia del partido
  G  = multiplicador por margen de goles
  W  = 1 gana / 0.5 empata / 0 pierde   (penales cuentan como empate)
"""

from app.models.enums import CompetitionKind

DEFAULT_INITIAL_RATING = 1500.0
DEFAULT_HOME_ADVANTAGE = 100.0

# K por importancia (valores oficiales del World Football Elo).
K_WORLD_CUP = 60
K_CONTINENTAL = 50
K_QUALIFIER_OR_MAJOR = 40
K_OTHER_TOURNAMENT = 30
K_FRIENDLY = 20

_K_BY_KIND = {
    CompetitionKind.WORLD_CUP: K_WORLD_CUP,
    CompetitionKind.CONTINENTAL: K_CONTINENTAL,
    CompetitionKind.QUALIFIER: K_QUALIFIER_OR_MAJOR,
    CompetitionKind.NATIONS_LEAGUE: K_QUALIFIER_OR_MAJOR,
    CompetitionKind.FRIENDLY: K_FRIENDLY,
}


def k_factor(kind: CompetitionKind) -> int:
    """K según el tipo de competición. Default 30 (otros torneos)."""
    return _K_BY_KIND.get(kind, K_OTHER_TOURNAMENT)


def expected_score(
    rating_a: float, rating_b: float, home_advantage: float = 0.0
) -> float:
    """We para A. `home_advantage` se suma al rating de A (0 si A no es local)."""
    dr = (rating_a + home_advantage) - rating_b
    return 1.0 / (1.0 + 10.0 ** (-dr / 400.0))


def goal_difference_index(goal_diff: int) -> float:
    """G: empate o 1 gol -> 1; 2 goles -> 1.5; 3+ -> (11 + N) / 8."""
    n = abs(goal_diff)
    if n <= 1:
        return 1.0
    if n == 2:
        return 1.5
    return (11 + n) / 8.0


def result_score(home_score: int, away_score: int) -> tuple[float, float]:
    """W para (local, visitante). Empate (incluye definición por penales) = 0.5/0.5."""
    if home_score > away_score:
        return 1.0, 0.0
    if home_score < away_score:
        return 0.0, 1.0
    return 0.5, 0.5


def update_ratings(
    home_rating: float,
    away_rating: float,
    home_score: int,
    away_score: int,
    k: float,
    *,
    neutral: bool = False,
    home_advantage: float = DEFAULT_HOME_ADVANTAGE,
) -> tuple[float, float]:
    """Ratings (local, visitante) DESPUÉS del partido. Suma cero entre ambos."""
    advantage = 0.0 if neutral else home_advantage
    we_home = expected_score(home_rating, away_rating, advantage)
    we_away = 1.0 - we_home
    w_home, w_away = result_score(home_score, away_score)
    g = goal_difference_index(home_score - away_score)
    new_home = home_rating + k * g * (w_home - we_home)
    new_away = away_rating + k * g * (w_away - we_away)
    return new_home, new_away
