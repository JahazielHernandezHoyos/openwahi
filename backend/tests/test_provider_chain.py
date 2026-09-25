"""Pure unit tests for the database-managed AI provider chain."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Register relationship targets before constructing SQLAlchemy model instances.
import app.modules.knowledge_base.models  # noqa: F401
import app.modules.whatsapp.models  # noqa: F401
from app.modules.admin.service import _set_chain_order
from app.modules.ai_assistant.encryption import decrypt_api_key, encrypt_api_key
from app.modules.ai_assistant.models import ManagedAIConfigDB
from app.modules.ai_assistant.provider import UnifiedAIProvider
from app.modules.ai_assistant.provider_chain import (
    choice_from_entry,
    ensure_default_chain,
    get_chain_choices,
    record_chain_failure,
    record_probe_result,
    resolve_chain_provider,
)


def _entry(position: int, **overrides) -> ManagedAIConfigDB:
    values = {
        "id": uuid4(),
        "position": position,
        "provider_name": "opencode-zen-go",
        "base_url": "https://opencode.ai/zen/go/v1",
        "model": "deepseek-v4-flash",
        "api_key_encrypted": encrypt_api_key("test-provider-key"),
        "requires_tools": True,
        "is_enabled": True,
        "is_healthy": True,
        "consecutive_failures": 0,
    }
    values.update(overrides)
    return ManagedAIConfigDB(**values)


def _result(*, scalar=None, entries=None):
    result = MagicMock()
    result.scalar_one.return_value = scalar
    result.scalars.return_value.all.return_value = entries or []
    return result


def test_chain_credential_round_trip_and_choice_adapter():
    entry = _entry(1)

    choice = choice_from_entry(entry)

    assert decrypt_api_key(entry.api_key_encrypted) == "test-provider-key"
    assert choice.provider == "openai_compatible"
    assert choice.provider_name == "opencode-zen-go"
    assert choice.model == "deepseek-v4-flash"
    assert choice.base_url == "https://opencode.ai/zen/go/v1"
    assert choice.api_key == "test-provider-key"
    assert choice.reason == "chain: opencode-zen-go/deepseek-v4-flash pos 1"


def test_openai_compatible_accepts_dynamic_models_and_base_url():
    chat_openai = MagicMock()
    config = {**UnifiedAIProvider.PROVIDERS["openai_compatible"], "class": chat_openai}
    with patch.dict(UnifiedAIProvider.PROVIDERS, {"openai_compatible": config}):
        provider = UnifiedAIProvider(
            provider="openai_compatible",
            model="deepseek-v4-flash",
            api_key="key",
            base_url="https://opencode.ai/zen/go/v1",
            temperature=0.2,
            max_tokens=128,
        )

    chat_openai.assert_called_once_with(
        model="deepseek-v4-flash",
        api_key="key",
        temperature=0.2,
        max_tokens=128,
        base_url="https://opencode.ai/zen/go/v1",
    )
    assert provider.get_llm() is chat_openai.return_value
    assert UnifiedAIProvider.validate_provider_model(
        "openai_compatible", "any-non-empty-model"
    )
    assert not UnifiedAIProvider.validate_provider_model("openai_compatible", "")


@pytest.mark.asyncio
async def test_default_chain_seeds_recommended_order_without_plaintext_keys():
    db = MagicMock()
    db.execute = AsyncMock(return_value=_result(scalar=0))
    db.commit = AsyncMock()

    with (
        patch("app.modules.ai_assistant.provider_chain.settings.OPENCODE_GO_API_KEY", "zen-key"),
        patch("app.modules.ai_assistant.provider_chain.settings.GROQ_API_KEY", "groq-key"),
    ):
        created = await ensure_default_chain(db)

    assert created is True
    entries = db.add_all.call_args.args[0]
    assert [(entry.position, entry.provider_name, entry.model) for entry in entries] == [
        (0, "llamacpp", "Qwen3.5-0.8B-Q8_0"),
        (1, "opencode-zen-go", "deepseek-v4-flash"),
        (2, "groq", "llama-3.3-70b-versatile"),
    ]
    assert entries[1].api_key_encrypted != "zen-key"
    assert decrypt_api_key(entries[1].api_key_encrypted) == "zen-key"
    assert decrypt_api_key(entries[2].api_key_encrypted) == "groq-key"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_tool_run_selects_first_healthy_tool_provider():
    opencode = _entry(1)
    groq = _entry(
        2,
        provider_name="groq",
        base_url=None,
        model="llama-3.3-70b-versatile",
    )
    db = AsyncMock()
    db.execute.side_effect = [
        _result(scalar=2),
        _result(entries=[opencode, groq]),
    ]

    choice = await resolve_chain_provider(
        db,
        tool_count=1,
        chat_provider="llamacpp",
        chat_model="Qwen3.5-0.8B-Q8_0",
        chat_api_key="",
    )

    assert choice.entry_id == opencode.id
    assert choice.provider_name == "opencode-zen-go"


@pytest.mark.asyncio
async def test_simple_chat_keeps_current_managed_provider():
    db = AsyncMock()
    db.execute.side_effect = [_result(scalar=3)]

    choice = await resolve_chain_provider(
        db,
        tool_count=0,
        chat_provider="llamacpp",
        chat_model="Qwen3.5-0.8B-Q8_0",
        chat_api_key="local",
    )

    assert choice.entry_id is None
    assert choice.provider == "llamacpp"
    assert choice.model == "Qwen3.5-0.8B-Q8_0"


@pytest.mark.asyncio
async def test_legacy_env_fallback_when_chain_is_empty():
    db = AsyncMock()
    db.execute.return_value = _result(scalar=0)
    with patch(
        "app.modules.ai_assistant.provider_chain.resolve_managed_agent_provider"
    ) as legacy:
        legacy.return_value = SimpleNamespace(provider="groq")
        choice = await resolve_chain_provider(
            db,
            tool_count=1,
            chat_provider="llamacpp",
            chat_model="local-model",
            chat_api_key="",
        )

    assert choice.provider == "groq"
    legacy.assert_called_once()


@pytest.mark.asyncio
async def test_unhealthy_entries_are_excluded_from_candidate_query():
    healthy = _entry(2, provider_name="groq", base_url=None)
    db = AsyncMock()
    db.execute.return_value = _result(entries=[healthy])

    choices = await get_chain_choices(
        db,
        tool_count=2,
        chat_provider="llamacpp",
        chat_model="local",
        chat_api_key="",
    )

    assert [choice.entry_id for choice in choices] == [healthy.id]
    statement = str(db.execute.call_args.args[0])
    assert "is_healthy" in statement
    assert "requires_tools" in statement
    assert "position" in statement


@pytest.mark.asyncio
async def test_three_failures_open_circuit_and_emit_events():
    entry = _entry(1)
    db = MagicMock()
    db.get = AsyncMock(return_value=entry)
    db.flush = AsyncMock()

    await record_chain_failure(db, entry.id, "one")
    await record_chain_failure(db, entry.id, "two")
    await record_chain_failure(db, entry.id, "three")

    assert entry.consecutive_failures == 3
    assert entry.is_healthy is False
    assert entry.last_error == "three"
    event_types = [call.args[0].event_type for call in db.add.call_args_list]
    assert event_types == ["failure", "failure", "failure", "circuit_open"]


@pytest.mark.asyncio
async def test_successful_probe_recovers_open_circuit():
    entry = _entry(1, is_healthy=False, consecutive_failures=3, last_error="down")
    db = MagicMock()
    db.get = AsyncMock(return_value=entry)
    db.commit = AsyncMock()

    await record_probe_result(db, entry.id, ok=True, latency_ms=42)

    assert entry.is_healthy is True
    assert entry.consecutive_failures == 0
    assert entry.last_error is None
    assert entry.last_probe_latency_ms == 42
    event_types = [call.args[0].event_type for call in db.add.call_args_list]
    assert event_types == ["probe_ok", "circuit_close", "recovery"]
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_reorder_uses_collision_free_temporary_positions():
    entries = [_entry(2), _entry(0), _entry(1)]
    db = MagicMock()
    db.flush = AsyncMock()
    positions_at_flush = []

    async def capture_flush():
        positions_at_flush.append([entry.position for entry in entries])

    db.flush.side_effect = capture_flush
    await _set_chain_order(db, entries)

    assert positions_at_flush[0] == [-1_000_000_000, -1_000_000_001, -1_000_000_002]
    assert positions_at_flush[1] == [0, 1, 2]
