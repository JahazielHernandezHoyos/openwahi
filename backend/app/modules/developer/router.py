"""API routes for developer portal - API tokens and webhook management."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.dependencies import get_current_user_id
from app.modules.developer.models import (
    ApiTokenCreate,
    ApiTokenCreatedResponse,
    ApiTokenListResponse,
    ApiTokenResponse,
    WebhookConfigCreate,
    WebhookConfigResponse,
    WebhookTestResponse,
)
from app.modules.developer.service import DeveloperService

router = APIRouter(prefix="/developer", tags=["developer"])


# API Token endpoints


@router.post(
    "/tokens",
    response_model=ApiTokenCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API token",
    description="Create a new API token. The full token is only shown once in the response.",
)
async def create_token(
    token_data: ApiTokenCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiTokenCreatedResponse:
    """Create a new API token for the current user."""
    return await DeveloperService.create_token(db, user_id, token_data.name)


@router.get(
    "/tokens",
    response_model=ApiTokenListResponse,
    summary="List API tokens",
    description="List all API tokens for the current user.",
)
async def list_tokens(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiTokenListResponse:
    """List all API tokens for the current user."""
    tokens = await DeveloperService.list_tokens(db, user_id)
    return ApiTokenListResponse(tokens=tokens, total=len(tokens))


@router.delete(
    "/tokens/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke API token",
    description="Revoke (delete) an API token.",
)
async def revoke_token(
    token_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke an API token."""
    deleted = await DeveloperService.revoke_token(db, user_id, token_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found",
        )


# Webhook endpoints


@router.get(
    "/webhook",
    response_model=WebhookConfigResponse,
    summary="Get webhook configuration",
    description="Get the current webhook configuration for the user.",
)
async def get_webhook_config(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> WebhookConfigResponse:
    """Get webhook configuration."""
    config = await DeveloperService.get_webhook_config(db, user_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No webhook configured",
        )
    return config


@router.put(
    "/webhook",
    response_model=WebhookConfigResponse,
    summary="Create or update webhook",
    description="Create or update the webhook configuration.",
)
async def upsert_webhook_config(
    config_data: WebhookConfigCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> WebhookConfigResponse:
    """Create or update webhook configuration."""
    return await DeveloperService.upsert_webhook_config(
        db,
        user_id,
        url=config_data.url,
        secret=config_data.secret,
        is_active=config_data.is_active,
    )


@router.delete(
    "/webhook",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete webhook",
    description="Delete the webhook configuration.",
)
async def delete_webhook_config(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete webhook configuration."""
    deleted = await DeveloperService.delete_webhook_config(db, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No webhook configured",
        )


@router.post(
    "/webhook/test",
    response_model=WebhookTestResponse,
    summary="Test webhook",
    description="Send a test payload to the configured webhook.",
)
async def test_webhook(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> WebhookTestResponse:
    """Test webhook by sending a test payload."""
    return await DeveloperService.test_webhook(db, user_id)
