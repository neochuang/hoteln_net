import uuid
from datetime import date

from pydantic import BaseModel


class LookupRequest(BaseModel):
    id_number: str


class LookupReservation(BaseModel):
    id: uuid.UUID
    check_in_date: date
    check_out_date: date
    room_type_name: str
    num_guests: int
    includes_breakfast: bool
    breakfast_guests: int


class LookupResponse(BaseModel):
    guest_name: str
    reservations: list[LookupReservation]


class ConfirmRequest(BaseModel):
    reservation_id: uuid.UUID
    id_number: str


class ConfirmResponse(BaseModel):
    room_number: str
    floor: int
    room_type_name: str
    check_in_date: date
    check_out_date: date
    includes_breakfast: bool
    breakfast_info: str
    wifi_password: str
