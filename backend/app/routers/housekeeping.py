import uuid
from datetime import date, datetime, timezone
from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_device_or_user, require_role
from app.models.api_key import ApiKey
from app.models.cleaning import CleaningRecord, CleaningType, ReportedVia
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomStatus
from app.models.user import User, UserRole
from app.schemas.cleaning import (
    CleanCompleteRequest,
    CleanCompleteResponse,
    CleaningRecordResponse,
    CleaningStatusRoom,
    MarkCleaningResponse,
)

router = APIRouter()


async def _has_active_reservation(db: AsyncSession, room_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(Reservation).where(
            Reservation.room_id == room_id,
            Reservation.status == ReservationStatus.checked_in,
        )
    )
    return result.scalar_one_or_none() is not None


@router.post("/rooms/{room_number}/mark-cleaning", response_model=MarkCleaningResponse)
async def mark_cleaning(
    room_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    result = await db.execute(select(Room).where(Room.room_number == room_number))
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.status != RoomStatus.occupied:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is not occupied")

    room.status = RoomStatus.cleaning

    record = CleaningRecord(
        room_id=room.id,
        cleaning_type=CleaningType.daily,
    )
    db.add(record)

    await db.commit()
    await db.refresh(room)
    await db.refresh(record)

    return MarkCleaningResponse(
        room_id=room.id,
        room_number=room.room_number,
        status=room.status.value,
        cleaning_record=CleaningRecordResponse.model_validate(record),
    )


@router.post("/rooms/{room_number}/clean-complete", response_model=CleanCompleteResponse)
async def clean_complete(
    room_number: str,
    body: CleanCompleteRequest,
    db: AsyncSession = Depends(get_db),
    auth: Union[ApiKey, User] = Depends(get_device_or_user),
):
    result = await db.execute(select(Room).where(Room.room_number == room_number))
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    # --- Active cleaning: execute completion flow ---
    if room.status == RoomStatus.cleaning:
        result = await db.execute(
            select(CleaningRecord)
            .where(CleaningRecord.room_id == room.id, CleaningRecord.completed_at.is_(None))
            .order_by(CleaningRecord.started_at.desc())
            .limit(1)
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No pending cleaning record found",
            )

        record.completed_at = datetime.now(timezone.utc)
        record.cleaned_by_name = body.cleaned_by_name
        record.notes = body.notes

        if isinstance(auth, ApiKey):
            record.reported_via = ReportedVia.device
            record.api_key_id = auth.id
        else:
            record.reported_via = ReportedVia.staff
            record.staff_user_id = auth.id

        has_active = await _has_active_reservation(db, room.id)
        room.status = RoomStatus.occupied if has_active else RoomStatus.available

        await db.commit()
        await db.refresh(room)
        await db.refresh(record)

        return CleanCompleteResponse(
            room_id=room.id,
            room_number=room.room_number,
            status=room.status.value,
            cleaning_record=CleaningRecordResponse.model_validate(record),
        )

    # --- Not cleaning: idempotent return ---
    result = await db.execute(
        select(CleaningRecord)
        .where(CleaningRecord.room_id == room.id, CleaningRecord.completed_at.is_not(None))
        .order_by(CleaningRecord.completed_at.desc())
        .limit(1)
    )
    last_record = result.scalar_one_or_none()

    return CleanCompleteResponse(
        room_id=room.id,
        room_number=room.room_number,
        status=room.status.value,
        cleaning_record=CleaningRecordResponse.model_validate(last_record) if last_record else None,
    )


@router.get("/rooms/cleaning-status", response_model=list[CleaningStatusRoom])
async def cleaning_status(
    db: AsyncSession = Depends(get_db),
    auth: Union[ApiKey, User] = Depends(get_device_or_user),
):
    result = await db.execute(
        select(Room)
        .options(selectinload(Room.room_type))
        .where(Room.status == RoomStatus.cleaning)
        .order_by(Room.room_number)
    )
    rooms = result.scalars().all()

    response = []
    for room in rooms:
        rec_result = await db.execute(
            select(CleaningRecord)
            .where(CleaningRecord.room_id == room.id, CleaningRecord.completed_at.is_(None))
            .order_by(CleaningRecord.started_at.desc())
            .limit(1)
        )
        record = rec_result.scalar_one_or_none()
        if record:
            response.append(CleaningStatusRoom(
                room_id=room.id,
                room_number=room.room_number,
                floor=room.floor,
                room_type_name=room.room_type.name,
                cleaning_type=record.cleaning_type,
                started_at=record.started_at,
            ))

    return response


@router.get("/cleaning-records", response_model=list[CleaningRecordResponse])
async def list_cleaning_records(
    room_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    cleaning_type: CleaningType | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    query = select(CleaningRecord).order_by(CleaningRecord.started_at.desc())
    if room_id:
        query = query.where(CleaningRecord.room_id == room_id)
    if date_from:
        query = query.where(CleaningRecord.started_at >= datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc))
    if date_to:
        query = query.where(CleaningRecord.started_at < datetime(date_to.year, date_to.month, date_to.day, tzinfo=timezone.utc))
    if cleaning_type:
        query = query.where(CleaningRecord.cleaning_type == cleaning_type)

    result = await db.execute(query)
    return result.scalars().all()
