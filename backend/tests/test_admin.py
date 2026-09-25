"""
Tests para el módulo admin — Issue #19.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.security import HTTPAuthorizationCredentials

# ─── Test: get_admin_user dependency ────────────────────────────────────────

class TestGetAdminUser:
    """Verifica que solo el admin pueda acceder."""

    @pytest.mark.asyncio
    async def test_admin_user_allowed(self):
        """Email admin verificado → pasa la dependency sin error."""
        from app.core.dependencies import get_admin_user

        admin_payload = {
            "uid": "admin123",
            "email": "Admin@Example.com",
            "email_verified": True,
        }
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token")

        with (
            patch(
                "app.core.dependencies.settings.ADMIN_EMAILS",
                "ops@example.com, admin@example.com",
            ),
            patch(
                "app.core.dependencies.decode_firebase_token",
                new=AsyncMock(return_value=admin_payload),
            ) as decode_token,
        ):
            result = await get_admin_user(credentials=credentials)

        assert result["uid"] == "admin123"
        decode_token.assert_awaited_once_with("valid-token")

    @pytest.mark.asyncio
    async def test_unverified_admin_email_gets_404(self):
        """Email admin sin verificar → 404."""
        from fastapi import HTTPException

        from app.core.dependencies import get_admin_user

        payload = {"uid": "admin123", "email": "admin@example.com", "email_verified": False}
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token")

        with (
            patch("app.core.dependencies.settings.ADMIN_EMAILS", "admin@example.com"),
            patch(
                "app.core.dependencies.decode_firebase_token",
                new=AsyncMock(return_value=payload),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await get_admin_user(credentials=credentials)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_admin_emails_disables_admin(self):
        """ADMIN_EMAILS vacío → 404 para todos, sin verificar el token."""
        from fastapi import HTTPException

        from app.core.dependencies import get_admin_user

        payload = {"uid": "admin123", "email": "admin@example.com", "email_verified": True}
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token")

        with (
            patch("app.core.dependencies.settings.ADMIN_EMAILS", ""),
            patch(
                "app.core.dependencies.decode_firebase_token",
                new=AsyncMock(return_value=payload),
            ) as decode_token,
            pytest.raises(HTTPException) as exc_info,
        ):
            await get_admin_user(credentials=credentials)

        assert exc_info.value.status_code == 404
        decode_token.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_non_admin_gets_404(self):
        """Email diferente → 404 (no 403)."""
        from fastapi import HTTPException

        from app.core.dependencies import get_admin_user

        non_admin = {"uid": "user456", "email": "otro@example.com", "email_verified": True}
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token")

        with (
            patch("app.core.dependencies.settings.ADMIN_EMAILS", "admin@example.com"),
            patch(
                "app.core.dependencies.decode_firebase_token",
                new=AsyncMock(return_value=non_admin),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await get_admin_user(credentials=credentials)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_missing_credentials_gets_404(self):
        """Sin credenciales → 404."""
        from fastapi import HTTPException

        from app.core.dependencies import get_admin_user

        with (
            patch("app.core.dependencies.settings.ADMIN_EMAILS", "admin@example.com"),
            patch(
                "app.core.dependencies.decode_firebase_token", new=AsyncMock()
            ) as decode_token,
            pytest.raises(HTTPException) as exc_info,
        ):
            await get_admin_user(credentials=None)

        assert exc_info.value.status_code == 404
        decode_token.assert_not_awaited()


# ─── Test: admin service ────────────────────────────────────────────────────

class TestAdminService:
    """Tests para las funciones del admin service."""

    def _make_mock_db(self):
        """Crea un AsyncSession mock con execute que retorna resultados vacíos."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        return mock_db

    @pytest.mark.asyncio
    async def test_get_global_stats_empty_db(self):
        """Con DB vacía, stats retorna zeros."""
        from app.modules.admin.service import get_global_stats
        mock_db = self._make_mock_db()
        stats = await get_global_stats(mock_db)
        assert "total_users" in stats
        assert "monthly_conversations" in stats
        assert "monthly_cost_usd" in stats
        assert "plan_counts" in stats
        assert isinstance(stats["total_users"], int)
        assert isinstance(stats["monthly_cost_usd"], float)

    @pytest.mark.asyncio
    async def test_list_users_with_usage_empty(self):
        """Con DB vacía, lista vacía."""
        from app.modules.admin.service import list_users_with_usage
        mock_db = self._make_mock_db()
        users = await list_users_with_usage(mock_db)
        assert isinstance(users, list)
        assert len(users) == 0

    @pytest.mark.asyncio
    async def test_override_user_plan_user_not_found(self):
        """Usuario no existe → success: False."""
        from app.modules.admin.service import override_user_plan
        mock_db = self._make_mock_db()
        result = await override_user_plan(mock_db, "nonexistent_user", "pro")
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_override_user_plan_invalid_plan(self):
        """Plan inválido → success: False."""
        from app.modules.admin.service import override_user_plan
        mock_db = self._make_mock_db()
        result = await override_user_plan(mock_db, "user123", "invalid_plan")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_toggle_user_subscription_not_found(self):
        """Usuario no existe → success: False."""
        from app.modules.admin.service import toggle_user_subscription
        mock_db = self._make_mock_db()
        result = await toggle_user_subscription(mock_db, "nonexistent")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_get_cost_by_month_empty(self):
        """Sin registros → lista vacía."""
        from app.modules.admin.service import get_cost_by_month
        mock_db = self._make_mock_db()
        costs = await get_cost_by_month(mock_db)
        assert isinstance(costs, list)

    @pytest.mark.asyncio
    async def test_get_user_usage_history_empty(self):
        """Sin registros → lista vacía."""
        from app.modules.admin.service import get_user_usage_history
        mock_db = self._make_mock_db()
        usage = await get_user_usage_history(mock_db, "user123")
        assert isinstance(usage, list)
