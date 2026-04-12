import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.guest import Guest
from app.models.user import User, UserRole
from app.schemas.guest import GuestCreate, GuestResponse, GuestUpdate

router = APIRouter()


@router.get("", response_model=list[GuestResponse])
async def list_guests(
    q: str | None = Query(None, description="Search by name, phone, or ID number"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(Guest)
    if q:
        pattern = f"%{q}%"
        query = query.where(
            or_(
                Guest.first_name.ilike(pattern),
                Guest.last_name.ilike(pattern),
                Guest.phone.ilike(pattern),
                Guest.id_number.ilike(pattern),
            )
        )
    query = query.order_by(Guest.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=GuestResponse, status_code=status.HTTP_201_CREATED)
async def create_guest(
    body: GuestCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    guest = Guest(**body.model_dump())
    db.add(guest)
    await db.commit()
    await db.refresh(guest)
    return guest


@router.get("/{guest_id}", response_model=GuestResponse)
async def get_guest(
    guest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Guest).where(Guest.id == guest_id))
    guest = result.scalar_one_or_none()
    if guest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")
    return guest


@router.patch("/{guest_id}", response_model=GuestResponse)
async def update_guest(
    guest_id: uuid.UUID,
    body: GuestUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    result = await db.execute(select(Guest).where(Guest.id == guest_id))
    guest = result.scalar_one_or_none()
    if guest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(guest, key, value)

    await db.commit()
    await db.refresh(guest)
    return guest
