import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.breakfast import BreakfastRecord
from app.models.reservation import Reservation, ReservationStatus
from app.models.user import User, UserRole
from app.schemas.breakfast import (
    BreakfastPurchase,
    BreakfastRecordCreate,
    BreakfastRecordResponse,
    BreakfastStats,
)

router = APIRouter()


@router.post("/record", response_model=BreakfastRecordResponse, status_code=status.HTTP_201_CREATED)
async def record_meal(
    body: BreakfastRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    reservation_id = body.reservation_id
    guest_id = body.guest_id
    today = date.today()

    # Validate reservation is checked in and includes breakfast
    result = await db.execute(select(Reservation).where(Reservation.id == reservation_id))
    reservation = result.scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    if reservation.status != ReservationStatus.checked_in:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reservation is not checked in")
    if not reservation.includes_breakfast:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reservation does not include breakfast")

    # Check duplicate
    existing = await db.execute(
        select(BreakfastRecord).where(
            BreakfastRecord.reservation_id == reservation_id,
            BreakfastRecord.guest_id == guest_id,
            BreakfastRecord.date == today,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Meal already recorded for today")

    record = BreakfastRecord(
        reservation_id=reservation_id,
        guest_id=guest_id,
        date=today,
        meal_time=datetime.now(timezone.utc),
        recorded_by=current_user.id,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.post("/purchase", response_model=BreakfastRecordResponse, status_code=status.HTTP_201_CREATED)
async def purchase_breakfast(
    body: BreakfastPurchase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    reservation_id = body.reservation_id
    guest_id = body.guest_id
    today = date.today()

    # Validate reservation is checked in
    result = await db.execute(select(Reservation).where(Reservation.id == reservation_id))
    reservation = result.scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    if reservation.status != ReservationStatus.checked_in:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reservation is not checked in")

    # Check duplicate
    existing = await db.execute(
        select(BreakfastRecord).where(
            BreakfastRecord.reservation_id == reservation_id,
            BreakfastRecord.guest_id == guest_id,
            BreakfastRecord.date == today,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Meal already recorded for today")

    record = BreakfastRecord(
        reservation_id=reservation_id,
        guest_id=guest_id,
        date=today,
        meal_time=datetime.now(timezone.utc),
        is_extra_purchase=True,
        extra_price=body.extra_price,
        recorded_by=current_user.id,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/today", response_model=list[BreakfastRecordResponse])
async def today_meals(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    today = date.today()
    result = await db.execute(
        select(BreakfastRecord)
        .where(BreakfastRecord.date == today)
        .order_by(BreakfastRecord.meal_time.desc())
    )
    return result.scalars().all()


@router.get("/stats", response_model=list[BreakfastStats])
async def meal_stats(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(
        BreakfastRecord.date,
        func.count().label("total_meals"),
        func.count().filter(BreakfastRecord.is_extra_purchase == False).label("included_meals"),  # noqa: E712
        func.count().filter(BreakfastRecord.is_extra_purchase == True).label("extra_purchases"),  # noqa: E712
        func.coalesce(func.sum(BreakfastRecord.extra_price).filter(BreakfastRecord.is_extra_purchase == True), 0).label("extra_revenue"),  # noqa: E712
    ).group_by(BreakfastRecord.date).order_by(BreakfastRecord.date.desc())

    if from_date:
        query = query.where(BreakfastRecord.date >= from_date)
    if to_date:
        query = query.where(BreakfastRecord.date <= to_date)

    result = await db.execute(query)
    rows = result.all()
    return [
        BreakfastStats(
            date=row.date,
            total_meals=row.total_meals,
            included_meals=row.included_meals,
            extra_purchases=row.extra_purchases,
            extra_revenue=float(row.extra_revenue),
        )
        for row in rows
    ]
