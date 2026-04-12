import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.reservation import Reservation, ReservationStatus
from app.models.user import User, UserRole
from app.schemas.reservation import ReservationCreate, ReservationResponse, ReservationUpdate

router = APIRouter()


@router.get("", response_model=list[ReservationResponse])
async def list_reservations(
    status_filter: ReservationStatus | None = Query(None, alias="status"),
    from_date: date | None = None,
    to_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(Reservation)
    if status_filter:
        query = query.where(Reservation.status == status_filter)
    if from_date:
        query = query.where(Reservation.check_in_date >= from_date)
    if to_date:
        query = query.where(Reservation.check_in_date <= to_date)
    query = query.order_by(Reservation.check_in_date.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    body: ReservationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    reservation = Reservation(
        guest_id=body.guest_id,
        room_type_id=body.room_type_id,
        check_in_date=body.check_in_date,
        check_out_date=body.check_out_date,
        num_guests=body.num_guests,
        includes_breakfast=body.includes_breakfast,
        breakfast_guests=body.breakfast_guests,
        total_price=body.total_price,
        notes=body.notes,
        created_by=current_user.id,
    )
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)
    return reservation


@router.get("/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(
    reservation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Reservation).where(Reservation.id == reservation_id))
    reservation = result.scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    return reservation


@router.patch("/{reservation_id}", response_model=ReservationResponse)
async def update_reservation(
    reservation_id: uuid.UUID,
    body: ReservationUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    result = await db.execute(select(Reservation).where(Reservation.id == reservation_id))
    reservation = result.scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    if reservation.status in (ReservationStatus.checked_out, ReservationStatus.cancelled):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify completed/cancelled reservation")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(reservation, key, value)

    await db.commit()
    await db.refresh(reservation)
    return reservation


@router.post("/{reservation_id}/cancel", response_model=ReservationResponse)
async def cancel_reservation(
    reservation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    result = await db.execute(select(Reservation).where(Reservation.id == reservation_id))
    reservation = result.scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    if reservation.status != ReservationStatus.confirmed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only confirmed reservations can be cancelled")

    reservation.status = ReservationStatus.cancelled
    await db.commit()
    await db.refresh(reservation)
    return reservation
