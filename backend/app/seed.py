"""Seed script to populate initial data.

WARNING: This script is intended for local development only. It prints a
freshly-minted device API key to stdout once at creation time. Do NOT run
this against any shared, staging, or production database — the output may
be captured by log collectors or CI job logs.
"""

import asyncio
import secrets
import uuid

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, engine, Base
from app.models.api_key import ApiKey
from app.models.user import User, UserRole
from app.models.room import RoomType, Room, RoomStatus
from app.services.auth import hash_password


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Create admin user
        admin = User(
            id=uuid.uuid4(),
            username="admin",
            password_hash=hash_password("admin123"),
            full_name="系統管理員",
            role=UserRole.admin,
        )
        session.add(admin)

        # Create staff user
        staff = User(
            id=uuid.uuid4(),
            username="staff",
            password_hash=hash_password("staff123"),
            full_name="前台人員",
            role=UserRole.staff,
        )
        session.add(staff)

        # Create cleaner user
        cleaner = User(
            username="cleaner1",
            password_hash=hash_password("cleaner1"),
            full_name="清潔人員一號",
            role=UserRole.cleaner,
            is_active=True,
        )
        session.add(cleaner)
        await session.flush()

        # Create room types
        room_types = {
            "single": RoomType(
                id=uuid.uuid4(), name="單人房", capacity=1, base_price=1500, description="標準單人房"
            ),
            "double": RoomType(
                id=uuid.uuid4(), name="雙人房", capacity=2, base_price=2500, description="標準雙人房"
            ),
            "family": RoomType(
                id=uuid.uuid4(), name="家庭房", capacity=4, base_price=4000, description="家庭四人房"
            ),
            "suite": RoomType(
                id=uuid.uuid4(), name="套房", capacity=2, base_price=5000, description="豪華套房"
            ),
        }
        for rt in room_types.values():
            session.add(rt)

        # Create sample rooms
        rooms = [
            # Floor 2: single rooms
            Room(room_number="201", floor=2, room_type_id=room_types["single"].id, status=RoomStatus.available),
            Room(room_number="202", floor=2, room_type_id=room_types["single"].id, status=RoomStatus.available),
            Room(room_number="203", floor=2, room_type_id=room_types["single"].id, status=RoomStatus.available),
            # Floor 3: double rooms
            Room(room_number="301", floor=3, room_type_id=room_types["double"].id, status=RoomStatus.available),
            Room(room_number="302", floor=3, room_type_id=room_types["double"].id, status=RoomStatus.available),
            Room(room_number="303", floor=3, room_type_id=room_types["double"].id, status=RoomStatus.available),
            # Floor 4: family rooms
            Room(room_number="401", floor=4, room_type_id=room_types["family"].id, status=RoomStatus.available),
            Room(room_number="402", floor=4, room_type_id=room_types["family"].id, status=RoomStatus.available),
            # Floor 5: suites
            Room(room_number="501", floor=5, room_type_id=room_types["suite"].id, status=RoomStatus.available),
            Room(room_number="502", floor=5, room_type_id=room_types["suite"].id, status=RoomStatus.available),
        ]
        for room in rooms:
            session.add(room)
        await session.flush()

        # Pick the first room to bind a demo device to
        first_room = (
            await session.execute(select(Room).order_by(Room.room_number).limit(1))
        ).scalar_one_or_none()
        if first_room is not None:
            raw = "neo_device_" + secrets.token_hex(8)
            device = ApiKey(
                key_hash=bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode(),
                key_prefix=raw[:8],
                name=f"Room {first_room.room_number} tablet",
                is_active=True,
                room_id=first_room.id,
            )
            session.add(device)
            print(f"[seed] Room-bound device API key for room {first_room.room_number}: {raw}")

        await session.commit()
        print("Seed data created successfully!")
        print(f"  Admin: admin / admin123")
        print(f"  Staff: staff / staff123")
        print(f"  Cleaner: cleaner1 / cleaner1")
        print(f"  Room types: {len(room_types)}")
        print(f"  Rooms: {len(rooms)}")


if __name__ == "__main__":
    asyncio.run(seed())
