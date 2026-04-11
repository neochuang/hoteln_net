import pytest
from httpx import AsyncClient


async def create_guest(client: AsyncClient, headers: dict) -> str:
    res = await client.post("/api/guests", headers=headers, json={
        "first_name": "小明",
        "last_name": "李",
        "id_type": "national_id",
        "id_number": "B123456789",
        "phone": "0911111111",
        "nationality": "台灣",
    })
    return res.json()["id"]


async def create_room_type(client: AsyncClient, headers: dict) -> str:
    res = await client.post("/api/rooms/types", headers=headers, json={
        "name": "標準房",
        "capacity": 2,
        "base_price": 2000,
    })
    return res.json()["id"]


@pytest.mark.asyncio
async def test_reservation_lifecycle(client: AsyncClient, admin_headers):
    guest_id = await create_guest(client, admin_headers)
    type_id = await create_room_type(client, admin_headers)

    # Create reservation
    res = await client.post("/api/reservations", headers=admin_headers, json={
        "guest_id": guest_id,
        "room_type_id": type_id,
        "check_in_date": "2026-04-10",
        "check_out_date": "2026-04-12",
        "num_guests": 2,
        "includes_breakfast": True,
        "breakfast_guests": 2,
        "total_price": 4000,
    })
    assert res.status_code == 201
    reservation_id = res.json()["id"]
    assert res.json()["status"] == "confirmed"

    # List
    res = await client.get("/api/reservations", headers=admin_headers)
    assert len(res.json()) == 1

    # Update
    res = await client.patch(f"/api/reservations/{reservation_id}", headers=admin_headers, json={
        "total_price": 4500,
    })
    assert res.status_code == 200
    assert res.json()["total_price"] == 4500

    # Cancel
    res = await client.post(f"/api/reservations/{reservation_id}/cancel", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cannot_cancel_non_confirmed(client: AsyncClient, admin_headers):
    guest_id = await create_guest(client, admin_headers)
    type_id = await create_room_type(client, admin_headers)

    res = await client.post("/api/reservations", headers=admin_headers, json={
        "guest_id": guest_id,
        "room_type_id": type_id,
        "check_in_date": "2026-05-01",
        "check_out_date": "2026-05-03",
        "num_guests": 1,
        "total_price": 2000,
    })
    rid = res.json()["id"]

    # Cancel first
    await client.post(f"/api/reservations/{rid}/cancel", headers=admin_headers)

    # Try cancel again
    res = await client.post(f"/api/reservations/{rid}/cancel", headers=admin_headers)
    assert res.status_code == 400
