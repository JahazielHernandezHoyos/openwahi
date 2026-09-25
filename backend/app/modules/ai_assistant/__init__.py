"""
AI Assistant module for WhatsApp integration.
Provides LLM-powered chat responses using LangChain.
"""

from .models import (
    AIConfigCreate,
    AIConfigResponse,
    AIConfigUpdate,
    AIConversationResponse,
    AIMessageResponse,
    WhatsAppAIConfigDB,
    WhatsAppAIConversationDB,
    WhatsAppAIMessageDB,
)
from .provider import UnifiedAIProvider
from .service import AIAssistantService

__all__ = [
    "WhatsAppAIConfigDB",
    "WhatsAppAIConversationDB",
    "WhatsAppAIMessageDB",
    "AIConfigCreate",
    "AIConfigUpdate",
    "AIConfigResponse",
    "AIMessageResponse",
    "AIConversationResponse",
    "AIAssistantService",
    "UnifiedAIProvider",
]
