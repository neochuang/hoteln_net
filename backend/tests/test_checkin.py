import pytest
from httpx import AsyncClient


async def setup_checkin_data(client: AsyncClient, headers: dict):
    """Create guest, room type, room, and reservation for check-in testing."""
    guest_res = await client.post("/api/guests", headers=headers, json={
        "first_name": "美麗",
        "last_name": "陳",
        "id_type": "national_id",
        "id_number": "C123456789",
        "phone": "0922222222",
        "nationality": "台灣",
    })
    guest_id = guest_res.json()["id"]

    type_res = await client.post("/api/rooms/types", headers=headers, json={
        "name": "豪華房",
        "capacity": 2,
        "base_price": 3000,
    })
    type_id = type_res.json()["id"]

    room_res = await client.post("/api/rooms", headers=headers, json={
        "room_number": "501",
        "floor": 5,
        "room_type_id": type_id,
    })
    room_id = room_res.json()["id"]

    res_res = await client.post("/api/reservations", headers=headers, json={
        "guest_id": guest_id,
        "room_type_id": type_id,
        "check_in_date": "2026-04-06",
        "check_out_date": "2026-04-08",
        "num_guests": 2,
        "includes_breakfast": True,
        "breakfast_guests": 2,
        "total_price": 6000,
    })
    reservation_id = res_res.json()["id"]

    return guest_id, type_id, room_id, reservation_id


@pytest.mark.asyncio
async def test_check_in_and_check_out(client: AsyncClient, admin_headers):
    guest_id, type_id, room_id, reservation_id = await setup_checkin_data(client, admin_headers)

    # Check in
    res = await client.post(f"/api/reservations/{reservation_id}/check-in", headers=admin_headers, json={
        "room_id": room_id,
    })
    assert res.status_code == 200
    assert res.json()["status"] == "checked_in"
    assert res.json()["room_id"] == room_id

    # Verify room is occupied
    rooms_res = await client.get("/api/rooms", headers=admin_headers, params={"status": "occupied"})
    assert len(rooms_res.json()) == 1

    # Check out
    res = await client.post(f"/api/reservations/{reservation_id}/check-out", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "checked_out"

    # Verify room is now cleaning
    rooms_res = await client.get("/api/rooms", headers=admin_headers, params={"status": "cleaning"})
    assert len(rooms_res.json()) == 1


@pytest.mark.asyncio
async def test_cannot_checkin_unavailable_room(client: AsyncClient, admin_headers):
    guest_id, type_id, room_id, reservation_id = await setup_checkin_data(client, admin_headers)

    # Set room to maintenance
    await client.patch(f"/api/rooms/{room_id}", headers=admin_headers, json={"status": "maintenance"})

    # Try check in
    res = await client.post(f"/api/reservations/{reservation_id}/check-in", headers=admin_headers, json={
        "room_id": room_id,
    })
    assert res.status_code == 400
