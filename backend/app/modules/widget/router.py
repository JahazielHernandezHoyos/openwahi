"""
Widget Router - API endpoints for the embeddable chat widget.

Two routers:
  - public_router: open CORS (allow_origins=["*"]), no auth required
                   Used by: widget.js running on third-party websites
  - auth_router:   standard auth (Bearer token), restricted CORS
                   Used by: the dashboard to manage tokens
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.dependencies import get_current_user_id

from .models import (
    WidgetChatRequest,
    WidgetChatResponse,
    WidgetConfigResponse,
    WidgetHistoryResponse,
    WidgetMessageResponse,
    WidgetTokenCreate,
    WidgetTokenResponse,
)
from .service import WidgetService

logger = logging.getLogger(__name__)

# ==================== Public Router (open CORS, no auth) ====================
# Mounted at /widget in main.py via a sub-app; no /widget prefix here.

public_router = APIRouter(tags=["Widget (public)"])


@public_router.post("/chat", response_model=WidgetChatResponse)
async def widget_chat(
    body: WidgetChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message from the embeddable widget and get an AI reply.

    Called by widget.js from third-party websites.
    No authentication required — access is controlled by the widget token.
    """
    origin = request.headers.get("origin")

    try:
        result = await WidgetService.chat(
            db=db,
            token_value=body.widget_token,
            visitor_id=body.visitor_id,
            message=body.message,
            origin=origin,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Widget chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    return result


@public_router.get("/config", response_model=WidgetConfigResponse)
async def widget_config(
    widget_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the public configuration for a widget token.

    Called by widget.js on page load to fetch display settings
    (primary_color, secondary_color) before rendering the widget.
    No visitor_id required — just the widget token.
    """
    origin = request.headers.get("origin")
    config = await WidgetService.get_config(
        db=db,
        token_value=widget_token,
        origin=origin,
    )

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget token not found or inactive",
        )

    return config


@public_router.get("/history", response_model=WidgetHistoryResponse)
async def widget_history(
    widget_token: str,
    visitor_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Get conversation history for a visitor.

    Called by widget.js on page load to restore the conversation.
    """
    origin = request.headers.get("origin")
    conversation = await WidgetService.get_history(
        db=db,
        token_value=widget_token,
        visitor_id=visitor_id,
        origin=origin,
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No conversation found for this visitor",
        )

    return WidgetHistoryResponse(
        conversation_id=conversation.id,
        visitor_id=conversation.visitor_id,
        message_count=conversation.message_count,
        messages=[WidgetMessageResponse.model_validate(m) for m in conversation.messages],
    )


# ==================== Auth Router (standard CORS, Bearer required) ====================
# Registered directly on the main app at prefix /widget in main.py.

auth_router = APIRouter(prefix="/widget", tags=["Widget (management)"])


@auth_router.post(
    "/tokens",
    response_model=WidgetTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new widget token",
)
async def create_widget_token(
    body: WidgetTokenCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Create a new embeddable chat widget token linked to an AI config.

    The token value (wgt_...) is what you put in the script tag:
    ```html
    <script src="..." data-widget-token="wgt_..."></script>
    ```
    """
    try:
        token = await WidgetService.create_token(
            db=db,
            user_id=user_id,
            ai_config_id=body.ai_config_id,
            name=body.name,
            allowed_origins=body.allowed_origins,
            primary_color=body.primary_color,
            secondary_color=body.secondary_color,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return token


@auth_router.get(
    "/tokens",
    response_model=List[WidgetTokenResponse],
    summary="List all widget tokens",
)
async def list_widget_tokens(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List all widget tokens for the current user."""
    return await WidgetService.list_tokens(db=db, user_id=user_id)


@auth_router.get(
    "/tokens/{token_id}",
    response_model=WidgetTokenResponse,
    summary="Get a widget token by ID",
)
async def get_widget_token(
    token_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get a specific widget token."""
    token = await WidgetService.get_token(db=db, token_id=token_id)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget token not found",
        )

    if token.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this token",
        )

    return token


@auth_router.post(
    "/tokens/{token_id}/revoke",
    summary="Revoke (deactivate) a widget token",
)
async def revoke_widget_token(
    token_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Deactivate a widget token. The embedded widget will stop working immediately.
    """
    success = await WidgetService.revoke_token(db=db, token_id=token_id, user_id=user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget token not found or does not belong to you",
        )

    return {"success": True, "message": "Token revoked successfully"}


@auth_router.delete(
    "/tokens/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a widget token",
)
async def delete_widget_token(
    token_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Permanently delete a widget token and all associated conversation history.
    """
    success = await WidgetService.delete_token(db=db, token_id=token_id, user_id=user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget token not found or does not belong to you",
        )
