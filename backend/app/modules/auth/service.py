from typing import Optional

from fastapi import HTTPException, status
from firebase_admin import auth as firebase_auth

from .models import UserResponse


async def get_user_by_id(user_id: str) -> Optional[UserResponse]:
    """
    Get user information from Firebase Auth by user ID (UID).
    """
    try:
        user_record = firebase_auth.get_user(user_id)

        return UserResponse(
            id=user_record.uid,
            email=user_record.email or "",
            created_at=None,
        )

    except firebase_auth.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user: {str(e)}",
        )
