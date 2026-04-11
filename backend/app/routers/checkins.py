import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.checkin import CheckInRecord
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomStatus
from app.models.user import User, UserRole
from app.schemas.reservation import CheckInRequest, ReservationResponse

router = APIRouter()


@router.post("/reservations/{reservation_id}/check-in", response_model=ReservationResponse)
async def check_in(
    reservation_id: uuid.UUID,
    body: CheckInRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    # Get reservation
    result = await db.execute(select(Reservation).where(Reservation.id == reservation_id))
    reservation = result.scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    if reservation.status != ReservationStatus.confirmed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reservation is not in confirmed status")

    # Get and validate room
    room_id = body.room_id
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.status != RoomStatus.available:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is not available")
    if room.room_type_id != reservation.room_type_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room type does not match reservation")

    # Update reservation
    reservation.status = ReservationStatus.checked_in
    reservation.room_id = room_id

    # Update room status
    room.status = RoomStatus.occupied

    # Create check-in record
    record = CheckInRecord(
        reservation_id=reservation.id,
        room_id=room_id,
        checked_in_by=current_user.id,
    )
    db.add(record)

    await db.commit()
    await db.refresh(reservation)
    return reservation


@router.post("/reservations/{reservation_id}/check-out", response_model=ReservationResponse)
async def check_out(
    reservation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    # Get reservation
    result = await db.execute(select(Reservation).where(Reservation.id == reservation_id))
    reservation = result.scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    if reservation.status != ReservationStatus.checked_in:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reservation is not checked in")

    # Get check-in record
    result = await db.execute(
        select(CheckInRecord).where(CheckInRecord.reservation_id == reservation_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Check-in record not found")

    # Update room status to cleaning
    result = await db.execute(select(Room).where(Room.id == record.room_id))
    room = result.scalar_one()
    room.status = RoomStatus.cleaning

    # Update check-in record
    from datetime import datetime, timezone
    record.checked_out_at = datetime.now(timezone.utc)
    record.checked_out_by = current_user.id

    # Update reservation
    reservation.status = ReservationStatus.checked_out

    await db.commit()
    await db.refresh(reservation)
    return reservation
