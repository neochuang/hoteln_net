# Guest Cleaning Request API + Cleaner Role — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a device-authenticated guest cleaning-request API, a new `cleaner` user role, and a housekeeping page that shows pending requests + in-progress cleanings with start/complete actions.

**Architecture:** A new `cleaning_requests` table (pending → fulfilled/cancelled) is populated by in-room devices (`ApiKey` bound to a room). The existing `mark-cleaning` endpoint atomically fulfills any pending request for the room in the same transaction. A new `cleaner` role reuses all existing housekeeping endpoints with expanded role guards. Frontend re-uses `CleaningView.vue` refactored into a two-section `HousekeepingView.vue`.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2, pytest-asyncio, PostgreSQL 15 (prod) / SQLite aiosqlite (tests). Vue 3 (`<script setup>`), TypeScript, Vite, Pinia, Vue Router.

**Spec:** `docs/superpowers/specs/2026-04-18-guest-cleaning-request-and-cleaner-role-design.md`

---

## File Structure

**Backend — new**
- `backend/app/models/cleaning_request.py` — `CleaningRequest` model + `CleaningRequestStatus` enum + partial unique index
- `backend/app/schemas/cleaning_request.py` — `CleaningRequestCreate`, `CleaningRequestResponse`, `CleaningRequestStatus`
- `backend/alembic/versions/<hash>_add_cleaning_requests_and_cleaner_role.py` — migration
- `backend/tests/test_cleaning_requests.py` — endpoint tests

**Backend — modified**
- `backend/app/models/user.py` — add `cleaner` to `UserRole` enum
- `backend/app/models/api_key.py` — add nullable `room_id` FK column
- `backend/app/schemas/api_key.py` — expose `room_id` in request/response
- `backend/app/routers/housekeeping.py` — add 3 cleaning-request endpoints, auto-fulfill in `mark-cleaning`, expand role guards
- `backend/app/routers/api_keys.py` — accept `room_id` on create/update, validate FK exists
- `backend/app/seed.py` — seed one `cleaner` user and bind a sample API key to a room
- `backend/tests/conftest.py` — add `cleaner_user`, `cleaner_headers`, `device_key_room_bound` fixtures
- `backend/tests/test_housekeeping.py` — tests for auto-fulfill + cleaner role on existing endpoints
- `backend/tests/test_api_keys.py` — tests for `room_id` binding

**Frontend — new**
- `frontend/src/views/HousekeepingView.vue` — replaces `CleaningView.vue`; two-section page

**Frontend — modified**
- `frontend/src/types/index.ts` — add `CleaningRequest`, add `'cleaner'` to `UserRole`, extend `Room` / `ApiKey` types as needed
- `frontend/src/stores/auth.ts` — add `isCleaner`, `canAccessHousekeeping` computed helpers
- `frontend/src/router/index.ts` — add `/housekeeping` route with `meta.roles`, extend guard
- `frontend/src/App.vue` — filter sidebar items by role; hide 旅客/訂房/早餐/房間/使用者 for cleaner
- `frontend/src/views/LoginView.vue` — role-based post-login redirect
- `frontend/src/views/ApiKeysView.vue` — 綁定房間 dropdown on create/edit

**Frontend — deleted**
- `frontend/src/views/CleaningView.vue` — replaced by `HousekeepingView.vue`

---

## Task 1: Extend `UserRole` and `ApiKey` models

**Files:**
- Modify: `backend/app/models/user.py:12-15` (add `cleaner` to `UserRole`)
- Modify: `backend/app/models/api_key.py` (add `room_id` column)

- [ ] **Step 1: Run existing tests to establish baseline**

Run: `cd backend && python3 -m pytest -q`
Expected: all pass (currently 39 tests).

- [ ] **Step 2: Add `cleaner` to `UserRole`**

Replace `backend/app/models/user.py` lines 12-15 with:

```python
class UserRole(str, enum.Enum):
    admin = "admin"
    staff = "staff"
    readonly = "readonly"
    cleaner = "cleaner"
```

- [ ] **Step 3: Add `room_id` column to `ApiKey`**

Replace `backend/app/models/api_key.py` with:

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_hash: Mapped[str] = mapped_column(String(255))
    key_prefix: Mapped[str] = mapped_column(String(8))
    name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    room_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 4: Re-run existing tests — confirm no regression**

Run: `cd backend && python3 -m pytest -q`
Expected: all 39 tests still pass. (SQLite recreates schema each test from `Base.metadata`, so the new column appears automatically in the test DB.)

- [ ] **Step 5: Commit**

```bash
cd /Users/mikimoto/Developer/hoteln_net
git add backend/app/models/user.py backend/app/models/api_key.py
git commit -m "feat(models): add cleaner role and room binding on ApiKey"
```

---

## Task 2: Create `CleaningRequest` model

**Files:**
- Create: `backend/app/models/cleaning_request.py`

- [ ] **Step 1: Write the model**

Create `backend/app/models/cleaning_request.py`:

```python
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
```

- [ ] **Step 2: Smoke-check with a quick unit test**

Create `backend/tests/test_cleaning_requests.py` with just the import + smoke test (rest added later tasks):

```python
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cleaning_request import CleaningRequest, CleaningRequestStatus
from app.models.room import Room, RoomStatus, RoomType
from app.models.api_key import ApiKey


@pytest.mark.asyncio
async def test_cleaning_request_table_created(db_session: AsyncSession):
    """Smoke: model can be inserted and the partial unique index works."""
    room_type = RoomType(id=uuid.uuid4(), name="標準房", capacity=2, base_price=2000)
    room = Room(
        id=uuid.uuid4(),
        room_number="501",
        floor=5,
        room_type_id=room_type.id,
        status=RoomStatus.occupied,
    )
    api_key = ApiKey(
        id=uuid.uuid4(), key_hash="x", key_prefix="neo_test", name="dev", room_id=room.id
    )
    db_session.add_all([room_type, room, api_key])
    await db_session.commit()

    req = CleaningRequest(room_id=room.id, api_key_id=api_key.id, notes="please")
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)

    assert req.status == CleaningRequestStatus.pending
    assert req.requested_at is not None
```

- [ ] **Step 3: Run the smoke test**

Run: `cd backend && python3 -m pytest tests/test_cleaning_requests.py -v`
Expected: 1 passed.

- [ ] **Step 4: Commit**

```bash
cd /Users/mikimoto/Developer/hoteln_net
git add backend/app/models/cleaning_request.py backend/tests/test_cleaning_requests.py
git commit -m "feat(models): add CleaningRequest model with partial unique index"
```

---

## Task 3: Alembic migration for all DB changes

**Files:**
- Create: `backend/alembic/versions/20260418_add_cleaning_requests_and_cleaner_role.py`

The migration file name `20260418_...` lets Alembic order it after the existing `fd4bc78ceafe`. Generate a revision hash manually (reuse the filename prefix).

- [ ] **Step 1: Write the migration**

Create `backend/alembic/versions/20260418_add_cleaning_requests_and_cleaner_role.py`:

```python
"""add cleaning_requests table, cleaner role, api_keys.room_id

Revision ID: 20260418cleanreq
Revises: fd4bc78ceafe
Create Date: 2026-04-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260418cleanreq"
down_revision: Union[str, Sequence[str], None] = "fd4bc78ceafe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extend UserRole enum with 'cleaner' (Postgres-only). Must run outside txn.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'cleaner'")

    # 2. Add room_id to api_keys
    op.add_column(
        "api_keys",
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_api_keys_room_id",
        "api_keys",
        "rooms",
        ["room_id"],
        ["id"],
    )

    # 3. Create cleaning_requests table
    op.create_table(
        "cleaning_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rooms.id"), nullable=False),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("api_keys.id"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "fulfilled", "cancelled", name="cleaningrequeststatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "fulfilled_by_cleaning_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cleaning_records.id"),
            nullable=True,
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )

    # 4. Partial unique index: one pending request per room
    op.create_index(
        "uq_cleaning_requests_pending_room",
        "cleaning_requests",
        ["room_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_cleaning_requests_status_requested_at",
        "cleaning_requests",
        ["status", "requested_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_cleaning_requests_status_requested_at", table_name="cleaning_requests")
    op.drop_index("uq_cleaning_requests_pending_room", table_name="cleaning_requests")
    op.drop_table("cleaning_requests")
    sa.Enum(name="cleaningrequeststatus").drop(op.get_bind(), checkfirst=True)
    op.drop_constraint("fk_api_keys_room_id", "api_keys", type_="foreignkey")
    op.drop_column("api_keys", "room_id")
    # Note: cannot remove a value from a Postgres enum; cleaner role stays.
```

- [ ] **Step 2: Verify migration imports compile**

Run: `cd backend && python3 -c "import importlib.util, pathlib; spec = importlib.util.spec_from_file_location('m', pathlib.Path('alembic/versions/20260418_add_cleaning_requests_and_cleaner_role.py')); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
cd /Users/mikimoto/Developer/hoteln_net
git add backend/alembic/versions/20260418_add_cleaning_requests_and_cleaner_role.py
git commit -m "feat(db): migration for cleaning_requests, cleaner role, api_keys.room_id"
```

---

## Task 4: Pydantic schemas for `CleaningRequest`

**Files:**
- Create: `backend/app/schemas/cleaning_request.py`

- [ ] **Step 1: Write the schemas**

Create `backend/app/schemas/cleaning_request.py`:

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.cleaning_request import CleaningRequestStatus


class CleaningRequestCreate(BaseModel):
    notes: str | None = Field(None, min_length=1, max_length=500)


class CleaningRequestResponse(BaseModel):
    id: uuid.UUID
    room_id: uuid.UUID
    room_number: str
    api_key_id: uuid.UUID
    notes: str | None
    status: CleaningRequestStatus
    requested_at: datetime
    fulfilled_at: datetime | None
    fulfilled_by_cleaning_record_id: uuid.UUID | None
    cancelled_at: datetime | None
    cancelled_by_user_id: uuid.UUID | None

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Import-check**

Run: `cd backend && python3 -c "from app.schemas.cleaning_request import CleaningRequestCreate, CleaningRequestResponse; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
cd /Users/mikimoto/Developer/hoteln_net
git add backend/app/schemas/cleaning_request.py
git commit -m "feat(schemas): add CleaningRequest pydantic schemas"
```

---

## Task 5: Expand `ApiKey` schemas with `room_id`

**Files:**
- Modify: `backend/app/schemas/api_key.py`

- [ ] **Step 1: Write the updated schemas**

Replace `backend/app/schemas/api_key.py` with:

```python
import uuid
from datetime import datetime

from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    name: str
    room_id: uuid.UUID | None = None


class ApiKeyUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    room_id: uuid.UUID | None = None


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    key_prefix: str
    name: str
    is_active: bool
    room_id: uuid.UUID | None = None
    created_at: datetime
    last_used_at: datetime | None

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    key: str
```

- [ ] **Step 2: Run api_keys tests (expect all still pass since room_id is optional)**

Run: `cd backend && python3 -m pytest tests/test_api_keys.py -v`
Expected: 5 passed.

- [ ] **Step 3: Commit**

```bash
cd /Users/mikimoto/Developer/hoteln_net
git add backend/app/schemas/api_key.py
git commit -m "feat(schemas): expose room_id on ApiKey schemas"
```

---

## Task 6: Test fixtures for cleaner user and room-bound device key

**Files:**
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Add fixtures**

Append to `backend/tests/conftest.py`:

```python
@pytest_asyncio.fixture
async def cleaner_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        username="testcleaner",
        password_hash=hash_password("cleaner123"),
        full_name="Test Cleaner",
        role=UserRole.cleaner,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def cleaner_token(cleaner_user: User) -> str:
    return create_access_token(str(cleaner_user.id))


@pytest_asyncio.fixture
async def cleaner_headers(cleaner_token: str) -> dict:
    return {"Authorization": f"Bearer {cleaner_token}"}
```

- [ ] **Step 2: Verify fixtures import and tests still pass**

Run: `cd backend && python3 -m pytest -q`
Expected: 40 passed (39 existing + the cleaning_requests smoke test from Task 2).

- [ ] **Step 3: Commit**

```bash
cd /Users/mikimoto/Developer/hoteln_net
git add backend/tests/conftest.py
git commit -m "test: add cleaner user/token/headers fixtures"
```

---

## Task 7: `POST /cleaning-requests` — create guest request (TDD)

**Files:**
- Modify: `backend/app/routers/housekeeping.py`
- Modify: `backend/tests/test_cleaning_requests.py`

- [ ] **Step 1: Add a helper in the test module for seeding devices**

Append to `backend/tests/test_cleaning_requests.py`:

```python
import bcrypt
from httpx import AsyncClient

from app.models.cleaning_request import CleaningRequest, CleaningRequestStatus


async def _seed_room(db_session: AsyncSession, status: RoomStatus = RoomStatus.occupied) -> Room:
    room_type = RoomType(id=uuid.uuid4(), name="標準房", capacity=2, base_price=2000)
    room = Room(
        id=uuid.uuid4(),
        room_number="601",
        floor=6,
        room_type_id=room_type.id,
        status=status,
    )
    db_session.add_all([room_type, room])
    await db_session.commit()
    return room


async def _seed_device_key(db_session: AsyncSession, room: Room | None) -> tuple[ApiKey, str]:
    raw = "neo_device_req_test_xxx"
    api_key = ApiKey(
        id=uuid.uuid4(),
        key_hash=bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode(),
        key_prefix=raw[:8],
        name="Room Device",
        is_active=True,
        room_id=room.id if room else None,
    )
    db_session.add(api_key)
    await db_session.commit()
    return api_key, raw
```

- [ ] **Step 2: Write the failing happy-path test**

Append to `backend/tests/test_cleaning_requests.py`:

```python
@pytest.mark.asyncio
async def test_create_cleaning_request_happy_path(
    client: AsyncClient, db_session: AsyncSession
):
    room = await _seed_room(db_session, RoomStatus.occupied)
    _, raw = await _seed_device_key(db_session, room)

    res = await client.post(
        "/api/housekeeping/cleaning-requests",
        headers={"X-API-Key": raw},
        json={"notes": "toilet paper"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "pending"
    assert data["room_number"] == room.room_number
    assert data["notes"] == "toilet paper"
```

- [ ] **Step 3: Run test — expect failure (endpoint does not exist)**

Run: `cd backend && python3 -m pytest tests/test_cleaning_requests.py::test_create_cleaning_request_happy_path -v`
Expected: FAIL with 404 (endpoint not found).

- [ ] **Step 4: Add imports to `housekeeping.py`**

In `backend/app/routers/housekeeping.py`, extend the imports block at the top:

```python
from sqlalchemy.exc import IntegrityError

from app.models.cleaning_request import CleaningRequest, CleaningRequestStatus
from app.schemas.cleaning_request import CleaningRequestCreate, CleaningRequestResponse
```

- [ ] **Step 5: Add a small helper to convert an ORM `CleaningRequest` into its response**

Append near the other helpers in `backend/app/routers/housekeeping.py`:

```python
async def _cleaning_request_response(
    db: AsyncSession, req: CleaningRequest
) -> CleaningRequestResponse:
    # room_number is needed in the response; fetch via the FK
    result = await db.execute(select(Room.room_number).where(Room.id == req.room_id))
    room_number = result.scalar_one()
    return CleaningRequestResponse(
        id=req.id,
        room_id=req.room_id,
        room_number=room_number,
        api_key_id=req.api_key_id,
        notes=req.notes,
        status=req.status,
        requested_at=req.requested_at,
        fulfilled_at=req.fulfilled_at,
        fulfilled_by_cleaning_record_id=req.fulfilled_by_cleaning_record_id,
        cancelled_at=req.cancelled_at,
        cancelled_by_user_id=req.cancelled_by_user_id,
    )
```

- [ ] **Step 6: Add the POST endpoint**

Append to `backend/app/routers/housekeeping.py`:

```python
@router.post("/cleaning-requests", response_model=CleaningRequestResponse)
async def create_cleaning_request(
    body: CleaningRequestCreate,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey = Depends(get_api_key),
):
    if api_key.room_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device not bound to a room",
        )

    result = await db.execute(select(Room).where(Room.id == api_key.room_id))
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device's bound room no longer exists",
        )
    if room.status != RoomStatus.occupied:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room is not occupied",
        )

    req = CleaningRequest(
        room_id=room.id,
        api_key_id=api_key.id,
        notes=body.notes,
    )
    db.add(req)
    try:
        await db.commit()
    except IntegrityError:
        # Partial unique index violation → an existing pending request is present
        await db.rollback()
        existing = await db.execute(
            select(CleaningRequest).where(
                CleaningRequest.room_id == room.id,
                CleaningRequest.status == CleaningRequestStatus.pending,
            )
        )
        req = existing.scalar_one()
    else:
        await db.refresh(req)

    return await _cleaning_request_response(db, req)
```

- [ ] **Step 7: Run the happy-path test — expect pass**

Run: `cd backend && python3 -m pytest tests/test_cleaning_requests.py::test_create_cleaning_request_happy_path -v`
Expected: PASS.

- [ ] **Step 8: Add the failure-mode tests**

Append to `backend/tests/test_cleaning_requests.py`:

```python
@pytest.mark.asyncio
async def test_create_cleaning_request_unbound_device_rejected(
    client: AsyncClient, db_session: AsyncSession
):
    _, raw = await _seed_device_key(db_session, room=None)
    res = await client.post(
        "/api/housekeeping/cleaning-requests",
        headers={"X-API-Key": raw},
        json={},
    )
    assert res.status_code == 400
    assert "not bound" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_cleaning_request_non_occupied_rejected(
    client: AsyncClient, db_session: AsyncSession
):
    room = await _seed_room(db_session, RoomStatus.available)
    _, raw = await _seed_device_key(db_session, room)
    res = await client.post(
        "/api/housekeeping/cleaning-requests",
        headers={"X-API-Key": raw},
        json={},
    )
    assert res.status_code == 400
    assert "not occupied" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_cleaning_request_idempotent_when_pending_exists(
    client: AsyncClient, db_session: AsyncSession
):
    room = await _seed_room(db_session, RoomStatus.occupied)
    _, raw = await _seed_device_key(db_session, room)

    res1 = await client.post(
        "/api/housekeeping/cleaning-requests",
        headers={"X-API-Key": raw},
        json={"notes": "first"},
    )
    res2 = await client.post(
        "/api/housekeeping/cleaning-requests",
        headers={"X-API-Key": raw},
        json={"notes": "second"},
    )
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json()["id"] == res2.json()["id"]
    # second call must NOT overwrite the first notes
    assert res2.json()["notes"] == "first"
```

- [ ] **Step 9: Run all cleaning_requests tests — expect pass**

Run: `cd backend && python3 -m pytest tests/test_cleaning_requests.py -v`
Expected: 4 passed.

- [ ] **Step 10: Commit**

```bash
cd /Users/mikimoto/Developer/hoteln_net
git add backend/app/routers/housekeeping.py backend/tests/test_cleaning_requests.py
git commit -m "feat(api): POST /housekeeping/cleaning-requests (device-auth, idempotent)"
```

---

## Task 8: `GET /cleaning-requests` — list requests (TDD)

**Files:**
- Modify: `backend/app/routers/housekeeping.py`
- Modify: `backend/tests/test_cleaning_requests.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_cleaning_requests.py`:

```python
@pytest.mark.asyncio
async def test_list_cleaning_requests_default_pending(
    client: AsyncClient, db_session: AsyncSession, staff_headers
):
    room = await _seed_room(db_session, RoomStatus.occupied)
    _, raw = await _seed_device_key(db_session, room)
    # create one pending
    await client.post(
        "/api/housekeeping/cleaning-requests",
        headers={"X-API-Key": raw},
        json={"notes": "hi"},
    )
    res = await client.get("/api/housekeeping/cleaning-requests", headers=staff_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_list_cleaning_requests_cleaner_allowed(
    client: AsyncClient, db_session: AsyncSession, cleaner_headers
):
    res = await client.get("/api/housekeeping/cleaning-requests", headers=cleaner_headers)
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_list_cleaning_requests_readonly_denied(
    client: AsyncClient, db_session: AsyncSession
):
    from app.models.user import User, UserRole
    from app.services.auth import create_access_token, hash_password

    ro = User(
        id=uuid.uuid4(),
        username="ro",
        password_hash=hash_password("x"),
        full_name="RO",
        role=UserRole.readonly,
    )
    db_session.add(ro)
    await db_session.commit()
    token = create_access_token(str(ro.id))

    res = await client.get(
        "/api/housekeeping/cleaning-requests",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
```

- [ ] **Step 2: Run tests — expect failures**

Run: `cd backend && python3 -m pytest tests/test_cleaning_requests.py -k list -v`
Expected: 3 failures (endpoint not found / 404).

- [ ] **Step 3: Implement the endpoint**

Append to `backend/app/routers/housekeeping.py`:

```python
@router.get("/cleaning-requests", response_model=list[CleaningRequestResponse])
async def list_cleaning_requests(
    status_filter: CleaningRequestStatus | None = Query(CleaningRequestStatus.pending, alias="status"),
    room_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin, UserRole.staff, UserRole.cleaner)),
):
    query = select(CleaningRequest).order_by(CleaningRequest.requested_at.desc())
    if status_filter is not None:
        query = query.where(CleaningRequest.status == status_filter)
    if room_id is not None:
        query = query.where(CleaningRequest.room_id == room_id)

    result = await db.execute(query)
    items = result.scalars().all()
    return [await _cleaning_request_response(db, r) for r in items]
```

Also allow the special `status=all` shorthand — update signature to parse:

Replace the query-parameter line with this two-step pattern:

```python
@router.get("/cleaning-requests", response_model=list[CleaningRequestResponse])
async def list_cleaning_requests(
    status: str | None = Query("pending"),
    room_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin, UserRole.staff, UserRole.cleaner)),
):
    query = select(CleaningRequest).order_by(CleaningRequest.requested_at.desc())
    if status and status != "all":
        try:
            status_enum = CleaningRequestStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        query = query.where(CleaningRequest.status == status_enum)
    if room_id is not None:
        query = query.where(CleaningRequest.room_id == room_id)

    result = await db.execute(query)
    items = result.scalars().all()
    return [await _cleaning_request_response(db, r) for r in items]
```

- [ ] **Step 4: Run tests — expect pass**

Run: `cd backend && python3 -m pytest tests/test_cleaning_requests.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/mikimoto/Developer/hoteln_net
git add backend/app/routers/housekeeping.py backend/tests/test_cleaning_requests.py
git commit -m "feat(api): GET /housekeeping/cleaning-requests with status/room filters"
```

---

## Task 9: `POST /cleaning-requests/{id}/cancel` (TDD)

**Files:**
- Modify: `backend/app/routers/housekeeping.py`
- Modify: `backend/tests/test_cleaning_requests.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_cleaning_requests.py`:

```python
@pytest.mark.asyncio
async def test_cancel_pending_request_by_staff(
    client: AsyncClient, db_session: AsyncSession, staff_headers, staff_user
):
    room = await _seed_room(db_session, RoomStatus.occupied)
    _, raw = await _seed_device_key(db_session, room)
    created = await client.post(
        "/api/housekeeping/cleaning-requests",
        headers={"X-API-Key": raw},
        json={},
    )
    req_id = created.json()["id"]

    res = await client.post(
        f"/api/housekeeping/cleaning-requests/{req_id}/cancel",
        headers=staff_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "cancelled"
    assert data["cancelled_by_user_id"] == str(staff_user.id)
    assert data["cancelled_at"] is not None


@pytest.mark.asyncio
async def test_cancel_non_pending_returns_409(
    client: AsyncClient, db_session: AsyncSession, staff_headers
):
    # Insert a request directly in 'cancelled' state
    room = await _seed_room(db_session, RoomStatus.occupied)
    api_key, _ = await _seed_device_key(db_session, room)
    req = CleaningRequest(
        room_id=room.id,
        api_key_id=api_key.id,
        status=CleaningRequestStatus.cancelled,
        cancelled_at=datetime.now(timezone.utc),
    )
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)

    res = await client.post(
        f"/api/housekeeping/cleaning-requests/{req.id}/cancel",
        headers=staff_headers,
    )
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_cancel_missing_id_returns_404(
    client: AsyncClient, db_session: AsyncSession, staff_headers
):
    res = await client.post(
        f"/api/housekeeping/cleaning-requests/{uuid.uuid4()}/cancel",
        headers=staff_headers,
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_cancel_rejected_for_cleaner(
    client: AsyncClient, db_session: AsyncSession, cleaner_headers
):
    room = await _seed_room(db_session, RoomStatus.occupied)
    api_key, _ = await _seed_device_key(db_session, room)
    req = CleaningRequest(room_id=room.id, api_key_id=api_key.id)
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)

    res = await client.post(
        f"/api/housekeeping/cleaning-requests/{req.id}/cancel",
        headers=cleaner_headers,
    )
    assert res.status_code == 403
```

- [ ] **Step 2: Run tests — expect failures**

Run: `cd backend && python3 -m pytest tests/test_cleaning_requests.py -k cancel -v`
Expected: failures (endpoint not found).

- [ ] **Step 3: Implement the cancel endpoint**

Append to `backend/app/routers/housekeeping.py`:

```python
@router.post("/cleaning-requests/{request_id}/cancel", response_model=CleaningRequestResponse)
async def cancel_cleaning_request(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    stmt = (
        update(CleaningRequest)
        .where(
            CleaningRequest.id == request_id,
            CleaningRequest.status == CleaningRequestStatus.pending,
        )
        .values(
            status=CleaningRequestStatus.cancelled,
            cancelled_at=datetime.now(timezone.utc),
            cancelled_by_user_id=current_user.id,
        )
        .returning(CleaningRequest)
    )
    req = (await db.execute(stmt)).scalar_one_or_none()

    if req is None:
        # Distinguish missing vs non-pending
        existing = await db.execute(select(CleaningRequest).where(CleaningRequest.id == request_id))
        found = existing.scalar_one_or_none()
        if found is None:
            raise HTTPException(status_code=404, detail="Cleaning request not found")
        raise HTTPException(status_code=409, detail="Cleaning request no longer pending")

    await db.commit()
    return await _cleaning_request_response(db, req)
```

- [ ] **Step 4: Run tests — expect pass**

Run: `cd backend && python3 -m pytest tests/test_cleaning_requests.py -k cancel -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/mikimoto/Developer/hoteln_net
git add backend/app/routers/housekeeping.py backend/tests/test_cleaning_requests.py
git commit -m "feat(api): POST /housekeeping/cleaning-requests/{id}/cancel"
```

---

## Task 10: Auto-fulfill pending request on `mark-cleaning` (TDD)

**Files:**
- Modify: `backend/app/routers/housekeeping.py`
- Modify: `backend/tests/test_housekeeping.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_housekeeping.py`:

```python
from app.models.cleaning_request import CleaningRequest, CleaningRequestStatus


@pytest.mark.asyncio
async def test_mark_cleaning_auto_fulfills_pending_request(
    client: AsyncClient, db_session: AsyncSession, admin_user, admin_headers
):
    room_type, room = await seed_room(db_session)
    _ = await seed_checked_in_reservation(db_session, room, room_type, admin_user.id)
    room.status = RoomStatus.occupied
    await db_session.commit()

    api_key = ApiKey(
        id=uuid.uuid4(),
        key_hash="x",
        key_prefix="neo_test",
        name="dev",
        is_active=True,
        room_id=room.id,
    )
    db_session.add(api_key)
    req = CleaningRequest(
        id=uuid.uuid4(),
        room_id=room.id,
        api_key_id=api_key.id,
        notes="pls",
    )
    db_session.add(req)
    await db_session.commit()

    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/mark-cleaning",
        headers=admin_headers,
    )
    assert res.status_code == 200
    record_id = res.json()["cleaning_record"]["id"]

    await db_session.refresh(req)
    assert req.status == CleaningRequestStatus.fulfilled
    assert str(req.fulfilled_by_cleaning_record_id) == record_id
    assert req.fulfilled_at is not None


@pytest.mark.asyncio
async def test_mark_cleaning_without_request_still_works(
    client: AsyncClient, db_session: AsyncSession, admin_user, admin_headers
):
    """Existing behaviour preserved: no request → still creates record, no error."""
    room_type, room = await seed_room(db_session)
    _ = await seed_checked_in_reservation(db_session, room, room_type, admin_user.id)
    room.status = RoomStatus.occupied
    await db_session.commit()

    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/mark-cleaning",
        headers=admin_headers,
    )
    assert res.status_code == 200
```

- [ ] **Step 2: Run — first test should fail (auto-fulfill not implemented), second should pass**

Run: `cd backend && python3 -m pytest tests/test_housekeeping.py -k mark_cleaning -v`
Expected: `test_mark_cleaning_auto_fulfills_pending_request` fails; others pass.

- [ ] **Step 3: Implement auto-fulfill in `mark_cleaning`**

In `backend/app/routers/housekeeping.py`, replace the body of `mark_cleaning` so that after the record is flushed and its id is available, a fulfillment UPDATE is attempted in the same transaction:

```python
@router.post("/rooms/{room_number}/mark-cleaning", response_model=MarkCleaningResponse)
async def mark_cleaning(
    room_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.staff, UserRole.cleaner)),
):
    result = await db.execute(select(Room).where(Room.room_number == room_number))
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.status != RoomStatus.occupied:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is not occupied")

    room.status = RoomStatus.cleaning

    record = CleaningRecord(
        room_id=room.id,
        cleaning_type=CleaningType.daily,
    )
    db.add(record)
    await db.flush()  # ensures record.id is assigned

    # Atomically fulfill any pending request for this room
    await db.execute(
        update(CleaningRequest)
        .where(
            CleaningRequest.room_id == room.id,
            CleaningRequest.status == CleaningRequestStatus.pending,
        )
        .values(
            status=CleaningRequestStatus.fulfilled,
            fulfilled_at=datetime.now(timezone.utc),
            fulfilled_by_cleaning_record_id=record.id,
        )
    )

    await db.commit()
    await db.refresh(room)
    await db.refresh(record)

    return MarkCleaningResponse(
        room_id=room.id,
        room_number=room.room_number,
        status=room.status.value,
        cleaning_record=CleaningRecordResponse.model_validate(record),
    )
```

- [ ] **Step 4: Run full housekeeping test file — expect all pass**

Run: `cd backend && python3 -m pytest tests/test_housekeeping.py -v`
Expected: all housekeeping tests pass (existing 14 + the 2 new).

- [ ] **Step 5: Commit**

```bash
cd /Users/mikimoto/Developer/hoteln_net
git add backend/app/routers/housekeeping.py backend/tests/test_housekeeping.py
git commit -m "feat(api): mark-cleaning atomically fulfills pending request"
```

---

## Task 11: Expand role guards on existing housekeeping endpoints (TDD)

**Files:**
- Modify: `backend/app/routers/housekeeping.py`
- Modify: `backend/tests/test_housekeeping.py`

- [ ] **Step 1: Write failing tests — cleaner should be able to call each endpoint**

Append to `backend/tests/test_housekeeping.py`:

```python
@pytest.mark.asyncio
async def test_cleaner_can_mark_cleaning(
    client: AsyncClient, db_session: AsyncSession, admin_user, cleaner_headers
):
    room_type, room = await seed_room(db_session)
    _ = await seed_checked_in_reservation(db_session, room, room_type, admin_user.id)
    room.status = RoomStatus.occupied
    await db_session.commit()

    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/mark-cleaning",
        headers=cleaner_headers,
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_cleaner_can_clean_complete(
    client: AsyncClient, db_session: AsyncSession, cleaner_headers
):
    room_type, room = await seed_room(db_session)
    room.status = RoomStatus.cleaning
    await db_session.commit()
    record = CleaningRecord(
        id=uuid.uuid4(), room_id=room.id, cleaning_type=CleaningType.checkout
    )
    db_session.add(record)
    await db_session.commit()

    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/clean-complete",
        headers=cleaner_headers,
        json={"cleaned_by_name": "清潔阿姨"},
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_cleaner_can_view_cleaning_status(
    client: AsyncClient, db_session: AsyncSession, cleaner_headers
):
    res = await client.get("/api/housekeeping/rooms/cleaning-status", headers=cleaner_headers)
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_cleaner_can_list_cleaning_records(
    client: AsyncClient, db_session: AsyncSession, cleaner_headers
):
    res = await client.get("/api/housekeeping/cleaning-records", headers=cleaner_headers)
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_cleaner_cannot_access_users(
    client: AsyncClient, db_session: AsyncSession, cleaner_headers
):
    res = await client.get("/api/users", headers=cleaner_headers)
    assert res.status_code == 403
```

- [ ] **Step 2: Run — mark-cleaning already updated in Task 10; the other three endpoints will 403**

Run: `cd backend && python3 -m pytest tests/test_housekeeping.py -k cleaner -v`
Expected: `test_cleaner_can_mark_cleaning` and `test_cleaner_cannot_access_users` pass; the three others fail with 403.

- [ ] **Step 3: Update role guards**

In `backend/app/routers/housekeeping.py`:

- `clean_complete` already uses `get_device_or_user` (no role check on the user branch) — keep.
- `cleaning_status` currently uses `get_device_or_user` — keep (devices + users, cleaner implicitly allowed).
- `list_cleaning_records` currently uses `require_role(UserRole.admin, UserRole.staff)` — change to include cleaner.

Change in `list_cleaning_records`:

```python
    _: User = Depends(require_role(UserRole.admin, UserRole.staff, UserRole.cleaner)),
```

For `clean_complete` — the existing `get_device_or_user` returns a `User` for any role; since the endpoint doesn't restrict user roles, cleaner will already work. Double-check via the test.

- [ ] **Step 4: Run — expect all pass**

Run: `cd backend && python3 -m pytest tests/test_housekeeping.py -k cleaner -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/mikimoto/Developer/hoteln_net
git add backend/app/routers/housekeeping.py backend/tests/test_housekeeping.py
git commit -m "feat(auth): allow cleaner role to access housekeeping endpoints"
```

---

## Task 12: API Keys router — accept and validate `room_id` (TDD)

**Files:**
- Modify: `backend/app/routers/api_keys.py`
- Modify: `backend/tests/test_api_keys.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_api_keys.py` (peek at the file first for its existing fixture conventions — follow the existing room seed pattern):

```python
@pytest.mark.asyncio
async def test_create_api_key_with_room_binding(
    client: AsyncClient, db_session: AsyncSession, admin_headers
):
    from app.models.room import Room, RoomStatus, RoomType

    room_type = RoomType(id=uuid.uuid4(), name="標準房", capacity=2, base_price=2000)
    room = Room(
        id=uuid.uuid4(),
        room_number="701",
        floor=7,
        room_type_id=room_type.id,
        status=RoomStatus.available,
    )
    db_session.add_all([room_type, room])
    await db_session.commit()

    res = await client.post(
        "/api/api-keys",
        headers=admin_headers,
        json={"name": "Room 701 tablet", "room_id": str(room.id)},
    )
    assert res.status_code == 201
    assert res.json()["room_id"] == str(room.id)


@pytest.mark.asyncio
async def test_create_api_key_unknown_room_id_rejected(
    client: AsyncClient, db_session: AsyncSession, admin_headers
):
    res = await client.post(
        "/api/api-keys",
        headers=admin_headers,
        json={"name": "ghost", "room_id": str(uuid.uuid4())},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_patch_api_key_sets_room_id(
    client: AsyncClient, db_session: AsyncSession, admin_headers
):
    from app.models.room import Room, RoomStatus, RoomType

    room_type = RoomType(id=uuid.uuid4(), name="標準房", capacity=2, base_price=2000)
    room = Room(
        id=uuid.uuid4(),
        room_number="702",
        floor=7,
        room_type_id=room_type.id,
        status=RoomStatus.available,
    )
    db_session.add_all([room_type, room])
    await db_session.commit()

    created = await client.post(
        "/api/api-keys",
        headers=admin_headers,
        json={"name": "later bind"},
    )
    key_id = created.json()["id"]
    res = await client.patch(
        f"/api/api-keys/{key_id}",
        headers=admin_headers,
        json={"room_id": str(room.id)},
    )
    assert res.status_code == 200
    assert res.json()["room_id"] == str(room.id)
```

- [ ] **Step 2: Run — expect failures**

Run: `cd backend && python3 -m pytest tests/test_api_keys.py -k room -v`
Expected: failures (room_id not persisted / validated).

- [ ] **Step 3: Update the router**

In `backend/app/routers/api_keys.py`, add a helper and update both `create_api_key` and `update_api_key`:

```python
from app.models.room import Room


async def _assert_room_exists(db: AsyncSession, room_id: uuid.UUID | None) -> None:
    if room_id is None:
        return
    result = await db.execute(select(Room).where(Room.id == room_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="Room not found")
```

Modify `create_api_key` to accept and persist `room_id`:

```python
@router.post("", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    await _assert_room_exists(db, body.room_id)

    raw_key = API_KEY_PREFIX + secrets.token_hex(24)
    key_hash = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()

    api_key = ApiKey(
        key_hash=key_hash,
        key_prefix=raw_key[:8],
        name=body.name,
        room_id=body.room_id,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return ApiKeyCreatedResponse(
        id=api_key.id,
        key=raw_key,
        key_prefix=api_key.key_prefix,
        name=api_key.name,
        is_active=api_key.is_active,
        room_id=api_key.room_id,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
    )
```

Modify `update_api_key` — add the room-exists guard before applying the patch:

```python
@router.patch("/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    key_id: uuid.UUID,
    body: ApiKeyUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    updates = body.model_dump(exclude_unset=True)
    if "room_id" in updates:
        await _assert_room_exists(db, updates["room_id"])
    for key, value in updates.items():
        setattr(api_key, key, value)

    await db.commit()
    await db.refresh(api_key)
    return api_key
```

- [ ] **Step 4: Run all api_keys tests**

Run: `cd backend && python3 -m pytest tests/test_api_keys.py -v`
Expected: all pass (existing 5 + new 3).

- [ ] **Step 5: Commit**

```bash
cd /Users/mikimoto/Developer/hoteln_net
git add backend/app/routers/api_keys.py backend/tests/test_api_keys.py
git commit -m "feat(api): bind ApiKey to a room via room_id on create/patch"
```

---

## Task 13: Seed script — cleaner user + room-bound device

**Files:**
- Modify: `backend/app/seed.py`

- [ ] **Step 1: Inspect the current seed to know where to insert**

Run: `head -50 /Users/mikimoto/Developer/hoteln_net/backend/app/seed.py`
Expected: see the current seed output to know the pattern (user insert, room insert, etc.). Follow the same style.

- [ ] **Step 2: Add seed data for a cleaner user and a bound API key**

Append the following into `seed.py` in the appropriate section (right after existing users are seeded; right after at least one room is seeded). Reuse existing helpers in that file:

```python
# Cleaner user
cleaner = User(
    username="cleaner1",
    password_hash=hash_password("cleaner1"),
    full_name="清潔人員一號",
    role=UserRole.cleaner,
    is_active=True,
)
session.add(cleaner)
await session.flush()

# Pick the first room to bind a demo device to
first_room = (await session.execute(select(Room).limit(1))).scalar_one_or_none()
if first_room is not None:
    raw = "neo_device_" + secrets.token_hex(8)
    device = ApiKey(
        key_hash=bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode(),
        key_prefix=raw[:8],
        name=f"Room {first_room.room_number} tablet",
        is_active=True,
        room_id=first_room.id,
    )
    session.add(device)
    print(f"[seed] Room-bound device API key for room {first_room.room_number}: {raw}")
```

Make sure the imports at the top of `seed.py` include `secrets`, `bcrypt`, `UserRole`, `Room`, `ApiKey`, `select`, `hash_password` — add any that are missing.

- [ ] **Step 3: Run the seed script against a dev DB (optional — skip if no dev DB is set up right now)**

Run: `cd backend && python3 -m app.seed || true`
Expected: prints the demo device key line (or any dev-DB-related error if the DB isn't up, which is fine for CI).

- [ ] **Step 4: Commit**

```bash
cd /Users/mikimoto/Developer/hoteln_net
git add backend/app/seed.py
git commit -m "feat(seed): add cleaner user and room-bound device API key"
```

---

## Task 14: Frontend — types and auth-store helpers

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/stores/auth.ts`

- [ ] **Step 1: Inspect the current types file**

Run: `cat /Users/mikimoto/Developer/hoteln_net/frontend/src/types/index.ts`
Expected: see current `User`, `Room`, `CleaningRecord`, `UserRole` definitions so the new types match style.

- [ ] **Step 2: Extend `UserRole` and add `CleaningRequest`**

In `frontend/src/types/index.ts`, update the `UserRole` literal type to include `'cleaner'` and add:

```ts
export interface CleaningRequest {
  id: string
  room_id: string
  room_number: string
  api_key_id: string
  notes: string | null
  status: 'pending' | 'fulfilled' | 'cancelled'
  requested_at: string
  fulfilled_at: string | null
  fulfilled_by_cleaning_record_id: string | null
  cancelled_at: string | null
  cancelled_by_user_id: string | null
}
```

Also extend the existing `ApiKey` interface (if present) with `room_id: string | null`.

- [ ] **Step 3: Add auth-store helpers**

In `frontend/src/stores/auth.ts`, add computed properties and export them:

```ts
const isCleaner = computed(() => user.value?.role === 'cleaner')
const canAccessHousekeeping = computed(
  () => user.value?.role === 'admin' || user.value?.role === 'staff' || user.value?.role === 'cleaner'
)
const canAccessAdminArea = computed(
  () => user.value?.role === 'admin' || user.value?.role === 'staff'
)

return {
  user, isLoggedIn, isAdmin, canEdit,
  isCleaner, canAccessHousekeeping, canAccessAdminArea,
  login, fetchUser, logout, init,
}
```

- [ ] **Step 4: Typecheck**

Run: `cd frontend && npm run build`
Expected: build succeeds (or at worst, only template-level issues to fix in later tasks — types should compile here).

- [ ] **Step 5: Commit**

```bash
cd /Users/mikimoto/Developer/hoteln_net
git add frontend/src/types/index.ts frontend/src/stores/auth.ts
git commit -m "feat(frontend): add cleaner role + CleaningRequest type + auth helpers"
```

---

## Task 15: Frontend — router roles-aware guard + `/housekeeping` route

**Files:**
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: Update the guard and add the route**

Replace the router definition with:

```ts
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

type RouteMeta = {
  public?: boolean
  adminOnly?: boolean
  roles?: Array<'admin' | 'staff' | 'cleaner' | 'readonly'>
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'Login', component: () => import('../views/LoginView.vue'), meta: { public: true } as RouteMeta },
    { path: '/', name: 'Dashboard', component: () => import('../views/DashboardView.vue'), meta: { roles: ['admin', 'staff', 'readonly'] } as RouteMeta },
    { path: '/guests', name: 'Guests', component: () => import('../views/GuestsView.vue'), meta: { roles: ['admin', 'staff', 'readonly'] } as RouteMeta },
    { path: '/rooms', name: 'Rooms', component: () => import('../views/RoomsView.vue'), meta: { roles: ['admin', 'staff', 'readonly'] } as RouteMeta },
    { path: '/reservations', name: 'Reservations', component: () => import('../views/ReservationsView.vue'), meta: { roles: ['admin', 'staff', 'readonly'] } as RouteMeta },
    { path: '/checkin', name: 'CheckIn', component: () => import('../views/CheckInView.vue'), meta: { roles: ['admin', 'staff'] } as RouteMeta },
    { path: '/breakfast', name: 'Breakfast', component: () => import('../views/BreakfastView.vue'), meta: { roles: ['admin', 'staff'] } as RouteMeta },
    { path: '/users', name: 'Users', component: () => import('../views/UsersView.vue'), meta: { adminOnly: true } as RouteMeta },
    { path: '/housekeeping', name: 'Housekeeping', component: () => import('../views/HousekeepingView.vue'), meta: { roles: ['admin', 'staff', 'cleaner'] } as RouteMeta },
    { path: '/cleaning', redirect: '/housekeeping' },
    { path: '/api-keys', name: 'ApiKeys', component: () => import('../views/ApiKeysView.vue'), meta: { adminOnly: true } as RouteMeta },
    { path: '/self-checkin', name: 'SelfCheckIn', component: () => import('../views/SelfCheckInView.vue'), meta: { public: true } as RouteMeta },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  const meta = to.meta as RouteMeta
  if (!auth.isLoggedIn && !meta.public) {
    return '/login'
  }
  if (meta.adminOnly && !auth.isAdmin) {
    return auth.isCleaner ? '/housekeeping' : '/'
  }
  if (meta.roles && auth.user && !meta.roles.includes(auth.user.role)) {
    return auth.isCleaner ? '/housekeeping' : '/'
  }
})

export default router
```

- [ ] **Step 2: Typecheck build**

Run: `cd frontend && npm run build`
Expected: build fails only because `HousekeepingView.vue` doesn't exist yet. That's expected; the next task adds it. If any other error appears, fix inline.

(It's acceptable to keep this task's commit at a temporarily-broken build state only if Task 16 lands in the same PR. To avoid a broken build in history, either merge Task 16 into Task 15's commit, or create an empty stub `HousekeepingView.vue` here; prefer the stub.)

- [ ] **Step 3: Create a minimal stub `HousekeepingView.vue` to keep the build green**

Create `frontend/src/views/HousekeepingView.vue` with:

```vue
<template>
  <div>房務清潔 (loading…)</div>
</template>
```

- [ ] **Step 4: Build again**

Run: `cd frontend && npm run build`
Expected: success.

- [ ] **Step 5: Commit**

```bash
cd /Users/mikimoto/Developer/hoteln_net
git add frontend/src/router/index.ts frontend/src/views/HousekeepingView.vue
git commit -m "feat(frontend): add /housekeeping route, role-aware router guard, stub view"
```

---

## Task 16: Frontend — `HousekeepingView.vue` two-section page

**Files:**
- Rewrite: `frontend/src/views/HousekeepingView.vue`
- Delete: `frontend/src/views/CleaningView.vue`

- [ ] **Step 1: Replace the stub with the real view**

Overwrite `frontend/src/views/HousekeepingView.vue` with:

```vue
<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import api from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { CleaningRequest } from '../types'

interface CleaningStatusRoom {
  room_id: string
  room_number: string
  floor: number
  room_type_name: string
  cleaning_type: 'daily' | 'checkout'
  started_at: string
}

const auth = useAuthStore()
const pending = ref<CleaningRequest[]>([])
const inProgress = ref<CleaningStatusRoom[]>([])
const completeTarget = ref<CleaningStatusRoom | null>(null)
const cleanedByName = ref('')
const completeNotes = ref('')
let timer: number | undefined

async function load() {
  const [pRes, iRes] = await Promise.all([
    api.get('/housekeeping/cleaning-requests', { params: { status: 'pending' } }),
    api.get('/housekeeping/rooms/cleaning-status'),
  ])
  pending.value = pRes.data
  inProgress.value = iRes.data
}

async function startCleaning(roomNumber: string) {
  await api.post(`/housekeeping/rooms/${roomNumber}/mark-cleaning`)
  await load()
}

function openCompleteModal(room: CleaningStatusRoom) {
  completeTarget.value = room
  cleanedByName.value = auth.user?.full_name ?? ''
  completeNotes.value = ''
}

async function submitComplete() {
  if (!completeTarget.value) return
  await api.post(`/housekeeping/rooms/${completeTarget.value.room_number}/clean-complete`, {
    cleaned_by_name: cleanedByName.value || null,
    notes: completeNotes.value || null,
  })
  completeTarget.value = null
  await load()
}

function formatRelative(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const mins = Math.round(diffMs / 60000)
  if (mins < 1) return '剛剛'
  if (mins < 60) return `${mins} 分鐘前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} 小時前`
  return new Date(iso).toLocaleString('zh-TW')
}

onMounted(() => {
  load()
  timer = window.setInterval(load, 30000)
})
onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div>
    <div class="page-header">
      <h2>房務清潔</h2>
      <button @click="load">重新整理</button>
    </div>

    <section style="margin-bottom: 24px">
      <h3>待清潔請求 ({{ pending.length }})</h3>
      <table>
        <thead>
          <tr>
            <th>房號</th>
            <th>請求時間</th>
            <th>備註</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in pending" :key="p.id">
            <td>{{ p.room_number }}</td>
            <td>{{ formatRelative(p.requested_at) }}</td>
            <td>{{ p.notes || '-' }}</td>
            <td>
              <button @click="startCleaning(p.room_number)">啟動清潔</button>
            </td>
          </tr>
          <tr v-if="pending.length === 0">
            <td colspan="4" style="text-align:center;color:#888">目前沒有待清潔請求</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section>
      <h3>進行中 ({{ inProgress.length }})</h3>
      <table>
        <thead>
          <tr>
            <th>房號</th>
            <th>類型</th>
            <th>開始時間</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in inProgress" :key="r.room_id">
            <td>{{ r.room_number }}</td>
            <td>{{ r.cleaning_type === 'checkout' ? '退房清潔' : '每日清潔' }}</td>
            <td>{{ formatRelative(r.started_at) }}</td>
            <td>
              <button @click="openCompleteModal(r)">完成清潔</button>
            </td>
          </tr>
          <tr v-if="inProgress.length === 0">
            <td colspan="4" style="text-align:center;color:#888">沒有進行中的清潔</td>
          </tr>
        </tbody>
      </table>
    </section>

    <div v-if="completeTarget" class="modal-backdrop">
      <div class="modal">
        <h3>完成清潔 — 房號 {{ completeTarget.room_number }}</h3>
        <label>清潔人員</label>
        <input v-model="cleanedByName" />
        <label>備註</label>
        <textarea v-model="completeNotes"></textarea>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:12px">
          <button @click="completeTarget = null">取消</button>
          <button @click="submitComplete">送出</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center;
}
.modal {
  background: white; padding: 16px; border-radius: 6px; min-width: 320px;
  display: flex; flex-direction: column; gap: 8px;
}
</style>
```

- [ ] **Step 2: Delete the old `CleaningView.vue`**

Run: `rm /Users/mikimoto/Developer/hoteln_net/frontend/src/views/CleaningView.vue`

- [ ] **Step 3: Typecheck build**

Run: `cd frontend && npm run build`
Expected: success.

- [ ] **Step 4: Manual smoke (local dev server)**

Run: `cd frontend && npm run dev` in a separate terminal, then:
- Log in as a staff user.
- Navigate to `/housekeeping`.
- Expect: empty or populated pending + in-progress sections render.
- Seed a request via API (using the device key from the seed script) and confirm it appears.
- Click "啟動清潔" → request disappears, entry shows in "進行中".
- Click "完成清潔" → modal opens, submit closes modal and clears row.

- [ ] **Step 5: Commit**

```bash
cd /Users/mikimoto/Developer/hoteln_net
git add frontend/src/views/HousekeepingView.vue
git rm frontend/src/views/CleaningView.vue
git commit -m "feat(frontend): HousekeepingView with pending requests + in-progress sections"
```

---

## Task 17: Frontend — sidebar role filtering + post-login landing

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/views/LoginView.vue`

- [ ] **Step 1: Inspect current sidebar and login**

Run: `sed -n '20,60p' /Users/mikimoto/Developer/hoteln_net/frontend/src/App.vue`
Run: `cat /Users/mikimoto/Developer/hoteln_net/frontend/src/views/LoginView.vue | head -30`

- [ ] **Step 2: Update the sidebar in `App.vue`**

In `App.vue`, wrap each sidebar router-link with a `v-if` based on the auth store. Keep 清潔紀錄 renamed to **房務清潔** and pointed at `/housekeeping`. Example:

```vue
<aside class="sidebar" v-if="auth.user">
  <div class="sidebar-title">Grand Hilai</div>
  <nav>
    <router-link to="/" v-if="auth.canAccessAdminArea">Dashboard</router-link>
    <router-link to="/guests" v-if="auth.canAccessAdminArea">旅客管理</router-link>
    <router-link to="/rooms" v-if="auth.canAccessAdminArea">房間管理</router-link>
    <router-link to="/reservations" v-if="auth.canAccessAdminArea">訂房管理</router-link>
    <router-link to="/checkin" v-if="auth.canEdit">報到 / 退房</router-link>
    <router-link to="/breakfast" v-if="auth.canEdit">早餐管理</router-link>
    <router-link to="/housekeeping" v-if="auth.canAccessHousekeeping">房務清潔</router-link>
    <router-link to="/users" v-if="auth.isAdmin">使用者</router-link>
    <router-link to="/api-keys" v-if="auth.isAdmin">API Keys</router-link>
  </nav>
  <div class="sidebar-footer">
    <span>{{ auth.user.full_name }}</span>
    <button @click="logout">登出</button>
  </div>
</aside>
```

Import the auth store at the top of the `<script setup>` block if not already:

```ts
import { useAuthStore } from './stores/auth'
const auth = useAuthStore()
```

- [ ] **Step 3: Role-based landing redirect in `LoginView.vue`**

In the `handleLogin` function, after `await auth.login(...)`, replace the hard-coded redirect to `/` with:

```ts
const target = auth.isCleaner ? '/housekeeping' : '/'
router.push(target)
```

Make sure `useRouter` and the auth store are imported.

- [ ] **Step 4: Build**

Run: `cd frontend && npm run build`
Expected: success.

- [ ] **Step 5: Manual smoke**

- Log in as admin → lands on `/` with full nav.
- Log in as staff → lands on `/`; no "使用者" / "API Keys" visible.
- Log in as cleaner → lands on `/housekeeping`; sidebar shows only **房務清潔** + logout.

- [ ] **Step 6: Commit**

```bash
cd /Users/mikimoto/Developer/hoteln_net
git add frontend/src/App.vue frontend/src/views/LoginView.vue
git commit -m "feat(frontend): role-based sidebar filter and post-login redirect"
```

---

## Task 18: Frontend — `ApiKeysView.vue` room-binding dropdown

**Files:**
- Modify: `frontend/src/views/ApiKeysView.vue`

- [ ] **Step 1: Inspect the current page**

Run: `sed -n '1,80p' /Users/mikimoto/Developer/hoteln_net/frontend/src/views/ApiKeysView.vue`
Expected: see the create + edit form layout.

- [ ] **Step 2: Fetch rooms alongside keys**

Add a `rooms` ref and a load call in `onMounted`:

```ts
import type { Room } from '../types'
const rooms = ref<Room[]>([])
// within loadData():
const [keysRes, roomsRes] = await Promise.all([
  api.get('/api-keys'),
  api.get('/rooms'),
])
keys.value = keysRes.data
rooms.value = roomsRes.data
```

- [ ] **Step 3: Add room_id to the create/edit form model**

In the form's reactive state, add `room_id: string | null = null` and bind a `<select>`:

```vue
<label>綁定房間 (可留空)</label>
<select v-model="form.room_id">
  <option :value="null">未綁定</option>
  <option v-for="r in rooms" :key="r.id" :value="r.id">{{ r.room_number }}</option>
</select>
```

When submitting:

```ts
await api.post('/api-keys', { name: form.name, room_id: form.room_id })
// or for edit:
await api.patch(`/api-keys/${editingId}`, { name: form.name, room_id: form.room_id })
```

Show the bound room in the list column (look up room by `room_id` against `rooms.value`).

- [ ] **Step 4: Build**

Run: `cd frontend && npm run build`
Expected: success.

- [ ] **Step 5: Manual smoke**

- Create a new API key with a room selected → row shows the room.
- Edit existing key → change the room → persists after reload.

- [ ] **Step 6: Commit**

```bash
cd /Users/mikimoto/Developer/hoteln_net
git add frontend/src/views/ApiKeysView.vue
git commit -m "feat(frontend): ApiKeys admin supports room binding"
```

---

## Task 19: End-to-end smoke (manual, integration check)

**Files:** none

- [ ] **Step 1: Spin up the stack**

Run: `docker compose up -d` (or equivalent). Wait for db, backend, frontend to be healthy.

- [ ] **Step 2: Seed**

Run: `docker compose exec backend python -m app.seed`
Note the printed `neo_device_...` key for the bound room.

- [ ] **Step 3: Exercise the full flow**

- As admin in the web UI: confirm the seeded cleaner user exists under `/users`.
- Call the request API with curl:
  ```bash
  curl -X POST http://localhost:8000/api/housekeeping/cleaning-requests \
    -H "X-API-Key: <pasted_key>" -H "Content-Type: application/json" \
    -d '{"notes":"toilet paper"}'
  ```
  Expect `200` with `status=pending`.
- Log in as `cleaner1 / cleaner1` → lands on `/housekeeping` → see the pending request.
- Click "啟動清潔" → it disappears from 待清潔請求, appears in 進行中.
- Click "完成清潔" → submit → row disappears.
- Check `/housekeeping/cleaning-requests?status=fulfilled` via curl (with an admin bearer) — confirm `fulfilled_by_cleaning_record_id` is set.

- [ ] **Step 4: Run the full test suite one more time**

Run: `cd backend && python3 -m pytest -v`
Expected: all tests pass.

- [ ] **Step 5: No code changes — nothing to commit.**

If any manual-smoke issue surfaces, fix it in a follow-up task (do not skip it).

---

## Cross-cutting Verifications

After the whole plan lands:

- [ ] Re-check `docs/superpowers/specs/2026-04-18-guest-cleaning-request-and-cleaner-role-design.md` and confirm every section has a corresponding task above.
- [ ] Review the list of modified files — confirm no stray placeholders, no TODOs, no dead code.
- [ ] Spec's "Open Questions / Future Work" items remain out of scope; do not sneak them in.
