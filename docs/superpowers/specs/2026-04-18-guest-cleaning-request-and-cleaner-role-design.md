# Guest Cleaning Request API + Cleaner Role — Design

- **Date**: 2026-04-18
- **Status**: Approved (pending implementation)
- **Related**: `2026-04-11-housekeeping-cleaning-design.md`

## Goal

Enable two related features:

1. **Guest-initiated cleaning requests**: in-room devices (tablet / button / IoT) call an API to create a "please clean my room" request. Staff and cleaners see these requests on a page and act on them.
2. **Cleaner role**: a new user role (`cleaner`) with a dedicated housekeeping page to view and act on cleaning work (pending requests + in-progress cleanings).

## Non-Goals

- Guest-side cancellation of a request.
- Scheduling / time-window requests (all requests are "clean as soon as possible").
- Multi-stage approval workflow (no supervisor sign-off).
- Rewriting the existing housekeeping flow — `mark-cleaning` and `clean-complete` remain the entry points for state transitions.
- Per-cleaner scoped data (a cleaner sees the full queue, not only their own assignments).
- Notifications / push alerts to cleaner devices.

## Core Concepts

A **`CleaningRequest`** is a distinct entity from `CleaningRecord`:

- `CleaningRequest` = intent ("a room should be cleaned"), sourced from a device. Lifecycle: `pending → fulfilled | cancelled`.
- `CleaningRecord` = the act of cleaning (has `started_at`, `completed_at`, cleaned-by metadata). Lifecycle: `started → completed` (existing).

The two are linked 1:1 when a cleaner starts cleaning: `mark-cleaning` on a room with a pending request atomically fulfills that request and creates the `CleaningRecord`, storing the link in `cleaning_requests.fulfilled_by_cleaning_record_id`.

Room status semantics are unchanged:

- Pending request → room stays `occupied`.
- `mark-cleaning` → room transitions to `cleaning` (existing).
- `clean-complete` → room transitions to `occupied` (reservation still checked in) or `available` (existing).

### Why a separate table?

- Multiple requests per room per stay are possible (re-cleaning on the same day).
- Request state (pending/fulfilled/cancelled) is orthogonal to cleaning state (started/completed).
- Existing `CleaningRecord` queries (reports, audits) are not disturbed by a "requested but not started" variant.

## Data Model Changes

### New table `cleaning_requests`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | `default=uuid.uuid4` |
| `room_id` | UUID FK → `rooms.id`, not null | |
| `api_key_id` | UUID FK → `api_keys.id`, not null | device that submitted the request |
| `notes` | text nullable | optional guest note |
| `status` | enum `pending / fulfilled / cancelled`, not null, default `pending` | |
| `requested_at` | timestamptz, not null, `server_default=func.now()` | |
| `fulfilled_at` | timestamptz nullable | set when transitioned to `fulfilled` |
| `fulfilled_by_cleaning_record_id` | UUID FK → `cleaning_records.id`, nullable | set atomically together with `fulfilled_at` |
| `cancelled_at` | timestamptz nullable | set when transitioned to `cancelled` |
| `cancelled_by_user_id` | UUID FK → `users.id`, nullable | staff/admin who cancelled |

**Indexes**:

- `UNIQUE (room_id) WHERE status = 'pending'` — DB-level guarantee that a room has at most one pending request.
- Regular index on `(status, requested_at)` for the list query.

**Invariants** (enforced in application code; DB enforces the uniqueness and FK constraints):

- `status = fulfilled` ⇒ `fulfilled_at IS NOT NULL AND fulfilled_by_cleaning_record_id IS NOT NULL`.
- `status = cancelled` ⇒ `cancelled_at IS NOT NULL AND cancelled_by_user_id IS NOT NULL`.
- `status = pending` ⇒ `fulfilled_* IS NULL AND cancelled_* IS NULL`.

### `api_keys` changes

Add column `room_id UUID FK → rooms.id, nullable`. Existing keys stay NULL; they remain valid for all other API-key-authenticated endpoints (e.g. `clean-complete`). The cleaning-request endpoint rejects requests from unbound keys.

### `users` / `UserRole` changes

Add `cleaner` to the `UserRole` enum. No schema change to the `users` table — only the enum values are extended. Migration handles the Postgres enum add.

## API Contract

All paths are prefixed with `/api/housekeeping`.

### 1. `POST /cleaning-requests` — create guest request

- **Auth**: device API key only (`X-API-Key` header).
- **Body**: `{ "notes"?: string | null }` (1–500 chars if present).
- **Behaviour**:
  1. Load the `ApiKey` from the header (existing `get_api_key` dependency).
  2. If `api_key.room_id IS NULL` → `400` "device not bound to a room".
  3. Load the room. If `room.status != occupied` → `400` "room is not occupied".
  4. Attempt to insert a `CleaningRequest` with `status=pending`. If the partial unique index rejects (a pending request already exists), SELECT and return the existing row with `200`.
  5. Otherwise commit and return the new row with `200`.

- **Idempotency**: the endpoint returns `200` in both the "newly created" and "already pending" cases (not `201`), so clients don't need to distinguish. This matches the pattern used by `clean-complete`.

- **Response**: `CleaningRequestResponse` (see schemas below).

### 2. `GET /cleaning-requests` — list requests

- **Auth**: admin / staff / cleaner.
- **Query params**:
  - `status` (optional, one of `pending / fulfilled / cancelled / all`; default `pending`).
  - `room_id` (optional UUID).
- **Response**: `list[CleaningRequestResponse]`, ordered by `requested_at DESC`.

### 3. `POST /cleaning-requests/{id}/cancel` — staff cancel

- **Auth**: admin / staff (cleaners cannot cancel).
- **Behaviour**: atomic `UPDATE ... WHERE id=<id> AND status='pending' SET status='cancelled', cancelled_at=now(), cancelled_by_user_id=current_user.id RETURNING *`. Disambiguated errors: if `SELECT` shows the id does not exist → `404`; if it exists but `status != pending` → `409 "request no longer pending"`.
- **Response**: `CleaningRequestResponse`.

### 4. Existing endpoint: `POST /rooms/{room_number}/mark-cleaning` — updated

- **Auth change**: add `cleaner` to `require_role(...)`.
- **Behaviour change**: inside the same transaction as the record insertion and room status update, atomically fulfill any pending request:

  ```
  UPDATE cleaning_requests
     SET status='fulfilled', fulfilled_at=now(), fulfilled_by_cleaning_record_id=<new_record_id>
   WHERE room_id=<room.id> AND status='pending'
  RETURNING *;
  ```

  Zero rows updated is normal (no guest request was pending — staff-initiated cleaning). One row updated is the fulfill case. The existing `mark-cleaning` contract (response shape, preconditions, idempotency) is unchanged.

### 5. Existing endpoints: auth updates only

- `POST /rooms/{room_number}/clean-complete` — add `cleaner` to allowed user roles (device path unchanged).
- `GET /rooms/cleaning-status` — add `cleaner`.
- `GET /cleaning-records` — add `cleaner`.

## Schemas (Pydantic)

```python
class CleaningRequestCreate(BaseModel):
    notes: str | None = Field(None, min_length=1, max_length=500)

class CleaningRequestStatus(str, enum.Enum):
    pending = "pending"
    fulfilled = "fulfilled"
    cancelled = "cancelled"

class CleaningRequestResponse(BaseModel):
    id: uuid.UUID
    room_id: uuid.UUID
    room_number: str  # joined for convenience on list queries
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

## Authorization Summary

| Endpoint | admin | staff | cleaner | device |
|---|:-:|:-:|:-:|:-:|
| `POST /cleaning-requests` | — | — | — | ✅ (room-bound only) |
| `GET /cleaning-requests` | ✅ | ✅ | ✅ | — |
| `POST /cleaning-requests/{id}/cancel` | ✅ | ✅ | — | — |
| `POST /rooms/{n}/mark-cleaning` | ✅ | ✅ | ✅ | — |
| `POST /rooms/{n}/clean-complete` | ✅ | ✅ | ✅ | ✅ |
| `GET /rooms/cleaning-status` | ✅ | ✅ | ✅ | ✅ (existing) |
| `GET /cleaning-records` | ✅ | ✅ | ✅ | — |

Users CRUD (`/api/users`) remains admin-only; admins create cleaner accounts by setting `role=cleaner` in the existing `UserCreate` payload.

## Race-Condition Handling

Same atomic-UPDATE-WHERE-condition pattern as the recent `clean-complete` fix:

- **Duplicate guest requests (same room, same instant)**: serialized by the partial unique index on `(room_id) WHERE status='pending'`. Losers of the race catch `IntegrityError`, then SELECT and return the existing pending row.
- **Two cleaners press "start" simultaneously**: the atomic fulfillment UPDATE (`WHERE room_id=? AND status='pending'`) matches only one request, so the link in `fulfilled_by_cleaning_record_id` is deterministic. Note that the existing `mark-cleaning` endpoint itself has a pre-existing concurrency gap — two concurrent calls on an `occupied` room can both create `CleaningRecord` rows. That is **out of scope** here and tracked separately; fixing it will use the same atomic-UPDATE pattern applied to `room.status`.
- **Request cancelled while a cleaner is starting cleaning**: the `mark-cleaning` fulfill-UPDATE matches zero rows (request already cancelled) and proceeds without linking. Behaviour is consistent: the cleaning still happens, just not linked to the cancelled request.

## Frontend

### Routing

Introduce a new `/housekeeping` route pointing to `HousekeepingView.vue`. The existing `/cleaning` route is repurposed: if `CleaningView.vue` currently holds content that fits the new two-section layout, it is refactored in place and `/housekeeping` is the canonical path with `/cleaning` aliased; otherwise a new `HousekeepingView.vue` is added and `/cleaning` redirects to `/housekeeping`. The implementation plan decides which based on current `CleaningView.vue` content.

Meta: `{ roles: ['admin', 'staff', 'cleaner'] }`. Router guard extended to read an optional `roles` array from `to.meta` and compare with `auth.user.role`; unauthorized → redirect to `/`.

### `HousekeepingView.vue`

Two stacked sections:

1. **待清潔請求** (pending requests)
   - Columns: 房號、樓層、requested_at (relative time)、notes、操作
   - Action: **啟動清潔** button → `POST /rooms/{room_number}/mark-cleaning` → auto-refreshes both sections on success
2. **進行中** (in-progress cleanings) — reuses existing `GET /rooms/cleaning-status`
   - Columns: 房號、樓層、cleaning_type、started_at (relative time)、操作
   - Action: **完成清潔** button → opens modal for `cleaned_by_name` (prefilled with `auth.user.full_name`) + optional notes → `POST /rooms/{room_number}/clean-complete`

Polling: light auto-refresh every 30s (`setInterval` inside `onMounted`, cleared in `onBeforeUnmount`).

### Navigation / landing page

- Sidebar (`App.vue`): for `cleaner` role, show only **房務清潔** (`/housekeeping`) and **登出**. Other menu items hidden via `v-if="auth.userCanSee(route)"`.
- `cleaner` user's login redirect: after successful login in `LoginView`, if `auth.user.role === 'cleaner'` push to `/housekeeping`; otherwise keep current `/` behaviour.

### API Keys admin page

Add a **綁定房間** dropdown (list of rooms) when editing / creating an `ApiKey`. Required for keys that will call the cleaning-request endpoint; optional for general device keys (e.g. staff tablets that only report `clean-complete`).

## Testing Plan

### Backend (pytest)

- **Create request**
  - device with `room_id` bound, room `occupied` → 200, row created
  - device with `room_id` NULL → 400
  - device bound to room that is `available`/`cleaning`/`maintenance` → 400
  - duplicate call (pending exists) → 200, same id returned, count stays 1
- **List requests**
  - filters by status / room_id correctly
  - cleaner role allowed; readonly denied
- **Cancel request**
  - staff cancels pending → 200, status=cancelled, audit fields set
  - cancel already-fulfilled → 409
  - cleaner attempts cancel → 403
- **mark-cleaning integration**
  - mark-cleaning with pending request → creates CleaningRecord, request fulfilled, `fulfilled_by_cleaning_record_id` correct
  - mark-cleaning without pending request → creates CleaningRecord, no request touched
  - cleaner role can call mark-cleaning
- **clean-complete**
  - cleaner role can complete
- **Role guards**
  - cleaner cannot access /users, /reservations, /guests, etc. → 403

### Frontend

- Unit: role-aware router guard rejects cleaner on admin/staff-only routes and allows them on `/housekeeping`.
- Manual smoke (no E2E harness exists in the repo today): cleaner logs in → lands on `/housekeeping` → pending requests render → 啟動清潔 → 完成清潔 round-trip.

## Migration Plan

Alembic migration `add_cleaning_requests_and_cleaner_role`:

1. `ALTER TYPE user_role ADD VALUE 'cleaner'` (non-transactional in Postgres — run in its own migration step).
2. `ALTER TABLE api_keys ADD COLUMN room_id UUID NULL REFERENCES rooms(id)`.
3. `CREATE TYPE cleaning_request_status AS ENUM ('pending', 'fulfilled', 'cancelled')`.
4. `CREATE TABLE cleaning_requests (...)` with the columns above.
5. Create the partial unique index `UNIQUE (room_id) WHERE status='pending'`.

Seed script (`app/seed.py`): add one sample cleaner user and bind one existing `ApiKey` to a room, so developers can exercise the flow immediately.

## Rollout & Backward Compatibility

- Existing devices without `room_id` binding continue to work for `clean-complete` unchanged. They will get `400` if they try the new cleaning-request endpoint — acceptable (they never called it before).
- Existing staff/admin keep full access; the only change is that `cleaner` is now a valid role.
- No data backfill required.

## Open Questions / Future Work

- Per-cleaner assignment + scoping of the queue.
- Push notifications to cleaner devices when new requests arrive.
- Guest-side cancellation (device needs a "cancel request" button).
- Analytics: average fulfillment time, per-room request frequency.
- Rate-limiting on the request endpoint (e.g. max 1 new request per room per hour after fulfillment) — currently not needed because of the pending uniqueness, but may become relevant if fulfillment is fast.
