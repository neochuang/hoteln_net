# Housekeeping Cleaning Notification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add room cleaning notification system with external device API, cleaning records, and frontend management pages.

**Architecture:** New `ApiKey` and `CleaningRecord` models. Housekeeping router with dual auth (API Key or JWT). Check-out flow modified to auto-create cleaning records. Frontend gets two new pages (CleaningView, ApiKeysView) and RoomsView gets cleaning action buttons.

**Tech Stack:** Python/FastAPI, SQLAlchemy 2.0 async, bcrypt, Vue 3 Composition API, TypeScript, Pinia, Axios

---

## File Structure

### Backend — New Files
| File | Responsibility |
|------|---------------|
| `backend/app/models/api_key.py` | ApiKey ORM model |
| `backend/app/models/cleaning.py` | CleaningRecord ORM model + enums |
| `backend/app/schemas/api_key.py` | Pydantic schemas for API Key CRUD |
| `backend/app/schemas/cleaning.py` | Pydantic schemas for cleaning records + housekeeping endpoints |
| `backend/app/routers/api_keys.py` | API Key management CRUD (admin only) |
| `backend/app/routers/housekeeping.py` | mark-cleaning, clean-complete, cleaning-status, cleaning-records |
| `backend/tests/test_api_keys.py` | API Key CRUD tests |
| `backend/tests/test_housekeeping.py` | Housekeeping endpoint tests |

### Backend — Modified Files
| File | Change |
|------|--------|
| `backend/app/models/__init__.py` | Register ApiKey, CleaningRecord |
| `backend/app/dependencies.py` | Add `get_api_key`, `get_device_or_user` dependencies |
| `backend/app/main.py` | Register housekeeping + api_keys routers |
| `backend/app/routers/checkins.py` | Create CleaningRecord on check-out |
| `backend/tests/test_checkin.py` | Verify CleaningRecord created on check-out |

### Frontend — New Files
| File | Responsibility |
|------|---------------|
| `frontend/src/views/CleaningView.vue` | Cleaning records list with filters |
| `frontend/src/views/ApiKeysView.vue` | API Key management (admin only) |

### Frontend — Modified Files
| File | Change |
|------|--------|
| `frontend/src/types/index.ts` | Add ApiKey, CleaningRecord, CleaningType, ReportedVia types |
| `frontend/src/views/RoomsView.vue` | Add mark-cleaning and clean-complete buttons |
| `frontend/src/router/index.ts` | Add /cleaning and /api-keys routes |
| `frontend/src/App.vue` | Add sidebar nav items |

---

### Task 1: ApiKey and CleaningRecord Models

**Files:**
- Create: `backend/app/models/api_key.py`
- Create: `backend/app/models/cleaning.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create ApiKey model**

Create `backend/app/models/api_key.py`:

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 2: Create CleaningRecord model**

Create `backend/app/models/cleaning.py`:

```python
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
```

- [ ] **Step 3: Register models in `__init__.py`**

Edit `backend/app/models/__init__.py` — add after existing imports:

```python
from app.models.api_key import ApiKey
from app.models.cleaning import CleaningRecord
```

And add `"ApiKey"` and `"CleaningRecord"` to the `__all__` list.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/api_key.py backend/app/models/cleaning.py backend/app/models/__init__.py
git commit -m "feat: add ApiKey and CleaningRecord models"
```

---

### Task 2: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/api_key.py`
- Create: `backend/app/schemas/cleaning.py`

- [ ] **Step 1: Create API Key schemas**

Create `backend/app/schemas/api_key.py`:

```python
import uuid
from datetime import datetime

from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    key_prefix: str
    name: str
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    key: str
```

- [ ] **Step 2: Create cleaning record schemas**

Create `backend/app/schemas/cleaning.py`:

```python
import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.cleaning import CleaningType, ReportedVia


class CleanCompleteRequest(BaseModel):
    cleaned_by_name: str | None = None
    notes: str | None = None


class CleaningRecordResponse(BaseModel):
    id: uuid.UUID
    room_id: uuid.UUID
    cleaning_type: CleaningType
    started_at: datetime
    completed_at: datetime | None
    cleaned_by_name: str | None
    reported_via: ReportedVia | None
    api_key_id: uuid.UUID | None
    staff_user_id: uuid.UUID | None
    notes: str | None

    model_config = {"from_attributes": True}


class MarkCleaningResponse(BaseModel):
    room_id: uuid.UUID
    room_number: str
    status: str
    cleaning_record: CleaningRecordResponse

    model_config = {"from_attributes": True}


class CleanCompleteResponse(BaseModel):
    room_id: uuid.UUID
    room_number: str
    status: str
    cleaning_record: CleaningRecordResponse

    model_config = {"from_attributes": True}


class CleaningStatusRoom(BaseModel):
    room_id: uuid.UUID
    room_number: str
    floor: int
    room_type_name: str
    cleaning_type: CleaningType
    started_at: datetime
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/api_key.py backend/app/schemas/cleaning.py
git commit -m "feat: add API Key and cleaning record schemas"
```

---

### Task 3: API Key Authentication Dependencies

**Files:**
- Modify: `backend/app/dependencies.py`

- [ ] **Step 1: Write failing test for API Key dependency**

Create `backend/tests/test_dependencies.py`:

```python
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import bcrypt
from app.models.api_key import ApiKey


async def seed_api_key(db: AsyncSession) -> tuple[ApiKey, str]:
    """Create an API key and return (model, raw_key)."""
    raw_key = "neo_testkey1234567890abcdef"
    key_hash = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
    api_key = ApiKey(
        id=uuid.uuid4(),
        key_hash=key_hash,
        key_prefix=raw_key[:8],
        name="Test Device",
        is_active=True,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return api_key, raw_key


@pytest.mark.asyncio
async def test_api_key_auth_valid(client: AsyncClient, db_session: AsyncSession):
    """Health endpoint works without auth, but we test the dependency via housekeeping endpoints in test_housekeeping.py."""
    api_key, raw_key = await seed_api_key(db_session)
    # This test validates seeding works; full auth tests are in test_housekeeping.py
    assert api_key.is_active is True
    assert api_key.key_prefix == "neo_test"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/mikimoto/Developer/neo/backend && python -m pytest tests/test_dependencies.py -v`
Expected: FAIL (or PASS for basic seeding — dependency will be tested end-to-end in Task 5)

- [ ] **Step 3: Add API Key dependencies to `dependencies.py`**

Edit `backend/app/dependencies.py` — add these imports at the top:

```python
from typing import Union

import bcrypt
from fastapi import Header
from datetime import datetime, timezone

from app.models.api_key import ApiKey
```

Then add after the `require_role` function:

```python
async def get_api_key(
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    result = await db.execute(select(ApiKey).where(ApiKey.is_active == True))
    api_keys = result.scalars().all()
    for key in api_keys:
        if bcrypt.checkpw(x_api_key.encode(), key.key_hash.encode()):
            key.last_used_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(key)
            return key
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


async def get_device_or_user(
    x_api_key: str | None = Header(None),
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> Union[ApiKey, User]:
    if x_api_key:
        return await get_api_key(x_api_key=x_api_key, db=db)
    if credentials:
        return await get_current_user(credentials=credentials, db=db)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/mikimoto/Developer/neo/backend && python -m pytest tests/test_dependencies.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/dependencies.py backend/tests/test_dependencies.py
git commit -m "feat: add API Key and dual auth dependencies"
```

---

### Task 4: API Key CRUD Router + Tests

**Files:**
- Create: `backend/app/routers/api_keys.py`
- Create: `backend/tests/test_api_keys.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_api_keys.py`:

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_api_key(client: AsyncClient, admin_headers):
    res = await client.post("/api/api-keys", headers=admin_headers, json={"name": "3F 清潔平板"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "3F 清潔平板"
    assert data["is_active"] is True
    assert "key" in data  # full key returned only on creation
    assert data["key"].startswith("neo_")
    assert data["key_prefix"] == data["key"][:8]


@pytest.mark.asyncio
async def test_list_api_keys(client: AsyncClient, admin_headers):
    # Create two keys
    await client.post("/api/api-keys", headers=admin_headers, json={"name": "Device A"})
    await client.post("/api/api-keys", headers=admin_headers, json={"name": "Device B"})

    res = await client.get("/api/api-keys", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    # Should NOT contain full key
    assert "key" not in data[0]


@pytest.mark.asyncio
async def test_update_api_key(client: AsyncClient, admin_headers):
    create_res = await client.post("/api/api-keys", headers=admin_headers, json={"name": "Old Name"})
    key_id = create_res.json()["id"]

    res = await client.patch(f"/api/api-keys/{key_id}", headers=admin_headers, json={
        "name": "New Name",
        "is_active": False,
    })
    assert res.status_code == 200
    assert res.json()["name"] == "New Name"
    assert res.json()["is_active"] is False


@pytest.mark.asyncio
async def test_delete_api_key(client: AsyncClient, admin_headers):
    create_res = await client.post("/api/api-keys", headers=admin_headers, json={"name": "To Delete"})
    key_id = create_res.json()["id"]

    res = await client.delete(f"/api/api-keys/{key_id}", headers=admin_headers)
    assert res.status_code == 204

    # Verify deleted
    list_res = await client.get("/api/api-keys", headers=admin_headers)
    assert len(list_res.json()) == 0


@pytest.mark.asyncio
async def test_staff_cannot_manage_api_keys(client: AsyncClient, staff_headers):
    res = await client.post("/api/api-keys", headers=staff_headers, json={"name": "Attempt"})
    assert res.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mikimoto/Developer/neo/backend && python -m pytest tests/test_api_keys.py -v`
Expected: FAIL (router not registered yet)

- [ ] **Step 3: Create API Key router**

Create `backend/app/routers/api_keys.py`:

```python
import secrets
import uuid

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.api_key import ApiKey
from app.models.user import User, UserRole
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse, ApiKeyUpdate

router = APIRouter()

API_KEY_PREFIX = "neo_"


@router.post("", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    raw_key = API_KEY_PREFIX + secrets.token_hex(24)
    key_hash = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()

    api_key = ApiKey(
        key_hash=key_hash,
        key_prefix=raw_key[:8],
        name=body.name,
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
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
    )


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    result = await db.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
    return result.scalars().all()


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

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(api_key, key, value)

    await db.commit()
    await db.refresh(api_key)
    return api_key


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    await db.delete(api_key)
    await db.commit()
```

- [ ] **Step 4: Register router in `main.py`**

Edit `backend/app/main.py` — add to the imports:

```python
from app.routers import auth, breakfast, checkins, guests, reservations, rooms, self_checkin, users, api_keys, housekeeping
```

Add after the existing `include_router` calls:

```python
app.include_router(api_keys.router, prefix="/api/api-keys", tags=["API Keys"])
```

(Do NOT add housekeeping yet — we'll add it in Task 5.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/mikimoto/Developer/neo/backend && python -m pytest tests/test_api_keys.py -v`
Expected: All 5 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/api_keys.py backend/tests/test_api_keys.py backend/app/main.py
git commit -m "feat: add API Key CRUD endpoints"
```

---

### Task 5: Housekeeping Router + Tests

**Files:**
- Create: `backend/app/routers/housekeeping.py`
- Create: `backend/tests/test_housekeeping.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_housekeeping.py`:

```python
import uuid
from datetime import date

import bcrypt
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey
from app.models.cleaning import CleaningRecord, CleaningType
from app.models.guest import Guest, IDType
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomStatus, RoomType


async def seed_room(db: AsyncSession) -> tuple[RoomType, Room]:
    room_type = RoomType(id=uuid.uuid4(), name="標準房", capacity=2, base_price=2000)
    db.add(room_type)
    room = Room(
        id=uuid.uuid4(),
        room_number="401",
        floor=4,
        room_type_id=room_type.id,
        status=RoomStatus.available,
    )
    db.add(room)
    await db.commit()
    return room_type, room


async def seed_checked_in_reservation(
    db: AsyncSession, room: Room, room_type: RoomType, admin_id: uuid.UUID
) -> Reservation:
    guest = Guest(
        id=uuid.uuid4(),
        first_name="小明",
        last_name="王",
        id_type=IDType.national_id,
        id_number="D123456789",
        phone="0911111111",
        nationality="台灣",
    )
    db.add(guest)
    reservation = Reservation(
        id=uuid.uuid4(),
        guest_id=guest.id,
        room_type_id=room_type.id,
        room_id=room.id,
        check_in_date=date(2026, 4, 10),
        check_out_date=date(2026, 4, 13),
        num_guests=2,
        status=ReservationStatus.checked_in,
        includes_breakfast=False,
        breakfast_guests=0,
        total_price=6000,
        created_by=admin_id,
    )
    db.add(reservation)
    await db.commit()
    return reservation


async def seed_api_key(db: AsyncSession) -> tuple[ApiKey, str]:
    raw_key = "neo_device_test_key_abc123"
    key_hash = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
    api_key = ApiKey(
        id=uuid.uuid4(),
        key_hash=key_hash,
        key_prefix=raw_key[:8],
        name="Test Device",
        is_active=True,
    )
    db.add(api_key)
    await db.commit()
    return api_key, raw_key


# --- mark-cleaning ---

@pytest.mark.asyncio
async def test_mark_cleaning_occupied_room(
    client: AsyncClient, db_session: AsyncSession, admin_user, admin_headers
):
    room_type, room = await seed_room(db_session)
    reservation = await seed_checked_in_reservation(db_session, room, room_type, admin_user.id)
    room.status = RoomStatus.occupied
    await db_session.commit()

    res = await client.post(f"/api/housekeeping/rooms/{room.room_number}/mark-cleaning", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "cleaning"
    assert data["cleaning_record"]["cleaning_type"] == "daily"

    await db_session.refresh(room)
    assert room.status == RoomStatus.cleaning


@pytest.mark.asyncio
async def test_mark_cleaning_rejects_non_occupied(
    client: AsyncClient, db_session: AsyncSession, admin_headers
):
    room_type, room = await seed_room(db_session)
    # room is available, not occupied
    res = await client.post(f"/api/housekeeping/rooms/{room.room_number}/mark-cleaning", headers=admin_headers)
    assert res.status_code == 400


# --- clean-complete ---

@pytest.mark.asyncio
async def test_clean_complete_checkout_to_available(
    client: AsyncClient, db_session: AsyncSession, admin_headers
):
    """After checkout cleaning (no active reservation), room should become available."""
    room_type, room = await seed_room(db_session)
    room.status = RoomStatus.cleaning
    await db_session.commit()

    # Create a cleaning record (simulating checkout)
    record = CleaningRecord(
        id=uuid.uuid4(),
        room_id=room.id,
        cleaning_type=CleaningType.checkout,
    )
    db_session.add(record)
    await db_session.commit()

    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/clean-complete",
        headers=admin_headers,
        json={"cleaned_by_name": "陳小美"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "available"
    assert data["cleaning_record"]["cleaned_by_name"] == "陳小美"
    assert data["cleaning_record"]["completed_at"] is not None

    await db_session.refresh(room)
    assert room.status == RoomStatus.available


@pytest.mark.asyncio
async def test_clean_complete_daily_to_occupied(
    client: AsyncClient, db_session: AsyncSession, admin_user, admin_headers
):
    """Daily cleaning with active reservation → room should return to occupied."""
    room_type, room = await seed_room(db_session)
    reservation = await seed_checked_in_reservation(db_session, room, room_type, admin_user.id)
    room.status = RoomStatus.cleaning
    await db_session.commit()

    record = CleaningRecord(
        id=uuid.uuid4(),
        room_id=room.id,
        cleaning_type=CleaningType.daily,
    )
    db_session.add(record)
    await db_session.commit()

    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/clean-complete",
        headers=admin_headers,
        json={},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "occupied"

    await db_session.refresh(room)
    assert room.status == RoomStatus.occupied


@pytest.mark.asyncio
async def test_clean_complete_via_api_key(
    client: AsyncClient, db_session: AsyncSession, admin_headers
):
    """External device can complete cleaning via API Key."""
    room_type, room = await seed_room(db_session)
    room.status = RoomStatus.cleaning
    await db_session.commit()

    record = CleaningRecord(
        id=uuid.uuid4(),
        room_id=room.id,
        cleaning_type=CleaningType.checkout,
    )
    db_session.add(record)
    await db_session.commit()

    api_key, raw_key = await seed_api_key(db_session)

    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/clean-complete",
        headers={"X-API-Key": raw_key},
        json={"cleaned_by_name": "王大姊"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "available"
    assert data["cleaning_record"]["reported_via"] == "device"
    assert data["cleaning_record"]["api_key_id"] == str(api_key.id)


@pytest.mark.asyncio
async def test_clean_complete_rejects_non_cleaning(
    client: AsyncClient, db_session: AsyncSession, admin_headers
):
    room_type, room = await seed_room(db_session)
    # room is available, not cleaning
    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/clean-complete",
        headers=admin_headers,
        json={},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_clean_complete_rejects_inactive_api_key(
    client: AsyncClient, db_session: AsyncSession,
):
    room_type, room = await seed_room(db_session)
    room.status = RoomStatus.cleaning
    await db_session.commit()

    record = CleaningRecord(room_id=room.id, cleaning_type=CleaningType.checkout)
    db_session.add(record)
    await db_session.commit()

    api_key, raw_key = await seed_api_key(db_session)
    api_key.is_active = False
    await db_session.commit()

    res = await client.post(
        f"/api/housekeeping/rooms/{room.room_number}/clean-complete",
        headers={"X-API-Key": raw_key},
        json={},
    )
    assert res.status_code == 401


# --- cleaning-status ---

@pytest.mark.asyncio
async def test_cleaning_status(client: AsyncClient, db_session: AsyncSession, admin_headers):
    room_type, room = await seed_room(db_session)
    room.status = RoomStatus.cleaning
    await db_session.commit()

    record = CleaningRecord(room_id=room.id, cleaning_type=CleaningType.checkout)
    db_session.add(record)
    await db_session.commit()

    res = await client.get("/api/housekeeping/rooms/cleaning-status", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["room_number"] == "401"
    assert data[0]["cleaning_type"] == "checkout"


# --- cleaning-records ---

@pytest.mark.asyncio
async def test_list_cleaning_records(client: AsyncClient, db_session: AsyncSession, admin_headers):
    room_type, room = await seed_room(db_session)
    record = CleaningRecord(room_id=room.id, cleaning_type=CleaningType.checkout)
    db_session.add(record)
    await db_session.commit()

    res = await client.get("/api/housekeeping/cleaning-records", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["room_id"] == str(room.id)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mikimoto/Developer/neo/backend && python -m pytest tests/test_housekeeping.py -v`
Expected: FAIL (router not found)

- [ ] **Step 3: Create housekeeping router**

Create `backend/app/routers/housekeeping.py`:

```python
import uuid
from datetime import date, datetime, timezone
from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_device_or_user, require_role
from app.models.api_key import ApiKey
from app.models.cleaning import CleaningRecord, CleaningType, ReportedVia
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomStatus
from app.models.user import User, UserRole
from app.schemas.cleaning import (
    CleanCompleteRequest,
    CleanCompleteResponse,
    CleaningRecordResponse,
    CleaningStatusRoom,
    MarkCleaningResponse,
)

router = APIRouter()


async def _has_active_reservation(db: AsyncSession, room_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(Reservation).where(
            Reservation.room_id == room_id,
            Reservation.status == ReservationStatus.checked_in,
        )
    )
    return result.scalar_one_or_none() is not None


@router.post("/rooms/{room_number}/mark-cleaning", response_model=MarkCleaningResponse)
async def mark_cleaning(
    room_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.staff)),
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

    await db.commit()
    await db.refresh(room)
    await db.refresh(record)

    return MarkCleaningResponse(
        room_id=room.id,
        room_number=room.room_number,
        status=room.status.value,
        cleaning_record=CleaningRecordResponse.model_validate(record),
    )


@router.post("/rooms/{room_number}/clean-complete", response_model=CleanCompleteResponse)
async def clean_complete(
    room_number: str,
    body: CleanCompleteRequest,
    db: AsyncSession = Depends(get_db),
    auth: Union[ApiKey, User] = Depends(get_device_or_user),
):
    result = await db.execute(select(Room).where(Room.room_number == room_number))
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.status != RoomStatus.cleaning:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is not in cleaning status")

    # Find the most recent incomplete cleaning record for this room
    result = await db.execute(
        select(CleaningRecord)
        .where(CleaningRecord.room_id == room.id, CleaningRecord.completed_at.is_(None))
        .order_by(CleaningRecord.started_at.desc())
        .limit(1)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No pending cleaning record found")

    # Update cleaning record
    record.completed_at = datetime.now(timezone.utc)
    record.cleaned_by_name = body.cleaned_by_name
    record.notes = body.notes

    if isinstance(auth, ApiKey):
        record.reported_via = ReportedVia.device
        record.api_key_id = auth.id
    else:
        record.reported_via = ReportedVia.staff
        record.staff_user_id = auth.id

    # Determine target room status
    has_active = await _has_active_reservation(db, room.id)
    room.status = RoomStatus.occupied if has_active else RoomStatus.available

    await db.commit()
    await db.refresh(room)
    await db.refresh(record)

    return CleanCompleteResponse(
        room_id=room.id,
        room_number=room.room_number,
        status=room.status.value,
        cleaning_record=CleaningRecordResponse.model_validate(record),
    )


@router.get("/rooms/cleaning-status", response_model=list[CleaningStatusRoom])
async def cleaning_status(
    db: AsyncSession = Depends(get_db),
    auth: Union[ApiKey, User] = Depends(get_device_or_user),
):
    result = await db.execute(
        select(Room)
        .options(selectinload(Room.room_type))
        .where(Room.status == RoomStatus.cleaning)
        .order_by(Room.room_number)
    )
    rooms = result.scalars().all()

    response = []
    for room in rooms:
        # Get the pending cleaning record
        rec_result = await db.execute(
            select(CleaningRecord)
            .where(CleaningRecord.room_id == room.id, CleaningRecord.completed_at.is_(None))
            .order_by(CleaningRecord.started_at.desc())
            .limit(1)
        )
        record = rec_result.scalar_one_or_none()
        if record:
            response.append(CleaningStatusRoom(
                room_id=room.id,
                room_number=room.room_number,
                floor=room.floor,
                room_type_name=room.room_type.name,
                cleaning_type=record.cleaning_type,
                started_at=record.started_at,
            ))

    return response


@router.get("/cleaning-records", response_model=list[CleaningRecordResponse])
async def list_cleaning_records(
    room_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    cleaning_type: CleaningType | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    query = select(CleaningRecord).order_by(CleaningRecord.started_at.desc())
    if room_id:
        query = query.where(CleaningRecord.room_id == room_id)
    if date_from:
        query = query.where(CleaningRecord.started_at >= datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc))
    if date_to:
        query = query.where(CleaningRecord.started_at < datetime(date_to.year, date_to.month, date_to.day, tzinfo=timezone.utc))
    if cleaning_type:
        query = query.where(CleaningRecord.cleaning_type == cleaning_type)

    result = await db.execute(query)
    return result.scalars().all()
```

- [ ] **Step 4: Register housekeeping router in `main.py`**

Edit `backend/app/main.py` — add after the api_keys router line:

```python
app.include_router(housekeeping.router, prefix="/api/housekeeping", tags=["Housekeeping"])
```

Also update the import line to include `housekeeping`:

```python
from app.routers import auth, breakfast, checkins, guests, reservations, rooms, self_checkin, users, api_keys, housekeeping
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/mikimoto/Developer/neo/backend && python -m pytest tests/test_housekeeping.py -v`
Expected: All tests PASS

- [ ] **Step 6: Run full test suite**

Run: `cd /Users/mikimoto/Developer/neo/backend && python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/housekeeping.py backend/tests/test_housekeeping.py backend/app/main.py
git commit -m "feat: add housekeeping endpoints (mark-cleaning, clean-complete, cleaning-status, cleaning-records)"
```

---

### Task 6: Modify Check-out to Create CleaningRecord

**Files:**
- Modify: `backend/app/routers/checkins.py`
- Modify: `backend/tests/test_checkin.py`

- [ ] **Step 1: Update check-out test to verify CleaningRecord creation**

Edit `backend/tests/test_checkin.py` — add at the top:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.cleaning import CleaningRecord, CleaningType
```

Add a new test at the end of the file:

```python
@pytest.mark.asyncio
async def test_check_out_creates_cleaning_record(client: AsyncClient, db_session: AsyncSession, admin_headers):
    guest_id, type_id, room_id, reservation_id = await setup_checkin_data(client, admin_headers)

    # Check in first
    await client.post(f"/api/reservations/{reservation_id}/check-in", headers=admin_headers, json={
        "room_id": room_id,
    })

    # Check out
    res = await client.post(f"/api/reservations/{reservation_id}/check-out", headers=admin_headers)
    assert res.status_code == 200

    # Verify CleaningRecord was created
    result = await db_session.execute(select(CleaningRecord).where(CleaningRecord.room_id == room_id))
    record = result.scalar_one_or_none()
    assert record is not None
    assert record.cleaning_type == CleaningType.checkout
    assert record.completed_at is None
```

- [ ] **Step 2: Run new test to verify it fails**

Run: `cd /Users/mikimoto/Developer/neo/backend && python -m pytest tests/test_checkin.py::test_check_out_creates_cleaning_record -v`
Expected: FAIL (no CleaningRecord created yet)

- [ ] **Step 3: Modify check-out endpoint to create CleaningRecord**

Edit `backend/app/routers/checkins.py` — add to imports:

```python
from app.models.cleaning import CleaningRecord, CleaningType
```

Then in the `check_out` function, after `room.status = RoomStatus.cleaning` (line 81), add:

```python
    # Create cleaning record
    cleaning_record = CleaningRecord(
        room_id=room.id,
        cleaning_type=CleaningType.checkout,
    )
    db.add(cleaning_record)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/mikimoto/Developer/neo/backend && python -m pytest tests/test_checkin.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Run full test suite**

Run: `cd /Users/mikimoto/Developer/neo/backend && python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/checkins.py backend/tests/test_checkin.py
git commit -m "feat: auto-create CleaningRecord on check-out"
```

---

### Task 7: Frontend TypeScript Types

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add new types**

Add at the end of `frontend/src/types/index.ts`:

```typescript
export interface ApiKey {
  id: string
  key_prefix: string
  name: string
  is_active: boolean
  created_at: string
  last_used_at: string | null
}

export interface ApiKeyCreated extends ApiKey {
  key: string
}

export interface CleaningRecord {
  id: string
  room_id: string
  cleaning_type: 'checkout' | 'daily'
  started_at: string
  completed_at: string | null
  cleaned_by_name: string | null
  reported_via: 'device' | 'staff' | null
  api_key_id: string | null
  staff_user_id: string | null
  notes: string | null
}

export interface MarkCleaningResponse {
  room_id: string
  room_number: string
  status: string
  cleaning_record: CleaningRecord
}

export interface CleanCompleteResponse {
  room_id: string
  room_number: string
  status: string
  cleaning_record: CleaningRecord
}

export interface CleaningStatusRoom {
  room_id: string
  room_number: string
  floor: number
  room_type_name: string
  cleaning_type: 'checkout' | 'daily'
  started_at: string
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add TypeScript types for ApiKey and CleaningRecord"
```

---

### Task 8: Frontend API Key Management Page

**Files:**
- Create: `frontend/src/views/ApiKeysView.vue`

- [ ] **Step 1: Create ApiKeysView component**

Create `frontend/src/views/ApiKeysView.vue`:

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'
import type { ApiKey, ApiKeyCreated } from '../types'

const apiKeys = ref<ApiKey[]>([])
const showCreateModal = ref(false)
const showKeyModal = ref(false)
const newKeyName = ref('')
const createdKey = ref('')

async function loadKeys() {
  const res = await api.get('/api-keys')
  apiKeys.value = res.data
}

async function createKey() {
  const res = await api.post('/api-keys', { name: newKeyName.value })
  const data: ApiKeyCreated = res.data
  createdKey.value = data.key
  showCreateModal.value = false
  newKeyName.value = ''
  showKeyModal.value = true
  await loadKeys()
}

async function toggleActive(key: ApiKey) {
  await api.patch(`/api-keys/${key.id}`, { is_active: !key.is_active })
  await loadKeys()
}

async function deleteKey(key: ApiKey) {
  if (!confirm(`確定要刪除「${key.name}」？`)) return
  await api.delete(`/api-keys/${key.id}`)
  await loadKeys()
}

function copyKey() {
  navigator.clipboard.writeText(createdKey.value)
}

function formatDate(d: string | null) {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-TW')
}

onMounted(loadKeys)
</script>

<template>
  <div>
    <div class="page-header">
      <h2>API Key 管理</h2>
      <button class="btn btn-primary" @click="showCreateModal = true">新增 API Key</button>
    </div>

    <table>
      <thead>
        <tr>
          <th>名稱</th>
          <th>Key 前綴</th>
          <th>狀態</th>
          <th>建立時間</th>
          <th>最後使用</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="key in apiKeys" :key="key.id">
          <td>{{ key.name }}</td>
          <td><code>{{ key.key_prefix }}...</code></td>
          <td>
            <span :class="['badge', key.is_active ? 'badge-available' : 'badge-cancelled']">
              {{ key.is_active ? '啟用' : '停用' }}
            </span>
          </td>
          <td>{{ formatDate(key.created_at) }}</td>
          <td>{{ formatDate(key.last_used_at) }}</td>
          <td>
            <button
              :class="['btn btn-sm', key.is_active ? 'btn-danger' : 'btn-success']"
              @click="toggleActive(key)"
            >
              {{ key.is_active ? '停用' : '啟用' }}
            </button>
            <button class="btn btn-sm btn-danger" @click="deleteKey(key)" style="margin-left: 4px">
              刪除
            </button>
          </td>
        </tr>
        <tr v-if="apiKeys.length === 0">
          <td colspan="6" style="text-align: center; color: #888">尚無 API Key</td>
        </tr>
      </tbody>
    </table>

    <!-- Create Modal -->
    <div v-if="showCreateModal" class="overlay" @click.self="showCreateModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>新增 API Key</h3>
        </div>
        <form @submit.prevent="createKey">
          <div class="form-group">
            <label>裝置名稱</label>
            <input v-model="newKeyName" required placeholder="例如：3F 清潔平板" />
          </div>
          <div class="modal-actions">
            <button type="button" class="btn" @click="showCreateModal = false">取消</button>
            <button type="submit" class="btn btn-primary">建立</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Key Display Modal -->
    <div v-if="showKeyModal" class="overlay">
      <div class="modal">
        <div class="modal-header">
          <h3>API Key 已建立</h3>
        </div>
        <p style="color: #dc2626; font-weight: bold">請立即複製此 Key，關閉後將無法再次查看！</p>
        <div style="background: #f3f4f6; padding: 12px; border-radius: 6px; word-break: break-all; font-family: monospace">
          {{ createdKey }}
        </div>
        <div class="modal-actions">
          <button class="btn" @click="copyKey">複製</button>
          <button class="btn btn-primary" @click="showKeyModal = false; createdKey = ''">我已複製，關閉</button>
        </div>
      </div>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/ApiKeysView.vue
git commit -m "feat: add API Key management page"
```

---

### Task 9: Frontend Cleaning Records Page

**Files:**
- Create: `frontend/src/views/CleaningView.vue`

- [ ] **Step 1: Create CleaningView component**

Create `frontend/src/views/CleaningView.vue`:

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'
import type { CleaningRecord, Room } from '../types'

const records = ref<CleaningRecord[]>([])
const rooms = ref<Room[]>([])
const filterRoomId = ref('')
const filterType = ref('')
const filterDateFrom = ref('')
const filterDateTo = ref('')

async function loadData() {
  const [roomsRes] = await Promise.all([api.get('/rooms')])
  rooms.value = roomsRes.data
  await loadRecords()
}

async function loadRecords() {
  const params: Record<string, string> = {}
  if (filterRoomId.value) params.room_id = filterRoomId.value
  if (filterType.value) params.cleaning_type = filterType.value
  if (filterDateFrom.value) params.date_from = filterDateFrom.value
  if (filterDateTo.value) params.date_to = filterDateTo.value

  const res = await api.get('/housekeeping/cleaning-records', { params })
  records.value = res.data
}

function roomNumber(roomId: string): string {
  const room = rooms.value.find((r) => r.id === roomId)
  return room ? room.room_number : roomId.slice(0, 8)
}

function formatDate(d: string | null) {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-TW')
}

function duration(record: CleaningRecord): string {
  if (!record.completed_at) return '進行中'
  const start = new Date(record.started_at).getTime()
  const end = new Date(record.completed_at).getTime()
  const mins = Math.round((end - start) / 60000)
  if (mins < 60) return `${mins} 分鐘`
  return `${Math.floor(mins / 60)} 小時 ${mins % 60} 分鐘`
}

const typeLabel: Record<string, string> = { checkout: '退房清潔', daily: '每日清潔' }
const viaLabel: Record<string, string> = { device: '裝置', staff: '前台人員' }

onMounted(loadData)
</script>

<template>
  <div>
    <div class="page-header">
      <h2>清潔紀錄</h2>
    </div>

    <div style="display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap">
      <select v-model="filterRoomId" @change="loadRecords">
        <option value="">全部房間</option>
        <option v-for="room in rooms" :key="room.id" :value="room.id">{{ room.room_number }}</option>
      </select>
      <select v-model="filterType" @change="loadRecords">
        <option value="">全部類型</option>
        <option value="checkout">退房清潔</option>
        <option value="daily">每日清潔</option>
      </select>
      <input type="date" v-model="filterDateFrom" @change="loadRecords" placeholder="開始日期" />
      <input type="date" v-model="filterDateTo" @change="loadRecords" placeholder="結束日期" />
    </div>

    <table>
      <thead>
        <tr>
          <th>房號</th>
          <th>清潔類型</th>
          <th>回報來源</th>
          <th>開始時間</th>
          <th>完成時間</th>
          <th>耗時</th>
          <th>清潔人員</th>
          <th>備註</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in records" :key="r.id">
          <td>{{ roomNumber(r.room_id) }}</td>
          <td>
            <span :class="['badge', r.cleaning_type === 'checkout' ? 'badge-maintenance' : 'badge-available']">
              {{ typeLabel[r.cleaning_type] || r.cleaning_type }}
            </span>
          </td>
          <td>{{ r.reported_via ? viaLabel[r.reported_via] || r.reported_via : '-' }}</td>
          <td>{{ formatDate(r.started_at) }}</td>
          <td>{{ formatDate(r.completed_at) }}</td>
          <td>{{ duration(r) }}</td>
          <td>{{ r.cleaned_by_name || '-' }}</td>
          <td>{{ r.notes || '-' }}</td>
        </tr>
        <tr v-if="records.length === 0">
          <td colspan="8" style="text-align: center; color: #888">無清潔紀錄</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/CleaningView.vue
git commit -m "feat: add cleaning records page"
```

---

### Task 10: Enhance RoomsView with Cleaning Actions

**Files:**
- Modify: `frontend/src/views/RoomsView.vue`

- [ ] **Step 1: Read current RoomsView**

Read: `frontend/src/views/RoomsView.vue`

- [ ] **Step 2: Add cleaning action functions and buttons**

In the `<script setup>` section, add after the existing imports:

```typescript
import type { MarkCleaningResponse, CleanCompleteResponse } from '../types'
```

Add two new functions after `updateStatus`:

```typescript
async function markCleaning(room: Room) {
  if (!confirm(`確定要將房間 ${room.room_number} 標註為可清潔？`)) return
  await api.post(`/housekeeping/rooms/${room.room_number}/mark-cleaning`)
  await loadData()
}

async function cleanComplete(room: Room) {
  if (!confirm(`確定房間 ${room.room_number} 已清潔完成？`)) return
  await api.post(`/housekeeping/rooms/${room.room_number}/clean-complete`, {})
  await loadData()
}
```

In the template's rooms table, in the row where room status actions are rendered, add two new buttons. Find the cell with the status `<select>` (or where `updateStatus` is called) and add adjacent to the existing action controls:

```html
<button
  v-if="room.status === 'occupied' && auth.canEdit"
  class="btn btn-sm"
  style="background: #f59e0b; color: white; margin-left: 4px"
  @click="markCleaning(room)"
>
  標註可清潔
</button>
<button
  v-if="room.status === 'cleaning' && auth.canEdit"
  class="btn btn-sm btn-success"
  style="margin-left: 4px"
  @click="cleanComplete(room)"
>
  清潔完成
</button>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/RoomsView.vue
git commit -m "feat: add mark-cleaning and clean-complete buttons to RoomsView"
```

---

### Task 11: Frontend Routing and Navigation

**Files:**
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Add routes**

Edit `frontend/src/router/index.ts` — add two new route objects before the `SelfCheckIn` route (before the `{ path: '/self-checkin', ... }` entry):

```typescript
    {
      path: '/cleaning',
      name: 'Cleaning',
      component: () => import('../views/CleaningView.vue'),
    },
    {
      path: '/api-keys',
      name: 'ApiKeys',
      meta: { adminOnly: true },
      component: () => import('../views/ApiKeysView.vue'),
    },
```

- [ ] **Step 2: Add sidebar navigation items**

Edit `frontend/src/App.vue` — in the `<nav>` section, add after the `<router-link to="/breakfast">` line:

```html
        <router-link to="/cleaning">清潔紀錄</router-link>
```

And after the existing `<router-link to="/users" v-if="auth.isAdmin">` line, add:

```html
        <router-link to="/api-keys" v-if="auth.isAdmin">API Key</router-link>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/router/index.ts frontend/src/App.vue
git commit -m "feat: add cleaning and API Key routes and sidebar navigation"
```

---

### Task 12: Alembic Migration

**Files:**
- Create: new migration file via alembic

- [ ] **Step 1: Generate migration**

Run: `cd /Users/mikimoto/Developer/neo/backend && alembic revision --autogenerate -m "add api_keys and cleaning_records tables"`

If autogenerate doesn't work (no existing migrations), create manually:

Run: `cd /Users/mikimoto/Developer/neo/backend && alembic revision -m "add api_keys and cleaning_records tables"`

Then edit the generated file in `backend/alembic/versions/` with:

```python
"""add api_keys and cleaning_records tables"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '<auto>'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('key_prefix', sa.String(8), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'cleaning_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('room_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rooms.id'), nullable=False),
        sa.Column('cleaning_type', sa.Enum('checkout', 'daily', name='cleaningtype'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cleaned_by_name', sa.String(50), nullable=True),
        sa.Column('reported_via', sa.Enum('device', 'staff', name='reportedvia'), nullable=True),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('api_keys.id'), nullable=True),
        sa.Column('staff_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('cleaning_records')
    op.drop_table('api_keys')
    sa.Enum(name='cleaningtype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='reportedvia').drop(op.get_bind(), checkfirst=True)
```

- [ ] **Step 2: Run full backend test suite to verify nothing is broken**

Run: `cd /Users/mikimoto/Developer/neo/backend && python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat: add migration for api_keys and cleaning_records tables"
```

---

### Task 13: Final Verification

- [ ] **Step 1: Run full backend test suite**

Run: `cd /Users/mikimoto/Developer/neo/backend && python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 2: Verify frontend builds**

Run: `cd /Users/mikimoto/Developer/neo/frontend && npm run build`
Expected: Build succeeds with no TypeScript errors

- [ ] **Step 3: Manual verification checklist**

Start the services: `docker compose up -d` (or run backend + frontend locally)

1. Admin creates API Key → full key shown once → list shows only prefix
2. Check-out a reservation → room becomes `cleaning` → CleaningRecord created with type `checkout`
3. Call `POST /api/housekeeping/rooms/{room_number}/clean-complete` with `X-API-Key` header → room becomes `available`
4. Check-in a multi-night guest → front desk marks room as "可清潔" → room becomes `cleaning` → CleaningRecord created with type `daily`
5. Call clean-complete → room returns to `occupied` (because active reservation exists)
6. Front desk marks clean-complete from UI → same result
7. Cleaning records page shows all records with correct filters
8. Deactivated API Key gets rejected on clean-complete call

- [ ] **Step 4: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: address issues found during final verification"
```
