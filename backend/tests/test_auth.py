"""Tests for auth endpoints."""

from unittest.mock import MagicMock, patch


def _mock_firebase_user():
    mock_user = MagicMock()
    mock_user.uid = "00000000-0000-0000-0000-000000000001"
    mock_user.email = "test@example.com"
    return mock_user


async def test_auth_me_authenticated(client):
    """GET /auth/me returns user info when authenticated."""
    # Mock Firebase Admin since tests do not call the real Firebase service.
    with patch(
        "app.modules.auth.service.firebase_auth.get_user", return_value=_mock_firebase_user()
    ) as get_user:
        resp = await client.get("/auth/me")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "00000000-0000-0000-0000-000000000001"
    assert data["email"] == "test@example.com"
    assert data["is_admin"] is False
    get_user.assert_called_once_with("00000000-0000-0000-0000-000000000001")


async def test_auth_me_reports_verified_admin(client):
    """GET /auth/me sets is_admin for a verified email listed in ADMIN_EMAILS."""
    from app.core.dependencies import get_current_user
    from app.main import app

    async def _verified_admin():
        return {
            "uid": "00000000-0000-0000-0000-000000000001",
            "email": "test@example.com",
            "email_verified": True,
        }

    app.dependency_overrides[get_current_user] = _verified_admin
    with (
        patch("app.core.dependencies.settings.ADMIN_EMAILS", "test@example.com"),
        patch(
            "app.modules.auth.service.firebase_auth.get_user",
            return_value=_mock_firebase_user(),
        ),
    ):
        resp = await client.get("/auth/me")

    assert resp.status_code == 200
    assert resp.json()["is_admin"] is True


async def test_auth_verify_authenticated(client):
    """GET /auth/verify returns valid message when authenticated."""
    resp = await client.get("/auth/verify")
    assert resp.status_code == 200
    data = resp.json()
    # The endpoint returns {"message": "Token is valid", "user_id": "<id>"}
    assert data["message"] == "Token is valid"
    assert data["user_id"] == "00000000-0000-0000-0000-000000000001"


async def test_auth_me_unauthenticated(unauthed_client):
    """GET /auth/me returns 401/403 without auth."""
    resp = await unauthed_client.get("/auth/me")
    assert resp.status_code in (401, 403)


async def test_auth_verify_unauthenticated(unauthed_client):
    """GET /auth/verify returns 401/403 without auth."""
    resp = await unauthed_client.get("/auth/verify")
    assert resp.status_code in (401, 403)
