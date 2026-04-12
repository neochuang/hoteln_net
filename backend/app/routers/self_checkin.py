from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.checkin import CheckInRecord
from app.models.guest import Guest
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomStatus, RoomType
from app.schemas.self_checkin import (
    ConfirmRequest,
    ConfirmResponse,
    LookupRequest,
    LookupReservation,
    LookupResponse,
)

router = APIRouter()


@router.post("/lookup", response_model=LookupResponse)
async def lookup(body: LookupRequest, db: AsyncSession = Depends(get_db)):
    # Find guest by ID number
    result = await db.execute(select(Guest).where(Guest.id_number == body.id_number))
    guest = result.scalar_one_or_none()
    if guest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到此證件號碼的旅客")

    # Find confirmed reservations
    result = await db.execute(
        select(Reservation)
        .where(Reservation.guest_id == guest.id, Reservation.status == ReservationStatus.confirmed)
        .options(selectinload(Reservation.room_type))
        .order_by(Reservation.check_in_date)
    )
    reservations = result.scalars().all()

    if not reservations:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="目前沒有待報到的訂房")

    return LookupResponse(
        guest_name=f"{guest.last_name}{guest.first_name}",
        reservations=[
            LookupReservation(
                id=r.id,
                check_in_date=r.check_in_date,
                check_out_date=r.check_out_date,
                room_type_name=r.room_type.name,
                num_guests=r.num_guests,
                includes_breakfast=r.includes_breakfast,
                breakfast_guests=r.breakfast_guests,
            )
            for r in reservations
        ],
    )


@router.post("/confirm", response_model=ConfirmResponse)
async def confirm(body: ConfirmRequest, db: AsyncSession = Depends(get_db)):
    # Get reservation with room type
    result = await db.execute(
        select(Reservation)
        .where(Reservation.id == body.reservation_id)
        .options(selectinload(Reservation.room_type), selectinload(Reservation.guest))
    )
    reservation = result.scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="訂房不存在")
    if reservation.status != ReservationStatus.confirmed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="此訂房無法報到")

    # Verify ID number matches
    if reservation.guest.id_number != body.id_number:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="證件號碼不匹配")

    # Auto-assign room: find first available room of the same type
    result = await db.execute(
        select(Room)
        .where(Room.room_type_id == reservation.room_type_id, Room.status == RoomStatus.available)
        .order_by(Room.room_number)
        .limit(1)
    )
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="目前沒有可用的房間，請洽櫃台")

    # Update reservation
    reservation.status = ReservationStatus.checked_in
    reservation.room_id = room.id

    # Update room
    room.status = RoomStatus.occupied

    # Create check-in record (checked_in_by = None for self check-in)
    record = CheckInRecord(
        reservation_id=reservation.id,
        room_id=room.id,
        checked_in_by=None,
    )
    db.add(record)

    await db.commit()

    return ConfirmResponse(
        room_number=room.room_number,
        floor=room.floor,
        room_type_name=reservation.room_type.name,
        check_in_date=reservation.check_in_date,
        check_out_date=reservation.check_out_date,
        includes_breakfast=reservation.includes_breakfast,
        breakfast_info=settings.breakfast_info if reservation.includes_breakfast else "未含早餐",
        wifi_password=settings.wifi_password,
    )
