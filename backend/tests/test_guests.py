import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_guests(client: AsyncClient, admin_headers):
    # Create
    res = await client.post("/api/guests", headers=admin_headers, json={
        "first_name": "大明",
        "last_name": "王",
        "id_type": "national_id",
        "id_number": "A123456789",
        "phone": "0912345678",
        "nationality": "台灣",
    })
    assert res.status_code == 201
    guest_id = res.json()["id"]

    # List
    res = await client.get("/api/guests", headers=admin_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1

    # Get by ID
    res = await client.get(f"/api/guests/{guest_id}", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["last_name"] == "王"

    # Search
    res = await client.get("/api/guests", headers=admin_headers, params={"q": "王"})
    assert len(res.json()) == 1

    # Update
    res = await client.patch(f"/api/guests/{guest_id}", headers=admin_headers, json={"phone": "0987654321"})
    assert res.status_code == 200
    assert res.json()["phone"] == "0987654321"


@pytest.mark.asyncio
async def test_guests_no_auth(client: AsyncClient):
    res = await client.get("/api/guests")
    assert res.status_code in (401, 403)
