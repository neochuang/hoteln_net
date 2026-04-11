import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guest import Guest, IDType
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomStatus, RoomType


async def seed_data(db: AsyncSession, admin_id: uuid.UUID):
    """Create guest, room type, room, and confirmed reservation."""
    guest = Guest(
        id=uuid.uuid4(),
        first_name="大明",
        last_name="王",
        id_type=IDType.national_id,
        id_number="A123456789",
        phone="0912345678",
        nationality="台灣",
    )
    db.add(guest)

    room_type = RoomType(id=uuid.uuid4(), name="雙人房", capacity=2, base_price=2500)
    db.add(room_type)

    room = Room(
        id=uuid.uuid4(),
        room_number="301",
        floor=3,
        room_type_id=room_type.id,
        status=RoomStatus.available,
    )
    db.add(room)

    reservation = Reservation(
        id=uuid.uuid4(),
        guest_id=guest.id,
        room_type_id=room_type.id,
        check_in_date=date(2026, 4, 6),
        check_out_date=date(2026, 4, 8),
        num_guests=2,
        status=ReservationStatus.confirmed,
        includes_breakfast=True,
        breakfast_guests=2,
        total_price=5000,
        created_by=admin_id,
    )
    db.add(reservation)
    await db.commit()

    return guest, room_type, room, reservation


@pytest.mark.asyncio
async def test_lookup_success(client: AsyncClient, db_session: AsyncSession, admin_user):
    await seed_data(db_session, admin_user.id)
    res = await client.post("/api/self-checkin/lookup", json={"id_number": "A123456789"})
    assert res.status_code == 200
    data = res.json()
    assert data["guest_name"] == "王大明"
    assert len(data["reservations"]) == 1
    assert data["reservations"][0]["room_type_name"] == "雙人房"


@pytest.mark.asyncio
async def test_lookup_no_guest(client: AsyncClient):
    res = await client.post("/api/self-checkin/lookup", json={"id_number": "Z999999999"})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_lookup_no_confirmed_reservations(client: AsyncClient, db_session: AsyncSession, admin_user):
    guest, room_type, room, reservation = await seed_data(db_session, admin_user.id)
    # Cancel the reservation
    reservation.status = ReservationStatus.cancelled
    await db_session.commit()

    res = await client.post("/api/self-checkin/lookup", json={"id_number": "A123456789"})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_confirm_success(client: AsyncClient, db_session: AsyncSession, admin_user):
    guest, room_type, room, reservation = await seed_data(db_session, admin_user.id)

    res = await client.post("/api/self-checkin/confirm", json={
        "reservation_id": str(reservation.id),
        "id_number": "A123456789",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["room_number"] == "301"
    assert data["floor"] == 3
    assert data["room_type_name"] == "雙人房"
    assert data["includes_breakfast"] is True
    assert "wifi_password" in data

    # Verify room is now occupied
    await db_session.refresh(room)
    assert room.status == RoomStatus.occupied

    # Verify reservation is checked in
    await db_session.refresh(reservation)
    assert reservation.status == ReservationStatus.checked_in


@pytest.mark.asyncio
async def test_confirm_wrong_id_number(client: AsyncClient, db_session: AsyncSession, admin_user):
    guest, room_type, room, reservation = await seed_data(db_session, admin_user.id)

    res = await client.post("/api/self-checkin/confirm", json={
        "reservation_id": str(reservation.id),
        "id_number": "WRONG123",
    })
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_confirm_no_available_room(client: AsyncClient, db_session: AsyncSession, admin_user):
    guest, room_type, room, reservation = await seed_data(db_session, admin_user.id)

    # Set room to maintenance
    room.status = RoomStatus.maintenance
    await db_session.commit()

    res = await client.post("/api/self-checkin/confirm", json={
        "reservation_id": str(reservation.id),
        "id_number": "A123456789",
    })
    assert res.status_code == 400
