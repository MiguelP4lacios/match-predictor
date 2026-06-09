import pytest

from app.model.elo import (
    K_FRIENDLY,
    K_WORLD_CUP,
    expected_score,
    goal_difference_index,
    k_factor,
    result_score,
    update_ratings,
)
from app.models.enums import CompetitionKind


def test_expected_score_equal_ratings_is_half():
    assert expected_score(1500, 1500) == pytest.approx(0.5)


def test_expected_score_increases_with_rating_and_home_advantage():
    assert expected_score(1700, 1500) > 0.5
    # La localía sube la expectativa del local.
    assert expected_score(1500, 1500, home_advantage=100) > 0.5


def test_goal_difference_index_table():
    assert goal_difference_index(1) == 1.0
    assert goal_difference_index(2) == 1.5
    assert goal_difference_index(3) == pytest.approx(1.75)  # (11+3)/8
    assert goal_difference_index(4) == pytest.approx(1.875)  # (11+4)/8
    assert goal_difference_index(5) == pytest.approx(2.0)  # (11+5)/8


def test_result_score():
    assert result_score(2, 1) == (1.0, 0.0)
    assert result_score(0, 3) == (0.0, 1.0)
    assert result_score(1, 1) == (0.5, 0.5)  # empate / penales


def test_k_factor_mapping():
    assert k_factor(CompetitionKind.WORLD_CUP) == K_WORLD_CUP
    assert k_factor(CompetitionKind.FRIENDLY) == K_FRIENDLY
    assert k_factor(CompetitionKind.CONTINENTAL) == 50
    assert k_factor(CompetitionKind.QUALIFIER) == 40


def test_update_is_zero_sum():
    new_home, new_away = update_ratings(1500, 1500, 2, 0, k=40)
    assert new_home + new_away == pytest.approx(3000.0)


def test_equal_teams_one_goal_neutral():
    new_home, new_away = update_ratings(1500, 1500, 1, 0, k=40, neutral=True)
    assert new_home == pytest.approx(1520.0)
    assert new_away == pytest.approx(1480.0)


def test_the_legendary_5_0_moves_a_lot():
    # Argentina (local) 0 - 5 Colombia (visitante), eliminatoria (K=40), con localía.
    # Equipos parejos: la goleada como visitante dispara el Elo de Colombia.
    new_home, new_away = update_ratings(
        1500, 1500, 0, 5, k=40, neutral=False, home_advantage=100
    )
    assert new_away > new_home
    assert new_away == pytest.approx(1551.2, abs=0.5)  # +51.2 para Colombia
    assert new_home == pytest.approx(1448.8, abs=0.5)
