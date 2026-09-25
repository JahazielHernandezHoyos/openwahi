from typing import Any, Dict

from fastapi import APIRouter, Depends, Request

from app.core.dependencies import get_current_user, get_current_user_id, is_admin_claims
from app.core.rate_limit import RateLimits, limiter

from .models import UserResponse
from .service import get_user_by_id

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
@limiter.limit(RateLimits.AUTH)
async def get_current_user_info(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    user_id: str = Depends(get_current_user_id),
) -> UserResponse:
    """
    Get current authenticated user information, including admin status.
    """
    user = await get_user_by_id(user_id)
    return user.model_copy(update={"is_admin": is_admin_claims(current_user)})


@router.get("/verify")
@limiter.limit(RateLimits.AUTH)
async def verify_token(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Verify JWT token validity.
    """
    return {
        "message": "Token is valid",
        "user_id": current_user.get("sub")
    }
