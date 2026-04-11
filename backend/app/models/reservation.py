import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReservationStatus(str, enum.Enum):
    confirmed = "confirmed"
    checked_in = "checked_in"
    checked_out = "checked_out"
    cancelled = "cancelled"


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guest_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("guests.id"))
    room_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("room_types.id"))
    room_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=True)
    check_in_date: Mapped[date] = mapped_column(Date)
    check_out_date: Mapped[date] = mapped_column(Date)
    num_guests: Mapped[int] = mapped_column(Integer)
    status: Mapped[ReservationStatus] = mapped_column(Enum(ReservationStatus), default=ReservationStatus.confirmed)
    includes_breakfast: Mapped[bool] = mapped_column(Boolean, default=False)
    breakfast_guests: Mapped[int] = mapped_column(Integer, default=0)
    total_price: Mapped[float] = mapped_column(Numeric(10, 2))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    guest = relationship("Guest", back_populates="reservations")
    room_type = relationship("RoomType")
    room = relationship("Room")
    checkin_record = relationship("CheckInRecord", back_populates="reservation", uselist=False)
    breakfast_records = relationship("BreakfastRecord", back_populates="reservation")
