import uuid
from datetime import date, datetime, timezone

import bcrypt
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey
from app.models.cleaning import CleaningRecord, CleaningType
from app.models.guest import Guest, IDType
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomStatus, RoomType


async def seed_room(db: AsyncSession) -> tuple[RoomType, Room]:
    room_type = RoomType(id=uuid.uuid4(), name="標準房", capacity=2, base_price=2000)
    db.add(room_type)
    room = Room(
        id=uuid.uuid4(),
        room_number="401",
        floor=4,
        room_type_id=room_type.id,
        status=RoomStatus.available,
    )
    db.add(room)
    await db.commit()
    return room_type, room


async def seed_checked_in_reservation(
    db: AsyncSession, room: Room, room_type: RoomType, admin_id: uuid.UUID
) -> Reservation:
    guest = Guest(
        id=uuid.uuid4(),
        first_name="小明",
        last_name="王",
        id_type=IDType.national_id,
        id_number="D123456789",
        phone="0911111111",
        nationality="台灣",
    )
    db.add(guest)
    reservation = Reservation(
        id=uuid.uuid4(),
        guest_id=guest.id,
        room_type_id=room_type.id,
        room_id=room.id,
        check_in_date=date(2026, 4, 10),
        check_out_date=date(2026, 4, 13),
        num_guests=2,
        status=ReservationStatus.checked_in,
        includes_breakfast=False,
        breakfast_guests=0,
        total_price=6000,
        created_by=admin_id,
    )
    db.add(reservation)
    await db.commit()
    return reservation


async def seed_api_key(db: AsyncSession) -> tuple[ApiKey, str]:
    raw_key = "neo_device_test_key_abc123"
    key_hash = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
    api_key = ApiKey(
        id=uuid.uuid4(),
        key_hash=key_hash,
        key_prefix=raw_key[:8],
        name="Test Device",
        is_active=True,
    )
    db.add(api_key)
    await db.commit()
    return api_key, raw_key


@pytest.mark.asyncio
async def test_mark_cleaning_occupied_room(
    client: AsyncClient, db_session: AsyncSession, admin_user, admin_headers
):
    room_type, room = await seed_room(db_session)
    reservation = await seed_checked_in_reservation(db_session, room, room_type, admin_user.id)
    room.status = RoomStatus.occupied
    await db_session.commit()

    res = await client.post(f"/api/housekeeping/rooms/{room.room_number}/mark-cleaning", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "cleaning"
    assert data["cleaning_record"]["cleaning_type"] == "daily"

    await db_session.refresh(room)
    assert room.status == RoomStatus.cleaning


@pytest.mark.asyncio
async def test_mark_cleaning_rejects_non_occupied(
    client: AsyncClient, db_session: AsyncSession, admin_headers
):
    room_type, room = await seed_room(db_session)
    res = await client.post(f"/api/housekeeping/rooms/{room.room_number}/mark-cleaning", headers=admin_headers)
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_clean_complete_checkout_to_available(
    client: AsyncClient, db_session: AsyncSession, admin_headers
):
    room_type, room = await seed_room(db_session)
    room.status = RoomStatus.cleaning
    await db_session.commit()

    record = CleaningRecord(
        id=uuid.uuid4(),
        room_id=room.id,
        cleaning_type=CleaningType.checkout,
    )
    db_session.add(record)
    await db_session.commit()

    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/clean-complete",
        headers=admin_headers,
        json={"cleaned_by_name": "陳小美"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "available"
    assert data["cleaning_record"]["cleaned_by_name"] == "陳小美"
    assert data["cleaning_record"]["completed_at"] is not None

    await db_session.refresh(room)
    assert room.status == RoomStatus.available


@pytest.mark.asyncio
async def test_clean_complete_daily_to_occupied(
    client: AsyncClient, db_session: AsyncSession, admin_user, admin_headers
):
    room_type, room = await seed_room(db_session)
    reservation = await seed_checked_in_reservation(db_session, room, room_type, admin_user.id)
    room.status = RoomStatus.cleaning
    await db_session.commit()

    record = CleaningRecord(
        id=uuid.uuid4(),
        room_id=room.id,
        cleaning_type=CleaningType.daily,
    )
    db_session.add(record)
    await db_session.commit()

    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/clean-complete",
        headers=admin_headers,
        json={},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "occupied"

    await db_session.refresh(room)
    assert room.status == RoomStatus.occupied


@pytest.mark.asyncio
async def test_clean_complete_via_api_key(
    client: AsyncClient, db_session: AsyncSession, admin_headers
):
    room_type, room = await seed_room(db_session)
    room.status = RoomStatus.cleaning
    await db_session.commit()

    record = CleaningRecord(
        id=uuid.uuid4(),
        room_id=room.id,
        cleaning_type=CleaningType.checkout,
    )
    db_session.add(record)
    await db_session.commit()

    api_key, raw_key = await seed_api_key(db_session)

    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/clean-complete",
        headers={"X-API-Key": raw_key},
        json={"cleaned_by_name": "王大姊"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "available"
    assert data["cleaning_record"]["reported_via"] == "device"
    assert data["cleaning_record"]["api_key_id"] == str(api_key.id)


@pytest.mark.asyncio
async def test_clean_complete_idempotent_when_not_cleaning(
    client: AsyncClient, db_session: AsyncSession, admin_headers
):
    """Room not in cleaning status — should return 200 idempotently, not 400."""
    room_type, room = await seed_room(db_session)
    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/clean-complete",
        headers=admin_headers,
        json={},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "available"
    assert data["cleaning_record"] is None


@pytest.mark.asyncio
async def test_clean_complete_rejects_inactive_api_key(
    client: AsyncClient, db_session: AsyncSession,
):
    room_type, room = await seed_room(db_session)
    room.status = RoomStatus.cleaning
    await db_session.commit()

    record = CleaningRecord(room_id=room.id, cleaning_type=CleaningType.checkout)
    db_session.add(record)
    await db_session.commit()

    api_key, raw_key = await seed_api_key(db_session)
    api_key.is_active = False
    await db_session.commit()

    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/clean-complete",
        headers={"X-API-Key": raw_key},
        json={},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_cleaning_status(client: AsyncClient, db_session: AsyncSession, admin_headers):
    room_type, room = await seed_room(db_session)
    room.status = RoomStatus.cleaning
    await db_session.commit()

    record = CleaningRecord(room_id=room.id, cleaning_type=CleaningType.checkout)
    db_session.add(record)
    await db_session.commit()

    res = await client.get("/api/housekeeping/rooms/cleaning-status", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["room_number"] == "401"
    assert data[0]["cleaning_type"] == "checkout"


@pytest.mark.asyncio
async def test_list_cleaning_records(client: AsyncClient, db_session: AsyncSession, admin_headers):
    room_type, room = await seed_room(db_session)
    record = CleaningRecord(room_id=room.id, cleaning_type=CleaningType.checkout)
    db_session.add(record)
    await db_session.commit()

    res = await client.get("/api/housekeeping/cleaning-records", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["room_id"] == str(room.id)


@pytest.mark.asyncio
async def test_clean_complete_idempotent_repeat_call(
    client: AsyncClient, db_session: AsyncSession, admin_headers
):
    """Call clean-complete twice — second call should return 200 with the completed record."""
    room_type, room = await seed_room(db_session)
    room.status = RoomStatus.cleaning
    await db_session.commit()

    record = CleaningRecord(
        id=uuid.uuid4(),
        room_id=room.id,
        cleaning_type=CleaningType.checkout,
    )
    db_session.add(record)
    await db_session.commit()

    # First call: actually completes cleaning
    res1 = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/clean-complete",
        headers=admin_headers,
        json={"cleaned_by_name": "陳小美"},
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "available"
    first_record_id = res1.json()["cleaning_record"]["id"]

    # Second call: idempotent return
    res2 = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/clean-complete",
        headers=admin_headers,
        json={"cleaned_by_name": "should be ignored"},
    )
    assert res2.status_code == 200
    data = res2.json()
    assert data["status"] == "available"
    assert data["cleaning_record"]["id"] == first_record_id
    assert data["cleaning_record"]["cleaned_by_name"] == "陳小美"  # not overwritten


@pytest.mark.asyncio
async def test_clean_complete_idempotent_occupied_with_record(
    client: AsyncClient, db_session: AsyncSession, admin_user, admin_headers
):
    """Occupied room with a completed cleaning record — returns 200 with that record."""
    room_type, room = await seed_room(db_session)
    reservation = await seed_checked_in_reservation(db_session, room, room_type, admin_user.id)
    room.status = RoomStatus.occupied
    await db_session.commit()

    record = CleaningRecord(
        id=uuid.uuid4(),
        room_id=room.id,
        cleaning_type=CleaningType.daily,
        completed_at=datetime(2026, 4, 15, 10, 0, tzinfo=timezone.utc),
        cleaned_by_name="王大姊",
    )
    db_session.add(record)
    await db_session.commit()

    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/clean-complete",
        headers=admin_headers,
        json={},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "occupied"
    assert data["cleaning_record"]["id"] == str(record.id)


@pytest.mark.asyncio
async def test_clean_complete_idempotent_maintenance(
    client: AsyncClient, db_session: AsyncSession, admin_headers
):
    """Maintenance room — returns 200 idempotently."""
    room_type, room = await seed_room(db_session)
    room.status = RoomStatus.maintenance
    await db_session.commit()

    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/clean-complete",
        headers=admin_headers,
        json={},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "maintenance"
    assert data["cleaning_record"] is None


@pytest.mark.asyncio
async def test_clean_complete_race_pending_record_already_claimed(
    client: AsyncClient, db_session: AsyncSession, admin_headers
):
    """Simulates losing a concurrent race: room.status is still 'cleaning' but
    the pending record has already been completed by another request. The losing
    request must fall through to idempotent 200, not raise 404."""
    room_type, room = await seed_room(db_session)
    room.status = RoomStatus.cleaning
    await db_session.commit()

    # Winner already claimed & completed the pending record; room.status not yet
    # transitioned (as it would be in the narrow window between commits).
    completed = CleaningRecord(
        id=uuid.uuid4(),
        room_id=room.id,
        cleaning_type=CleaningType.checkout,
        completed_at=datetime(2026, 4, 15, 10, 0, tzinfo=timezone.utc),
        cleaned_by_name="winner",
    )
    db_session.add(completed)
    await db_session.commit()

    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/clean-complete",
        headers=admin_headers,
        json={"cleaned_by_name": "loser"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["cleaning_record"]["id"] == str(completed.id)
    assert data["cleaning_record"]["cleaned_by_name"] == "winner"  # not overwritten


@pytest.mark.asyncio
async def test_clean_complete_idempotent_via_api_key(
    client: AsyncClient, db_session: AsyncSession,
):
    """Device calls clean-complete on non-cleaning room — returns 200."""
    room_type, room = await seed_room(db_session)
    api_key, raw_key = await seed_api_key(db_session)

    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/clean-complete",
        headers={"X-API-Key": raw_key},
        json={},
    )
    assert res.status_code == 200
    assert res.json()["cleaning_record"] is None


from app.models.cleaning_request import CleaningRequest, CleaningRequestStatus


@pytest.mark.asyncio
async def test_mark_cleaning_auto_fulfills_pending_request(
    client: AsyncClient, db_session: AsyncSession, admin_user, admin_headers
):
    room_type, room = await seed_room(db_session)
    _ = await seed_checked_in_reservation(db_session, room, room_type, admin_user.id)
    room.status = RoomStatus.occupied
    await db_session.commit()

    api_key = ApiKey(
        id=uuid.uuid4(),
        key_hash="x",
        key_prefix="neo_test",
        name="dev",
        is_active=True,
        room_id=room.id,
    )
    db_session.add(api_key)
    req = CleaningRequest(
        id=uuid.uuid4(),
        room_id=room.id,
        api_key_id=api_key.id,
        notes="pls",
    )
    db_session.add(req)
    await db_session.commit()

    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/mark-cleaning",
        headers=admin_headers,
    )
    assert res.status_code == 200
    record_id = res.json()["cleaning_record"]["id"]

    await db_session.refresh(req)
    assert req.status == CleaningRequestStatus.fulfilled
    assert str(req.fulfilled_by_cleaning_record_id) == record_id
    assert req.fulfilled_at is not None


@pytest.mark.asyncio
async def test_mark_cleaning_without_request_still_works(
    client: AsyncClient, db_session: AsyncSession, admin_user, admin_headers
):
    """Existing behaviour preserved: no request → still creates record, no error."""
    room_type, room = await seed_room(db_session)
    _ = await seed_checked_in_reservation(db_session, room, room_type, admin_user.id)
    room.status = RoomStatus.occupied
    await db_session.commit()

    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/mark-cleaning",
        headers=admin_headers,
    )
    assert res.status_code == 200
