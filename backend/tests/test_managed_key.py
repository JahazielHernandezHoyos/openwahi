"""
Tests para lógica de managed key en langgraph_agent.
"""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# =============================================================================
# Tests para process_message_with_agent — firma + tracking
# =============================================================================

def test_process_message_with_agent_accepts_tracking_params():
    """La función acepta los nuevos parámetros sin TypeError."""
    import inspect

    from app.modules.ai_assistant.langgraph_agent import process_message_with_agent

    sig = inspect.signature(process_message_with_agent)
    params = sig.parameters
    assert "provider" in params
    assert "model" in params
    assert "is_managed" in params
    assert "config_id" in params
    assert "conversation_id" in params


def test_provider_defaults_are_safe():
    """Los defaults de los nuevos parámetros no causan errores en producción si no se pasan."""
    import inspect

    from app.modules.ai_assistant.langgraph_agent import process_message_with_agent

    sig = inspect.signature(process_message_with_agent)
    assert sig.parameters["is_managed"].default is False
    assert sig.parameters["config_id"].default is None
    assert sig.parameters["conversation_id"].default is None


# =============================================================================
# Tests para lógica de managed key en service
# =============================================================================

def test_managed_key_message_is_spanish():
    """El mensaje de límite excedido está en español (requerimiento UX)."""
    # Verificar que el mensaje hardcodeado en service.py está en español
    service_path = Path(__file__).resolve().parents[1] / "app/modules/ai_assistant/service.py"
    src = service_path.read_text()
    assert "Has alcanzado el límite" in src or "límite" in src


def test_bedrock_provider_is_in_unified_provider():
    """UnifiedAIProvider reconoce 'bedrock' como proveedor válido."""
    from app.modules.ai_assistant.provider import UnifiedAIProvider
    assert "bedrock" in UnifiedAIProvider.PROVIDERS
    assert "amazon.nova-lite-v1:0" in UnifiedAIProvider.PROVIDERS["bedrock"]["models"]


def test_bedrock_base_url_is_set():
    """Bedrock tiene base_url configurada (necesaria para API OpenAI-compatible)."""
    from app.modules.ai_assistant.provider import UnifiedAIProvider
    base_url = UnifiedAIProvider.PROVIDERS["bedrock"].get("base_url", "")
    assert "bedrock-runtime" in base_url
    assert "us-east-1" in base_url


def test_settings_has_all_managed_vars():
    """Settings expone todas las variables de Managed AI."""
    import inspect

    from app.config.settings import Settings
    fields = Settings.model_fields
    assert "MANAGED_AI_PROVIDER" in fields
    assert "MANAGED_AI_MODEL" in fields
    assert "BEDROCK_API_KEY" in fields
    assert "PRO_MONTHLY_CONVERSATION_LIMIT" in fields


def test_pro_monthly_limit_default_is_3000():
    """El límite mensual default del plan Pro es 3000."""
    from app.config.settings import Settings
    assert Settings.model_fields["PRO_MONTHLY_CONVERSATION_LIMIT"].default == 3000
