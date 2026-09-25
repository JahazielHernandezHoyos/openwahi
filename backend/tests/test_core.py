"""Tests for core endpoints: root, health, docs."""


async def test_root(client):
    """GET / returns API metadata."""
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "1.0.0"
    assert "docs" in data


async def test_health(client):
    """GET /health returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "environment" in data


async def test_openapi_schema(client):
    """OpenAPI schema is accessible."""
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "paths" in schema


async def test_docs_page(client):
    """Swagger UI docs page is accessible."""
    resp = await client.get("/docs")
    assert resp.status_code == 200


async def test_developer_docs(client):
    """Developer API docs page is accessible."""
    resp = await client.get("/api-docs")
    assert resp.status_code == 200


async def test_developer_openapi_json(client):
    """Developer filtered OpenAPI JSON is accessible."""
    resp = await client.get("/api-docs/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "paths" in data
    # Should only contain /whatsapp and /developer paths
    for path in data["paths"]:
        assert path.startswith("/whatsapp") or path.startswith("/developer"), (
            f"Unexpected path in developer docs: {path}"
        )
