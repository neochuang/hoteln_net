# Hotel Guest Check-in System - Design Spec

## Overview

中型旅館（30-100 房）旅客報到系統，提供完整的旅客管理、訂房、報到退房、早餐用餐管理功能。前後端分離架構，支援角色分權。

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3 + TypeScript + Vite + Pinia + Vue Router |
| Backend API | Python + FastAPI + Pydantic v2 |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 15 |
| Migration | Alembic |
| Auth | JWT (access + refresh token) |
| Testing | pytest (backend) + Vitest (frontend) |
| Containerization | Docker Compose |

## Project Structure

```
neo/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Settings (DB URL, JWT secret, etc.)
│   │   ├── database.py          # SQLAlchemy async engine/session
│   │   ├── models/              # SQLAlchemy ORM models
│   │   │   ├── user.py          # System users (staff accounts)
│   │   │   ├── guest.py         # Guests
│   │   │   ├── room.py          # Rooms & room types
│   │   │   ├── reservation.py   # Reservations
│   │   │   ├── checkin.py       # Check-in/out records
│   │   │   └── breakfast.py     # Breakfast records
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── routers/             # API routes (by module)
│   │   │   ├── auth.py
│   │   │   ├── guests.py
│   │   │   ├── rooms.py
│   │   │   ├── reservations.py
│   │   │   ├── checkins.py
│   │   │   └── breakfast.py
│   │   ├── services/            # Business logic layer
│   │   ├── dependencies.py      # FastAPI DI (auth, db session)
│   │   └── utils/               # Utility functions
│   ├── alembic/                 # DB migrations
│   ├── tests/
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── views/               # Page components
│   │   ├── components/          # Shared components
│   │   ├── stores/              # Pinia stores
│   │   ├── api/                 # API client (from OpenAPI)
│   │   ├── router/              # Vue Router
│   │   └── types/               # TypeScript types
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml           # PostgreSQL + Backend + Frontend
└── README.md
```

**Architecture**: Router → Service → Model (3-layer separation)
- Router: HTTP handling only
- Service: Business logic
- Model: Data access

## Data Models

### User (System Users / Staff)

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| username | VARCHAR(50) | unique |
| password_hash | VARCHAR(255) | bcrypt |
| full_name | VARCHAR(100) | |
| role | ENUM | admin / staff / readonly |
| is_active | BOOLEAN | default true |
| created_at | TIMESTAMP | |

### Guest

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| first_name | VARCHAR(50) | |
| last_name | VARCHAR(50) | |
| id_type | ENUM | national_id / passport / other |
| id_number | VARCHAR(50) | |
| phone | VARCHAR(20) | |
| email | VARCHAR(100) | nullable |
| nationality | VARCHAR(50) | |
| notes | TEXT | nullable |
| created_at | TIMESTAMP | |

### RoomType

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| name | VARCHAR(50) | e.g. 單人房, 雙人房, 家庭房 |
| capacity | INTEGER | max guests |
| base_price | DECIMAL(10,2) | |
| description | TEXT | nullable |

### Room

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| room_number | VARCHAR(10) | unique |
| floor | INTEGER | |
| room_type_id | UUID | FK → RoomType |
| status | ENUM | available / occupied / cleaning / maintenance |
| notes | TEXT | nullable |

### Reservation

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| guest_id | UUID | FK → Guest |
| room_type_id | UUID | FK → RoomType |
| room_id | UUID | FK → Room, nullable (assigned at check-in) |
| check_in_date | DATE | |
| check_out_date | DATE | |
| num_guests | INTEGER | |
| status | ENUM | confirmed / checked_in / checked_out / cancelled |
| includes_breakfast | BOOLEAN | |
| breakfast_guests | INTEGER | number of guests with breakfast |
| total_price | DECIMAL(10,2) | |
| notes | TEXT | nullable |
| created_by | UUID | FK → User |
| created_at | TIMESTAMP | |

### CheckInRecord

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| reservation_id | UUID | FK → Reservation, unique |
| room_id | UUID | FK → Room |
| checked_in_at | TIMESTAMP | |
| checked_in_by | UUID | FK → User |
| checked_out_at | TIMESTAMP | nullable |
| checked_out_by | UUID | FK → User, nullable |

### BreakfastRecord

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| reservation_id | UUID | FK → Reservation |
| guest_id | UUID | FK → Guest |
| date | DATE | |
| meal_time | TIMESTAMP | |
| is_extra_purchase | BOOLEAN | default false |
| extra_price | DECIMAL(10,2) | nullable |
| recorded_by | UUID | FK → User |

**Constraint**: UNIQUE(reservation_id, guest_id, date) — prevent duplicate meals per guest per day.

### Key Relationships
- Guest 1:N Reservation
- RoomType 1:N Room
- Reservation 1:1 CheckInRecord
- Reservation 1:N BreakfastRecord

## API Endpoints

### Auth
| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/login` | Login, returns JWT |
| POST | `/api/auth/refresh` | Refresh token |
| GET | `/api/auth/me` | Current user info |

### Users (admin only)
| Method | Path | Description |
|---|---|---|
| GET | `/api/users` | List users |
| POST | `/api/users` | Create user |
| PATCH | `/api/users/{id}` | Update user |

### Guests
| Method | Path | Description |
|---|---|---|
| GET | `/api/guests` | List/search guests |
| POST | `/api/guests` | Create guest |
| GET | `/api/guests/{id}` | Guest detail (with history) |
| PATCH | `/api/guests/{id}` | Update guest |

### Room Types & Rooms
| Method | Path | Description |
|---|---|---|
| GET | `/api/room-types` | List room types |
| POST | `/api/room-types` | Create room type |
| GET | `/api/rooms` | List rooms (filter by status) |
| POST | `/api/rooms` | Create room |
| PATCH | `/api/rooms/{id}` | Update room status |

### Reservations
| Method | Path | Description |
|---|---|---|
| GET | `/api/reservations` | List (filter by date/status) |
| POST | `/api/reservations` | Create reservation |
| GET | `/api/reservations/{id}` | Reservation detail |
| PATCH | `/api/reservations/{id}` | Update reservation |
| POST | `/api/reservations/{id}/cancel` | Cancel reservation |

### Check-in / Check-out
| Method | Path | Description |
|---|---|---|
| POST | `/api/reservations/{id}/check-in` | Check in (assign room, create record) |
| POST | `/api/reservations/{id}/check-out` | Check out (update room status) |

### Breakfast
| Method | Path | Description |
|---|---|---|
| POST | `/api/breakfast/record` | Record meal (punch in) |
| GET | `/api/breakfast/today` | Today's meal list |
| GET | `/api/breakfast/stats` | Meal statistics report |
| POST | `/api/breakfast/purchase` | Extra breakfast purchase |

## Authentication & Authorization

### JWT Strategy
- **Access token**: 30-minute expiry
- **Refresh token**: 7-day expiry
- Tokens stored in HTTP-only cookies or Authorization header

### Roles & Permissions
| Permission | admin | staff | readonly |
|---|---|---|---|
| User management | Y | N | N |
| Guest CRUD | Y | Y | Read only |
| Room management | Y | Y | Read only |
| Reservation CRUD | Y | Y | Read only |
| Check-in/out | Y | Y | N |
| Breakfast management | Y | Y | Read only |

## Frontend Pages

1. **Login** — authentication page
2. **Dashboard** — today's overview (check-ins, check-outs, occupancy rate, breakfast count)
3. **Guest Management** — list + search + create/edit
4. **Room Management** — room type settings + room status board (visual floor map)
5. **Reservation Management** — list + calendar view + create/edit
6. **Check-in/Check-out** — quick operation interface, search then one-click check-in
7. **Breakfast Management** — today's meal punch-in + statistics report

## Development & Deployment

### Docker Compose Services
- `db`: PostgreSQL 15
- `backend`: FastAPI (uvicorn, hot reload in dev)
- `frontend`: Vue dev server (Vite)

### Environment Variables (.env)
- `DATABASE_URL`
- `JWT_SECRET`
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS`

### Seed Data
- Default admin account
- Sample room types (single, double, family, suite)
- Sample rooms

### Testing Strategy
- **Backend**: pytest + httpx (async test client), test each service and endpoint
- **Frontend**: Vitest + Vue Test Utils for component tests

## Verification

1. `docker-compose up` starts all services
2. Access API docs at `http://localhost:8000/docs` (Swagger UI)
3. Login with seed admin account
4. Create room types and rooms
5. Create a guest and reservation
6. Perform check-in flow
7. Record breakfast meal
8. Perform check-out flow
9. Verify dashboard statistics
10. Run `pytest` for backend tests
11. Run `npm run test` for frontend tests
