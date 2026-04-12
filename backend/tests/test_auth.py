import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, admin_user):
    res = await client.post("/api/auth/login", json={"username": "testadmin", "password": "admin123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_user):
    res = await client.post("/api/auth/login", json={"username": "testadmin", "password": "wrong"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_me(client: AsyncClient, admin_headers):
    res = await client.get("/api/auth/me", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["username"] == "testadmin"


@pytest.mark.asyncio
async def test_me_no_token(client: AsyncClient):
    res = await client.get("/api/auth/me")
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, admin_user):
    login_res = await client.post("/api/auth/login", json={"username": "testadmin", "password": "admin123"})
    refresh_token = login_res.json()["refresh_token"]
    res = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 200
    assert "access_token" in res.json()
