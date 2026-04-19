import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from app.database import Base


class CleaningRequestStatus(str, enum.Enum):
    pending = "pending"
    fulfilled = "fulfilled"
    cancelled = "cancelled"


class CleaningRequest(Base):
    __tablename__ = "cleaning_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rooms.id"))
    api_key_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[CleaningRequestStatus] = mapped_column(
        Enum(CleaningRequestStatus), default=CleaningRequestStatus.pending, nullable=False
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fulfilled_by_cleaning_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cleaning_records.id"), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    room = relationship("Room")

    __table_args__ = (
        Index(
            "uq_cleaning_requests_pending_room",
            "room_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
            sqlite_where=text("status = 'pending'"),
        ),
        Index("ix_cleaning_requests_status_requested_at", "status", "requested_at"),
    )
