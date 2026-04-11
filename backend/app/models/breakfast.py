import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BreakfastRecord(Base):
    __tablename__ = "breakfast_records"
    __table_args__ = (
        UniqueConstraint("reservation_id", "guest_id", "date", name="uq_breakfast_per_guest_per_day"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reservation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reservations.id"))
    guest_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("guests.id"))
    date: Mapped[date] = mapped_column(Date)
    meal_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_extra_purchase: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    recorded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    reservation = relationship("Reservation", back_populates="breakfast_records")
    guest = relationship("Guest")
