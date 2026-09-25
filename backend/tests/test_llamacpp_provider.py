"""Unit tests for the local llama.cpp OpenAI-compatible provider."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.modules.ai_assistant.models import AIConfigCreate, AIConfigUpdate
from app.modules.ai_assistant.provider import UnifiedAIProvider
from app.modules.ai_assistant.service import AIAssistantService


def test_llamacpp_provider_uses_configurable_openai_endpoint(monkeypatch):
    monkeypatch.setenv("LLAMACPP_BASE_URL", "http://model-server:9090/v1")

    chat_openai = MagicMock()
    local_config = {**UnifiedAIProvider.PROVIDERS["llamacpp"], "class": chat_openai}
    with patch.dict(UnifiedAIProvider.PROVIDERS, {"llamacpp": local_config}):
        provider = UnifiedAIProvider(
            provider="llamacpp",
            model="Qwen3.5-0.8B-Q8_0",
            api_key="must-not-leak-to-local-server",
            temperature=0.2,
            max_tokens=256,
        )

    chat_openai.assert_called_once_with(
        model="Qwen3.5-0.8B-Q8_0",
        api_key="local-no-key",
        temperature=0.2,
        max_tokens=256,
        base_url="http://model-server:9090/v1",
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    assert provider.get_llm() is chat_openai.return_value


def test_llamacpp_config_does_not_require_user_api_key():
    config = AIConfigCreate(
        provider="llamacpp",
        model="Qwen3.5-0.8B-Q8_0",
    )

    assert config.api_key is None


def test_llamacpp_is_the_default_config():
    config = AIConfigCreate()

    assert config.provider == "llamacpp"
    assert config.model == "Qwen3.5-0.8B-Q8_0"
    assert config.api_key is None


def test_remote_provider_still_requires_user_api_key():
    with pytest.raises(ValidationError, match="api_key is required"):
        AIConfigCreate(
            provider="groq",
            model="llama-3.3-70b-versatile",
        )


def test_switching_to_remote_provider_requires_new_api_key():
    with pytest.raises(ValidationError, match="api_key is required"):
        AIConfigUpdate(provider="groq", model="llama-3.3-70b-versatile")


def test_llamacpp_model_is_available():
    assert UnifiedAIProvider.validate_provider_model(
        "llamacpp", "Qwen3.5-0.8B-Q8_0"
    )


@pytest.mark.asyncio
async def test_service_creates_keyless_llamacpp_config_with_internal_sentinel():
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    stored_config = MagicMock()
    result = MagicMock()
    result.scalar_one.return_value = stored_config
    db.execute = AsyncMock(return_value=result)

    with patch(
        "app.modules.ai_assistant.service.encrypt_api_key",
        return_value="encrypted-sentinel",
    ) as encrypt:
        created = await AIAssistantService.create_config(
            db=db,
            user_id="user-1",
            provider="llamacpp",
            model="Qwen3.5-0.8B-Q8_0",
            api_key=None,
        )

    plaintext = encrypt.call_args.args[0]
    assert plaintext
    assert plaintext != "local-no-key"
    assert db.add.call_args.args[0].api_key_encrypted == "encrypted-sentinel"
    assert created is stored_config


@pytest.mark.asyncio
async def test_service_edits_keyless_llamacpp_config_without_replacing_api_key():
    config = MagicMock()
    config.provider = "llamacpp"
    result = MagicMock()
    result.scalar_one.return_value = config
    db = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(return_value=result)

    with (
        patch.object(
            AIAssistantService,
            "get_config",
            new=AsyncMock(return_value=config),
        ),
        patch("app.modules.ai_assistant.service.encrypt_api_key") as encrypt,
    ):
        updated = await AIAssistantService.update_config(
            db,
            config_id=MagicMock(),
            system_prompt="Updated prompt",
        )

    encrypt.assert_not_called()
    assert config.system_prompt == "Updated prompt"
    assert updated is config


@pytest.mark.asyncio
async def test_service_rejects_keyless_remote_config_even_if_schema_is_bypassed():
    db = MagicMock()

    with pytest.raises(ValueError, match="API key is required"):
        await AIAssistantService.create_config(
            db=db,
            user_id="user-1",
            provider="groq",
            model="llama-3.3-70b-versatile",
            api_key=None,
        )
