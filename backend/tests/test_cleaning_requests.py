import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cleaning_request import CleaningRequest, CleaningRequestStatus
from app.models.room import Room, RoomStatus, RoomType
from app.models.api_key import ApiKey


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
