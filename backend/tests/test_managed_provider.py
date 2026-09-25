"""Tests for managed (Plan Pro) provider escalation when tools are needed."""

from app.modules.ai_assistant.managed_provider import (
    TOOL_UNRELIABLE_PROVIDERS,
    resolve_managed_agent_provider,
)

LOCAL = dict(
    provider="llamacpp",
    model="Qwen3.5-0.8B-Q8_0",
    api_key="local-sentinel",
)

FALLBACK = dict(
    tool_provider="groq",
    tool_model="llama-3.3-70b-versatile",
    tool_api_key="groq-key",
)


def _resolve(**overrides):
    kwargs = {
        **LOCAL,
        **FALLBACK,
        "tool_count": 1,
        "escalation_enabled": True,
    }
    kwargs.update(overrides)
    return resolve_managed_agent_provider(**kwargs)


def test_local_provider_is_marked_tool_unreliable():
    assert "llamacpp" in TOOL_UNRELIABLE_PROVIDERS


def test_escalates_to_tool_provider_when_tools_enabled():
    choice = _resolve()

    assert choice.escalated is True
    assert choice.provider == "groq"
    assert choice.model == "llama-3.3-70b-versatile"
    assert choice.api_key == "groq-key"
    assert "escalated from llamacpp to groq" in choice.reason


def test_keeps_local_provider_when_user_has_no_tools():
    choice = _resolve(tool_count=0)

    assert choice.escalated is False
    assert choice.provider == "llamacpp"
    assert choice.api_key == "local-sentinel"
    assert "no tools enabled" in choice.reason


def test_keeps_local_provider_when_escalation_disabled():
    choice = _resolve(escalation_enabled=False)

    assert choice.escalated is False
    assert choice.provider == "llamacpp"
    assert "disabled by configuration" in choice.reason


def test_keeps_local_provider_when_fallback_key_missing():
    choice = _resolve(tool_api_key="")

    assert choice.escalated is False
    assert choice.provider == "llamacpp"
    assert "no tool-capable fallback configured" in choice.reason


def test_keeps_local_provider_when_fallback_model_missing():
    choice = _resolve(tool_model="")

    assert choice.escalated is False
    assert choice.provider == "llamacpp"


def test_remote_provider_is_never_escalated():
    choice = _resolve(provider="bedrock", model="amazon.nova-pro-v1:0", api_key="bk")

    assert choice.escalated is False
    assert choice.provider == "bedrock"
    assert choice.model == "amazon.nova-pro-v1:0"
    assert choice.api_key == "bk"
    assert "supports tool calling" in choice.reason


def test_choice_is_immutable():
    choice = _resolve()

    try:
        choice.provider = "other"  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("ManagedProviderChoice should be frozen")
