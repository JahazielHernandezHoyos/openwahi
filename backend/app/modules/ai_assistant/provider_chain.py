"""Database-managed provider selection and health tracking for Plan Pro runs."""

from __future__ import annotations

import logging
from collections.abc import Collection
from datetime import UTC, datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings

from .encryption import decrypt_api_key, encrypt_api_key
from .managed_provider import ManagedProviderChoice, resolve_managed_agent_provider
from .models import ManagedAIConfigDB, ProviderHealthEventDB

logger = logging.getLogger(__name__)

FAILURES_TO_OPEN_CIRCUIT = 3
OPENCODE_GO_BASE_URL = "https://opencode.ai/zen/go/v1"


def provider_adapter_name(entry: ManagedAIConfigDB) -> str:
    """Translate a display/provider identity into a UnifiedAIProvider adapter."""
    if entry.provider_name in {"groq", "bedrock", "llamacpp"} and not entry.base_url:
        return entry.provider_name
    return "openai_compatible"


def choice_from_entry(entry: ManagedAIConfigDB) -> ManagedProviderChoice:
    """Build a runtime choice without exposing the encrypted credential."""
    api_key = (
        decrypt_api_key(entry.api_key_encrypted)
        if entry.api_key_encrypted
        else ""
    )
    return ManagedProviderChoice(
        provider=provider_adapter_name(entry),
        model=entry.model,
        api_key=api_key,
        escalated=entry.position > 0,
        reason=f"chain: {entry.provider_name}/{entry.model} pos {entry.position}",
        entry_id=entry.id,
        provider_name=entry.provider_name,
        base_url=entry.base_url,
        position=entry.position,
    )


async def chain_exists(db: AsyncSession) -> bool:
    result = await db.execute(select(func.count()).select_from(ManagedAIConfigDB))
    return bool(result.scalar_one())


async def ensure_default_chain(db: AsyncSession) -> bool:
    """Seed the recommended chain once; never overwrite admin configuration."""
    if await chain_exists(db):
        return False

    defaults = [
        ManagedAIConfigDB(
            position=0,
            provider_name="llamacpp",
            model=settings.MANAGED_AI_MODEL,
            requires_tools=False,
        ),
        ManagedAIConfigDB(
            position=1,
            provider_name="opencode-zen-go",
            base_url=OPENCODE_GO_BASE_URL,
            model="deepseek-v4-flash",
            api_key_encrypted=(
                encrypt_api_key(settings.OPENCODE_GO_API_KEY)
                if settings.OPENCODE_GO_API_KEY
                else None
            ),
            requires_tools=True,
        ),
        ManagedAIConfigDB(
            position=2,
            provider_name="groq",
            model="llama-3.3-70b-versatile",
            api_key_encrypted=(
                encrypt_api_key(settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
            ),
            requires_tools=True,
        ),
    ]
    db.add_all(defaults)
    await db.commit()
    logger.info("🔗 Seeded default managed AI provider chain")
    return True


async def get_chain_choices(
    db: AsyncSession,
    *,
    tool_count: int,
    chat_provider: str,
    chat_model: str,
    chat_api_key: str,
    excluded_entry_ids: Collection[UUID] = (),
) -> list[ManagedProviderChoice]:
    """Return eligible choices in failover order."""
    if tool_count <= 0:
        return [
            ManagedProviderChoice(
                provider=chat_provider,
                model=chat_model,
                api_key=chat_api_key,
                escalated=False,
                reason="chain: simple chat keeps managed settings provider",
                provider_name=chat_provider,
            )
        ]

    statement = (
        select(ManagedAIConfigDB)
        .where(ManagedAIConfigDB.is_enabled.is_(True))
        .where(ManagedAIConfigDB.is_healthy.is_(True))
        .where(ManagedAIConfigDB.requires_tools.is_(True))
        .order_by(ManagedAIConfigDB.position)
    )
    if excluded_entry_ids:
        statement = statement.where(ManagedAIConfigDB.id.not_in(excluded_entry_ids))
    result = await db.execute(statement)
    return [choice_from_entry(entry) for entry in result.scalars().all()]


async def resolve_chain_provider(
    db: AsyncSession,
    *,
    tool_count: int,
    chat_provider: str,
    chat_model: str,
    chat_api_key: str,
) -> ManagedProviderChoice:
    """Resolve a managed run, preserving the legacy env fallback for an empty chain."""
    if not await chain_exists(db):
        return resolve_managed_agent_provider(
            provider=chat_provider,
            model=chat_model,
            api_key=chat_api_key,
            tool_count=tool_count,
            escalation_enabled=settings.MANAGED_AI_TOOL_ESCALATION_ENABLED,
            tool_provider=settings.MANAGED_AI_TOOL_PROVIDER,
            tool_model=settings.MANAGED_AI_TOOL_MODEL,
            tool_api_key=settings.GROQ_API_KEY or "",
        )

    choices = await get_chain_choices(
        db,
        tool_count=tool_count,
        chat_provider=chat_provider,
        chat_model=chat_model,
        chat_api_key=chat_api_key,
    )
    if choices:
        return choices[0]

    # A configured but unavailable chain must not silently route to an unhealthy entry.
    raise RuntimeError("Managed AI chain has no enabled healthy tool-capable provider")


async def _event(
    db: AsyncSession,
    entry_id: UUID,
    event_type: str,
    *,
    error: str | None = None,
    latency_ms: int | None = None,
) -> None:
    db.add(
        ProviderHealthEventDB(
            entry_id=entry_id,
            event_type=event_type,
            error=error,
            latency_ms=latency_ms,
        )
    )


async def record_chain_failure(db: AsyncSession, entry_id: UUID, error: Exception | str) -> None:
    entry = await db.get(ManagedAIConfigDB, entry_id)
    if entry is None:
        return
    error_text = str(error)[:4000]
    entry.consecutive_failures = (entry.consecutive_failures or 0) + 1
    entry.last_error = error_text
    await _event(db, entry_id, "failure", error=error_text)
    if entry.consecutive_failures >= FAILURES_TO_OPEN_CIRCUIT and entry.is_healthy:
        entry.is_healthy = False
        await _event(db, entry_id, "circuit_open", error=error_text)
        logger.warning(f"🔴 Provider circuit opened: {entry.provider_name}/{entry.model}")
    await db.flush()


async def record_chain_success(db: AsyncSession, entry_id: UUID, latency_ms: int) -> None:
    entry = await db.get(ManagedAIConfigDB, entry_id)
    if entry is None:
        return
    was_unhealthy = not entry.is_healthy
    had_failures = bool(entry.consecutive_failures)
    entry.consecutive_failures = 0
    entry.last_error = None
    entry.is_healthy = True
    if was_unhealthy:
        await _event(db, entry_id, "circuit_close", latency_ms=latency_ms)
    if was_unhealthy or had_failures:
        await _event(db, entry_id, "recovery", latency_ms=latency_ms)
    await db.flush()


async def record_probe_result(
    db: AsyncSession,
    entry_id: UUID,
    *,
    ok: bool,
    latency_ms: int,
    error: str | None = None,
) -> None:
    """Persist active-probe state; only a successful probe revives an open circuit."""
    entry = await db.get(ManagedAIConfigDB, entry_id)
    if entry is None:
        return
    entry.last_probe_at = datetime.now(UTC)
    entry.last_probe_latency_ms = latency_ms
    if ok:
        was_unhealthy = not entry.is_healthy
        entry.is_healthy = True
        entry.consecutive_failures = 0
        entry.last_error = None
        await _event(db, entry_id, "probe_ok", latency_ms=latency_ms)
        if was_unhealthy:
            await _event(db, entry_id, "circuit_close", latency_ms=latency_ms)
            await _event(db, entry_id, "recovery", latency_ms=latency_ms)
    else:
        entry.last_error = (error or "Probe failed")[:4000]
        await _event(
            db,
            entry_id,
            "probe_fail",
            error=entry.last_error,
            latency_ms=latency_ms,
        )
    await db.commit()
