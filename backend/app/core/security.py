import logging
from typing import Any, Dict

from fastapi import HTTPException, status
from firebase_admin import auth as firebase_auth

logger = logging.getLogger(__name__)


async def decode_firebase_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a Firebase ID Token using the Firebase Admin SDK.

    Firebase Admin SDK automatically verifies:
    - Token signature (using Google's public keys)
    - Token expiration
    - Token audience (must match Firebase project ID)
    - Token issuer

    Args:
        token: Firebase ID Token string from the frontend

    Returns:
        Decoded token payload containing user information.
        Key fields: uid, email, name, picture, email_verified

    Raises:
        HTTPException 401: If token is invalid, expired, or malformed
    """
    try:
        decoded = firebase_auth.verify_id_token(token)
        logger.debug(f"Firebase token verified. UID: {decoded.get('uid')}")
        return decoded
    except firebase_auth.ExpiredIdTokenError:
        logger.warning("Firebase token is expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except firebase_auth.RevokedIdTokenError:
        logger.warning("Firebase token has been revoked")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except firebase_auth.InvalidIdTokenError as e:
        logger.warning(f"Invalid Firebase token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error verifying Firebase token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_user_id_from_token(token: str) -> str:
    """
    Extract user ID (uid) from Firebase ID Token.

    Args:
        token: Firebase ID Token string

    Returns:
        Firebase UID string

    Raises:
        HTTPException: If token is invalid or UID not found
    """
    payload = await decode_firebase_token(token)
    user_id = payload.get("uid")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id
