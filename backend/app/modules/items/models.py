import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.config.database import Base

# --- Database Models ---

class ItemDB(Base):
    """SQLAlchemy model for items table."""

    __tablename__ = "items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


# --- Pydantic Schemas ---

class ItemCreate(BaseModel):
    """Schema for creating a new item."""

    title: str
    description: Optional[str] = None


class ItemUpdate(BaseModel):
    """Schema for updating an existing item."""

    title: Optional[str] = None
    description: Optional[str] = None


class ItemResponse(BaseModel):
    """Schema for item response."""

    id: uuid.UUID
    title: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# For backward compatibility if needed in some places
# though better to use ItemResponse or ItemDB explicitly
class Item(ItemResponse):
    """Item model representing an item in the system."""
    pass
