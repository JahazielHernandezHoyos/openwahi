from typing import Any, Dict, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.config.settings import settings
from app.core.security import decode_firebase_token

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    FastAPI dependency to get current authenticated user from Firebase ID Token.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        Dictionary containing user information from Firebase token payload
        Key fields: uid, email, name, picture, email_verified

    Raises:
        HTTPException: If token is invalid or missing
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = await decode_firebase_token(token)

    return payload


async def get_current_user_id(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> str:
    """
    FastAPI dependency to get current user ID (Firebase UID).

    Args:
        current_user: Current user payload from get_current_user

    Returns:
        Firebase UID string

    Raises:
        HTTPException: If user ID not found in token
    """
    user_id = current_user.get("uid")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


async def get_current_user_id_flexible(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    x_api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> str:
    """
    FastAPI dependency that accepts both Firebase ID Token and API key authentication.

    This allows endpoints to be accessed via:
    1. Authorization: Bearer <firebase_id_token> (session-based auth)
    2. X-API-Key: <api_token> (API token auth)

    Args:
        credentials: Optional HTTP Bearer token credentials
        x_api_key: Optional API key from header
        db: Database session

    Returns:
        User ID string (Firebase UID)

    Raises:
        HTTPException: If neither auth method provides valid credentials
    """
    # Try Firebase ID Token first
    if credentials and credentials.credentials:
        try:
            payload = await decode_firebase_token(credentials.credentials)
            user_id = payload.get("uid")
            if user_id:
                return user_id
        except Exception:
            pass  # Fall through to try API key

    # Try API key
    if x_api_key:
        # Import here to avoid circular imports
        from app.modules.developer.service import DeveloperService

        try:
            user_id = await DeveloperService.validate_token(db, x_api_key)
            if user_id:
                return user_id
        except Exception:
            # Rollback on database errors to prevent transaction pollution
            await db.rollback()
            pass  # Fall through to authentication failure

    # Neither auth method worked
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Provide either Authorization Bearer token or X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def is_admin_claims(claims: Dict[str, Any]) -> bool:
    """
    Return True when decoded Firebase claims belong to a configured admin.

    Requires a verified email (``email_verified`` is True) whose lowercase value
    is listed in ADMIN_EMAILS. An empty ADMIN_EMAILS disables admin access.
    """
    if claims.get("email_verified") is not True:
        return False
    email = str(claims.get("email") or "").strip().lower()
    return bool(email) and email in settings.admin_emails_set


async def get_admin_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
) -> Dict[str, Any]:
    """
    FastAPI dependency that restricts access to verified emails in ADMIN_EMAILS.
    Returns 404 (not 403/401) to avoid leaking that an admin panel exists.
    Uses security_optional so FastAPI never auto-raises 401 before this guard runs.

    Raises:
        HTTPException 404: always, unless a valid admin token is provided.
    """
    _not_found = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if not settings.admin_emails_set:
        raise _not_found

    if not credentials or not credentials.credentials:
        raise _not_found

    try:
        payload = await decode_firebase_token(credentials.credentials)
    except Exception:
        raise _not_found

    if not is_admin_claims(payload):
        raise _not_found

    return payload
