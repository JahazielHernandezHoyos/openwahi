from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class User(BaseModel):
    """User model representing a user in the system."""

    id: str
    email: EmailStr
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """Schema for user response."""

    id: str
    email: EmailStr
    created_at: Optional[datetime] = None
    is_admin: bool = False

    class Config:
        from_attributes = True
