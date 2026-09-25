"""Provider selection for managed (Plan Pro) assistant runs.

The managed provider defaults to local CPU inference, which is fast and free but
unreliable at emitting tool calls. When a Plan Pro user has webhook tools
enabled, the agent must run on a provider that reliably supports tool calling,
otherwise lead-capture tools silently never fire.
"""

from dataclasses import dataclass
from uuid import UUID

# Providers that serve chat well but cannot be trusted to emit tool calls.
TOOL_UNRELIABLE_PROVIDERS = frozenset({"llamacpp"})


@dataclass(frozen=True)
class ManagedProviderChoice:
    """Resolved provider for a single managed agent run."""

    provider: str
    model: str
    api_key: str
    escalated: bool
    reason: str
    entry_id: UUID | None = None
    provider_name: str | None = None
    base_url: str | None = None
    position: int | None = None


def resolve_managed_agent_provider(
    *,
    provider: str,
    model: str,
    api_key: str,
    tool_count: int,
    escalation_enabled: bool,
    tool_provider: str,
    tool_model: str,
    tool_api_key: str,
) -> ManagedProviderChoice:
    """Pick the provider for a managed agent run.

    Escalates away from a tool-unreliable provider only when the run actually
    needs tools and a usable fallback is configured. Every other case keeps the
    default provider so local inference stays the norm for plain chat.
    """

    def keep(reason: str) -> ManagedProviderChoice:
        return ManagedProviderChoice(
            provider=provider,
            model=model,
            api_key=api_key,
            escalated=False,
            reason=reason,
        )

    if provider not in TOOL_UNRELIABLE_PROVIDERS:
        return keep("provider supports tool calling")

    if tool_count <= 0:
        return keep("no tools enabled for this user")

    if not escalation_enabled:
        return keep("tool escalation disabled by configuration")

    if not tool_provider or not tool_model or not tool_api_key:
        return keep("no tool-capable fallback configured")

    return ManagedProviderChoice(
        provider=tool_provider,
        model=tool_model,
        api_key=tool_api_key,
        escalated=True,
        reason=(
            f"escalated from {provider} to {tool_provider} "
            f"for {tool_count} enabled tool(s)"
        ),
    )
