"""
API Router para configuración de herramientas webhook.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import AnyHttpUrl, BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.dependencies import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook-tools", tags=["Webhook Tools"])


class WebhookToolConfigCreate(BaseModel):
    """Schema para crear una herramienta webhook."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    webhook_url: AnyHttpUrl = Field(..., max_length=2048)
    method: str = Field(default="POST", pattern="^(GET|POST|PUT|PATCH|DELETE)$")
    headers: dict = Field(default_factory=dict)
    input_schema: dict = Field(...)
    auth_type: str | None = Field(default=None)
    auth_value: str | None = Field(default=None)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    max_retries: int = Field(default=3, ge=0, le=10)
    is_enabled: bool = Field(default=True)


class WebhookToolConfigUpdate(BaseModel):
    """Schema para actualizar una herramienta webhook."""

    name: str | None = None
    description: str | None = None
    webhook_url: AnyHttpUrl | None = Field(default=None, max_length=2048)
    method: str | None = None
    headers: dict | None = None
    input_schema: dict | None = None
    auth_type: str | None = None
    auth_value: str | None = None
    timeout_seconds: int | None = None
    max_retries: int | None = None
    is_enabled: bool | None = None


class WebhookToolConfigResponse(BaseModel):
    """Schema de respuesta para herramienta webhook."""

    id: str
    user_id: str
    name: str
    description: str
    webhook_url: str
    method: str
    headers: dict
    input_schema: dict
    auth_type: str | None
    timeout_seconds: int
    max_retries: int
    is_enabled: bool
    created_at: str
    updated_at: str | None


@router.get("", response_model=List[WebhookToolConfigResponse])
async def get_webhook_tools(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Obtiene todas las herramientas webhook del usuario."""
    try:
        query = text("""
            SELECT
                id, user_id, name, description, webhook_url, method,
                headers, input_schema, auth_type, timeout_seconds,
                max_retries, is_enabled, created_at, updated_at
            FROM webhook_tool_configs
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """)

        result = await db.execute(query, {"user_id": user_id})
        rows = result.fetchall()

        return [
            {
                "id": str(row.id),
                "user_id": str(row.user_id),
                "name": row.name,
                "description": row.description,
                "webhook_url": row.webhook_url,
                "method": row.method,
                "headers": row.headers or {},
                "input_schema": row.input_schema,
                "auth_type": row.auth_type,
                "timeout_seconds": row.timeout_seconds,
                "max_retries": row.max_retries,
                "is_enabled": row.is_enabled,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Error fetching webhook tools: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener herramientas webhook",
        )


@router.post("", response_model=WebhookToolConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook_tool(
    config: WebhookToolConfigCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Crea una nueva herramienta webhook."""
    try:
        import json
        import uuid

        tool_id = uuid.uuid4()

        query = text("""
            INSERT INTO webhook_tool_configs
            (id, user_id, name, description, webhook_url, method, headers,
             input_schema, auth_type, auth_value_encrypted, timeout_seconds,
             max_retries, is_enabled)
            VALUES
            (:id, :user_id, :name, :description, :webhook_url, :method, :headers,
             :input_schema, :auth_type, :auth_value, :timeout_seconds,
             :max_retries, :is_enabled)
            RETURNING id, user_id, name, description, webhook_url, method, headers,
                      input_schema, auth_type, timeout_seconds, max_retries,
                      is_enabled, created_at, updated_at
        """)

        result = await db.execute(
            query,
            {
                "id": tool_id,
                "user_id": user_id,
                "name": config.name,
                "description": config.description,
                "webhook_url": str(config.webhook_url),
                "method": config.method,
                "headers": json.dumps(config.headers),
                "input_schema": json.dumps(config.input_schema),
                "auth_type": config.auth_type,
                "auth_value": config.auth_value,  # TODO: Encrypt
                "timeout_seconds": config.timeout_seconds,
                "max_retries": config.max_retries,
                "is_enabled": config.is_enabled,
            },
        )

        await db.commit()
        row = result.fetchone()

        return {
            "id": str(row.id),
            "user_id": str(row.user_id),
            "name": row.name,
            "description": row.description,
            "webhook_url": row.webhook_url,
            "method": row.method,
            "headers": row.headers or {},
            "input_schema": row.input_schema,
            "auth_type": row.auth_type,
            "timeout_seconds": row.timeout_seconds,
            "max_retries": row.max_retries,
            "is_enabled": row.is_enabled,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating webhook tool: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear herramienta webhook",
        )


@router.put("/{tool_id}", response_model=WebhookToolConfigResponse)
async def update_webhook_tool(
    tool_id: str,
    config: WebhookToolConfigUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Actualiza una herramienta webhook."""
    try:
        import json

        # Build dynamic update query
        updates = []
        params = {"tool_id": tool_id, "user_id": user_id}

        if config.name is not None:
            updates.append("name = :name")
            params["name"] = config.name

        if config.description is not None:
            updates.append("description = :description")
            params["description"] = config.description

        if config.webhook_url is not None:
            updates.append("webhook_url = :webhook_url")
            params["webhook_url"] = str(config.webhook_url)

        if config.method is not None:
            updates.append("method = :method")
            params["method"] = config.method

        if config.headers is not None:
            updates.append("headers = :headers")
            params["headers"] = json.dumps(config.headers)

        if config.input_schema is not None:
            updates.append("input_schema = :input_schema")
            params["input_schema"] = json.dumps(config.input_schema)

        if config.auth_type is not None:
            updates.append("auth_type = :auth_type")
            params["auth_type"] = config.auth_type

        if config.auth_value is not None:
            updates.append("auth_value_encrypted = :auth_value")
            params["auth_value"] = config.auth_value  # TODO: Encrypt

        if config.timeout_seconds is not None:
            updates.append("timeout_seconds = :timeout_seconds")
            params["timeout_seconds"] = config.timeout_seconds

        if config.max_retries is not None:
            updates.append("max_retries = :max_retries")
            params["max_retries"] = config.max_retries

        if config.is_enabled is not None:
            updates.append("is_enabled = :is_enabled")
            params["is_enabled"] = config.is_enabled

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay campos para actualizar",
            )

        updates.append("updated_at = NOW()")

        query = text(f"""
            UPDATE webhook_tool_configs
            SET {', '.join(updates)}
            WHERE id = :tool_id AND user_id = :user_id
            RETURNING id, user_id, name, description, webhook_url, method, headers,
                      input_schema, auth_type, timeout_seconds, max_retries,
                      is_enabled, created_at, updated_at
        """)

        result = await db.execute(query, params)
        await db.commit()

        row = result.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Herramienta webhook no encontrada",
            )

        return {
            "id": str(row.id),
            "user_id": str(row.user_id),
            "name": row.name,
            "description": row.description,
            "webhook_url": row.webhook_url,
            "method": row.method,
            "headers": row.headers or {},
            "input_schema": row.input_schema,
            "auth_type": row.auth_type,
            "timeout_seconds": row.timeout_seconds,
            "max_retries": row.max_retries,
            "is_enabled": row.is_enabled,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating webhook tool: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar herramienta webhook",
        )


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook_tool(
    tool_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Elimina una herramienta webhook."""
    try:
        query = text("""
            DELETE FROM webhook_tool_configs
            WHERE id = :tool_id AND user_id = :user_id
        """)

        result = await db.execute(query, {"tool_id": tool_id, "user_id": user_id})
        await db.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Herramienta webhook no encontrada",
            )

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting webhook tool: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar herramienta webhook",
        )
