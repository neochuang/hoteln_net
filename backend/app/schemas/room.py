import uuid

from pydantic import BaseModel

from app.models.room import RoomStatus


class RoomTypeCreate(BaseModel):
    name: str
    capacity: int
    base_price: float
    description: str | None = None


class RoomTypeResponse(BaseModel):
    id: uuid.UUID
    name: str
    capacity: int
    base_price: float
    description: str | None

    model_config = {"from_attributes": True}


class RoomCreate(BaseModel):
    room_number: str
    floor: int
    room_type_id: uuid.UUID
    notes: str | None = None


class RoomUpdate(BaseModel):
    status: RoomStatus | None = None
    notes: str | None = None


class RoomResponse(BaseModel):
    id: uuid.UUID
    room_number: str
    floor: int
    room_type_id: uuid.UUID
    status: RoomStatus
    notes: str | None
    room_type: RoomTypeResponse | None = None

    model_config = {"from_attributes": True}
