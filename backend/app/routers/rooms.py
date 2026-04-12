import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.room import Room, RoomStatus, RoomType
from app.models.user import User, UserRole
from app.schemas.room import RoomCreate, RoomResponse, RoomTypeCreate, RoomTypeResponse, RoomUpdate

router = APIRouter()


# --- Room Types ---

@router.get("/types", response_model=list[RoomTypeResponse])
async def list_room_types(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(RoomType).order_by(RoomType.name))
    return result.scalars().all()


@router.post("/types", response_model=RoomTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_room_type(
    body: RoomTypeCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    room_type = RoomType(**body.model_dump())
    db.add(room_type)
    await db.commit()
    await db.refresh(room_type)
    return room_type


# --- Rooms ---

@router.get("", response_model=list[RoomResponse])
async def list_rooms(
    status_filter: RoomStatus | None = Query(None, alias="status"),
    floor: int | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(Room).options(selectinload(Room.room_type))
    if status_filter:
        query = query.where(Room.status == status_filter)
    if floor:
        query = query.where(Room.floor == floor)
    query = query.order_by(Room.room_number)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    body: RoomCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    room = Room(
        room_number=body.room_number,
        floor=body.floor,
        room_type_id=body.room_type_id,
        notes=body.notes,
    )
    db.add(room)
    await db.commit()
    # Re-fetch with eager load
    result = await db.execute(select(Room).options(selectinload(Room.room_type)).where(Room.id == room.id))
    return result.scalar_one()


@router.patch("/{room_id}", response_model=RoomResponse)
async def update_room(
    room_id: uuid.UUID,
    body: RoomUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    result = await db.execute(select(Room).options(selectinload(Room.room_type)).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(room, key, value)

    await db.commit()
    result = await db.execute(select(Room).options(selectinload(Room.room_type)).where(Room.id == room_id))
    return result.scalar_one()
