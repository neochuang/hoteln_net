import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_api_key(client: AsyncClient, admin_headers):
    res = await client.post("/api/api-keys", headers=admin_headers, json={"name": "3F 清潔平板"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "3F 清潔平板"
    assert data["is_active"] is True
    assert "key" in data
    assert data["key"].startswith("neo_")
    assert data["key_prefix"] == data["key"][:8]


@pytest.mark.asyncio
async def test_list_api_keys(client: AsyncClient, admin_headers):
    await client.post("/api/api-keys", headers=admin_headers, json={"name": "Device A"})
    await client.post("/api/api-keys", headers=admin_headers, json={"name": "Device B"})

    res = await client.get("/api/api-keys", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    assert "key" not in data[0]


@pytest.mark.asyncio
async def test_update_api_key(client: AsyncClient, admin_headers):
    create_res = await client.post("/api/api-keys", headers=admin_headers, json={"name": "Old Name"})
    key_id = create_res.json()["id"]

    res = await client.patch(f"/api/api-keys/{key_id}", headers=admin_headers, json={
        "name": "New Name",
        "is_active": False,
    })
    assert res.status_code == 200
    assert res.json()["name"] == "New Name"
    assert res.json()["is_active"] is False


@pytest.mark.asyncio
async def test_delete_api_key(client: AsyncClient, admin_headers):
    create_res = await client.post("/api/api-keys", headers=admin_headers, json={"name": "To Delete"})
    key_id = create_res.json()["id"]

    res = await client.delete(f"/api/api-keys/{key_id}", headers=admin_headers)
    assert res.status_code == 204

    list_res = await client.get("/api/api-keys", headers=admin_headers)
    assert len(list_res.json()) == 0


@pytest.mark.asyncio
async def test_staff_cannot_manage_api_keys(client: AsyncClient, staff_headers):
    res = await client.post("/api/api-keys", headers=staff_headers, json={"name": "Attempt"})
    assert res.status_code == 403
