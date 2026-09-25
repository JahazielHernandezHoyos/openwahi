"""
Admin router — endpoints del dashboard de administración.
Solo accesible para emails verificados listados en ADMIN_EMAILS.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.dependencies import get_admin_user
from app.modules.admin import service
from app.modules.ai_assistant.models import (
    ManagedAIChainReorder,
    ManagedAIConfigCreate,
    ManagedAIConfigUpdate,
)

router = APIRouter(tags=["admin"])


@router.get("/stats", response_model=dict)
async def get_stats(
    _: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Estadísticas globales del sistema."""
    return await service.get_global_stats(db)


@router.get("/users", response_model=list)
async def list_users(
    _: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Lista de usuarios con su plan y uso mensual."""
    return await service.list_users_with_usage(db)


@router.patch("/{user_id}/plan", response_model=dict)
@router.patch("/users/{user_id}/plan", response_model=dict)
async def update_user_plan(
    user_id: str,
    body: dict,
    _: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Cambia el plan de un usuario (override admin)."""
    plan = body.get("plan", "")
    return await service.override_user_plan(db, user_id, plan)


@router.patch("/{user_id}/toggle", response_model=dict)
@router.patch("/users/{user_id}/toggle", response_model=dict)
@router.patch("/users/{user_id}/subscription/toggle", response_model=dict)
async def toggle_subscription(
    user_id: str,
    _: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Activa/desactiva la suscripción de un usuario."""
    return await service.toggle_user_subscription(db, user_id)


@router.get("/costs/monthly", response_model=list)
@router.get("/costs", response_model=list)
async def get_monthly_costs(
    _: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Costo total agrupado por mes."""
    return await service.get_cost_by_month(db)


@router.get("/{user_id}/usage", response_model=list)
@router.get("/users/{user_id}/usage", response_model=list)
async def get_user_usage(
    user_id: str,
    _: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Historial de uso de tokens de un usuario."""
    return await service.get_user_usage_history(db, user_id)


@router.get("/ai-chain", response_model=list)
async def get_ai_chain(
    _: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await service.list_ai_chain(db)


@router.post("/ai-chain", response_model=dict)
async def create_ai_chain_entry(
    body: ManagedAIConfigCreate,
    _: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await service.create_ai_chain_entry(db, body)


@router.patch("/ai-chain/{entry_id:uuid}", response_model=dict)
async def update_ai_chain_entry(
    entry_id: UUID,
    body: ManagedAIConfigUpdate,
    _: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await service.update_ai_chain_entry(db, entry_id, body)


@router.delete("/ai-chain/{entry_id:uuid}", response_model=dict)
async def delete_ai_chain_entry(
    entry_id: UUID,
    _: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await service.delete_ai_chain_entry(db, entry_id)


@router.post("/ai-chain/reorder", response_model=dict)
async def reorder_ai_chain(
    body: ManagedAIChainReorder,
    _: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await service.reorder_ai_chain(db, body.ordered_ids)


@router.post("/ai-chain/{entry_id:uuid}/probe", response_model=dict)
async def probe_ai_chain_entry(
    entry_id: UUID,
    _: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await service.probe_ai_chain_entry(db, entry_id)


@router.get("/ai-chain/events", response_model=list)
async def get_ai_chain_events(
    limit: int = 100,
    _: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await service.list_ai_chain_events(db, limit)
