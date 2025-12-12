import json
import pytest
from httpx import AsyncClient
from fastapi import status

from app.main import app


@pytest.mark.asyncio
async def test_create_job_validation():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/jobs", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
