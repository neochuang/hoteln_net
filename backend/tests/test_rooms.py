import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_room_type_crud(client: AsyncClient, admin_headers):
    # Create room type
    res = await client.post("/api/rooms/types", headers=admin_headers, json={
        "name": "單人房",
        "capacity": 1,
        "base_price": 1500,
    })
    assert res.status_code == 201
    type_id = res.json()["id"]

    # List room types
    res = await client.get("/api/rooms/types", headers=admin_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1

    return type_id


@pytest.mark.asyncio
async def test_room_crud(client: AsyncClient, admin_headers):
    # Create room type first
    type_res = await client.post("/api/rooms/types", headers=admin_headers, json={
        "name": "雙人房",
        "capacity": 2,
        "base_price": 2500,
    })
    type_id = type_res.json()["id"]

    # Create room
    res = await client.post("/api/rooms", headers=admin_headers, json={
        "room_number": "301",
        "floor": 3,
        "room_type_id": type_id,
    })
    assert res.status_code == 201
    room_id = res.json()["id"]
    assert res.json()["status"] == "available"

    # List rooms
    res = await client.get("/api/rooms", headers=admin_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1

    # Update room status
    res = await client.patch(f"/api/rooms/{room_id}", headers=admin_headers, json={"status": "maintenance"})
    assert res.status_code == 200
    assert res.json()["status"] == "maintenance"
