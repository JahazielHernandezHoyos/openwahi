"""
Tests para usage_tracker.py
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.modules.ai_assistant.usage_tracker import (
    _calculate_cost,
    check_conversation_limit,
    get_monthly_conversation_count,
    get_monthly_usage,
    record_usage,
)
from app.modules.subscriptions.models import Plan


# =============================================================================
# Tests para _calculate_cost
# =============================================================================

def test_calculate_cost_bedrock_nova_lite():
    """Nova Lite: $0.06 input / $0.24 output por 1M tokens."""
    cost = _calculate_cost("bedrock", "amazon.nova-lite-v1:0", 1_000_000, 1_000_000)
    assert cost == Decimal("0.30")  # 0.06 + 0.24


def test_calculate_cost_zero_tokens():
    cost = _calculate_cost("bedrock", "amazon.nova-lite-v1:0", 0, 0)
    assert cost == Decimal("0")


def test_calculate_cost_unknown_model():
    """Modelo desconocido devuelve 0 sin lanzar excepción."""
    cost = _calculate_cost("unknown", "mystery-model", 1000, 500)
    assert cost == Decimal("0")


def test_calculate_cost_only_input_tokens():
    """Solo tokens de entrada."""
    cost = _calculate_cost("bedrock", "amazon.nova-lite-v1:0", 100_000, 0)
    expected = Decimal("100000") * Decimal("0.06") / Decimal("1000000")
    assert cost == expected


def test_calculate_cost_groq_model():
    """Groq llama-3.3-70b: $0.59 input / $0.79 output."""
    cost = _calculate_cost("groq", "llama-3.3-70b-versatile", 1_000_000, 1_000_000)
    assert cost == Decimal("1.38")  # 0.59 + 0.79


# =============================================================================
# Tests para record_usage (mock DB)
# =============================================================================

@pytest.mark.asyncio
async def test_record_usage_adds_record_to_db():
    """record_usage llama db.add y db.flush."""
    # Usar MagicMock para db.add (sync) y AsyncMock para db.flush (async)
    mock_db = MagicMock()
    mock_db.flush = AsyncMock()
    user_id = str(uuid4())

    # Parchear AIUsageRecordDB para evitar que SQLAlchemy intente resolver
    # relaciones entre modelos (KnowledgeBaseDB, etc.) en el contexto de tests
    mock_record_class = MagicMock()
    mock_record_instance = MagicMock()
    mock_record_class.return_value = mock_record_instance

    with patch.dict("sys.modules", {"app.modules.ai_assistant.models": MagicMock(AIUsageRecordDB=mock_record_class)}):
        await record_usage(
            db=mock_db,
            user_id=user_id,
            provider="bedrock",
            model="amazon.nova-lite-v1:0",
            tokens_input=500,
            tokens_output=200,
            is_managed=True,
        )

    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_record_usage_does_not_raise_on_db_error():
    """Si la DB falla, record_usage no propaga la excepción."""
    mock_db = AsyncMock()
    mock_db.add.side_effect = Exception("DB is down")
    # No debe lanzar
    await record_usage(
        db=mock_db,
        user_id="user123",
        provider="groq",
        model="llama-3.3-70b-versatile",
        tokens_input=100,
        tokens_output=50,
        is_managed=False,
    )


# =============================================================================
# Tests para check_conversation_limit
# =============================================================================

@pytest.mark.asyncio
async def test_check_limit_free_plan_always_allowed():
    """Plan free siempre retorna (True, -1)."""
    mock_db = AsyncMock()
    allowed, remaining = await check_conversation_limit(mock_db, "user1", Plan.free)
    assert allowed is True
    assert remaining == -1


@pytest.mark.asyncio
async def test_check_limit_enterprise_plan_always_allowed():
    """Plan enterprise siempre retorna (True, -1)."""
    mock_db = AsyncMock()
    allowed, remaining = await check_conversation_limit(mock_db, "user1", Plan.enterprise)
    assert allowed is True
    assert remaining == -1


@pytest.mark.asyncio
async def test_check_limit_pro_within_limit():
    """Pro con 100 conversaciones usadas de 3000: allowed=True, remaining=2900."""
    mock_db = AsyncMock()
    with patch(
        "app.modules.ai_assistant.usage_tracker.get_monthly_conversation_count",
        new=AsyncMock(return_value=100),
    ):
        allowed, remaining = await check_conversation_limit(mock_db, "user1", Plan.pro)
    assert allowed is True
    assert remaining == 2900


@pytest.mark.asyncio
async def test_check_limit_pro_at_limit():
    """Pro con exactamente 3000 conversaciones: allowed=False, remaining=0."""
    mock_db = AsyncMock()
    with patch(
        "app.modules.ai_assistant.usage_tracker.get_monthly_conversation_count",
        new=AsyncMock(return_value=3000),
    ):
        allowed, remaining = await check_conversation_limit(mock_db, "user1", Plan.pro)
    assert allowed is False
    assert remaining == 0


@pytest.mark.asyncio
async def test_check_limit_pro_over_limit():
    """Pro con 3001 conversaciones: allowed=False, remaining=0 (no negativo)."""
    mock_db = AsyncMock()
    with patch(
        "app.modules.ai_assistant.usage_tracker.get_monthly_conversation_count",
        new=AsyncMock(return_value=3001),
    ):
        allowed, remaining = await check_conversation_limit(mock_db, "user1", Plan.pro)
    assert allowed is False
    assert remaining == 0
