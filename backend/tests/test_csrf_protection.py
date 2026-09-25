"""Regression tests for origin validation responses."""

import httpx
import pytest
from fastapi import FastAPI

from app.core.csrf_protection import OriginValidationMiddleware


@pytest.fixture
async def csrf_client():
    app = FastAPI()
    app.add_middleware(
        OriginValidationMiddleware,
        allowed_origins=["https://app.example.com"],
        strict_mode=True,
    )

    @app.post("/resource")
    async def create_resource():
        return {"created": True}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_missing_origin_returns_403(csrf_client: httpx.AsyncClient) -> None:
    response = await csrf_client.post("/resource")

    assert response.status_code == 403
    assert response.json() == {"detail": "Origin header required for this operation"}


async def test_disallowed_origin_returns_403(csrf_client: httpx.AsyncClient) -> None:
    response = await csrf_client.post(
        "/resource", headers={"Origin": "https://evil.example"}
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Origin not allowed: https://evil.example"
    }


async def test_allowed_origin_reaches_endpoint(csrf_client: httpx.AsyncClient) -> None:
    response = await csrf_client.post(
        "/resource", headers={"Origin": "https://app.example.com"}
    )

    assert response.status_code == 200
    assert response.json() == {"created": True}
