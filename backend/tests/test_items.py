"""Tests for items CRUD - full lifecycle against real PostgreSQL.

Note: Tests share a database session that rolls back after each test,
so items created in one test don't affect others.
"""

import uuid


async def test_create_item(client):
    """POST /items/ creates a new item."""
    resp = await client.post(
        "/items/",
        json={
            "title": "Test Item",
            "description": "A test item description",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Item"
    assert data["description"] == "A test item description"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


async def test_create_item_minimal(client):
    """POST /items/ with only required fields."""
    resp = await client.post("/items/", json={"title": "Minimal Item"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Minimal Item"


async def test_create_item_missing_title(client):
    """POST /items/ without title returns 422."""
    resp = await client.post("/items/", json={"description": "no title"})
    assert resp.status_code == 422


async def test_list_items(client):
    """GET /items/ returns items list structure."""
    resp = await client.get("/items/")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


async def test_list_items_with_data(client):
    """GET /items/ returns created items."""
    # Create two items
    await client.post("/items/", json={"title": "Item A"})
    await client.post("/items/", json={"title": "Item B"})

    resp = await client.get("/items/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    titles = [item["title"] for item in data["items"]]
    assert "Item A" in titles
    assert "Item B" in titles


async def test_list_items_pagination(client):
    """GET /items/ respects limit and offset."""
    # Create 3 items
    for i in range(3):
        await client.post("/items/", json={"title": f"Page Item {i}"})

    resp = await client.get("/items/?limit=2&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) <= 2
    assert data["limit"] == 2
    assert data["offset"] == 0


async def test_get_item_by_id(client):
    """GET /items/{id} returns specific item."""
    create_resp = await client.post("/items/", json={"title": "Find Me"})
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]

    resp = await client.get(f"/items/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Find Me"
    assert resp.json()["id"] == item_id


async def test_get_item_not_found(client):
    """GET /items/{id} returns 404 for non-existent item."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/items/{fake_id}")
    assert resp.status_code == 404


async def test_update_item(client):
    """PUT /items/{id} updates item fields."""
    create_resp = await client.post(
        "/items/",
        json={
            "title": "Original",
            "description": "Original desc",
        },
    )
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]

    resp = await client.put(
        f"/items/{item_id}",
        json={
            "title": "Updated",
            "description": "Updated desc",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Updated"
    assert data["description"] == "Updated desc"


async def test_update_item_partial(client):
    """PUT /items/{id} with partial data only updates provided fields."""
    create_resp = await client.post(
        "/items/",
        json={
            "title": "Keep This",
            "description": "Change This",
        },
    )
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]

    resp = await client.put(f"/items/{item_id}", json={"description": "Changed"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Keep This"
    assert data["description"] == "Changed"


async def test_update_item_not_found(client):
    """PUT /items/{id} returns 404 for non-existent item."""
    fake_id = str(uuid.uuid4())
    resp = await client.put(f"/items/{fake_id}", json={"title": "Nope"})
    assert resp.status_code == 404


async def test_delete_item(client):
    """DELETE /items/{id} removes the item."""
    create_resp = await client.post("/items/", json={"title": "Delete Me"})
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]

    resp = await client.delete(f"/items/{item_id}")
    assert resp.status_code == 200
    assert "deleted" in resp.json()["message"].lower()

    # Verify it's gone
    get_resp = await client.get(f"/items/{item_id}")
    assert get_resp.status_code == 404


async def test_delete_item_not_found(client):
    """DELETE /items/{id} returns 404 for non-existent item."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/items/{fake_id}")
    assert resp.status_code == 404


async def test_full_crud_lifecycle(client):
    """Full Create -> Read -> Update -> Delete lifecycle."""
    # Create
    create_resp = await client.post(
        "/items/",
        json={
            "title": "Lifecycle Item",
            "description": "Testing full lifecycle",
        },
    )
    assert create_resp.status_code == 201
    item = create_resp.json()
    item_id = item["id"]

    # Read
    read_resp = await client.get(f"/items/{item_id}")
    assert read_resp.status_code == 200
    assert read_resp.json()["title"] == "Lifecycle Item"

    # Update
    update_resp = await client.put(
        f"/items/{item_id}", json={"title": "Updated Lifecycle"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Updated Lifecycle"

    # Verify update persisted
    read2_resp = await client.get(f"/items/{item_id}")
    assert read2_resp.json()["title"] == "Updated Lifecycle"

    # Delete
    delete_resp = await client.delete(f"/items/{item_id}")
    assert delete_resp.status_code == 200

    # Verify deleted
    read3_resp = await client.get(f"/items/{item_id}")
    assert read3_resp.status_code == 404


async def test_items_unauthenticated(unauthed_client):
    """Items endpoints require authentication."""
    resp = await unauthed_client.get("/items/")
    assert resp.status_code in (401, 403)

    resp = await unauthed_client.post("/items/", json={"title": "Nope"})
    assert resp.status_code in (401, 403)
