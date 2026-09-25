"""
Memory management for AI conversations.
Manages conversation history and context building.
"""

import logging
from typing import Dict, List
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import WhatsAppAIMessageDB

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Gestiona el contexto/historial de conversaciones."""

    @staticmethod
    async def build_context(
        db: AsyncSession,
        conversation_id: UUID,
        window_size: int = 10,
    ) -> List[Dict[str, str]]:
        """
        Construye el contexto de conversación desde el historial.

        Args:
            db: Sesión de base de datos
            conversation_id: ID de la conversación
            window_size: Número de mensajes a incluir

        Returns:
            Lista de mensajes en formato {"role": "...", "content": "..."}
        """

        try:
            # Obtener últimos N mensajes
            result = await db.execute(
                select(WhatsAppAIMessageDB)
                .where(WhatsAppAIMessageDB.conversation_id == conversation_id)
                .order_by(desc(WhatsAppAIMessageDB.created_at))
                .limit(window_size)
            )

            messages = result.scalars().all()

            # Invertir para orden cronológico (más antiguo primero)
            messages = list(reversed(messages))

            # Convertir a formato de contexto
            context = []
            for msg in messages:
                context.append({"role": msg.role, "content": msg.content})

            logger.info(
                f"Built context with {len(context)} messages for conversation {conversation_id}"
            )

            return context

        except Exception as e:
            logger.error(
                f"Error building context for conversation {conversation_id}: {e}"
            )
            return []

    @staticmethod
    async def save_message(
        db: AsyncSession,
        conversation_id: UUID,
        role: str,
        content: str,
        provider: str = None,
        model: str = None,
        tokens_used: int = None,
        processing_time_ms: int = None,
        whatsapp_message_id: UUID = None,
    ) -> WhatsAppAIMessageDB:
        """
        Guarda un mensaje en el historial.

        Args:
            db: Sesión de base de datos
            conversation_id: ID de la conversación
            role: Rol del mensaje ('user' o 'assistant')
            content: Contenido del mensaje
            provider: Proveedor de IA usado (solo para assistant)
            model: Modelo usado (solo para assistant)
            tokens_used: Tokens usados (solo para assistant)
            processing_time_ms: Tiempo de procesamiento (solo para assistant)
            whatsapp_message_id: ID del mensaje de WhatsApp original

        Returns:
            El mensaje guardado
        """

        try:
            message = WhatsAppAIMessageDB(
                conversation_id=conversation_id,
                whatsapp_message_id=whatsapp_message_id,
                role=role,
                content=content,
                provider=provider,
                model=model,
                tokens_used=tokens_used,
                processing_time_ms=processing_time_ms,
            )

            db.add(message)
            await db.commit()
            await db.refresh(message)

            logger.info(f"Saved {role} message to conversation {conversation_id}")

            return message

        except Exception as e:
            logger.error(f"Error saving message to conversation {conversation_id}: {e}")
            await db.rollback()
            raise

    @staticmethod
    async def get_last_user_message(
        db: AsyncSession,
        conversation_id: UUID,
    ) -> str | None:
        """
        Obtiene el último mensaje del usuario.

        Args:
            db: Sesión de base de datos
            conversation_id: ID de la conversación

        Returns:
            Contenido del último mensaje del usuario o None
        """

        try:
            result = await db.execute(
                select(WhatsAppAIMessageDB)
                .where(
                    WhatsAppAIMessageDB.conversation_id == conversation_id,
                    WhatsAppAIMessageDB.role == "user",
                )
                .order_by(desc(WhatsAppAIMessageDB.created_at))
                .limit(1)
            )

            message = result.scalar_one_or_none()

            if message:
                return message.content

            return None

        except Exception as e:
            logger.error(
                f"Error getting last user message for conversation {conversation_id}: {e}"
            )
            return None

    @staticmethod
    async def get_conversation_summary(
        db: AsyncSession,
        conversation_id: UUID,
        max_messages: int = 5,
    ) -> str:
        """
        Genera un resumen textual de la conversación.
        Útil para contexto adicional o debugging.

        Args:
            db: Sesión de base de datos
            conversation_id: ID de la conversación
            max_messages: Número máximo de mensajes a incluir

        Returns:
            Resumen textual de la conversación
        """

        try:
            context = await ConversationMemory.build_context(
                db, conversation_id, max_messages
            )

            if not context:
                return "No hay mensajes en esta conversación."

            summary_lines = []
            for msg in context:
                role_label = "Usuario" if msg["role"] == "user" else "Asistente"
                content_preview = (
                    msg["content"][:100] + "..."
                    if len(msg["content"]) > 100
                    else msg["content"]
                )
                summary_lines.append(f"{role_label}: {content_preview}")

            return "\n".join(summary_lines)

        except Exception as e:
            logger.error(
                f"Error generating summary for conversation {conversation_id}: {e}"
            )
            return "Error al generar resumen."

    @staticmethod
    async def clear_conversation(
        db: AsyncSession,
        conversation_id: UUID,
    ) -> bool:
        """
        Limpia todos los mensajes de una conversación.
        Útil para resetear el contexto.

        Args:
            db: Sesión de base de datos
            conversation_id: ID de la conversación

        Returns:
            True si se limpió exitosamente
        """

        try:
            # Obtener todos los mensajes
            result = await db.execute(
                select(WhatsAppAIMessageDB).where(
                    WhatsAppAIMessageDB.conversation_id == conversation_id
                )
            )

            messages = result.scalars().all()

            # Eliminar todos
            for message in messages:
                await db.delete(message)

            await db.commit()

            logger.info(
                f"Cleared {len(messages)} messages from conversation {conversation_id}"
            )

            return True

        except Exception as e:
            logger.error(f"Error clearing conversation {conversation_id}: {e}")
            await db.rollback()
            return False
