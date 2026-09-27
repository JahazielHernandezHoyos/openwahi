"""
Usage tracker — registra tokens y costos por usuario para el plan Pro.
Usado por el Admin Dashboard (issue #19) y el guard de límite mensual.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.subscriptions.models import Plan

logger = logging.getLogger(__name__)

# Precios en USD por 1M tokens (actualizados 2025)
PRICING: dict[str, dict[str, float]] = {
    "bedrock/amazon.nova-lite-v1:0": {"input": 0.06, "output": 0.24},
    "bedrock/amazon.nova-micro-v1:0": {"input": 0.035, "output": 0.14},
    "bedrock/amazon.nova-pro-v1:0": {"input": 0.80, "output": 3.20},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "openai/gpt-4o": {"input": 2.50, "output": 10.00},
    "groq/llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    "groq/llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "llamacpp/Qwen3.5-0.8B-Q8_0": {"input": 0.0, "output": 0.0},
    # OpenCode Zen Go price list, verified 2026-09-06 (USD / 1M tokens).
    "opencode-zen-go/deepseek-v4-flash": {"input": 0.22, "output": 0.66, "cache_read": 0.007},
    "opencode-zen-go/glm-5.3-flash": {"input": 0.075, "output": 0.25, "cache_read": 0.015},
    "opencode-zen-go/qwen3.8-flash": {"input": 0.15, "output": 0.47, "cache_read": 0.016},
    "opencode-zen-go/deepseek-v4-pro": {"input": 0.66, "output": 1.98, "cache_read": 0.022},
    "opencode-zen-go/minimax-m3": {"input": 0.3, "output": 1.2, "cache_read": 0.06},
}


def _calculate_cost(provider: str, model: str, tokens_input: int, tokens_output: int) -> Decimal:
    """Calcula el costo en USD dado proveedor, modelo y tokens usados."""
    key = f"{provider}/{model}"
    pricing = PRICING.get(key)
    if not pricing:
        # Proveedor/modelo desconocido — costo 0 para no bloquear el flujo
        logger.warning(f"No pricing found for {key}, defaulting to 0")
        return Decimal("0")

    cost_input = Decimal(str(tokens_input)) * Decimal(str(pricing["input"])) / Decimal("1000000")
    cost_output = Decimal(str(tokens_output)) * Decimal(str(pricing["output"])) / Decimal("1000000")
    return cost_input + cost_output


async def record_usage(
    db: AsyncSession,
    user_id: str,
    provider: str,
    model: str,
    tokens_input: int,
    tokens_output: int,
    is_managed: bool,
    config_id: Optional[UUID] = None,
    conversation_id: Optional[UUID] = None,
) -> None:
    """
    Registra el uso de tokens de una respuesta del agente.
    No lanza excepción — si falla, solo loguea (no interrumpir el chat).
    """
    try:
        from app.modules.ai_assistant.models import AIUsageRecordDB

        cost = _calculate_cost(provider, model, tokens_input, tokens_output)
        record = AIUsageRecordDB(
            user_id=user_id,
            config_id=config_id,
            conversation_id=conversation_id,
            provider=provider,
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_usd=cost,
            is_managed=is_managed,
        )
        db.add(record)
        await db.flush()  # No commit — el caller decide cuándo commitear
        logger.debug(
            f"Usage recorded: user={user_id} {provider}/{model} "
            f"in={tokens_input} out={tokens_output} cost=${cost:.8f}"
        )
    except Exception as e:
        logger.error(f"Failed to record usage for user {user_id}: {e}", exc_info=True)


async def get_monthly_conversation_count(db: AsyncSession, user_id: str, year: int, month: int) -> int:
    """
    Cuenta conversaciones únicas (distinct conversation_id) del usuario en el mes dado.
    Conversaciones sin conversation_id (conversation_id IS NULL) se cuentan como 1 cada una.
    """
    from app.modules.ai_assistant.models import AIUsageRecordDB

    result = await db.execute(
        select(func.count(func.distinct(AIUsageRecordDB.conversation_id)))
        .where(AIUsageRecordDB.user_id == user_id)
        .where(extract("year", AIUsageRecordDB.created_at) == year)
        .where(extract("month", AIUsageRecordDB.created_at) == month)
        .where(AIUsageRecordDB.is_managed == True)  # solo cuenta las managed (plan Pro)
    )
    return result.scalar_one() or 0


async def get_monthly_usage(db: AsyncSession, user_id: str, year: int, month: int) -> dict:
    """
    Retorna resumen de uso mensual del usuario.
    """
    from app.modules.ai_assistant.models import AIUsageRecordDB

    result = await db.execute(
        select(
            func.count(func.distinct(AIUsageRecordDB.conversation_id)).label("total_conversations"),
            func.sum(AIUsageRecordDB.tokens_input).label("total_tokens_input"),
            func.sum(AIUsageRecordDB.tokens_output).label("total_tokens_output"),
            func.sum(AIUsageRecordDB.cost_usd).label("total_cost_usd"),
        )
        .where(AIUsageRecordDB.user_id == user_id)
        .where(extract("year", AIUsageRecordDB.created_at) == year)
        .where(extract("month", AIUsageRecordDB.created_at) == month)
    )
    row = result.fetchone()
    return {
        "user_id": user_id,
        "year": year,
        "month": month,
        "total_conversations": row.total_conversations or 0,
        "total_tokens_input": row.total_tokens_input or 0,
        "total_tokens_output": row.total_tokens_output or 0,
        "total_cost_usd": float(row.total_cost_usd or 0),
    }


async def check_conversation_limit(
    db: AsyncSession, user_id: str, plan: Plan
) -> tuple[bool, int]:
    """
    Verifica si el usuario puede iniciar otra conversación este mes.

    Returns:
        (allowed: bool, remaining: int)
        - remaining = -1 para planes sin límite
    """
    from app.config.settings import settings

    if plan != Plan.pro:
        return True, -1  # free y enterprise: sin límite managed

    now = datetime.now(UTC)
    count = await get_monthly_conversation_count(db, user_id, now.year, now.month)
    limit = settings.PRO_MONTHLY_CONVERSATION_LIMIT
    remaining = max(0, limit - count)
    allowed = count < limit
    return allowed, remaining
