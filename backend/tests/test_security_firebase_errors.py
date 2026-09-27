"""Tests for Firebase error handling in app.core.security."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from firebase_admin import auth as firebase_auth

from app.core.security import decode_firebase_token

# Each case pairs a Firebase error with the exact client-facing detail. The
# revoked and expired errors subclass InvalidIdTokenError, so the handler order
# is what makes their specific messages reach the client.
FIREBASE_ERROR_CASES = [
    (
        firebase_auth.ExpiredIdTokenError("expired internal detail", None),
        "Token has expired",
    ),
    (
        firebase_auth.RevokedIdTokenError("revoked internal detail"),
        "Token has been revoked",
    ),
    (
        firebase_auth.InvalidIdTokenError("invalid internal detail"),
        "Invalid authentication credentials",
    ),
]


@pytest.mark.parametrize(("exception", "expected_detail"), FIREBASE_ERROR_CASES)
async def test_decode_firebase_token_returns_fixed_401_detail(exception, expected_detail):
    """Each Firebase error maps to its own fixed 401 detail."""
    with patch("app.core.security.firebase_auth.verify_id_token", side_effect=exception):
        with pytest.raises(HTTPException) as exc_info:
            await decode_firebase_token("some-token")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == expected_detail


@pytest.mark.parametrize(("exception", "expected_detail"), FIREBASE_ERROR_CASES)
async def test_auth_endpoint_returns_fixed_401_detail(
    unauthed_client, exception, expected_detail
):
    """The HTTP response exposes the fixed detail and a 401 status."""
    with patch("app.core.security.firebase_auth.verify_id_token", side_effect=exception):
        response = await unauthed_client.get(
            "/auth/me", headers={"Authorization": "Bearer some-token"}
        )

    assert response.status_code == 401
    assert response.json()["detail"] == expected_detail


async def test_invalid_token_detail_does_not_leak_firebase_message():
    """The internal Firebase message never reaches the client."""
    internal_message = "Firebase signature verification failed for project xyz"

    with patch(
        "app.core.security.firebase_auth.verify_id_token",
        side_effect=firebase_auth.InvalidIdTokenError(internal_message),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await decode_firebase_token("some-token")

    assert internal_message not in exc_info.value.detail


async def test_revoked_token_reports_revocation_not_invalid():
    """RevokedIdTokenError is caught before its InvalidIdTokenError parent."""
    with patch(
        "app.core.security.firebase_auth.verify_id_token",
        side_effect=firebase_auth.RevokedIdTokenError("internal revoked detail"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await decode_firebase_token("some-token")

    assert exc_info.value.detail == "Token has been revoked"
