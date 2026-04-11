import uuid
from datetime import date, datetime

from pydantic import BaseModel


class BreakfastRecordCreate(BaseModel):
    reservation_id: uuid.UUID
    guest_id: uuid.UUID


class BreakfastPurchase(BaseModel):
    reservation_id: uuid.UUID
    guest_id: uuid.UUID
    extra_price: float


class BreakfastRecordResponse(BaseModel):
    id: uuid.UUID
    reservation_id: uuid.UUID
    guest_id: uuid.UUID
    date: date
    meal_time: datetime
    is_extra_purchase: bool
    extra_price: float | None
    recorded_by: uuid.UUID

    model_config = {"from_attributes": True}


class BreakfastStats(BaseModel):
    date: date
    total_meals: int
    included_meals: int
    extra_purchases: int
    extra_revenue: float
