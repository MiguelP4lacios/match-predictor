"""Ensamblador de explicación de señal +EV — solo lectura, cero llamadas externas.

Reconstruye el triple de-vig best-per-outcome fijado al captured_at del odds_id
(mismo método que el pipeline de señales). Todos los valores canónicos salen
verbatim de las tablas persistidas; p_fair = p_model − edge siempre.

Jerarquía de dataclasses:
    Explanation
        sections: list[ExplainSection]
            steps: list[ExplainStep]
            note: str | None

Contrato de formatted:
    - Canónicos (edge, p_model, p_fair, kelly_fraction, recommended_stake, ev):
      formatted=None → el front los formatea con formatters.ts
    - Intermedios ilustrativos (1/odds, overround, elo_diff, brier, ...):
      formatted=str → el servidor los formatea, el front los renderiza verbatim
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.model.ratings import HOME_ADVANTAGE, lookup_rating
from app.models.betting import ValueSignal
from app.models.match import Match
from app.models.model import ModelVersion, Prediction
from app.models.odds import Odds
from app.models.team import Team

# ---------------------------------------------------------------------------
# Dataclasses de salida
# ---------------------------------------------------------------------------


@dataclass
class ExplainStep:
    """Un paso dentro de una sección de explicación.

    formatted:
        None  → el front formatea raw con formatters.ts (canónicos)
        str   → el servidor ya lo formateó; renderizar verbatim (intermedios)
    """

    key: str
    label_es: str
    raw: float | str | bool | int | None
    formatted: str | None
    glossary_term: str | None = None


@dataclass
class ExplainSection:
    """Sección trazable de la explicación."""

    key: str
    titulo: str
    steps: list[ExplainStep] = field(default_factory=list)
    note: str | None = None


@dataclass
class Explanation:
    """Raíz: lista de secciones que componen la explicación completa."""

    sections: list[ExplainSection] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

_OUTCOME_ORDER = {"HOME": 0, "DRAW": 1, "AWAY": 2}


def _best_per_outcome_at_snapshot(
    session: Session,
    match_id: int,
    captured_at: datetime.datetime,
) -> dict[str, float]:
    """Mejor cuota (máx decimal_odds) por outcome_code en el snapshot exacto.

    Fija la consulta al captured_at del odds_id original para reproducir
    el mismo triple que el pipeline de señales usó.

    Returns:
        {outcome_code: decimal_odds} — vacío si no hay datos para ese snapshot.
    """
    from app.models.enums import MarketType

    # Subquery: max(decimal_odds) por outcome_code en el snapshot exacto
    subq = (
        select(
            Odds.outcome_code,
            func.max(Odds.decimal_odds).label("best_odds"),
        )
        .where(
            Odds.match_id == match_id,
            Odds.market_type == MarketType.MATCH_1X2,
            Odds.captured_at == captured_at,
            Odds.outcome_code.in_(["HOME", "DRAW", "AWAY"]),
        )
        .group_by(Odds.outcome_code)
        .subquery()
    )

    rows = session.execute(select(subq.c.outcome_code, subq.c.best_odds)).all()
    return {r.outcome_code: float(r.best_odds) for r in rows}


def _build_apuesta_section(
    signal: ValueSignal,
    prediction: Prediction,
    odds: Odds,
    match: Match,
    session: Session,
) -> ExplainSection:
    """Sección apuesta: qué se apostó, a qué cuota y en qué casa.

    outcome_label:
        HOME  → nombre del equipo local
        DRAW  → "Empate"
        AWAY  → nombre del equipo visitante
    """
    outcome_code = prediction.outcome_code or "HOME"

    home_team = session.get(Team, match.home_team_id)
    away_team = session.get(Team, match.away_team_id)
    home_name = home_team.name if home_team else str(match.home_team_id)
    away_name = away_team.name if away_team else str(match.away_team_id)

    if outcome_code == "HOME":
        outcome_label = home_name
    elif outcome_code == "DRAW":
        outcome_label = "Empate"
    else:
        outcome_label = away_name

    cuota = float(odds.decimal_odds)

    steps = [
        ExplainStep(
            key="outcome_label",
            label_es="Resultado apostado",
            raw=outcome_label,
            formatted=outcome_label,
        ),
        ExplainStep(
            key="cuota",
            label_es="Cuota decimal",
            raw=cuota,
            formatted=f"{cuota:.2f}",
        ),
        ExplainStep(
            key="bookmaker",
            label_es="Casa de apuestas",
            raw=odds.bookmaker,
            formatted=odds.bookmaker,
        ),
        ExplainStep(
            key="home_team",
            label_es="Equipo local",
            raw=home_name,
            formatted=home_name,
        ),
        ExplainStep(
            key="away_team",
            label_es="Equipo visitante",
            raw=away_name,
            formatted=away_name,
        ),
        ExplainStep(
            key="match_date",
            label_es="Fecha del partido",
            raw=match.match_date.isoformat(),
            formatted=match.match_date.strftime("%d/%m/%Y"),
        ),
    ]

    return ExplainSection(
        key="apuesta",
        titulo="¿Qué apostamos?",
        steps=steps,
    )


def _build_edge_section(
    p_model: float,
    edge: float,
    triple: dict[str, float],
    outcome_code: str,
) -> ExplainSection:
    """Construye la sección 'edge' con pasos canónicos e ilustrativos.

    Si el triple está incompleto (falta alguna pata) → note, sin fallar.
    """
    p_fair_derived = p_model - edge

    steps: list[ExplainStep] = [
        ExplainStep(
            key="p_model",
            label_es="Probabilidad del modelo",
            raw=round(p_model, 5),
            formatted=None,
            glossary_term="elo",
        ),
    ]

    note: str | None = None
    has_complete_triple = all(k in triple for k in ("HOME", "DRAW", "AWAY"))

    if has_complete_triple:
        h_odds = triple["HOME"]
        d_odds = triple["DRAW"]
        a_odds = triple["AWAY"]

        # Intermedios ilustrativos: 1/odds por pata
        steps.append(
            ExplainStep(
                key="inv_home",
                label_es="1 / cuota LOCAL (mejor precio)",
                raw=round(1.0 / h_odds, 5),
                formatted=f"{1.0 / h_odds:.5f}",
            )
        )
        steps.append(
            ExplainStep(
                key="inv_draw",
                label_es="1 / cuota EMPATE (mejor precio)",
                raw=round(1.0 / d_odds, 5),
                formatted=f"{1.0 / d_odds:.5f}",
            )
        )
        steps.append(
            ExplainStep(
                key="inv_away",
                label_es="1 / cuota VISITA (mejor precio)",
                raw=round(1.0 / a_odds, 5),
                formatted=f"{1.0 / a_odds:.5f}",
            )
        )

        # Overround ilustrativo
        overround = (1.0 / h_odds) + (1.0 / d_odds) + (1.0 / a_odds)
        steps.append(
            ExplainStep(
                key="overround",
                label_es="Sobrerronda (suma de probabilidades implícitas)",
                raw=round(overround, 5),
                formatted=f"{overround:.5f}",
                glossary_term="de-vig",
            )
        )

        # p_fair_reconstructed para el outcome del signal (ilustrativo)
        outcome_odds = triple.get(outcome_code, h_odds)
        p_fair_reconstructed = (1.0 / outcome_odds) / overround
        steps.append(
            ExplainStep(
                key="p_fair_reconstructed",
                label_es="Prob. justa reconstruida (de-vig, ilustrativo)",
                raw=round(p_fair_reconstructed, 5),
                formatted=f"{p_fair_reconstructed:.5f}",
                glossary_term="de-vig",
            )
        )

        # Nota si la tolerancia de reconciliación se excede (> 1e-3)
        recon_diff = abs(p_fair_reconstructed - p_fair_derived)
        if recon_diff > 1e-3:
            note = (
                f"El mejor precio combinó casas/snapshots distintos; "
                f"diferencia ilustrativa={recon_diff:.5f}"
            )
    else:
        note = "no reconstruible desde el snapshot; se muestra prob. justa derivada"

    # p_fair derivada: SIEMPRE p_model − edge (canónico)
    steps.append(
        ExplainStep(
            key="p_fair_derived",
            label_es="Probabilidad justa (derivada: p_modelo − edge)",
            raw=round(p_fair_derived, 5),
            formatted=None,
            glossary_term="de-vig",
        )
    )

    # edge verbatim
    steps.append(
        ExplainStep(
            key="edge",
            label_es="Edge (ventaja sobre la cuota)",
            raw=round(edge, 5),
            formatted=None,
            glossary_term="edge",
        )
    )

    return ExplainSection(
        key="edge",
        titulo="¿Cómo se calculó el edge?",
        steps=steps,
        note=note,
    )


def _build_origen_section(
    session: Session,
    match: Match,
    prediction: Prediction,
    model_version: ModelVersion,
) -> ExplainSection:
    """Sección origen_p_model: ratings Elo point-in-time + parámetros del modelo."""
    home_rating, _ = lookup_rating(session, match.home_team_id, match.match_date)
    away_rating, _ = lookup_rating(session, match.away_team_id, match.match_date)

    advantage = 0.0 if match.neutral_site else HOME_ADVANTAGE
    elo_diff = (home_rating + advantage) - away_rating

    # nombres de equipos
    home_team = session.get(Team, match.home_team_id)
    away_team = session.get(Team, match.away_team_id)
    home_name = home_team.name if home_team else str(match.home_team_id)
    away_name = away_team.name if away_team else str(match.away_team_id)

    steps = [
        ExplainStep(
            key="elo_home",
            label_es=f"Elo {home_name} (point-in-time)",
            raw=round(home_rating, 2),
            formatted=f"{home_rating:.2f}",
            glossary_term="elo",
        ),
        ExplainStep(
            key="elo_away",
            label_es=f"Elo {away_name} (point-in-time)",
            raw=round(away_rating, 2),
            formatted=f"{away_rating:.2f}",
            glossary_term="elo",
        ),
        ExplainStep(
            key="advantage",
            label_es="Ventaja de localía",
            raw=advantage,
            formatted=f"{advantage:.0f}",
        ),
        ExplainStep(
            key="elo_diff",
            label_es="Diferencia Elo efectiva (local + ventaja − visita)",
            raw=round(elo_diff, 2),
            formatted=f"{elo_diff:.2f}",
            glossary_term="elo",
        ),
        ExplainStep(
            key="neutral",
            label_es="Sede neutral",
            raw=match.neutral_site,
            formatted="Sí" if match.neutral_site else "No",
        ),
        ExplainStep(
            key="low_confidence",
            label_es="Baja confianza (sin rating histórico previo)",
            raw=prediction.low_confidence,
            formatted="Sí" if prediction.low_confidence else "No",
        ),
        ExplainStep(
            key="model_name",
            label_es="Modelo",
            raw=model_version.name,
            formatted=model_version.name,
        ),
        ExplainStep(
            key="model_version_id",
            label_es="ID versión del modelo",
            raw=model_version.id,
            formatted=str(model_version.id),
        ),
    ]

    return ExplainSection(
        key="origen_p_model",
        titulo="¿De dónde viene la probabilidad del modelo?",
        steps=steps,
    )


def _build_stake_section(
    signal: ValueSignal,
    model_version: ModelVersion,
) -> ExplainSection:
    """Sección stake: ¼-Kelly, bankroll y stake recomendado."""
    thresholds = model_version.params_json.get("thresholds", {})
    bankroll = float(thresholds.get("bankroll", 1000.0))
    kelly_frac = float(signal.kelly_fraction)
    stake_str = str(signal.recommended_stake)

    steps = [
        ExplainStep(
            key="formula_label",
            label_es="Fórmula de staking",
            raw="¼-Kelly fraccionado",
            formatted="¼-Kelly fraccionado",
        ),
        ExplainStep(
            key="kelly_fraction",
            label_es="Fracción Kelly calculada",
            raw=round(kelly_frac, 5),
            formatted=None,
            glossary_term="kelly",
        ),
        ExplainStep(
            key="bankroll",
            label_es="Bankroll",
            raw=bankroll,
            formatted=f"${bankroll:,.2f}",
        ),
        ExplainStep(
            key="recommended_stake",
            label_es="Stake recomendado",
            raw=stake_str,
            formatted=None,
        ),
    ]

    return ExplainSection(
        key="stake",
        titulo="¿Cuánto apostar?",
        steps=steps,
    )


def _build_calidad_section(model_version: ModelVersion) -> ExplainSection:
    """Sección calidad_modelo: métricas de backtest."""
    backtest = model_version.params_json.get("backtest", {})
    baselines = backtest.get("baselines", {})

    brier = backtest.get("brier", None)
    logloss = backtest.get("logloss", None)
    brier_uniform = baselines.get("uniform_brier", None)
    brier_binned = baselines.get("binned_brier", None)
    logloss_uniform = baselines.get("uniform_logloss", None)
    logloss_binned = baselines.get("binned_logloss", None)
    beats = backtest.get("beats_baselines", None)
    eval_n = backtest.get("eval_n", None)

    def _fmt_float(v: float | None, precision: int = 4) -> str | None:
        return f"{v:.{precision}f}" if v is not None else None

    steps = [
        ExplainStep(
            key="brier",
            label_es="Brier score (modelo)",
            raw=brier,
            formatted=_fmt_float(brier),
            glossary_term="brier",
        ),
        ExplainStep(
            key="brier_uniform",
            label_es="Brier score (baseline uniforme)",
            raw=brier_uniform,
            formatted=_fmt_float(brier_uniform),
        ),
        ExplainStep(
            key="brier_binned",
            label_es="Brier score (baseline calibrado por cubo)",
            raw=brier_binned,
            formatted=_fmt_float(brier_binned),
        ),
        ExplainStep(
            key="logloss",
            label_es="Log-loss (modelo)",
            raw=logloss,
            formatted=_fmt_float(logloss),
            glossary_term="calibración",
        ),
        ExplainStep(
            key="logloss_uniform",
            label_es="Log-loss (baseline uniforme)",
            raw=logloss_uniform,
            formatted=_fmt_float(logloss_uniform),
        ),
        ExplainStep(
            key="logloss_binned",
            label_es="Log-loss (baseline calibrado por cubo)",
            raw=logloss_binned,
            formatted=_fmt_float(logloss_binned),
        ),
        ExplainStep(
            key="beats_baselines",
            label_es="¿Supera los baselines?",
            raw=beats,
            formatted="Sí" if beats else "No" if beats is not None else None,
        ),
        ExplainStep(
            key="eval_n",
            label_es="Partidos evaluados en backtest",
            raw=eval_n,
            formatted=f"{eval_n:,}" if eval_n is not None else None,
        ),
    ]

    return ExplainSection(
        key="calidad_modelo",
        titulo="¿Qué tan confiable es el modelo?",
        steps=steps,
    )


def _build_metadata_section(
    signal: ValueSignal,
    prediction: Prediction,
    odds: Odds,
) -> ExplainSection:
    """Sección metadata: trazabilidad de la señal."""
    steps = [
        ExplainStep(
            key="signal_id",
            label_es="ID de la señal",
            raw=signal.id,
            formatted=str(signal.id),
        ),
        ExplainStep(
            key="prediction_id",
            label_es="ID de la predicción",
            raw=prediction.id,
            formatted=str(prediction.id),
        ),
        ExplainStep(
            key="odds_id",
            label_es="ID del snapshot de cuota",
            raw=odds.id,
            formatted=str(odds.id),
        ),
        ExplainStep(
            key="bookmaker",
            label_es="Casa de apuestas",
            raw=odds.bookmaker,
            formatted=odds.bookmaker,
        ),
        ExplainStep(
            key="captured_at",
            label_es="Capturado el",
            raw=odds.captured_at.isoformat(),
            formatted=odds.captured_at.strftime("%Y-%m-%d %H:%M:%S"),
        ),
    ]

    return ExplainSection(
        key="metadata",
        titulo="Metadatos de la señal",
        steps=steps,
    )


# ---------------------------------------------------------------------------
# Punto de entrada público
# ---------------------------------------------------------------------------


def build_explanation(session: Session, signal_id: int) -> Explanation | None:
    """Ensambla la explicación completa para una señal +EV.

    Retorna None si signal_id no existe (el router responde 404).
    No realiza llamadas externas; todo proviene de Postgres.

    Args:
        session:   sesión SQLAlchemy activa.
        signal_id: ID de la señal en value_signal.

    Returns:
        Explanation con secciones rellenas, o None si no existe.
    """
    signal: ValueSignal | None = session.get(ValueSignal, signal_id)
    if signal is None:
        return None

    prediction: Prediction | None = session.get(Prediction, signal.prediction_id)
    if prediction is None:
        return None

    odds: Odds | None = session.get(Odds, signal.odds_id)
    if odds is None:
        return None

    match: Match | None = session.get(Match, prediction.match_id)
    if match is None:
        return None

    model_version: ModelVersion | None = session.get(ModelVersion, prediction.model_version_id)
    if model_version is None:
        return None

    p_model = float(prediction.probability)
    edge = float(signal.edge)

    # Triple best-per-outcome fijado al snapshot del odds_id
    triple = _best_per_outcome_at_snapshot(session, match.id, odds.captured_at)

    sections = [
        _build_apuesta_section(signal, prediction, odds, match, session),
        _build_edge_section(p_model, edge, triple, prediction.outcome_code or "HOME"),
        _build_origen_section(session, match, prediction, model_version),
        _build_stake_section(signal, model_version),
        _build_calidad_section(model_version),
        _build_metadata_section(signal, prediction, odds),
    ]

    return Explanation(sections=sections)
