import uuid
from datetime import date, datetime, timezone
from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_api_key, get_device_or_user, require_role
from app.models.api_key import ApiKey
from app.models.cleaning import CleaningRecord, CleaningType, ReportedVia
from app.models.cleaning_request import CleaningRequest, CleaningRequestStatus
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
from app.schemas.cleaning_request import CleaningRequestCreate, CleaningRequestResponse

router = APIRouter()


async def _has_active_reservation(db: AsyncSession, room_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(Reservation).where(
            Reservation.room_id == room_id,
            Reservation.status == ReservationStatus.checked_in,
        )
    )
    return result.scalar_one_or_none() is not None


async def _cleaning_request_response(
    db: AsyncSession, req: CleaningRequest
) -> CleaningRequestResponse:
    # room_number is needed in the response; fetch via the FK
    result = await db.execute(select(Room.room_number).where(Room.id == req.room_id))
    room_number = result.scalar_one()
    return CleaningRequestResponse(
        id=req.id,
        room_id=req.room_id,
        room_number=room_number,
        api_key_id=req.api_key_id,
        notes=req.notes,
        status=req.status,
        requested_at=req.requested_at,
        fulfilled_at=req.fulfilled_at,
        fulfilled_by_cleaning_record_id=req.fulfilled_by_cleaning_record_id,
        cancelled_at=req.cancelled_at,
        cancelled_by_user_id=req.cancelled_by_user_id,
    )


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

    # --- Active cleaning: atomically claim the pending record ---
    if room.status == RoomStatus.cleaning:
        values = {
            "completed_at": datetime.now(timezone.utc),
            "cleaned_by_name": body.cleaned_by_name,
            "notes": body.notes,
        }
        if isinstance(auth, ApiKey):
            values["reported_via"] = ReportedVia.device
            values["api_key_id"] = auth.id
        else:
            values["reported_via"] = ReportedVia.staff
            values["staff_user_id"] = auth.id

        stmt = (
            update(CleaningRecord)
            .where(
                CleaningRecord.room_id == room.id,
                CleaningRecord.completed_at.is_(None),
            )
            .values(**values)
            .returning(CleaningRecord)
        )
        record = (await db.execute(stmt)).scalar_one_or_none()

        if record is not None:
            has_active = await _has_active_reservation(db, room.id)
            room.status = RoomStatus.occupied if has_active else RoomStatus.available

            await db.commit()
            await db.refresh(room)

            return CleanCompleteResponse(
                room_id=room.id,
                room_number=room.room_number,
                status=room.status.value,
                cleaning_record=CleaningRecordResponse.model_validate(record),
            )

        # Race lost (another request already completed) — refresh and fall through
        await db.refresh(room)

    # --- Idempotent return ---
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


@router.post("/cleaning-requests", response_model=CleaningRequestResponse)
async def create_cleaning_request(
    body: CleaningRequestCreate,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey = Depends(get_api_key),
):
    if api_key.room_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device not bound to a room",
        )

    result = await db.execute(select(Room).where(Room.id == api_key.room_id))
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device's bound room no longer exists",
        )
    if room.status != RoomStatus.occupied:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room is not occupied",
        )

    # Snapshot identifiers so they survive a potential rollback (which expires ORM state)
    room_id = room.id
    api_key_id = api_key.id

    req = CleaningRequest(
        room_id=room_id,
        api_key_id=api_key_id,
        notes=body.notes,
    )
    db.add(req)
    try:
        await db.commit()
    except IntegrityError:
        # Partial unique index violation → an existing pending request is present
        await db.rollback()
        existing = await db.execute(
            select(CleaningRequest).where(
                CleaningRequest.room_id == room_id,
                CleaningRequest.status == CleaningRequestStatus.pending,
            )
        )
        req = existing.scalar_one()
    else:
        await db.refresh(req)

    return await _cleaning_request_response(db, req)


@router.get("/cleaning-requests", response_model=list[CleaningRequestResponse])
async def list_cleaning_requests(
    status_filter: str | None = Query("pending", alias="status"),
    room_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin, UserRole.staff, UserRole.cleaner)),
):
    query = select(CleaningRequest).order_by(CleaningRequest.requested_at.desc())
    if status_filter and status_filter != "all":
        try:
            status_enum = CleaningRequestStatus(status_filter)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")
        query = query.where(CleaningRequest.status == status_enum)
    if room_id is not None:
        query = query.where(CleaningRequest.room_id == room_id)

    result = await db.execute(query)
    items = result.scalars().all()
    return [await _cleaning_request_response(db, r) for r in items]
