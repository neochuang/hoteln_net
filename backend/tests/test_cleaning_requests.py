import uuid
from datetime import datetime, timezone

import bcrypt
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cleaning_request import CleaningRequest, CleaningRequestStatus
from app.models.room import Room, RoomStatus, RoomType
from app.models.api_key import ApiKey


async def _seed_room(db_session: AsyncSession, status: RoomStatus = RoomStatus.occupied) -> Room:
    room_type = RoomType(id=uuid.uuid4(), name="標準房", capacity=2, base_price=2000)
    room = Room(
        id=uuid.uuid4(),
        room_number="601",
        floor=6,
        room_type_id=room_type.id,
        status=status,
    )
    db_session.add_all([room_type, room])
    await db_session.commit()
    return room


async def _seed_device_key(db_session: AsyncSession, room: Room | None) -> tuple[ApiKey, str]:
    raw = "neo_device_req_test_xxx"
    api_key = ApiKey(
        id=uuid.uuid4(),
        key_hash=bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode(),
        key_prefix=raw[:8],
        name="Room Device",
        is_active=True,
        room_id=room.id if room else None,
    )
    db_session.add(api_key)
    await db_session.commit()
    return api_key, raw


@pytest.mark.asyncio
async def test_cleaning_request_table_created(db_session: AsyncSession):
    """Smoke: model can be inserted and the partial unique index works."""
    room_type = RoomType(id=uuid.uuid4(), name="標準房", capacity=2, base_price=2000)
    room = Room(
        id=uuid.uuid4(),
        room_number="501",
        floor=5,
        room_type_id=room_type.id,
        status=RoomStatus.occupied,
    )
    api_key = ApiKey(
        id=uuid.uuid4(), key_hash="x", key_prefix="neo_test", name="dev", room_id=room.id
    )
    db_session.add_all([room_type, room, api_key])
    await db_session.commit()

    req = CleaningRequest(room_id=room.id, api_key_id=api_key.id, notes="please")
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)

    assert req.status == CleaningRequestStatus.pending
    assert req.requested_at is not None


@pytest.mark.asyncio
async def test_create_cleaning_request_happy_path(
    client: AsyncClient, db_session: AsyncSession
):
    room = await _seed_room(db_session, RoomStatus.occupied)
    _, raw = await _seed_device_key(db_session, room)

    res = await client.post(
        "/api/housekeeping/cleaning-requests",
        headers={"X-API-Key": raw},
        json={"notes": "toilet paper"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "pending"
    assert data["room_number"] == room.room_number
    assert data["notes"] == "toilet paper"


@pytest.mark.asyncio
async def test_create_cleaning_request_unbound_device_rejected(
    client: AsyncClient, db_session: AsyncSession
):
    _, raw = await _seed_device_key(db_session, room=None)
    res = await client.post(
        "/api/housekeeping/cleaning-requests",
        headers={"X-API-Key": raw},
        json={},
    )
    assert res.status_code == 400
    assert "not bound" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_cleaning_request_non_occupied_rejected(
    client: AsyncClient, db_session: AsyncSession
):
    room = await _seed_room(db_session, RoomStatus.available)
    _, raw = await _seed_device_key(db_session, room)
    res = await client.post(
        "/api/housekeeping/cleaning-requests",
        headers={"X-API-Key": raw},
        json={},
    )
    assert res.status_code == 400
    assert "not occupied" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_cleaning_request_idempotent_when_pending_exists(
    client: AsyncClient, db_session: AsyncSession
):
    room = await _seed_room(db_session, RoomStatus.occupied)
    _, raw = await _seed_device_key(db_session, room)

    res1 = await client.post(
        "/api/housekeeping/cleaning-requests",
        headers={"X-API-Key": raw},
        json={"notes": "first"},
    )
    res2 = await client.post(
        "/api/housekeeping/cleaning-requests",
        headers={"X-API-Key": raw},
        json={"notes": "second"},
    )
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json()["id"] == res2.json()["id"]
    # second call must NOT overwrite the first notes
    assert res2.json()["notes"] == "first"


@pytest.mark.asyncio
async def test_list_cleaning_requests_default_pending(
    client: AsyncClient, db_session: AsyncSession, staff_headers
):
    room = await _seed_room(db_session, RoomStatus.occupied)
    _, raw = await _seed_device_key(db_session, room)
    # create one pending
    await client.post(
        "/api/housekeeping/cleaning-requests",
        headers={"X-API-Key": raw},
        json={"notes": "hi"},
    )
    res = await client.get("/api/housekeeping/cleaning-requests", headers=staff_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_list_cleaning_requests_cleaner_allowed(
    client: AsyncClient, db_session: AsyncSession, cleaner_headers
):
    res = await client.get("/api/housekeeping/cleaning-requests", headers=cleaner_headers)
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_list_cleaning_requests_readonly_denied(
    client: AsyncClient, db_session: AsyncSession
):
    from app.models.user import User, UserRole
    from app.services.auth import create_access_token, hash_password

    ro = User(
        id=uuid.uuid4(),
        username="ro",
        password_hash=hash_password("x"),
        full_name="RO",
        role=UserRole.readonly,
    )
    db_session.add(ro)
    await db_session.commit()
    token = create_access_token(str(ro.id))

    res = await client.get(
        "/api/housekeeping/cleaning-requests",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_cancel_pending_request_by_staff(
    client: AsyncClient, db_session: AsyncSession, staff_headers, staff_user
):
    room = await _seed_room(db_session, RoomStatus.occupied)
    _, raw = await _seed_device_key(db_session, room)
    created = await client.post(
        "/api/housekeeping/cleaning-requests",
        headers={"X-API-Key": raw},
        json={},
    )
    req_id = created.json()["id"]

    res = await client.post(
        f"/api/housekeeping/cleaning-requests/{req_id}/cancel",
        headers=staff_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "cancelled"
    assert data["cancelled_by_user_id"] == str(staff_user.id)
    assert data["cancelled_at"] is not None


@pytest.mark.asyncio
async def test_cancel_non_pending_returns_409(
    client: AsyncClient, db_session: AsyncSession, staff_headers
):
    # Insert a request directly in 'cancelled' state
    room = await _seed_room(db_session, RoomStatus.occupied)
    api_key, _ = await _seed_device_key(db_session, room)
    req = CleaningRequest(
        room_id=room.id,
        api_key_id=api_key.id,
        status=CleaningRequestStatus.cancelled,
        cancelled_at=datetime.now(timezone.utc),
    )
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)

    res = await client.post(
        f"/api/housekeeping/cleaning-requests/{req.id}/cancel",
        headers=staff_headers,
    )
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_cancel_missing_id_returns_404(
    client: AsyncClient, db_session: AsyncSession, staff_headers
):
    res = await client.post(
        f"/api/housekeeping/cleaning-requests/{uuid.uuid4()}/cancel",
        headers=staff_headers,
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_cancel_rejected_for_cleaner(
    client: AsyncClient, db_session: AsyncSession, cleaner_headers
):
    room = await _seed_room(db_session, RoomStatus.occupied)
    api_key, _ = await _seed_device_key(db_session, room)
    req = CleaningRequest(room_id=room.id, api_key_id=api_key.id)
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)

    res = await client.post(
        f"/api/housekeeping/cleaning-requests/{req.id}/cancel",
        headers=cleaner_headers,
    )
    assert res.status_code == 403
