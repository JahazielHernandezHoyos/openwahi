"""Service layer for API tokens and webhook management."""

import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import UTC, datetime, timezone
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_assistant.encryption import EncryptionService
from app.modules.developer.models import (
    ApiTokenCreatedResponse,
    ApiTokenDB,
    ApiTokenResponse,
    WebhookConfigDB,
    WebhookConfigResponse,
    WebhookTestResponse,
)

logger = logging.getLogger(__name__)


class DeveloperService:
    """Service for managing API tokens and webhooks."""

    # API Token methods

    @staticmethod
    def _generate_token() -> tuple[str, str, str]:
        """
        Generate a new API token.

        Returns:
            Tuple of (full_token, token_hash, token_prefix)
        """
        # Generate a 32-byte (256-bit) random token
        secrets.token_bytes(32)
        full_token = f"whapi_{secrets.token_urlsafe(32)}"

        # Hash the token for storage
        token_hash = hashlib.sha256(full_token.encode()).hexdigest()

        # Get prefix for identification
        token_prefix = full_token[:12]

        return full_token, token_hash, token_prefix

    @staticmethod
    async def create_token(
        db: AsyncSession, user_id: str, name: str
    ) -> ApiTokenCreatedResponse:
        """
        Create a new API token for a user.

        Args:
            db: Database session
            user_id: User ID
            name: Token name

        Returns:
            Created token response with full token (shown only once)
        """
        full_token, token_hash, token_prefix = DeveloperService._generate_token()

        db_token = ApiTokenDB(
            user_id=user_id,
            name=name,
            token_hash=token_hash,
            token_prefix=token_prefix,
        )

        db.add(db_token)
        await db.commit()
        await db.refresh(db_token)

        logger.info(f"Created API token '{name}' for user {user_id}")

        return ApiTokenCreatedResponse(
            id=str(db_token.id),
            name=db_token.name,
            token=full_token,
            token_prefix=db_token.token_prefix,
            created_at=db_token.created_at,
        )

    @staticmethod
    async def list_tokens(db: AsyncSession, user_id: str) -> list[ApiTokenResponse]:
        """
        List all API tokens for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            List of token responses (without actual tokens)
        """
        result = await db.execute(
            select(ApiTokenDB)
            .where(ApiTokenDB.user_id == user_id)
            .order_by(ApiTokenDB.created_at.desc())
        )
        tokens = result.scalars().all()

        return [
            ApiTokenResponse(
                id=str(token.id),
                name=token.name,
                token_prefix=token.token_prefix,
                last_used_at=token.last_used_at,
                is_active=token.is_active,
                created_at=token.created_at,
            )
            for token in tokens
        ]

    @staticmethod
    async def revoke_token(db: AsyncSession, user_id: str, token_id: str) -> bool:
        """
        Revoke (delete) an API token.

        Args:
            db: Database session
            user_id: User ID
            token_id: Token ID

        Returns:
            True if token was deleted, False if not found
        """
        result = await db.execute(
            select(ApiTokenDB).where(
                ApiTokenDB.id == UUID(token_id),
                ApiTokenDB.user_id == user_id,
            )
        )
        token = result.scalar_one_or_none()

        if not token:
            return False

        await db.delete(token)
        await db.commit()

        logger.info(f"Revoked API token '{token.name}' for user {user_id}")
        return True

    @staticmethod
    async def validate_token(db: AsyncSession, token: str) -> Optional[str]:
        """
        Validate an API token and return the user_id if valid.

        Args:
            db: Database session
            token: Full API token

        Returns:
            User ID if token is valid, None otherwise
        """
        # Hash the provided token
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Find token in database
        result = await db.execute(
            select(ApiTokenDB).where(
                ApiTokenDB.token_hash == token_hash,
                ApiTokenDB.is_active == True,  # noqa: E712
            )
        )
        db_token = result.scalar_one_or_none()

        if not db_token:
            return None

        # Update last_used_at
        await db.execute(
            update(ApiTokenDB)
            .where(ApiTokenDB.id == db_token.id)
            .values(last_used_at=datetime.now(UTC))
        )
        await db.commit()

        return str(db_token.user_id)

    # Webhook methods

    @staticmethod
    async def get_webhook_config(
        db: AsyncSession, user_id: str
    ) -> Optional[WebhookConfigResponse]:
        """
        Get webhook configuration for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Webhook config response or None
        """
        result = await db.execute(
            select(WebhookConfigDB).where(WebhookConfigDB.user_id == user_id)
        )
        config = result.scalar_one_or_none()

        if not config:
            return None

        return WebhookConfigResponse(
            id=str(config.id),
            url=config.url,
            has_secret=bool(config.secret),
            is_active=config.is_active,
            last_triggered_at=config.last_triggered_at,
            failure_count=config.failure_count,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )

    @staticmethod
    async def upsert_webhook_config(
        db: AsyncSession,
        user_id: str,
        url: str,
        secret: Optional[str] = None,
        is_active: bool = True,
    ) -> WebhookConfigResponse:
        """
        Create or update webhook configuration for a user.

        Args:
            db: Database session
            user_id: User ID
            url: Webhook URL
            secret: Optional secret for HMAC signing
            is_active: Whether webhook is active

        Returns:
            Webhook config response
        """
        result = await db.execute(
            select(WebhookConfigDB).where(WebhookConfigDB.user_id == user_id)
        )
        config = result.scalar_one_or_none()

        # Encrypt secret if provided
        encrypted_secret = None
        if secret:
            encrypted_secret = EncryptionService.encrypt(secret)

        if config:
            # Update existing
            config.url = url
            if secret is not None:
                config.secret = encrypted_secret
            config.is_active = is_active
            config.updated_at = datetime.now(UTC)
            config.failure_count = 0  # Reset failure count on update
        else:
            # Create new
            config = WebhookConfigDB(
                user_id=user_id,
                url=url,
                secret=encrypted_secret,
                is_active=is_active,
            )
            db.add(config)

        await db.commit()
        await db.refresh(config)

        logger.info(f"{'Updated' if config.updated_at else 'Created'} webhook config for user {user_id}")

        return WebhookConfigResponse(
            id=str(config.id),
            url=config.url,
            has_secret=bool(config.secret),
            is_active=config.is_active,
            last_triggered_at=config.last_triggered_at,
            failure_count=config.failure_count,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )

    @staticmethod
    async def delete_webhook_config(db: AsyncSession, user_id: str) -> bool:
        """
        Delete webhook configuration for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            True if deleted, False if not found
        """
        result = await db.execute(
            select(WebhookConfigDB).where(WebhookConfigDB.user_id == user_id)
        )
        config = result.scalar_one_or_none()

        if not config:
            return False

        await db.delete(config)
        await db.commit()

        logger.info(f"Deleted webhook config for user {user_id}")
        return True

    @staticmethod
    async def test_webhook(db: AsyncSession, user_id: str) -> WebhookTestResponse:
        """
        Test webhook configuration by sending a test payload.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Test result response
        """
        result = await db.execute(
            select(WebhookConfigDB).where(WebhookConfigDB.user_id == user_id)
        )
        config = result.scalar_one_or_none()

        if not config:
            return WebhookTestResponse(
                success=False,
                message="No webhook configured",
            )

        # Prepare test payload
        test_payload = {
            "event": "test",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "message": "This is a test webhook from your WhatsApp API",
                "test_id": secrets.token_hex(8),
            },
        }

        # Serialize once: the signature must cover the exact bytes sent.
        payload_bytes = json.dumps(test_payload).encode()
        headers = {"Content-Type": "application/json"}

        # Add HMAC signature if secret is configured
        if config.secret:
            try:
                decrypted_secret = EncryptionService.decrypt(config.secret)
                signature = hmac.new(
                    decrypted_secret.encode(), payload_bytes, hashlib.sha256
                ).hexdigest()
                headers["X-Webhook-Signature"] = f"sha256={signature}"
            except Exception as e:
                logger.error(f"Failed to create webhook signature: {e}")

        # Send test request
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    config.url,
                    content=payload_bytes,
                    headers=headers,
                )

            response_time_ms = int((time.time() - start_time) * 1000)

            if response.status_code >= 200 and response.status_code < 300:
                return WebhookTestResponse(
                    success=True,
                    status_code=response.status_code,
                    message="Webhook test successful",
                    response_time_ms=response_time_ms,
                )
            else:
                return WebhookTestResponse(
                    success=False,
                    status_code=response.status_code,
                    message=f"Webhook returned status {response.status_code}",
                    response_time_ms=response_time_ms,
                )

        except httpx.TimeoutException:
            return WebhookTestResponse(
                success=False,
                message="Webhook request timed out (10s)",
            )
        except httpx.RequestError as e:
            return WebhookTestResponse(
                success=False,
                message=f"Failed to connect to webhook: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Webhook test error: {e}")
            return WebhookTestResponse(
                success=False,
                message=f"Unexpected error: {str(e)}",
            )

    @staticmethod
    async def trigger_webhook(
        db: AsyncSession,
        user_id: str,
        event: str,
        data: dict,
    ) -> bool:
        """
        Trigger webhook for a user with the given event and data.
        This is called when incoming WhatsApp messages are received.

        Args:
            db: Database session
            user_id: User ID
            event: Event type (e.g., "message.received")
            data: Event data

        Returns:
            True if webhook was triggered successfully
        """
        result = await db.execute(
            select(WebhookConfigDB).where(
                WebhookConfigDB.user_id == user_id,
                WebhookConfigDB.is_active == True,  # noqa: E712
            )
        )
        config = result.scalar_one_or_none()

        if not config:
            return False

        # Prepare payload
        payload = {
            "event": event,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": data,
        }

        # Serialize once: the signature must cover the exact bytes sent.
        payload_bytes = json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"}

        # Add HMAC signature if secret is configured
        if config.secret:
            try:
                decrypted_secret = EncryptionService.decrypt(config.secret)
                signature = hmac.new(
                    decrypted_secret.encode(), payload_bytes, hashlib.sha256
                ).hexdigest()
                headers["X-Webhook-Signature"] = f"sha256={signature}"
            except Exception as e:
                logger.error(f"Failed to create webhook signature: {e}")

        # Send webhook
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    config.url,
                    content=payload_bytes,
                    headers=headers,
                )

            # Update last_triggered_at
            config.last_triggered_at = datetime.now(UTC)

            if response.status_code >= 200 and response.status_code < 300:
                config.failure_count = 0
                await db.commit()
                logger.info(f"Webhook triggered successfully for user {user_id}")
                return True
            else:
                config.failure_count += 1
                await db.commit()
                logger.warning(
                    f"Webhook returned status {response.status_code} for user {user_id}"
                )
                return False

        except Exception as e:
            config.failure_count += 1
            config.last_triggered_at = datetime.now(UTC)
            await db.commit()
            logger.error(f"Webhook trigger error for user {user_id}: {e}")
            return False
