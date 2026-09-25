from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.dependencies import get_current_user_id

from .models import ItemCreate, ItemResponse, ItemUpdate
from .service import create_item, delete_item, get_item, get_items, update_item

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/")
async def list_items(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
) -> dict:
    """
    Get items with pagination.
    """
    items, total = await get_items(db, user_id, limit, offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item_by_id(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
) -> ItemResponse:
    """
    Get a specific item by ID.
    """
    item = await get_item(db, item_id, user_id)
    return item


@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_new_item(
    item_data: ItemCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
) -> ItemResponse:
    """
    Create a new item.
    """
    item = await create_item(db, item_data, user_id)
    return item


@router.put("/{item_id}", response_model=ItemResponse)
async def update_existing_item(
    item_id: str,
    item_data: ItemUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
) -> ItemResponse:
    """
    Update an existing item.
    """
    item = await update_item(db, item_id, item_data, user_id)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_200_OK)
async def delete_existing_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
) -> dict:
    """
    Delete an item.
    """
    result = await delete_item(db, item_id, user_id)
    return result
