from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ItemCreate, ItemDB, ItemResponse, ItemUpdate


async def get_items(
    db: AsyncSession, user_id: Optional[str] = None, limit: int = 50, offset: int = 0
) -> Tuple[List[ItemResponse], int]:
    """
    Get items with pagination.

    Returns:
        Tuple of (items list, total count)
    """
    try:
        # Query with pagination
        query = select(ItemDB).order_by(ItemDB.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        items = result.scalars().all()

        # Get total count
        count_result = await db.execute(select(func.count(ItemDB.id)))
        total = count_result.scalar_one()

        return [ItemResponse.model_validate(item) for item in items], total

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching items: {str(e)}",
        )


async def get_item(db: AsyncSession, item_id: str, user_id: Optional[str] = None) -> ItemResponse:
    """
    Get a specific item by ID.
    """
    try:
        result = await db.execute(select(ItemDB).where(ItemDB.id == item_id))
        item = result.scalar_one_or_none()

        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

        return ItemResponse.model_validate(item)

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching item: {str(e)}",
        )


async def create_item(
    db: AsyncSession, item_data: ItemCreate, user_id: Optional[str] = None
) -> ItemResponse:
    """
    Create a new item.
    """
    try:
        new_item = ItemDB(title=item_data.title, description=item_data.description)
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)

        return ItemResponse.model_validate(new_item)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating item: {str(e)}",
        )


async def update_item(
    db: AsyncSession, item_id: str, item_data: ItemUpdate, user_id: Optional[str] = None
) -> ItemResponse:
    """
    Update an existing item.
    """
    try:
        result = await db.execute(select(ItemDB).where(ItemDB.id == item_id))
        item = result.scalar_one_or_none()

        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

        # Update fields
        update_data = item_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(item, key, value)

        await db.commit()
        await db.refresh(item)

        return ItemResponse.model_validate(item)

    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating item: {str(e)}",
        )


async def delete_item(db: AsyncSession, item_id: str, user_id: Optional[str] = None) -> dict:
    """
    Delete an item using a single database roundtrip.
    """
    try:
        # Direct delete query
        stmt = delete(ItemDB).where(ItemDB.id == item_id)
        result = await db.execute(stmt)

        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

        await db.commit()
        return {"message": "Item deleted successfully"}

    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting item: {str(e)}",
        )
