"""Seed script to populate initial data."""

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, engine, Base
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

        await session.commit()
        print("Seed data created successfully!")
        print(f"  Admin: admin / admin123")
        print(f"  Staff: staff / staff123")
        print(f"  Room types: {len(room_types)}")
        print(f"  Rooms: {len(rooms)}")


if __name__ == "__main__":
    asyncio.run(seed())
