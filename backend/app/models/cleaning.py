import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CleaningType(str, enum.Enum):
    checkout = "checkout"
    daily = "daily"


class ReportedVia(str, enum.Enum):
    device = "device"
    staff = "staff"


class CleaningRecord(Base):
    __tablename__ = "cleaning_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rooms.id"))
    cleaning_type: Mapped[CleaningType] = mapped_column(Enum(CleaningType))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cleaned_by_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reported_via: Mapped[ReportedVia | None] = mapped_column(Enum(ReportedVia), nullable=True)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)
    staff_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    room = relationship("Room")
