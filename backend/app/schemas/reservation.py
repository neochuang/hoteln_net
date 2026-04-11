import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.reservation import ReservationStatus


class ReservationCreate(BaseModel):
    guest_id: uuid.UUID
    room_type_id: uuid.UUID
    check_in_date: date
    check_out_date: date
    num_guests: int
    includes_breakfast: bool = False
    breakfast_guests: int = 0
    total_price: float
    notes: str | None = None


class ReservationUpdate(BaseModel):
    room_type_id: uuid.UUID | None = None
    check_in_date: date | None = None
    check_out_date: date | None = None
    num_guests: int | None = None
    includes_breakfast: bool | None = None
    breakfast_guests: int | None = None
    total_price: float | None = None
    notes: str | None = None


class CheckInRequest(BaseModel):
    room_id: uuid.UUID


class ReservationResponse(BaseModel):
    id: uuid.UUID
    guest_id: uuid.UUID
    room_type_id: uuid.UUID
    room_id: uuid.UUID | None
    check_in_date: date
    check_out_date: date
    num_guests: int
    status: ReservationStatus
    includes_breakfast: bool
    breakfast_guests: int
    total_price: float
    notes: str | None
    created_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
