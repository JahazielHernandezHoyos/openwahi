"""
Admin service — funciones de negocio para el dashboard de administración.
Issue #19.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from firebase_admin import auth as firebase_auth
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_assistant.encryption import encrypt_api_key
from app.modules.ai_assistant.models import (
    AIUsageRecordDB,
    ManagedAIConfigCreate,
    ManagedAIConfigDB,
    ManagedAIConfigUpdate,
    ProviderHealthEventDB,
)
from app.modules.ai_assistant.provider import UnifiedAIProvider
from app.modules.ai_assistant.provider_chain import (
    choice_from_entry,
    ensure_default_chain,
    record_probe_result,
)
from app.modules.subscriptions.models import Plan, UserSubscriptionDB

logger = logging.getLogger(__name__)

VALID_PLANS = {p.value for p in Plan}


async def get_global_stats(db: AsyncSession) -> dict[str, Any]:
    """
    Estadísticas globales del sistema:
    - total_users: usuarios con suscripción
    - monthly_conversations: conversaciones únicas este mes
    - monthly_cost_usd: costo total este mes (managed)
    - plan_counts: breakdown por plan
    """
    now = datetime.now(UTC)

    # Total users
    result = await db.execute(select(func.count()).select_from(UserSubscriptionDB))
    total_users = result.scalar_one() or 0

    # Monthly conversations (distinct conversation_id en registros managed)
    result = await db.execute(
        select(func.count(func.distinct(AIUsageRecordDB.conversation_id)))
        .where(AIUsageRecordDB.is_managed == True)  # noqa: E712
        .where(extract("year", AIUsageRecordDB.created_at) == now.year)
        .where(extract("month", AIUsageRecordDB.created_at) == now.month)
    )
    monthly_conversations = result.scalar_one() or 0

    # Monthly cost
    result = await db.execute(
        select(func.sum(AIUsageRecordDB.cost_usd))
        .where(AIUsageRecordDB.is_managed == True)  # noqa: E712
        .where(extract("year", AIUsageRecordDB.created_at) == now.year)
        .where(extract("month", AIUsageRecordDB.created_at) == now.month)
    )
    monthly_cost_usd = float(result.scalar_one() or 0)

    # Plan breakdown
    plan_counts: dict[str, int] = {p.value: 0 for p in Plan}
    result = await db.execute(
        select(UserSubscriptionDB.plan, func.count()).group_by(UserSubscriptionDB.plan)
    )
    for row in result.all():
        plan_key = row[0].value if hasattr(row[0], "value") else str(row[0])
        plan_counts[plan_key] = row[1]

    return {
        "total_users": int(total_users),
        "monthly_conversations": int(monthly_conversations),
        "monthly_cost_usd": monthly_cost_usd,
        "plan_counts": plan_counts,
    }


async def list_users_with_usage(db: AsyncSession) -> list[dict[str, Any]]:
    """
    Lista todos los usuarios con su plan y uso mensual.
    """
    now = datetime.now(UTC)

    result = await db.execute(select(UserSubscriptionDB).order_by(UserSubscriptionDB.created_at.desc()))
    subscriptions = result.scalars().all()

    users = []
    for sub in subscriptions:
        # Monthly cost for this user
        cost_result = await db.execute(
            select(func.sum(AIUsageRecordDB.cost_usd))
            .where(AIUsageRecordDB.user_id == sub.user_id)
            .where(AIUsageRecordDB.is_managed == True)  # noqa: E712
            .where(extract("year", AIUsageRecordDB.created_at) == now.year)
            .where(extract("month", AIUsageRecordDB.created_at) == now.month)
        )
        monthly_cost = float(cost_result.scalar_one() or 0)

        # Monthly conversation count
        conv_result = await db.execute(
            select(func.count(func.distinct(AIUsageRecordDB.conversation_id)))
            .where(AIUsageRecordDB.user_id == sub.user_id)
            .where(AIUsageRecordDB.is_managed == True)  # noqa: E712
            .where(extract("year", AIUsageRecordDB.created_at) == now.year)
            .where(extract("month", AIUsageRecordDB.created_at) == now.month)
        )
        monthly_conversations = int(conv_result.scalar_one() or 0)

        # Fetch email from Firebase (best-effort, fallback to empty string)
        try:
            fb_user = firebase_auth.get_user(sub.user_id)
            email = fb_user.email or ""
        except Exception:
            email = ""

        users.append({
            "user_id": sub.user_id,
            "email": email,
            "plan": sub.plan.value if hasattr(sub.plan, "value") else str(sub.plan),
            "status": sub.status,
            "monthly_cost_usd": monthly_cost,
            "monthly_conversations": monthly_conversations,
            "created_at": sub.created_at.isoformat() if sub.created_at else None,
        })

    return users


async def override_user_plan(
    db: AsyncSession, user_id: str, plan: str
) -> dict[str, Any]:
    """
    Cambia el plan de un usuario directamente (override admin).
    Returns: {"success": bool, "error": str (si falla)}
    """
    if plan not in VALID_PLANS:
        return {"success": False, "error": f"Plan inválido: '{plan}'. Opciones: {sorted(VALID_PLANS)}"}

    result = await db.execute(
        select(UserSubscriptionDB).where(UserSubscriptionDB.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()

    if subscription is None:
        return {"success": False, "error": f"Usuario '{user_id}' no encontrado"}

    subscription.plan = Plan(plan)
    await db.commit()
    logger.info(f"[Admin] Plan override: user={user_id} → plan={plan}")
    return {"success": True, "user_id": user_id, "new_plan": plan}


async def toggle_user_subscription(
    db: AsyncSession, user_id: str
) -> dict[str, Any]:
    """
    Activa/desactiva la suscripción de un usuario (toggle status active ↔ paused).
    """
    result = await db.execute(
        select(UserSubscriptionDB).where(UserSubscriptionDB.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()

    if subscription is None:
        return {"success": False, "error": f"Usuario '{user_id}' no encontrado"}

    old_status = subscription.status
    subscription.status = "paused" if old_status == "active" else "active"
    await db.commit()
    logger.info(f"[Admin] Toggle subscription: user={user_id} {old_status} → {subscription.status}")
    return {"success": True, "user_id": user_id, "old_status": old_status, "new_status": subscription.status}


async def get_cost_by_month(db: AsyncSession) -> list[dict[str, Any]]:
    """
    Retorna costo total (managed) agrupado por año/mes.
    """
    result = await db.execute(
        select(
            extract("year", AIUsageRecordDB.created_at).label("year"),
            extract("month", AIUsageRecordDB.created_at).label("month"),
            func.sum(AIUsageRecordDB.cost_usd).label("total_cost_usd"),
            func.count(func.distinct(AIUsageRecordDB.conversation_id)).label("total_conversations"),
        )
        .where(AIUsageRecordDB.is_managed == True)  # noqa: E712
        .group_by("year", "month")
        .order_by("year", "month")
    )
    rows = result.all()
    return [
        {
            "year": int(row.year),
            "month": int(row.month),
            "total_cost_usd": float(row.total_cost_usd or 0),
            "total_conversations": int(row.total_conversations or 0),
        }
        for row in rows
    ]


async def get_user_usage_history(
    db: AsyncSession, user_id: str, limit: int = 100
) -> list[dict[str, Any]]:
    """
    Historial de uso de tokens de un usuario (más reciente primero).
    """
    result = await db.execute(
        select(AIUsageRecordDB)
        .where(AIUsageRecordDB.user_id == user_id)
        .order_by(AIUsageRecordDB.created_at.desc())
        .limit(limit)
    )
    records = result.scalars().all()
    return [
        {
            "id": str(record.id),
            "provider": record.provider,
            "model": record.model,
            "tokens_input": record.tokens_input,
            "tokens_output": record.tokens_output,
            "cost_usd": float(record.cost_usd or 0),
            "is_managed": record.is_managed,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
        for record in records
    ]


async def _chain_entries(db: AsyncSession) -> list[ManagedAIConfigDB]:
    result = await db.execute(select(ManagedAIConfigDB).order_by(ManagedAIConfigDB.position))
    return list(result.scalars().all())


async def _set_chain_order(
    db: AsyncSession, entries: list[ManagedAIConfigDB]
) -> None:
    """Use a temporary range so the unique position constraint never collides."""
    for index, entry in enumerate(entries):
        entry.position = -1_000_000_000 - index
    await db.flush()
    for index, entry in enumerate(entries):
        entry.position = index
    await db.flush()


async def list_ai_chain(db: AsyncSession) -> list[dict[str, Any]]:
    await ensure_default_chain(db)
    entries = await _chain_entries(db)
    since = datetime.now(UTC) - timedelta(hours=24)

    events_result = await db.execute(
        select(
            ProviderHealthEventDB.entry_id,
            func.count().filter(
                ProviderHealthEventDB.event_type.in_(["failure", "probe_fail"])
            ),
        )
        .where(ProviderHealthEventDB.created_at >= since)
        .group_by(ProviderHealthEventDB.entry_id)
    )
    failures = {row[0]: int(row[1]) for row in events_result.all()}

    usage_result = await db.execute(
        select(
            AIUsageRecordDB.provider,
            AIUsageRecordDB.model,
            func.count(),
            func.sum(AIUsageRecordDB.cost_usd),
        )
        .where(AIUsageRecordDB.created_at >= since)
        .where(AIUsageRecordDB.is_managed.is_(True))
        .group_by(AIUsageRecordDB.provider, AIUsageRecordDB.model)
    )
    usage = {
        (row[0], row[1]): {"calls": int(row[2]), "cost_usd": float(row[3] or 0)}
        for row in usage_result.all()
    }

    response = []
    for entry in entries:
        entry_usage = usage.get((entry.provider_name, entry.model), {"calls": 0, "cost_usd": 0.0})
        response.append(
            {
                "id": str(entry.id),
                "position": entry.position,
                "provider_name": entry.provider_name,
                "model": entry.model,
                "base_url": entry.base_url,
                "requires_tools": entry.requires_tools,
                "is_enabled": entry.is_enabled,
                "is_healthy": entry.is_healthy,
                "consecutive_failures": entry.consecutive_failures,
                "last_error": entry.last_error[:200] if entry.last_error else None,
                "last_probe_at": entry.last_probe_at.isoformat() if entry.last_probe_at else None,
                "last_probe_latency_ms": entry.last_probe_latency_ms,
                "has_api_key": bool(entry.api_key_encrypted),
                "summary_24h": {
                    "calls": entry_usage["calls"],
                    "failures": failures.get(entry.id, 0),
                    "cost_usd": entry_usage["cost_usd"],
                },
            }
        )
    return response


async def create_ai_chain_entry(
    db: AsyncSession, body: ManagedAIConfigCreate
) -> dict[str, Any]:
    entries = await _chain_entries(db)
    position = len(entries) if body.position is None else min(body.position, len(entries))
    entry = ManagedAIConfigDB(
        # Outside the temporary reorder range and all valid API positions.
        position=-2_000_000_000 + len(entries),
        provider_name=body.provider_name,
        base_url=body.base_url,
        model=body.model,
        api_key_encrypted=encrypt_api_key(body.api_key) if body.api_key else None,
        requires_tools=body.requires_tools,
    )
    db.add(entry)
    await db.flush()
    entries.insert(position, entry)
    await _set_chain_order(db, entries)
    await db.commit()
    await db.refresh(entry)
    return {"success": True, "id": str(entry.id), "position": entry.position}


async def update_ai_chain_entry(
    db: AsyncSession, entry_id: UUID, body: ManagedAIConfigUpdate
) -> dict[str, Any]:
    entry = await db.get(ManagedAIConfigDB, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="AI chain entry not found")

    values = body.model_dump(exclude_unset=True, exclude={"position", "api_key"})
    for field, value in values.items():
        setattr(entry, field, value)
    if "api_key" in body.model_fields_set and body.api_key is not None:
        entry.api_key_encrypted = encrypt_api_key(body.api_key)

    if body.position is not None:
        entries = [item for item in await _chain_entries(db) if item.id != entry.id]
        entries.insert(min(body.position, len(entries)), entry)
        await _set_chain_order(db, entries)
    await db.commit()
    return {"success": True, "id": str(entry.id), "position": entry.position}


async def delete_ai_chain_entry(db: AsyncSession, entry_id: UUID) -> dict[str, Any]:
    entry = await db.get(ManagedAIConfigDB, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="AI chain entry not found")
    await db.delete(entry)
    await db.flush()
    await _set_chain_order(db, await _chain_entries(db))
    await db.commit()
    return {"success": True, "id": str(entry_id)}


async def reorder_ai_chain(db: AsyncSession, ordered_ids: list[UUID]) -> dict[str, Any]:
    entries = await _chain_entries(db)
    existing_ids = {entry.id for entry in entries}
    if len(ordered_ids) != len(set(ordered_ids)) or set(ordered_ids) != existing_ids:
        raise HTTPException(
            status_code=400,
            detail="ordered_ids must contain every chain entry exactly once",
        )
    by_id = {entry.id: entry for entry in entries}
    await _set_chain_order(db, [by_id[entry_id] for entry_id in ordered_ids])
    await db.commit()
    return {"success": True, "ordered_ids": [str(value) for value in ordered_ids]}


async def probe_ai_chain_entry(db: AsyncSession, entry_id: UUID) -> dict[str, Any]:
    entry = await db.get(ManagedAIConfigDB, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="AI chain entry not found")
    choice = choice_from_entry(entry)
    started = time.perf_counter()
    try:
        provider = UnifiedAIProvider(
            provider=choice.provider,
            model=choice.model,
            api_key=choice.api_key,
            base_url=choice.base_url,
            temperature=0,
            max_tokens=8,
        )
        await asyncio.wait_for(
            provider.generate_response(messages=[{"role": "user", "content": "ping"}]),
            timeout=15,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        await record_probe_result(db, entry_id, ok=True, latency_ms=latency_ms)
        return {"ok": True, "latency_ms": latency_ms}
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        error = str(exc)[:200]
        await record_probe_result(
            db, entry_id, ok=False, latency_ms=latency_ms, error=error
        )
        return {"ok": False, "latency_ms": latency_ms, "error": error}


async def list_ai_chain_events(
    db: AsyncSession, limit: int = 100
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(ProviderHealthEventDB, ManagedAIConfigDB.provider_name, ManagedAIConfigDB.model)
        .join(ManagedAIConfigDB, ManagedAIConfigDB.id == ProviderHealthEventDB.entry_id)
        .order_by(ProviderHealthEventDB.created_at.desc())
        .limit(max(1, min(limit, 500)))
    )
    return [
        {
            "id": str(event.id),
            "entry_id": str(event.entry_id),
            "provider_name": provider_name,
            "model": model,
            "event_type": event.event_type,
            "error": event.error[:200] if event.error else None,
            "latency_ms": event.latency_ms,
            "created_at": event.created_at.isoformat(),
        }
        for event, provider_name, model in result.all()
    ]
