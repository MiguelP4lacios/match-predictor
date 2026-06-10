"""Tests para redacción del apiKey en OddsApiSource (ops-resilience R3 S2, D8).

Verifica que errores HTTP de The Odds API no expongan el apiKey en el mensaje
de excepción. Puro: no llama a ninguna API real.
"""

from unittest.mock import MagicMock

import pytest

from app.ingestion.sources.odds_api import _raise_for_status_redacted, _redact_url

# ---------------------------------------------------------------------------
# _redact_url — función pura
# ---------------------------------------------------------------------------

def test_redact_url_masks_api_key():
    """La clave secreta en apiKey=<VALUE> queda reemplazada por ***."""
    url = "https://api.the-odds-api.com/v4/sports?apiKey=supersecret123&regions=eu"
    redacted = _redact_url(url)
    assert "supersecret123" not in redacted
    assert "apiKey=***" in redacted


def test_redact_url_preserves_other_params():
    """El resto de los query params queda intacto."""
    url = "https://api.example.com/odds?apiKey=mykey&regions=eu&markets=h2h"
    redacted = _redact_url(url)
    assert "regions=eu" in redacted
    assert "markets=h2h" in redacted
    assert "mykey" not in redacted


def test_redact_url_no_api_key_unchanged():
    """URL sin apiKey no se modifica."""
    url = "https://api.example.com/sports"
    assert _redact_url(url) == url


# ---------------------------------------------------------------------------
# _raise_for_status_redacted — lanza solo ante error
# ---------------------------------------------------------------------------

_FAKE_URL = "https://api.the-odds-api.com/v4/odds?apiKey=MYKEY123"


def _mock_response(status_code: int, url: str = _FAKE_URL) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.reason_phrase = "Unauthorized" if status_code == 401 else "Error"
    req = MagicMock()
    req.url = url
    resp.request = req
    return resp


def test_raise_for_status_redacted_does_not_expose_key():
    """RuntimeError no contiene el apiKey literal."""
    resp = _mock_response(401)
    with pytest.raises(RuntimeError) as exc_info:
        _raise_for_status_redacted(resp)
    assert "MYKEY123" not in str(exc_info.value)
    assert "***" in str(exc_info.value)


def test_raise_for_status_redacted_includes_status_code():
    """RuntimeError menciona el código de estado HTTP."""
    resp = _mock_response(403)
    with pytest.raises(RuntimeError) as exc_info:
        _raise_for_status_redacted(resp)
    assert "403" in str(exc_info.value)


def test_raise_for_status_redacted_ok_does_not_raise():
    """200 OK no lanza ninguna excepción."""
    resp = _mock_response(200)
    _raise_for_status_redacted(resp)  # no debe lanzar


def test_raise_for_status_redacted_200_range_ok():
    """Cualquier 2xx no lanza excepción."""
    for code in (200, 201, 204):
        resp = _mock_response(code)
        _raise_for_status_redacted(resp)  # sin excepción
