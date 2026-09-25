"""
Cargador dinámico de herramientas desde base de datos.
"""

import logging
from typing import List
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .webhook_tools import DynamicWebhookTool, WebhookToolConfig

logger = logging.getLogger(__name__)


class DynamicToolLoader:
    """Carga herramientas dinámicamente desde la base de datos."""

    @staticmethod
    async def count_enabled_tools(db: AsyncSession, user_id) -> int:
        """Count enabled tools for a user without building them.

        Used to decide provider capabilities before the LLM is instantiated.
        """
        try:
            query = text("""
                SELECT COUNT(*)
                FROM webhook_tool_configs
                WHERE user_id = :user_id AND is_enabled = true
            """)
            result = await db.execute(query, {"user_id": user_id})
            return int(result.scalar() or 0)
        except Exception as e:
            logger.error(f"Error counting tools: {e}", exc_info=True)
            return 0

    @staticmethod
    async def load_tools_for_user(db: AsyncSession, user_id: UUID) -> List:
        """
        Carga todas las herramientas habilitadas para un usuario.

        Returns:
            Lista de herramientas LangChain listas para usar
        """
        try:
            # Consultar herramientas de la DB usando raw SQL para evitar problemas de dependencia
            query = text("""
                SELECT
                    id, user_id, name, description, webhook_url, method,
                    headers, input_schema, auth_type, auth_value_encrypted,
                    timeout_seconds, max_retries, is_enabled
                FROM webhook_tool_configs
                WHERE user_id = :user_id AND is_enabled = true
            """)

            result = await db.execute(query, {"user_id": user_id})
            rows = result.fetchall()

            # Convertir cada config a una herramienta LangChain
            tools = []
            for row in rows:
                # Convertir a Pydantic
                config = WebhookToolConfig(
                    name=row.name,
                    description=row.description,
                    webhook_url=row.webhook_url,
                    method=row.method,
                    headers=row.headers or {},
                    input_schema=row.input_schema,
                    auth_type=row.auth_type,
                    auth_value=row.auth_value_encrypted,  # TODO: Decrypt
                    timeout_seconds=row.timeout_seconds,
                    max_retries=row.max_retries,
                    is_enabled=row.is_enabled,
                )

                # Crear herramienta
                tool = DynamicWebhookTool.create_tool(config)
                tools.append(tool)

                logger.info(f"✅ Loaded tool: {config.name}")

            return tools

        except Exception as e:
            logger.error(f"Error loading tools: {e}", exc_info=True)
            return []
