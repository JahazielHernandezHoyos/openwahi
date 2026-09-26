"""
Widget Service - Business logic for embeddable chat widget.

Handles token validation, visitor conversations, and AI response generation.
"""

import logging
import time
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.ai_assistant.encryption import decrypt_api_key
from app.modules.ai_assistant.memory import ConversationMemory
from app.modules.ai_assistant.models import WhatsAppAIConfigDB
from app.modules.ai_assistant.prompt_enhancer import PromptEnhancer
from app.modules.ai_assistant.provider import UnifiedAIProvider
from app.modules.ai_assistant.rate_limit_handler import (
    RateLimitError,
    generate_with_rate_limit_handling,
    get_user_friendly_error_message,
)
from app.modules.ai_assistant.service import _get_agentic_rag_context

from .models import (
    WidgetConfigResponse,
    WidgetConversationDB,
    WidgetMessageDB,
    WidgetTokenDB,
)

logger = logging.getLogger(__name__)


class WidgetService:
    """Service for managing chat widget tokens and conversations."""

    # ==================== Token Management ====================

    @staticmethod
    async def create_token(
        db: AsyncSession,
        user_id: str,
        ai_config_id: UUID,
        name: str,
        allowed_origins: Optional[str] = None,
        primary_color: Optional[str] = None,
        secondary_color: Optional[str] = None,
    ) -> WidgetTokenDB:
        """
        Create a new widget token linked to an AI config.

        Args:
            db: Database session
            user_id: Owner's Firebase UID
            ai_config_id: ID of the AI config to use for this widget
            name: Human-readable name for the token
            allowed_origins: Optional comma-separated allowed origins
            primary_color: Optional primary hex color (e.g. "#2563eb")
            secondary_color: Optional secondary hex color (e.g. "#1e40af")

        Returns:
            Created WidgetTokenDB
        """
        # Verify the AI config exists and belongs to this user
        result = await db.execute(
            select(WhatsAppAIConfigDB).where(
                WhatsAppAIConfigDB.id == ai_config_id,
                WhatsAppAIConfigDB.user_id == user_id,
            )
        )
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError("AI config not found or does not belong to you")

        token = WidgetTokenDB(
            user_id=user_id,
            ai_config_id=ai_config_id,
            name=name,
            allowed_origins=allowed_origins,
            primary_color=primary_color,
            secondary_color=secondary_color,
        )
        db.add(token)
        await db.commit()
        await db.refresh(token)

        logger.info(f"Created widget token '{name}' for user {user_id}")
        return token

    @staticmethod
    async def list_tokens(
        db: AsyncSession,
        user_id: str,
    ) -> List[WidgetTokenDB]:
        """List all widget tokens for a user."""
        result = await db.execute(
            select(WidgetTokenDB)
            .where(WidgetTokenDB.user_id == user_id)
            .order_by(WidgetTokenDB.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_token(
        db: AsyncSession,
        token_id: UUID,
    ) -> Optional[WidgetTokenDB]:
        """Get a widget token by ID."""
        result = await db.execute(select(WidgetTokenDB).where(WidgetTokenDB.id == token_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def revoke_token(
        db: AsyncSession,
        token_id: UUID,
        user_id: str,
    ) -> bool:
        """
        Revoke (deactivate) a widget token.

        Returns True if revoked, False if not found / not owned by user.
        """
        result = await db.execute(
            select(WidgetTokenDB).where(
                WidgetTokenDB.id == token_id,
                WidgetTokenDB.user_id == user_id,
            )
        )
        token = result.scalar_one_or_none()
        if not token:
            return False

        token.is_active = False
        await db.commit()
        logger.info(f"Revoked widget token {token_id}")
        return True

    @staticmethod
    async def delete_token(
        db: AsyncSession,
        token_id: UUID,
        user_id: str,
    ) -> bool:
        """
        Permanently delete a widget token and all its conversations.

        Returns True if deleted, False if not found / not owned by user.
        """
        result = await db.execute(
            select(WidgetTokenDB).where(
                WidgetTokenDB.id == token_id,
                WidgetTokenDB.user_id == user_id,
            )
        )
        token = result.scalar_one_or_none()
        if not token:
            return False

        await db.delete(token)
        await db.commit()
        logger.info(f"Deleted widget token {token_id}")
        return True

    # ==================== Public Chat (used by widget.js) ====================

    @staticmethod
    async def validate_token(
        db: AsyncSession,
        token_value: str,
        origin: Optional[str] = None,
    ) -> Optional[WidgetTokenDB]:
        """
        Validate a widget token string.

        Checks:
        - Token exists and is active
        - If allowed_origins is set, origin must match

        Args:
            db: Database session
            token_value: The raw token string (wgt_...)
            origin: Request Origin header (for domain validation)

        Returns:
            WidgetTokenDB if valid, None otherwise
        """
        result = await db.execute(
            select(WidgetTokenDB).where(
                WidgetTokenDB.token == token_value,
                WidgetTokenDB.is_active == True,
            )
        )
        token = result.scalar_one_or_none()

        if not token:
            return None

        # Domain restriction check
        if token.allowed_origins:
            # A token restricted to specific domains must not be usable when the
            # request carries no Origin at all (curl, server-side scripts).
            if not origin:
                logger.warning(
                    f"Widget token {token.id} rejected request without Origin. "
                    f"Allowed: {token.allowed_origins}"
                )
                return None

            allowed = [o.strip().rstrip("/") for o in token.allowed_origins.split(",")]
            origin_clean = origin.rstrip("/")
            if origin_clean not in allowed:
                logger.warning(
                    f"Widget token {token.id} rejected origin '{origin_clean}'. Allowed: {allowed}"
                )
                return None

        return token

    @staticmethod
    async def chat(
        db: AsyncSession,
        token_value: str,
        visitor_id: str,
        message: str,
        origin: Optional[str] = None,
    ) -> dict:
        """
        Process a visitor message and return AI reply.

        Args:
            db: Database session
            token_value: Widget token from the script tag
            visitor_id: Browser-generated visitor UUID (from localStorage)
            message: Visitor's message text
            origin: Request origin for domain validation

        Returns:
            dict with keys: reply, visitor_id, conversation_id
        """
        start_time = time.time()

        # 1. Validate token
        widget_token = await WidgetService.validate_token(db, token_value, origin)
        if not widget_token:
            raise ValueError("Invalid or inactive widget token")

        # 2. Load AI config with knowledge bases
        result = await db.execute(
            select(WhatsAppAIConfigDB)
            .where(WhatsAppAIConfigDB.id == widget_token.ai_config_id)
            .options(selectinload(WhatsAppAIConfigDB.knowledge_bases))
        )
        config = result.scalar_one_or_none()

        if not config:
            raise ValueError("AI config not found for this widget token")

        # 3. Get or create conversation for this visitor
        conversation = await WidgetService._get_or_create_conversation(
            db, widget_token.id, visitor_id
        )

        # 4. Save user message
        user_msg = WidgetMessageDB(
            conversation_id=conversation.id,
            role="user",
            content=message,
        )
        db.add(user_msg)
        await db.commit()

        # 5. Build conversation context (memory)
        context_messages = []
        if config.use_memory:
            # Reuse existing memory builder by loading widget messages as dicts
            result = await db.execute(
                select(WidgetMessageDB)
                .where(WidgetMessageDB.conversation_id == conversation.id)
                .order_by(WidgetMessageDB.created_at.desc())
                .limit(config.memory_window)
            )
            recent_msgs = list(reversed(result.scalars().all()))
            context_messages = [{"role": m.role, "content": m.content} for m in recent_msgs]
        else:
            context_messages = [{"role": "user", "content": message}]

        # 6. Build system prompt
        system_prompt = config.system_prompt or ""
        if config.auto_enhance_prompt:
            system_prompt = PromptEnhancer.enhance_prompt(system_prompt)

        # 7. Add RAG context if enabled
        rag_context = await _get_agentic_rag_context(db, config, message)
        if rag_context:
            system_prompt += rag_context
        elif config.use_knowledge_base and config.knowledge_bases:
            system_prompt += (
                "\n\n⚠️ ADVERTENCIA: No se encontró información en la base de conocimientos. "
                "Informa al usuario que no tienes esa información. NO inventes datos."
            )

        # 8. Generate AI response
        api_key = decrypt_api_key(config.api_key_encrypted)

        async def _generate(provider: str, model: str):
            provider_instance = UnifiedAIProvider(
                provider=provider,
                model=model,
                api_key=api_key,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
            return await provider_instance.generate_response(
                messages=context_messages,
                system_prompt=system_prompt,
            )

        try:
            response = await generate_with_rate_limit_handling(
                generate_func=_generate,
                provider=config.provider,
                model=config.model,
                estimated_tokens=config.max_tokens,
                enable_queue=True,
                enable_retry=True,
                enable_fallback=True,
            )
        except RateLimitError as e:
            reply_text = get_user_friendly_error_message(e)
            response = {
                "content": reply_text,
                "provider": config.provider,
                "model": config.model,
                "tokens_used": None,
            }

        processing_time = int((time.time() - start_time) * 1000)

        # 9. Save assistant message
        assistant_msg = WidgetMessageDB(
            conversation_id=conversation.id,
            role="assistant",
            content=response["content"],
            provider=response.get("provider"),
            model=response.get("model"),
            tokens_used=response.get("tokens_used"),
            processing_time_ms=processing_time,
        )
        db.add(assistant_msg)

        # 10. Update conversation metadata
        conversation.message_count += 2
        from sqlalchemy.sql import func

        conversation.last_message_at = func.now()
        await db.commit()

        logger.info(
            f"Widget chat: visitor={visitor_id}, token={widget_token.id}, "
            f"response_ms={processing_time}"
        )

        return {
            "reply": response["content"],
            "visitor_id": visitor_id,
            "conversation_id": conversation.id,
        }

    @staticmethod
    async def get_history(
        db: AsyncSession,
        token_value: str,
        visitor_id: str,
        origin: Optional[str] = None,
    ) -> Optional[WidgetConversationDB]:
        """
        Get conversation history for a visitor.

        Args:
            db: Database session
            token_value: Widget token
            visitor_id: Visitor UUID
            origin: Request origin for domain validation

        Returns:
            WidgetConversationDB with messages loaded, or None
        """
        widget_token = await WidgetService.validate_token(db, token_value, origin)
        if not widget_token:
            return None

        result = await db.execute(
            select(WidgetConversationDB)
            .where(
                WidgetConversationDB.widget_token_id == widget_token.id,
                WidgetConversationDB.visitor_id == visitor_id,
            )
            .options(selectinload(WidgetConversationDB.messages))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _get_or_create_conversation(
        db: AsyncSession,
        widget_token_id: UUID,
        visitor_id: str,
    ) -> WidgetConversationDB:
        """Get existing conversation or create a new one."""
        result = await db.execute(
            select(WidgetConversationDB).where(
                WidgetConversationDB.widget_token_id == widget_token_id,
                WidgetConversationDB.visitor_id == visitor_id,
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = WidgetConversationDB(
                widget_token_id=widget_token_id,
                visitor_id=visitor_id,
            )
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)

        return conversation

    # ==================== Public Config (used by widget.js) ====================

    @staticmethod
    async def get_config(
        db: AsyncSession,
        token_value: str,
        origin: Optional[str] = None,
    ) -> Optional[WidgetConfigResponse]:
        """
        Return the public config for a widget token.

        Called by widget.js on init to fetch primary/secondary colors and other
        display settings from the server before rendering the widget UI.

        Args:
            db: Database session
            token_value: Widget token string (wgt_...)
            origin: Request Origin header for domain validation

        Returns:
            WidgetConfigResponse or None if token is invalid/inactive
        """
        token = await WidgetService.validate_token(db, token_value, origin)
        if not token:
            return None

        return WidgetConfigResponse(
            token=token_value,
            primary_color=token.primary_color or None,
            secondary_color=token.secondary_color or None,
            title=None,  # Reserved for future per-token title support
        )
